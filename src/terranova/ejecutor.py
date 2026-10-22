"""Ejecutor genérico (F2.1): ficha del catálogo → conector → lista blanca → sobre `rt/1`.

Todo lo que es propio de una fuente sale del catálogo (ADR-0006, ADR-0007, ADR-0012): qué
herramienta del conector se llama y con qué argumentos, qué campos salen y con qué nombre, qué se
calcula (derivados) y qué índice de cobertura decide entre «no encontrado» y «fuera de cobertura».
Aquí solo vive la mecánica común.
"""

from __future__ import annotations

import asyncio
import math
import re
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

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
    Sobre,
    ZonaUsada,
    ahora,
    huella,
    nueva_solicitud_id,
    texto_es_limpio,
)

MAX_TEXTO_LIBRE = 200
Plan = Literal["evaluacion", "normal"]


class ErrorEntrada(Exception):
    """Entrada que no cumple su tipo: `parametro_invalido`, no se llama a la fuente."""

    def __init__(self, param: str, mensaje: str) -> None:
        super().__init__(f"{param}: {mensaje}")
        self.param = param


class ErrorEjecucion(Exception):
    """Fallo total: no hay sobre, hay un error con código estable (spec 01, §6.3)."""

    def __init__(self, codigo: str, mensaje: str, reintentar_en_s: int | None = None) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.reintentar_en_s = reintentar_en_s


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
            out[campo.nombre] = convertir(fila[clave], campo.tipo)
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
        sc = await ej.llamar("arcgis-mcp", "arcgis_query_features", argumentos)
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


class Ejecutor:
    def __init__(self, catalogo: Catalogo, conectores: dict[str, Conector]) -> None:
        self.catalogo = catalogo
        self.conectores = conectores
        self._indices: dict[str, dict[str, Any]] = {}

    def indice(self, nombre: str) -> dict[str, Any]:
        if nombre not in self._indices:
            self._indices[nombre] = cargar_cobertura(nombre)
        return self._indices[nombre]

    async def llamar(self, conector: str, tool: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        c = self.conectores.get(conector)
        if c is None:
            raise ErrorEjecucion(
                "fuente_no_disponible", f"el conector {conector} no está configurado"
            )
        try:
            return await c.llamar(tool, argumentos)
        except ErrorConector as exc:
            raise ErrorEjecucion(exc.codigo, str(exc), exc.reintentar_en_s) from exc

    async def ejecutar(
        self, herramienta: str, entrada: dict[str, Any], *, plan: Plan = "normal"
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
                    rasgos.append({"type": "Feature", "geometry": geom, "properties": fila})
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
        if any(p.completitud.total is None for p in procedencia):
            avisos.append("La fuente no dijo cuántos elementos hay: no se sabe si vino todo.")
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
            zona_usada=_zona(h, valores),
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
        sc = await self.llamar(conector, h.consulta.tool, argumentos)
        return separar(h, capa, argumentos, sc)

    def _procedencia(
        self,
        h: Herramienta,
        fuente: Fuente,
        r: Respuesta,
        consultado_en: datetime,
        mapeadas: list[dict[str, Any]],
    ) -> Procedencia:
        return Procedencia(
            fuente_id=fuente.id,
            entidad=fuente.entidad,
            acto=fuente.acto,
            url=str(r.argumentos.get("url") or fuente.url),
            licencia=licencia_de(fuente),
            atribucion=fuente.atribucion,
            servido_desde="fuente",
            consultado_en=consultado_en,
            consulta={**r.argumentos, **({"capa": r.capa} if r.capa else {})},
            completitud=completitud_de(r, h.consulta.completo_por_construccion),
            cache=Cache(acierto=False, edad_s=0),
            transformaciones=[],
            conector=fuente.conector,
            huella=huella({"elementos": mapeadas}),
        )


def _zona(h: Herramienta, v: dict[str, Any]) -> ZonaUsada | None:
    if "lon" in v and "lat" in v:
        return ZonaUsada(tipo="punto", valor=[v["lon"], v["lat"]], crs="EPSG:4326")
    for nombre, tipo in h.entrada.items():
        if tipo == "bbox":
            return ZonaUsada(tipo="bbox", valor=v[nombre], crs="EPSG:4326")
        if tipo == "divipola":
            return ZonaUsada(tipo="divipola", valor=v[nombre])
        if tipo == "codigo_predial":
            return ZonaUsada(tipo="codigo", valor=v[nombre])
    return None
