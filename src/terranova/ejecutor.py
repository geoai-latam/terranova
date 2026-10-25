"""Ejecutor genérico (F2.1): ficha del catálogo → conector → lista blanca → sobre `rt/1`.

Todo lo que es propio de una fuente sale del catálogo (ADR-0006, ADR-0007, ADR-0012): qué
herramienta del conector se llama y con qué argumentos, qué campos salen y con qué nombre, qué se
calcula (derivados) y qué índice de cobertura decide entre «no encontrado» y «fuera de cobertura».
Aquí solo vive la mecánica común.
"""

from __future__ import annotations

import asyncio
import functools
import math
import re
import time
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from terranova import metricas
from terranova.cache import RETENCION_S, Almacen
from terranova.cache import clave as clave_cache
from terranova.catalogo import (
    MARCADOR,
    PATRONES_ENTRADA,
    Catalogo,
    Derivado,
    Fuente,
    Herramienta,
    cargar_cobertura,
)
from terranova.conector import Conector, ErrorConector
from terranova.contrato import (
    MAX_TEXTO,
    Cache,
    Completitud,
    Estado,
    GeoResult,
    Licencia,
    Procedencia,
    ServidoDesde,
    Sobre,
    ZonaUsada,
    ahora,
    huella,
    nueva_solicitud_id,
    texto_es_limpio,
)
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.proteccion import Proteccion

MAX_TEXTO_LIBRE = 200
Plan = Literal["evaluacion", "normal"]


# --- entrada ---------------------------------------------------------------------------------


def validar_entrada(h: Herramienta, entrada: dict[str, Any]) -> dict[str, Any]:
    """Comprueba cada parámetro contra su tipo del catálogo y devuelve los valores normalizados."""
    if faltan := set(h.entrada) - set(entrada):
        raise ErrorEntrada(sorted(faltan)[0], "falta")
    if sobran := set(entrada) - set(h.entrada):
        raise ErrorEntrada(sorted(sobran)[0], "no es un parámetro de esta herramienta")
    return {nombre: _valor(nombre, tipo, entrada[nombre]) for nombre, tipo in h.entrada.items()}


def _valor(nombre: str, tipo: str, v: Any) -> Any:
    if tipo in ("float", "int"):
        if isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v):
            raise ErrorEntrada(nombre, f"debe ser un número ({tipo})")
        if tipo == "int" and int(v) != v:
            raise ErrorEntrada(nombre, "debe ser entero")
        if (nombre == "lon" and not -180 <= v <= 180) or (nombre == "lat" and not -90 <= v <= 90):
            raise ErrorEntrada(nombre, "fuera de rango (EPSG:4326)")
        return int(v) if tipo == "int" else float(v)
    if tipo == "bool":
        if not isinstance(v, bool):
            raise ErrorEntrada(nombre, "debe ser true o false")
        return v
    if tipo == "bbox":
        if not (isinstance(v, list) and len(v) == 4 and all(_numero(x) for x in v)):
            raise ErrorEntrada(nombre, "debe ser [lon_min, lat_min, lon_max, lat_max]")
        x0, y0, x1, y1 = (float(x) for x in v)
        if not (-180 <= x0 < x1 <= 180 and -90 <= y0 < y1 <= 90):
            raise ErrorEntrada(nombre, "rectángulo inválido en EPSG:4326 (lon, lat; min < max)")
        return [x0, y0, x1, y1]
    if tipo == "geojson":
        if not isinstance(v, dict) or "type" not in v:
            raise ErrorEntrada(nombre, "debe ser un objeto GeoJSON")
        return v
    if not isinstance(v, str):
        raise ErrorEntrada(nombre, "debe ser texto")
    if tipo in PATRONES_ENTRADA:
        if not re.fullmatch(PATRONES_ENTRADA[tipo], v):
            raise ErrorEntrada(nombre, f"no tiene el formato de {tipo}")
        if tipo == "divipola" and not v.isdigit():
            return municipio_por_nombre(nombre, v, _municipios())
        return v
    if len(v) > MAX_TEXTO_LIBRE or not texto_es_limpio(v):
        raise ErrorEntrada(nombre, f"texto de hasta {MAX_TEXTO_LIBRE} caracteres, sin control")
    return v


def _numero(x: Any) -> bool:
    return isinstance(x, int | float) and not isinstance(x, bool) and math.isfinite(x)


def renderizar(plantilla: Any, valores: dict[str, Any]) -> Any:
    """Reemplaza `{marcador}`: si el texto es solo el marcador, el valor conserva su tipo."""
    if isinstance(plantilla, str):
        entero = MARCADOR.fullmatch(plantilla)
        if entero:
            return valores[entero.group(1)]
        return MARCADOR.sub(lambda m: str(valores[m.group(1)]), plantilla)
    if isinstance(plantilla, list):
        return [renderizar(v, valores) for v in plantilla]
    if isinstance(plantilla, dict):
        return {k: renderizar(v, valores) for k, v in plantilla.items()}
    return plantilla


# --- salida ----------------------------------------------------------------------------------

_BIDI_Y_CONTROL = re.compile(
    "[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]"
)


def sanear(texto: str) -> str:
    """Texto de la fuente sin control ni bidi y con el largo máximo de `rt/1` (regla 9)."""
    limpio = _BIDI_Y_CONTROL.sub("", unicodedata.normalize("NFC", texto))
    return limpio if len(limpio) <= MAX_TEXTO else limpio[: MAX_TEXTO - 1] + "…"


_AÑO = re.compile(r"^(\d{4})")


def convertir(valor: Any, tipo: str) -> Any:
    """Al tipo del catálogo. Lo que no se puede convertir sale como `None`, nunca inventado."""
    if valor is None:
        return None
    try:
        if tipo == "int":
            return int(float(valor))
        if tipo == "float":
            return float(valor)
        if tipo == "bool":
            return (
                valor
                if isinstance(valor, bool)
                else str(valor).strip().lower() in ("true", "1", "si", "sí")
            )
        if tipo == "date":
            return _fecha(valor)[:10]
        if tipo == "datetime":
            return _fecha(valor)
    except (TypeError, ValueError):
        return None
    if isinstance(valor, dict) and "url" in valor:  # Socrata da las URL como {url: …}
        valor = valor["url"]
    return sanear(valor if isinstance(valor, str) else str(valor))


def _fecha(valor: Any) -> str:
    if isinstance(valor, int | float) and not isinstance(valor, bool):  # epoch ms de ArcGIS
        from datetime import UTC

        return datetime.fromtimestamp(valor / 1000, UTC).isoformat()
    return sanear(str(valor))


@dataclass
class Respuesta:
    """Lo que devolvió una llamada al conector, ya separado en filas y hechos."""

    capa: str | None
    argumentos: dict[str, Any]
    filas: list[dict[str, Any]]
    geometrias: list[Any]
    hechos: dict[str, Any]
    crs: str | None = None


def separar(
    h: Herramienta, capa: str | None, argumentos: dict[str, Any], sc: dict[str, Any]
) -> Respuesta:
    hechos = (
        sc.get("facts") if isinstance(sc.get("facts"), dict) else ({} if "geo_result" in sc else sc)
    )
    filas: list[dict[str, Any]] = []
    geometrias: list[Any] = []
    crs = None
    for art in sc.get("artifacts") or []:
        if art.get("kind") == "feature_collection":
            for rasgo in (art.get("data") or {}).get("features") or []:
                filas.append(rasgo.get("properties") or {})
                geometrias.append(rasgo.get("geometry"))
            crs = art.get("crs")
            break
        if art.get("kind") == "table":
            filas = list(art.get("rows") or [])
            break
    if not filas and h.consulta.filas_en:
        actual: Any = sc
        for parte in h.consulta.filas_en.split("."):
            actual = actual.get(parte) if isinstance(actual, dict) else None
        filas = [f for f in actual or [] if isinstance(f, dict)]
    if len(geometrias) != len(filas):
        geometrias = [None] * len(filas)
    return Respuesta(capa, argumentos, filas, geometrias, hechos or {}, crs)


def mapear_fila(
    h: Herramienta, fuente: Fuente, fila: dict[str, Any], capa: str | None
) -> dict[str, Any]:
    """La fila con SOLO la lista blanca (regla 10), renombrada y con los derivados por elemento."""
    out: dict[str, Any] = {}
    for clave, campo in fuente.campos.items():
        if campo.origen == "fila" and clave in fila:
            valor = fila[clave]
            if campo.coma_decimal and isinstance(valor, str):
                valor = valor.replace(",", ".")
            out[campo.nombre] = convertir(valor, campo.tipo)
    for nombre, d in h.derivados.items():
        if not d.por_elemento:
            continue
        if d.de == "capa":
            out[nombre] = (d.valores or {}).get(str(capa))
        elif d.de == "prefijo":
            base = out.get(d.campo or "")
            out[nombre] = str(base)[: d.n] if base else None
        elif d.de == "columna":
            out[nombre] = convertir(fila.get(d.campo or ""), d.tipo)
    return out


def derivar_resultado(d: Derivado, elementos: list[dict[str, Any]], total: int | None) -> Any:
    valores = [e.get(d.campo or "") for e in elementos]
    numeros = [float(v) for v in valores if v is not None and _numero(v)]
    if d.de == "conteo":
        return len(elementos)
    if d.de == "suma":
        return convertir(round(sum(numeros), 6), d.tipo) if numeros else None
    if d.de == "maximo":
        return convertir(max(numeros), d.tipo) if numeros else None
    if d.de == "primero":
        return convertir(valores[0], d.tipo) if valores else None
    if d.de == "completitud_total":
        return total
    raise ValueError(d.de)


def completitud_de(r: Respuesta, por_construccion: bool) -> Completitud:
    c = r.hechos.get("completitud")
    if isinstance(c, dict) and isinstance(c.get("vistos"), int):
        total = c.get("total") if isinstance(c.get("total"), int) else None
        return Completitud(
            vistos=c["vistos"],
            total=total,
            truncado=bool(c.get("truncado")) if total is None else c["vistos"] < total,
        )
    vistos = len(r.filas)
    total = r.hechos.get("total_en_servicio")
    if por_construccion:
        return Completitud(vistos=vistos, total=vistos, truncado=False)
    if isinstance(total, int) and total >= vistos:
        return Completitud(vistos=vistos, total=total, truncado=vistos < total)
    return Completitud(vistos=vistos, total=None, truncado=False)


def licencia_de(fuente: Fuente) -> Licencia:
    return Licencia(
        spdx=fuente.licencia.spdx or "LicenseRef-por-verificar",
        url=fuente.licencia.url,
        uso_comercial=fuente.uso_comercial,
    )


# --- cobertura -------------------------------------------------------------------------------

Cobertura = Callable[["Ejecutor", Herramienta, dict[str, Any], datetime], Awaitable["Veredicto"]]


@dataclass
class Veredicto:
    fuera: bool
    aviso: str | None = None
    procedencia: list[Procedencia] = field(default_factory=list)


async def cobertura_catastral(
    ej: Ejecutor, h: Herramienta, entrada: dict[str, Any], consultado_en: datetime
) -> Veredicto:
    """¿El municipio está en la base catastral pública del IGAC? (F1.5, medido por sectores)."""
    municipios: dict[str, Any] = ej.indice("cobertura_catastral")["municipios"]
    procedencia: list[Procedencia] = []
    divipola = next(
        (str(v)[:5] for k, v in entrada.items() if h.entrada[k] == "codigo_predial"), None
    )
    if divipola is None and "lon" in entrada and "lat" in entrada:
        argumentos = {
            "url": CAPA_GESTORES,
            "bbox": [entrada["lon"], entrada["lat"], entrada["lon"], entrada["lat"]],
            "out_fields": ["divipola"],
            "max_features": 1,
        }
        sc = await ej.llamar(
            "arcgis-mcp", "arcgis_query_features", argumentos, fuente_id="igac.catastro.gestores"
        )
        rasgos = ((sc.get("artifacts") or [{}])[0].get("data") or {}).get("features") or []
        divipola = str(rasgos[0]["properties"].get("divipola") or "") if rasgos else None
        procedencia.append(
            Procedencia(
                fuente_id="igac.catastro.gestores",
                entidad="Instituto Geográfico Agustín Codazzi (IGAC)",
                url=CAPA_GESTORES,
                licencia=Licencia(spdx="LicenseRef-por-verificar", uso_comercial="por_verificar"),
                atribucion="Fuente: IGAC, Gestores catastrales",
                servido_desde="fuente",
                consultado_en=consultado_en,
                consulta=argumentos,
                completitud=Completitud(vistos=len(rasgos), total=len(rasgos), truncado=False),
                cache=Cache(acierto=False, edad_s=0),
                transformaciones=[],
                conector="arcgis-mcp",
                huella=huella({}),
            )
        )
    m = municipios.get(divipola or "")
    if m is None:
        return Veredicto(False, None, procedencia)
    if m["rural"] or m["urbano"]:
        return Veredicto(False, None, procedencia)
    nombre = m["municipio"] or divipola
    if m["gestor"] == "IGAC":
        aviso = (
            f"{nombre} ({divipola}) figura con gestor IGAC, pero la base pública no trae sus datos."
        )
    else:
        gestor = m["gestor"]
        aviso = f"{nombre} ({divipola}) lo gestiona {gestor}; la base del IGAC no lo cubre."
    return Veredicto(True, aviso, procedencia)


CAPA_GESTORES = (
    "https://mapas.igac.gov.co/server/rest/services/catastro/Gestores_Catastrales/MapServer/1"
)
COBERTURAS: dict[str, Cobertura] = {"cobertura_catastral": cobertura_catastral}


# --- ejecutor --------------------------------------------------------------------------------


Frescura = Literal["normal", "estricta"]
CODIGOS_DE_CAIDA = frozenset({"fuente_no_disponible", "fuente_lenta"})


class Ejecutor:
    def __init__(
        self,
        catalogo: Catalogo,
        conectores: dict[str, Conector],
        almacen: Almacen | None = None,
        reloj: Callable[[], float] = time.time,
        proteccion: Proteccion | None = None,
    ) -> None:
        self.catalogo = catalogo
        self.conectores = conectores
        self.almacen = almacen
        self.proteccion = proteccion
        self.reloj = reloj
        self._indices: dict[str, dict[str, Any]] = {}

    def _anio_fuera(self, fuente: Fuente, valores: dict[str, Any]) -> str | None:
        """Un año pedido fuera de los que cubre la fuente (spec 08: mínimo y máximo cosechados de
        su columna de tiempo). Solo se usa si la consulta volvió vacía: un año publicado después de
        la cosecha trae datos y no pasa por aquí. Sin esto, «¿homicidios en Chía en 2030?» volvía
        `no_encontrado` y un agente lo dio como «0 homicidios» (GEO Copilot, fiabilidad)."""
        anio = valores.get("anio")
        columna = fuente.cobertura.columna_tiempo
        metadatos = self.catalogo.metadatos.get(fuente.id)
        campo = metadatos.campos.get(columna) if metadatos and columna else None
        if not isinstance(anio, int) or not campo or not campo.minimo or not campo.maximo:
            return None
        desde, hasta = (
            int(m[1]) if (m := _AÑO.match(v)) else None for v in (campo.minimo, campo.maximo)
        )
        if desde is None or hasta is None or desde <= anio <= hasta:
            return None
        return (
            f"La fuente cubre de {desde} a {hasta}: {anio} está fuera de su cobertura (no es que "
            "haya cero casos)."
        )

    def indice(self, nombre: str) -> dict[str, Any]:
        if nombre not in self._indices:
            self._indices[nombre] = cargar_cobertura(nombre)
        return self._indices[nombre]

    async def llamar(
        self, conector: str, tool: str, argumentos: dict[str, Any], *, fuente_id: str | None = None
    ) -> dict[str, Any]:
        c = self.conectores.get(conector)
        if c is None:
            raise ErrorEjecucion(
                "fuente_no_disponible", f"el conector {conector} no está configurado"
            )

        async def una() -> dict[str, Any]:
            inicio = time.monotonic()
            try:
                return await c.llamar(tool, argumentos)
            except ErrorConector as exc:
                raise ErrorEjecucion(exc.codigo, str(exc), exc.reintentar_en_s) from exc
            finally:
                metricas.FUENTE_LATENCIA.labels(fuente_id or conector).observe(
                    time.monotonic() - inicio
                )

        if self.proteccion is None:
            return await una()
        return await self.proteccion.llamar(fuente_id or conector, una)

    async def ejecutar(
        self,
        herramienta: str,
        entrada: dict[str, Any],
        *,
        plan: Plan = "normal",
        frescura: Frescura = "normal",
    ) -> Sobre:
        h = self.catalogo.herramientas.get(herramienta)
        if h is None:
            raise ErrorEjecucion("no_existe", f"no hay herramienta {herramienta}")
        fuente = self.catalogo.fuentes[h.fuente]
        # ADR-0007: sin licencia verificada, la fuente solo responde a llaves de evaluación
        if fuente.uso_comercial == "por_verificar" and plan != "evaluacion":
            raise ErrorEjecucion(
                "licencia_no_habilitada",
                f"{fuente.id}: licencia por verificar; solo responde a llaves de evaluación",
            )
        valores = validar_entrada(h, entrada)

        # ADR-0008: caché por frescura de la fuente; con la fuente caída, la copia vieja sale como
        # «obsoleto» y lo dice. `frescura=estricta` nunca usa caché.
        k = clave_cache(h.id, h.version, valores)
        guardado = None
        if self.almacen is not None and frescura == "normal":
            guardado = await self.almacen.leer(k)
            if guardado and self.reloj() - guardado["guardado_en"] <= fuente.frescura.ttl_cache_s:
                metricas.CACHE_ACIERTOS.inc()
                return _con_homonimos(self._desde_cache(guardado, "cache"), h, valores)
        try:
            sobre = await self._desde_fuente(h, fuente, valores)
        except ErrorEjecucion as exc:
            if guardado and exc.codigo in CODIGOS_DE_CAIDA:
                return _con_homonimos(
                    self._desde_cache(guardado, "obsoleto", exc.codigo), h, valores
                )
            raise
        if self.almacen is not None and sobre.estado != "parcial":
            await self.almacen.guardar(
                k,
                {"guardado_en": self.reloj(), "sobre": sobre.model_dump(mode="json")},
                RETENCION_S,
            )
        return _con_homonimos(sobre, h, valores)

    def _desde_cache(
        self, guardado: dict[str, Any], modo: Literal["cache", "obsoleto"], causa: str | None = None
    ) -> Sobre:
        crudo = guardado["sobre"]
        edad = max(0, int(self.reloj() - guardado["guardado_en"]))
        for p in crudo["procedencia"]:
            p["servido_desde"] = modo  # `consultado_en` queda el original (regla 6)
            p["cache"] = {"acierto": True, "edad_s": edad}
        avisos = list(crudo["avisos"])
        if modo == "obsoleto":
            fecha = crudo["procedencia"][0]["consultado_en"]
            avisos.append(
                f"La fuente no respondió ({causa}): este dato es del {fecha}, no es actual."
            )
        # ADR-0010: lo que sale de caché no descuenta
        return Sobre.model_validate(
            {**crudo, "solicitud_id": nueva_solicitud_id(), "avisos": avisos, "creditos": 0}
        )

    async def _desde_fuente(self, h: Herramienta, fuente: Fuente, valores: dict[str, Any]) -> Sobre:
        consultado_en = ahora()

        capas: list[str | None] = [str(c) for c in h.consulta.capas] or [None]
        llamadas = []
        for capa in capas:
            argumentos = renderizar(
                h.consulta.argumentos,
                {**valores, "url_fuente": fuente.url, "url_capa": f"{fuente.url}/{capa}"},
            )
            llamadas.append(self._una(h, fuente.conector, capa, argumentos))
        respuestas = await asyncio.gather(*llamadas)
        hechos_de_dato = [k for k, c in fuente.campos.items() if c.origen == "hecho"]
        reintentos = 0
        while reintentos < fuente.comportamiento.reintentos_si_vacio and all(
            not r.filas and not any(k in r.hechos for k in hechos_de_dato) for r in respuestas
        ):
            reintentos += 1
            respuestas = await asyncio.gather(
                *(self._una(h, fuente.conector, r.capa, r.argumentos) for r in respuestas)
            )

        elementos: list[dict[str, Any]] = []
        rasgos: list[dict[str, Any]] = []
        procedencia: list[Procedencia] = []
        hechos: dict[str, Any] = {}
        crs = "EPSG:4326"
        for r in respuestas:
            mapeadas = [mapear_fila(h, fuente, f, r.capa) for f in r.filas]
            elementos += mapeadas
            for fila, geom in zip(mapeadas, r.geometrias, strict=True):
                if geom is not None:
                    rasgos.append({"type": "Feature", "geometry": a_2d(geom), "properties": fila})
            crs = r.crs or crs
            for clave, campo in fuente.campos.items():
                if campo.origen == "hecho" and clave in r.hechos:
                    hechos[campo.nombre] = convertir(r.hechos[clave], campo.tipo)
            procedencia.append(self._procedencia(h, fuente, r, consultado_en, mapeadas))

        total = None
        if len(procedencia) == 1:
            total = procedencia[0].completitud.total
        elif all(p.completitud.total is not None for p in procedencia):
            total = sum(p.completitud.total or 0 for p in procedencia)
        agregados = {
            nombre: derivar_resultado(d, elementos, total)
            for nombre, d in h.derivados.items()
            if not d.por_elemento
        }

        hay_algo = bool(elementos) or bool(hechos)
        if h.consulta.forma == "uno":
            datos = {
                **(elementos[0] if elementos else {}),
                **hechos,
                **(agregados if hay_algo else {}),
            }
        else:
            datos = {**hechos, **(agregados if hay_algo else {})}
            if any(c.origen == "fila" for c in fuente.campos.values()):
                datos["elementos"] = elementos
        datos = {k: v for k, v in datos.items() if v is not None} if hay_algo else {}

        avisos: list[str] = []
        estado: Estado = "encontrado" if hay_algo else "no_encontrado"
        if not hay_algo and reintentos:
            avisos.append(
                f"Esta fuente a veces responde vacío sin error: se consultó {reintentos + 1} veces "
                "y en todas vino vacía."
            )
        if h.consulta.forma == "uno" and len(elementos) > 1:
            avisos.append(
                f"Hay {len(elementos)} resultados; se muestra el primero (todos van en la capa)."
            )
        if not hay_algo and fuente.cobertura.indice in COBERTURAS:
            veredicto = await COBERTURAS[fuente.cobertura.indice](self, h, valores, consultado_en)
            procedencia += veredicto.procedencia
            if veredicto.aviso:
                avisos.append(veredicto.aviso)
            if veredicto.fuera:
                estado = "fuera_de_cobertura"
        if (
            not hay_algo
            and estado == "no_encontrado"
            and (fuera := self._anio_fuera(fuente, valores))
        ):
            estado = "fuera_de_cobertura"
            avisos.append(fuera)
        if any(p.completitud.total is None for p in procedencia):
            avisos.append("La fuente no dijo cuántos elementos hay: no se sabe si vino todo.")
        if fuente.modo == "copia":
            avisos += [_aviso_de_copia(r.hechos) for r in respuestas[:1]]
        if fuente.uso_comercial == "no":
            avisos.append(
                f"Licencia no comercial ({fuente.licencia.spdx}): "
                "el uso posterior debe ser no comercial."
            )

        geo = None
        if rasgos:
            geo = GeoResult.model_validate(
                {
                    "geo_result": "1",
                    "artifacts": [
                        {
                            "kind": "feature_collection",
                            "name": fuente.titulo,
                            "crs": crs,
                            "data": {"type": "FeatureCollection", "features": rasgos},
                        }
                    ],
                    "facts": {},
                }
            )
        return Sobre(
            solicitud_id=nueva_solicitud_id(),
            herramienta=f"{h.id}@{h.version}",
            estado=estado,
            entrada=valores,
            zona_usada=_zona(h, valores, _municipios()),
            datos=datos,
            huella=huella(datos),
            geo_result=geo,
            procedencia=procedencia,
            avisos=avisos,
            errores=[],
            creditos=0 if estado == "fuera_de_cobertura" else h.creditos,
        )

    async def _una(
        self, h: Herramienta, conector: str, capa: str | None, argumentos: dict[str, Any]
    ) -> Respuesta:
        sc = await self.llamar(conector, h.consulta.tool, argumentos, fuente_id=h.fuente)
        return separar(h, capa, argumentos, sc)

    def _procedencia(
        self,
        h: Herramienta,
        fuente: Fuente,
        r: Respuesta,
        consultado_en: datetime,
        mapeadas: list[dict[str, Any]],
    ) -> Procedencia:
        servido_desde: ServidoDesde = "fuente"
        if fuente.modo == "copia":  # ADR-0024: la fecha es la de la copia, no la de la pregunta
            servido_desde = "obsoleto" if r.hechos.get("servido_desde") == "obsoleto" else "copia"
            consultado_en = _fecha_de_copia(r.hechos)
        return Procedencia(
            fuente_id=fuente.id,
            entidad=fuente.entidad,
            acto=fuente.acto,
            url=str(r.argumentos.get("url") or fuente.url),
            licencia=licencia_de(fuente),
            atribucion=fuente.atribucion,
            servido_desde=servido_desde,
            consultado_en=consultado_en,
            consulta={**r.argumentos, **({"capa": r.capa} if r.capa else {})},
            completitud=completitud_de(r, h.consulta.completo_por_construccion),
            cache=Cache(acierto=False, edad_s=0),
            transformaciones=[],
            conector=fuente.conector,
            huella=huella({"elementos": mapeadas}),
        )


def _fecha_de_copia(hechos: dict[str, Any]) -> datetime:
    """Sin la fecha de la copia no se sabe qué tan vieja es: no se responde como si fuera actual."""
    try:
        return datetime.fromisoformat(str(hechos["consultado_en"]))
    except (KeyError, ValueError) as exc:
        raise ErrorEjecucion("fuente_respuesta_invalida", "la copia no dijo de cuándo es") from exc


def _aviso_de_copia(hechos: dict[str, Any]) -> str:
    """ADR-0024: de cuándo es la copia y qué ventana cubre; vencida, se dice."""
    copia = hechos.get("copia") or {}
    fecha = str(hechos.get("consultado_en", ""))[:10]
    desde = f", con lo firmado desde {copia['ventana_desde']}" if copia.get("ventana_desde") else ""
    vencida = (
        " Está vencida: puede faltar lo más reciente."
        if hechos.get("servido_desde") == "obsoleto"
        else ""
    )
    return f"Sale de la copia de Terranova del {fecha}{desde}, no de la fuente en vivo.{vencida}"


def a_2d(geometria: Any) -> Any:
    """La geometría solo con lon y lat (regla 8 de rt/1). USGS manda la profundidad como tercera
    coordenada y GEO Copilot no pudo pintar los sismos («Geometry has Z dimension»); la
    profundidad ya va en las propiedades."""
    if not isinstance(geometria, dict):
        return geometria
    if geometria.get("type") == "GeometryCollection":
        return {**geometria, "geometries": [a_2d(g) for g in geometria.get("geometries") or []]}

    def recortar(c: Any) -> Any:
        if isinstance(c, list) and c and isinstance(c[0], int | float):
            return c[:2]
        return [recortar(x) for x in c] if isinstance(c, list) else c

    if "coordinates" not in geometria:
        return geometria
    return {**geometria, "coordinates": recortar(geometria["coordinates"])}


@functools.cache
def _municipios() -> dict[str, Any]:
    """Nombre de cada municipio para `zona_usada` (regla 11), leído una vez por proceso: el índice
    pesa 0,3 s y el ejecutor se crea en cada solicitud (Schemathesis se colgaba)."""
    municipios: dict[str, Any] = cargar_cobertura("cobertura_catastral")["municipios"]
    return municipios


def _plano(texto: str) -> str:
    sin = unicodedata.normalize("NFD", texto.casefold())
    return " ".join("".join(c for c in sin if unicodedata.category(c) != "Mn").split())


def _clave(texto: str) -> str:
    """Solo letras y espacios: «BOGOTA, D.C.» → «bogota d c»."""
    return " ".join(re.sub(r"[^a-zñ ]", " ", _plano(texto)).split())


_VACIAS = frozenset({"y", "de", "del", "la", "el", "los", "las"})


def municipio_por_nombre(param: str, texto: str, municipios: dict[str, Any]) -> str:
    """El código DIVIPOLA de un municipio dicho por su nombre («Chía», «San Andrés, Santander»).

    Un agente que ponía el código de memoria mandó 08001 (Barranquilla) por «San Andrés» (GEO
    Copilot, plan de fiabilidad F4): con el nombre, la puerta resuelve con el índice y, si hay
    varios, no elige: el error los lista con su código."""
    nombre, _, depto = texto.partition(",")
    # «Bogotá D.C.» y «Bogotá, D.C.»: «D.C.» es Distrito Capital, no un departamento aparte
    q = re.sub(r"( d ?c| distrito capital)$", "", _clave(nombre))
    qd = set(re.sub(r"^(d ?c|distrito capital)$", "", _clave(depto)).split()) - _VACIAS
    todos = [(c, m) for c, m in sorted(municipios.items()) if m.get("municipio")]
    exactos = [(c, m) for c, m in todos if _clave(m["municipio"]) == q]
    parecidos = [(c, m) for c, m in todos if _clave(m["municipio"]).startswith(q + " ")]
    # «Tumaco» es SAN ANDRES DE TUMACO: el nombre como palabras dentro del oficial, de último
    contienen = [(c, m) for c, m in todos if f" {q} " in f" {_clave(m['municipio'])} "]
    candidatos = exactos or parecidos or contienen
    if qd:
        # «San Andrés y Providencia» está en «ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y …»
        candidatos = [
            (c, m) for c, m in candidatos if qd <= set(_clave(m.get("departamento") or "").split())
        ]
    if len(candidatos) == 1:
        return candidatos[0][0]
    if not candidatos:
        raise ErrorEntrada(
            param,
            f"no hay un municipio llamado «{texto.strip()}» en el DIVIPOLA; búscalo con "
            "dane_divipola_buscar o usa su código",
        )
    vistos = {c for c, _ in candidatos}
    lista = [*candidatos, *((c, m) for c, m in exactos + parecidos if c not in vistos)]
    opciones = "; ".join(
        f"{c} {m['municipio']} ({m.get('departamento') or '?'})" for c, m in lista[:8]
    ) + (f"; y {len(lista) - 8} más" if len(lista) > 8 else "")
    raise ErrorEntrada(
        param,
        f"«{texto.strip()}» es ambiguo: {len(lista)} municipios se llaman así: {opciones}. Usa el "
        "código o «nombre, departamento»",
    )


def homonimos(codigo: str, municipios: dict[str, Any], *, tope: int = 6) -> list[str]:
    """Los otros municipios que se llaman igual que `codigo` o empiezan por su nombre («SAN
    ANDRES»: el de Santander, SAN ANDRES DE SOTAVENTO…), como «código NOMBRE (DEPTO)»."""
    nombre = (municipios.get(codigo) or {}).get("municipio")
    if not nombre:
        return []
    base = _plano(nombre)
    otros = []
    for cod, m in sorted(municipios.items()):
        otro = _plano(m.get("municipio") or "")
        if cod != codigo and (otro == base or otro.startswith(base + " ")):
            otros.append(f"{cod} {m['municipio']} ({m.get('departamento') or '?'})")
    return otros[:tope] + ([f"y {len(otros) - tope} más"] if len(otros) > tope else [])


def _aviso_de_homonimos(h: Herramienta, v: dict[str, Any]) -> str | None:
    """Con un municipio por código, el hecho de que hay otros con ese nombre. Un agente que puso de
    memoria 88001 para «San Andrés» respondía «no hay masacres» sin decir que hay cinco San Andrés
    (GEO Copilot, plan de fiabilidad F4): con el aviso, decide si pregunta o dice cuál tomó."""
    municipios = _municipios()
    for nombre, tipo in h.entrada.items():
        if tipo != "divipola" or not isinstance(v.get(nombre), str):
            continue
        if otros := homonimos(v[nombre], municipios):
            lugar = municipios[v[nombre]]
            depto = lugar.get("departamento") or "?"
            return (
                f"Se consultó {v[nombre]} = {lugar['municipio']} ({depto}). "
                f"Otros municipios con ese nombre: {'; '.join(otros)}. Si la pregunta era por "
                "otro, no se consultó."
            )
    return None


def _con_homonimos(sobre: Sobre, h: Herramienta, v: dict[str, Any]) -> Sobre:
    """El sobre con el aviso de homónimos. Se agrega al servir (de la fuente o de la caché) y no se
    guarda en la caché: sale del índice de municipios, no de la fuente."""
    aviso = _aviso_de_homonimos(h, v)
    if not aviso or aviso in sobre.avisos:
        return sobre
    return sobre.model_copy(update={"avisos": [*sobre.avisos, aviso]})


def _zona(
    h: Herramienta, v: dict[str, Any], municipios: dict[str, Any] | None = None
) -> ZonaUsada | None:
    if "lon" in v and "lat" in v:
        return ZonaUsada(tipo="punto", valor=[v["lon"], v["lat"]], crs="EPSG:4326")
    for nombre, tipo in h.entrada.items():
        if tipo == "bbox":
            return ZonaUsada(tipo="bbox", valor=v[nombre], crs="EPSG:4326")
        if tipo == "divipola":
            lugar = (municipios or {}).get(v[nombre]) or {}
            nombre_lugar = ", ".join(
                x for x in (lugar.get("municipio"), lugar.get("departamento")) if x
            )
            return ZonaUsada(tipo="divipola", valor=v[nombre], nombre=nombre_lugar or None)
        if tipo == "codigo_predial":
            return ZonaUsada(tipo="codigo", valor=v[nombre])
    return None
