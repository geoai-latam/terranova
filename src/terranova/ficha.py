"""Ficha de un lugar (F4.2, spec 03 §8.3): herramientas del catálogo en paralelo, en un sobre.

Cada parte es una herramienta del catálogo con su propia procedencia. Si una falla, la ficha sale
`parcial` con el error de esa parte (reglas 3 y 5 de `rt/1`) y las demás completas; lo que no llega
dentro del tope total es `fuente_lenta`. Una parte que no se consultó (licencia por verificar para
el plan, scope ausente, predio no encontrado) no es un error: sale en `avisos` y no está en
`procedencia`. Créditos: la suma de las partes que respondieron, con tope (ADR-0010).

Dos etapas: las partes por punto van juntas; las que necesitan el código predial o el municipio
(construcciones, población, precio de la tierra) arrancan en cuanto llega el predio.

Restricciones: con la base curada (`TERRANOVA_CURADO_URL`, F4.1) salen de una sola consulta
espacial, `servido_desde: curado`, con la procedencia de cada fuente de origen (RUNAP, ANT) y la
versión del dataset; sin ella, de RUNAP y ANT en vivo (spec 03 §8.3).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import pairwise
from typing import Any, cast

from terranova.contrato import (
    ESQUEMA_GEOMETRIA,
    GEOMETRIA,
    Artefacto,
    Cache,
    CodigoError,
    Completitud,
    ErrorParte,
    Estado,
    GeoResult,
    Procedencia,
    Sobre,
    ZonaUsada,
    ahora,
    huella,
    nueva_solicitud_id,
)
from terranova.curado import Restricciones
from terranova.ejecutor import Ejecutor, Plan, licencia_de, validar_entrada
from terranova.errores import ErrorEjecucion, ErrorEntrada

HERRAMIENTA = "ficha_lugar"
VERSION = 1
FAMILIA = "territorio"
TOPE_S = 12.0  # ADR-0023: p95 en vivo < 15 s sin depender de la agrología del IGAC
TOPE_CREDITOS = 50
PREGUNTA = "¿Qué hay en este lugar: predio, restricciones, suelo, cobertura y sismos?"
DESCRIPCION = (
    "Ficha de un lugar de Colombia por punto (lon, lat) o por número predial: predio (de la "
    "copia del SINIC en los municipios con gestor catastral propio; del IGAC en los demás) y "
    "construcciones (IGAC), vereda, áreas protegidas (RUNAP), resguardos y zonas de reserva "
    "campesina (ANT), vocación, capacidad y conflictos de uso del suelo (IGAC), cobertura (ESA "
    "WorldCover), sismos M≥3 del último año a ~55 km (USGS), población (DANE) y precio de la "
    "tierra rural (UPRA). Partes en paralelo, cada una con su procedencia y licencia; si una "
    "falla, la ficha sale «parcial» con el error de esa parte. Tope de 12 s. Es el resumen de "
    "todo un lugar: si la pregunta es por una sola capa o por una zona (áreas protegidas en un "
    "rectángulo, el resguardo, la cobertura, los sismos de una región), use la herramienta de esa "
    "capa."
)
Punto = tuple[float, float]
_EN_SEGUNDO_PLANO: set[asyncio.Future[Any]] = set()


def _seguir_en_segundo_plano(tarea: asyncio.Future[Any]) -> None:
    """Guarda la referencia hasta que termine (si no, el recolector puede llevársela) y recoge su
    error para que no quede «never retrieved»."""
    _EN_SEGUNDO_PLANO.add(tarea)

    def fin(t: asyncio.Future[Any]) -> None:
        _EN_SEGUNDO_PLANO.discard(t)
        if not t.cancelled():
            t.exception()

    tarea.add_done_callback(fin)


@dataclass(frozen=True)
class Parte:
    nombre: str
    herramienta: str
    # punto, día → entrada; o datos del predio → entrada (None si el predio no la trae)
    entrada: Callable[..., dict[str, Any] | None]
    del_predio: bool = False


def _punto(p: Punto, _: date) -> dict[str, Any]:
    return {"lon": p[0], "lat": p[1]}


def _sismos(p: Punto, hoy: date) -> dict[str, Any]:
    # M ≥ 3 en ±0,5° (~55 km) durante el último año
    lon, lat = p
    return {
        "bbox": [round(c, 4) for c in (lon - 0.5, lat - 0.5, lon + 0.5, lat + 0.5)],
        "desde": (hoy - timedelta(days=365)).isoformat(),
        "hasta": hoy.isoformat(),
        "magnitud_min": 3.0,
    }


def _codigo(predio: dict[str, Any]) -> dict[str, Any] | None:
    c = predio.get("codigo_predial")
    return {"codigo": c} if c else None


def _municipio(predio: dict[str, Any]) -> dict[str, Any] | None:
    m = predio.get("municipio_divipola")
    return {"municipio_divipola": m} if m else None


PREDIO_EN_PUNTO = Parte("predio", "igac_predio_en_punto", _punto)
# La copia del SINIC (milisegundos) cubre los 333 municipios con gestor catastral propio; si el
# punto cae en ella, la ficha no espera al IGAC en vivo (que llegó a tardar 38 s, auditoría del
# 2026-10-31). Si no, el predio sale del IGAC como siempre.
PREDIO_SINIC = Parte("predio", "sinic_predio_en_punto", _punto)
FUENTE_SINIC = "igac.sinic_terreno"
PARTES_PUNTO = (
    Parte("vereda", "igac_vereda_en_punto", _punto),
    Parte("areas_protegidas", "pnn_areas_protegidas_en_punto", _punto),
    Parte("resguardos", "ant_resguardos_en_punto", _punto),
    Parte("reservas_campesinas", "ant_zonas_reserva_campesina_en_punto", _punto),
    Parte("vocacion_uso", "igac_vocacion_uso_en_punto", _punto),
    Parte("capacidad_uso", "igac_capacidad_uso_en_punto", _punto),
    Parte("conflictos_uso", "igac_conflictos_uso_en_punto", _punto),
    Parte("cobertura_suelo", "esa_cobertura_suelo_en_punto", _punto),
    Parte("sismos_cercanos", "usgs_sismos_en_zona", _sismos),
)
PARTES_PREDIO = (
    Parte("construcciones", "igac_construcciones_en_predio", _codigo, del_predio=True),
    Parte("poblacion_municipio", "dane_poblacion_municipio", _municipio, del_predio=True),
    Parte("precio_tierra", "upra_precio_tierra_rural_municipio", _municipio, del_predio=True),
)
# restricciones: las tres partes en vivo, o una sola desde el dataset curado
PARTES_RESTRICCIONES = {
    "area_protegida": "areas_protegidas",
    "resguardo_indigena": "resguardos",
    "zona_reserva_campesina": "reservas_campesinas",
}
ORIGENES_CURADO = ("pnn.runap", "ant.resguardos_indigenas", "ant.zonas_reserva_campesina")
CREDITOS_CURADO = 5
HERRAMIENTAS = frozenset(
    p.herramienta for p in (PREDIO_EN_PUNTO, PREDIO_SINIC, *PARTES_PUNTO, *PARTES_PREDIO)
) | {"igac_predio_por_codigo"}

# Punto o código, no los dos. Va en OpenAPI; en MCP no: OpenAI rechaza la lista ENTERA de
# herramientas si una trae oneOf/anyOf/allOf/not arriba (banco de agente, 2026-10-23). La regla la
# hace cumplir `ficha` (se espera {lon, lat} o {codigo}) y la descripción del esquema la dice.
ALTERNATIVAS_ENTRADA: list[Any] = [
    {"required": ["lon", "lat"], "not": {"required": ["codigo"]}},
    {"required": ["codigo"], "not": {"anyOf": [{"required": ["lon"]}, {"required": ["lat"]}]}},
]
ESQUEMA_ENTRADA: dict[str, Any] = {
    "type": "object",
    "description": "Un punto (lon y lat) o un número predial (codigo), no los dos.",
    "properties": {
        "lon": {"type": "number", "minimum": -180, "maximum": 180, "description": "Longitud"},
        "lat": {"type": "number", "minimum": -90, "maximum": 90, "description": "Latitud"},
        "codigo": {
            "type": "string",
            "pattern": r"^[0-9]{30}$",
            "description": "Número predial nacional (30 dígitos). Solo sin punto: con lon y lat,"
            " no se envía",
        },
        GEOMETRIA: ESQUEMA_GEOMETRIA,
    },
    "additionalProperties": False,
}


# --- un punto dentro del predio, sin dependencias geométricas ---------------------------------


def punto_interior(geometria: dict[str, Any]) -> Punto:
    """Un punto dentro del (multi)polígono: el centro del tramo interior más ancho sobre la
    horizontal que pasa por la mitad del polígono más grande. El centroide puede caer fuera."""
    tipo, coords = geometria.get("type"), geometria.get("coordinates") or []
    if tipo == "Point":
        return float(coords[0]), float(coords[1])
    poligonos: list[list[list[list[float]]]]
    if tipo == "Polygon":
        poligonos = [coords]
    elif tipo == "MultiPolygon":
        poligonos = list(coords)
    else:
        raise ValueError(f"geometría no soportada: {tipo}")

    def ancho_alto(pol: list[list[list[float]]]) -> float:
        xs, ys = [c[0] for c in pol[0]], [c[1] for c in pol[0]]
        return (max(xs) - min(xs)) * (max(ys) - min(ys))

    pol = max(poligonos, key=ancho_alto)
    ys = [c[1] for c in pol[0]]
    y = (min(ys) + max(ys)) / 2
    cortes: list[float] = []
    for anillo in pol:  # exterior y huecos: la regla par-impar los resuelve
        for (x1, y1), (x2, y2) in pairwise(anillo):
            if (y1 > y) != (y2 > y):
                cortes.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    cortes.sort()
    tramos = [(cortes[i], cortes[i + 1]) for i in range(0, len(cortes) - 1, 2)]
    if not tramos:
        x0 = pol[0][0]
        return float(x0[0]), float(x0[1])
    a, b = max(tramos, key=lambda t: t[1] - t[0])
    return round((a + b) / 2, 7), round(y, 7)


# --- la ficha -----------------------------------------------------------------------------------


@dataclass
class _Acumulado:
    datos: dict[str, Any]
    procedencia: list[Procedencia]
    errores: list[ErrorParte]
    artefactos: list[Artefacto]
    avisos: list[str]
    creditos: int = 0


def _procedencia_fallida(ej: Ejecutor, parte: Parte, consultado_en: datetime) -> Procedencia:
    """Regla 3: la fuente consultada aparece en procedencia aunque haya fallado."""
    fuente_id = ej.catalogo.herramientas[parte.herramienta].fuente
    return _procedencia_vacia(ej, fuente_id, consultado_en, {"herramienta": parte.herramienta})


def _procedencia_vacia(
    ej: Ejecutor, fuente_id: str, consultado_en: datetime, consulta: dict[str, Any]
) -> Procedencia:
    fuente = ej.catalogo.fuentes[fuente_id]
    return Procedencia(
        fuente_id=fuente.id,
        entidad=fuente.entidad,
        acto=fuente.acto,
        url=fuente.url,
        licencia=licencia_de(fuente),
        atribucion=fuente.atribucion,
        servido_desde="fuente",
        consultado_en=consultado_en,
        consulta=consulta,
        completitud=Completitud(vistos=0, total=0, truncado=False),
        cache=Cache(acierto=False, edad_s=0),
        transformaciones=[],
        conector=fuente.conector,
        huella=huella({}),
    )


def _sumar(
    ej: Ejecutor, acc: _Acumulado, parte: Parte, r: Sobre | ErrorEjecucion, consultado_en: datetime
) -> None:
    if isinstance(r, ErrorEjecucion):
        fuente_id = ej.catalogo.herramientas[parte.herramienta].fuente
        acc.errores.append(
            ErrorParte(
                codigo=cast(CodigoError, r.codigo),
                fuente_id=fuente_id,
                detalle=f"{parte.nombre}: {r}"[:300],
                reintentar_en_s=r.reintentar_en_s,
            )
        )
        acc.procedencia.append(_procedencia_fallida(ej, parte, consultado_en))
        acc.avisos.append(f"La parte «{parte.nombre}» no respondió ({r.codigo}).")
        return
    acc.datos[parte.nombre] = {"estado": r.estado, **r.datos}
    acc.procedencia += r.procedencia
    acc.errores += r.errores
    acc.avisos += [f"{parte.nombre}: {a}" for a in r.avisos]
    acc.creditos += r.creditos
    if r.geo_result:
        acc.artefactos += [
            Artefacto.model_validate({**a.model_dump(mode="json"), "name": parte.nombre})
            for a in r.geo_result.artifacts
        ]


async def _restricciones_curadas(
    ej: Ejecutor,
    curado: Restricciones,
    punto: Punto,
    consultado_en: datetime,
    resta_s: float,
    acc: _Acumulado,
) -> bool:
    """False si no hay dataset cargado (`no_existe`): entonces las restricciones van en vivo."""
    consulta = {"dataset": "restricciones", "punto": list(punto)}
    try:
        c = await asyncio.wait_for(curado.en_punto(*punto), resta_s)
    except ErrorEjecucion as exc:
        if exc.codigo == "no_existe":
            return False
        _fallo_curado(ej, exc.codigo, str(exc), exc.reintentar_en_s, consulta, consultado_en, acc)
        return True
    except TimeoutError:
        detalle = f"no llegó en {resta_s:.0f} s"
        _fallo_curado(ej, "fuente_lenta", detalle, None, consulta, consultado_en, acc)
        return True
    m = c.manifiesto
    datos: dict[str, Any] = {
        "estado": "encontrado" if c.filas else "no_encontrado",
        "version_dataset": m["version"],
    }
    for tipo, parte in PARTES_RESTRICCIONES.items():
        datos[parte] = [
            {k: f[k] for k in ("id", "nombre", "categoria", "acto", "fecha", "url") if f.get(k)}
            for f in c.filas
            if f["tipo"] == tipo
        ]
    acc.datos["restricciones"] = datos
    for o in m.get("origenes", []):
        fuente = ej.catalogo.fuentes.get(o["fuente_id"])
        if fuente is None:
            continue
        propias = [f for f in c.filas if f["fuente_id"] == o["fuente_id"]]
        acc.procedencia.append(
            Procedencia(
                fuente_id=fuente.id,
                entidad=fuente.entidad,
                acto=fuente.acto,
                url=o.get("url") or fuente.url,
                licencia=licencia_de(fuente),
                atribucion=fuente.atribucion,
                servido_desde="curado",
                consultado_en=consultado_en,
                version_dataset=m["version"],
                consulta=consulta,
                completitud=Completitud(vistos=len(propias), total=len(propias), truncado=False),
                cache=Cache(acierto=False, edad_s=0),
                transformaciones=["F4.1: make_valid, precisión 1e-7, normalize"],
                conector="postgis",
                huella=huella({"elementos": propias}),
            )
        )
    excluidas = "; ".join(m.get("excluidas", [])) or "nada"
    acc.avisos.append(
        f"restricciones: dataset curado {m['version']} (generado {str(m.get('generado'))[:10]}); "
        f"fuera: {excluidas}."
    )
    acc.creditos += CREDITOS_CURADO
    return True


def _fallo_curado(
    ej: Ejecutor,
    codigo: str,
    detalle: str,
    reintentar_en_s: int | None,
    consulta: dict[str, Any],
    consultado_en: datetime,
    acc: _Acumulado,
) -> None:
    """La base curada no respondió: error y procedencia por cada fuente de origen (regla 3)."""
    for fuente_id in ORIGENES_CURADO:
        acc.errores.append(
            ErrorParte(
                codigo=cast(CodigoError, codigo),
                fuente_id=fuente_id,
                detalle=f"restricciones (curado): {detalle}"[:300],
                reintentar_en_s=reintentar_en_s,
            )
        )
        acc.procedencia.append(_procedencia_vacia(ej, fuente_id, consultado_en, consulta))
    acc.avisos.append(f"La parte «restricciones» no respondió ({codigo}).")


async def ficha(
    ej: Ejecutor,
    entrada: dict[str, Any],
    *,
    plan: Plan = "normal",
    puede: Callable[[str], bool] = lambda _familia: True,
    hoy: date | None = None,
    tope_s: float = TOPE_S,
    curado: Restricciones | None = None,
) -> Sobre:
    """`entrada`: `{lon, lat}` o `{codigo}` (número predial nacional)."""
    hoy = hoy or date.today()
    consultado_en = ahora()
    limite = time.monotonic() + tope_s
    acc = _Acumulado({}, [], [], [], [])

    def omitir(parte: Parte) -> str | None:
        h = ej.catalogo.herramientas[parte.herramienta]
        if not puede(h.familia):
            return f"la llave no tiene el scope «{h.familia}»"
        if ej.catalogo.fuentes[h.fuente].uso_comercial == "por_verificar" and plan != "evaluacion":
            return "licencia de la fuente por verificar"
        return None

    async def una(parte: Parte, e: dict[str, Any]) -> tuple[Parte, Sobre | ErrorEjecucion]:
        try:
            resta = max(0.1, limite - time.monotonic())
            tarea = asyncio.ensure_future(ej.ejecutar(parte.herramienta, e, plan=plan))
            # al vencer el tope la llamada no se cancela: termina sola y deja su resultado en la
            # caché, así la ficha siguiente sí lo trae (una fuente con arranque en frío no queda
            # lenta para siempre). Su propio límite lo pone el conector.
            _seguir_en_segundo_plano(tarea)
            sobre = await asyncio.wait_for(asyncio.shield(tarea), resta)
            return parte, sobre
        except TimeoutError:
            return parte, ErrorEjecucion("fuente_lenta", f"no llegó en el tope de {tope_s:.0f} s")
        except ErrorEjecucion as exc:
            return parte, exc
        except ErrorEntrada as exc:  # la entrada derivada del predio no pasó: no es de quien llama
            return parte, ErrorEjecucion("fuente_respuesta_invalida", str(exc))

    if set(entrada) == {"codigo"}:
        codigo = validar_entrada(ej.catalogo.herramientas["igac_predio_por_codigo"], entrada)[
            "codigo"
        ]
        zona = ZonaUsada(tipo="codigo", valor=codigo)
        predio_parte = Parte("predio", "igac_predio_por_codigo", lambda *_: {"codigo": codigo})
        _, predio = await una(predio_parte, {"codigo": codigo})
        _sumar(ej, acc, predio_parte, predio, consultado_en)
        if isinstance(predio, ErrorEjecucion):
            raise ErrorEjecucion(predio.codigo, f"predio: {predio}", predio.reintentar_en_s)
        if predio.estado != "encontrado":
            # sin predio no hay lugar: la ficha dice lo mismo que el predio (no_encontrado o
            # fuera_de_cobertura, que no descuenta)
            return _sobre(entrada, zona, acc, predio.estado)
        rasgos = predio.geo_result.artifacts[0].data["features"] if predio.geo_result else []
        if not rasgos:
            raise ErrorEjecucion("fuente_respuesta_invalida", "el predio llegó sin geometría")
        punto = punto_interior(rasgos[0]["geometry"])
        tarea_predio = None
    elif set(entrada) == {"lon", "lat"}:
        if not all(
            isinstance(entrada[k], int | float) and not isinstance(entrada[k], bool)
            for k in ("lon", "lat")
        ):
            raise ErrorEntrada("lon", "lon y lat deben ser números")
        punto = (float(entrada["lon"]), float(entrada["lat"]))
        if not (-180 <= punto[0] <= 180 and -90 <= punto[1] <= 90):
            raise ErrorEntrada("lon", "fuera de rango (EPSG:4326)")
        zona = ZonaUsada(tipo="punto", valor=list(punto), crs="EPSG:4326")
        predio = None

        async def predio_en_punto() -> tuple[Parte, Sobre | ErrorEjecucion]:
            if omitir(PREDIO_SINIC) is None:
                parte, sinic = await una(PREDIO_SINIC, _punto(punto, hoy))
                if isinstance(sinic, Sobre) and sinic.estado == "encontrado":
                    return parte, sinic
                # consultada sin resultado o caída: queda en la procedencia (regla 3), sin cobrarla
                # ni volver parcial la ficha, porque el predio sigue con el IGAC
                if isinstance(sinic, Sobre):
                    acc.procedencia += sinic.procedencia
                else:
                    acc.procedencia.append(_procedencia_fallida(ej, parte, consultado_en))
            return await una(PREDIO_EN_PUNTO, _punto(punto, hoy))

        tarea_predio = asyncio.ensure_future(predio_en_punto())
    else:
        # el banco de escala vio al agente rellenar `codigo` con ceros junto al punto, seis veces
        # seguidas: el error dice qué quitar
        raise ErrorEntrada(
            "entrada", "envíe solo {lon, lat} o solo {codigo}, no los dos (sin codigo si hay punto)"
        )

    async def segunda_etapa() -> list[tuple[Parte, Sobre | ErrorEjecucion]]:
        nonlocal predio
        if tarea_predio is not None:
            parte, predio = await tarea_predio
            _sumar(ej, acc, parte, predio, consultado_en)
        if not isinstance(predio, Sobre) or predio.estado != "encontrado":
            por_que = "el predio no respondió" if not isinstance(predio, Sobre) else predio.estado
            acc.avisos += [f"«{p.nombre}» no se consultó: {por_que}." for p in PARTES_PREDIO]
            return []
        tareas = []
        del_sinic = any(pr.fuente_id == FUENTE_SINIC for pr in predio.procedencia)
        for p in PARTES_PREDIO:
            e = p.entrada(predio.datos)
            if del_sinic and p.herramienta == "igac_construcciones_en_predio":
                # el SINIC no trae construcciones y la base del IGAC no cubre a su gestor
                acc.avisos.append(
                    f"«{p.nombre}» no se consultó: el predio sale del SINIC y la base del IGAC "
                    "no cubre a su gestor."
                )
                continue
            motivo = omitir(p) or (None if e else "falta el dato")
            if motivo or e is None:
                acc.avisos.append(f"«{p.nombre}» no se consultó: {motivo}.")
                continue
            tareas.append(una(p, e))
        return list(await asyncio.gather(*tareas))

    async def restricciones() -> None:
        if curado is None:
            return
        familia = ej.catalogo.herramientas["pnn_areas_protegidas_en_punto"].familia
        if not puede(familia):
            acc.avisos.append(f"«restricciones» no se consultó: la llave no tiene «{familia}».")
            return
        resta = max(0.1, limite - time.monotonic())
        if await _restricciones_curadas(ej, curado, punto, consultado_en, resta, acc):
            return
        # sin dataset cargado: las tres partes en vivo, como sin base curada
        acc.avisos.append("restricciones: no hay dataset curado cargado; se consultan en vivo.")
        vivas = [p for p in PARTES_PUNTO if p.nombre in curadas and not omitir(p)]
        for parte, r in await asyncio.gather(*(una(p, _punto(punto, hoy)) for p in vivas)):
            _sumar(ej, acc, parte, r, consultado_en)

    curadas = set(PARTES_RESTRICCIONES.values()) if curado is not None else set()
    primera = []
    for p in PARTES_PUNTO:
        if p.nombre in curadas:
            continue
        if motivo := omitir(p):
            acc.avisos.append(f"«{p.nombre}» no se consultó: {motivo}.")
        elif (e := p.entrada(punto, hoy)) is not None:
            primera.append(una(p, e))
    resultados, segunda, _ = await asyncio.gather(
        asyncio.gather(*primera), segunda_etapa(), restricciones()
    )
    for parte, r in [*resultados, *segunda]:
        _sumar(ej, acc, parte, r, consultado_en)

    if not acc.datos:
        raise ErrorEjecucion("fuente_no_disponible", "ninguna parte de la ficha respondió")
    return _sobre(entrada, zona, acc, "parcial" if acc.errores else "encontrado")


def _sobre(entrada: dict[str, Any], zona: ZonaUsada, acc: _Acumulado, estado: Estado) -> Sobre:
    return Sobre(
        solicitud_id=nueva_solicitud_id(),
        herramienta=f"{HERRAMIENTA}@{VERSION}",
        estado=estado,
        entrada=dict(entrada),
        zona_usada=zona,
        datos=acc.datos,
        huella=huella(acc.datos),
        geo_result=GeoResult(artifacts=acc.artefactos) if acc.artefactos else None,
        procedencia=acc.procedencia,
        avisos=acc.avisos,
        errores=acc.errores,
        creditos=0 if estado == "fuera_de_cobertura" else min(acc.creditos, TOPE_CREDITOS),
    )
