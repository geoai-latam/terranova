"""Cosecha de la ficha técnica (spec 08): lo que cada fuente publica de sí misma.

- datos.gov.co (Socrata): `/api/views/<id>.json` trae título, descripción, fechas, frecuencia y
  cobertura declaradas, y por columna su tipo, su descripción y estadísticas (nulos, mínimo,
  máximo, valores frecuentes).
- ArcGIS REST: el servicio, cada capa (geometría, CRS, extensión, campos y dominios, última
  edición) y el ítem de ArcGIS Online, si lo hay.

Las funciones `de_socrata` y `de_arcgis` solo interpretan JSON: se prueban sin red. `cosechar`
hace las pocas peticiones (una por capa más el servicio y el ítem; no es carga) y `diferencias`
dice qué cambió entre dos cosechas: es el canario de deriva.
"""

from __future__ import annotations

import json
import math
import re
import time
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from terranova.catalogo import (
    CampoDeLaFuente,
    Catalogo,
    Fuente,
    Geografia,
    Geometria,
    Metadatos,
)

PAUSA_S = 1.0
_EPOCA = datetime(1970, 1, 1, tzinfo=UTC)
USER_AGENT = "terranova-cosecha/1"
_DESCRIPCION_MAX = 1200

# Valores frecuentes: solo si caben en pocas categorías y la columna no puede traer personas.
# El repo es público (ADR-0014): un `documento_proveedor` frecuente es una cédula.
_PERSONAS = re.compile(
    r"doc|nit|ident|cedula|c_dula|nombre|proveedor|contratista|representante|direcc|telefono|"
    r"correo|email|multado|proponente|titular|rol",
    re.IGNORECASE,
)
_COBERTURA_MINIMA = 0.95
_GEOMETRIAS_ESRI: dict[str, Geometria] = {
    "esriGeometryPoint": "punto",
    "esriGeometryMultipoint": "multipunto",
    "esriGeometryPolyline": "linea",
    "esriGeometryPolygon": "poligono",
}
_GEOMETRIAS_SOCRATA: dict[str, Geometria] = {
    "point": "punto",
    "location": "punto",
    "multipoint": "multipunto",
    "line": "linea",
    "multiline": "linea",
    "polygon": "poligono",
    "multipolygon": "poligono",
}
_NUMERICOS_SOCRATA = {"number", "money", "percent", "double"}
_NUMERICOS_ESRI = {
    "esriFieldTypeInteger",
    "esriFieldTypeSmallInteger",
    "esriFieldTypeDouble",
    "esriFieldTypeSingle",
    "esriFieldTypeBigInteger",
}
_CORTE = re.compile(r"(?:a\s+)?corte\s+(?:de|del|al)\s+([^.<\n]{4,60})", re.IGNORECASE)
_ETIQUETAS_HTML = re.compile(r"<[^>]+>")


def _fecha(segundos: float | int | None) -> date | None:
    if segundos is None:
        return None
    # sin `fromtimestamp`: en Windows falla antes de 1970, y hay zonas del IGAC de 1899
    return (_EPOCA + timedelta(seconds=float(segundos))).date()


def _texto(html: str | None) -> str | None:
    """Texto plano y corto de una descripción que puede venir en HTML."""
    if not html:
        return None
    limpio = " ".join(_ETIQUETAS_HTML.sub(" ", html).replace("&nbsp;", " ").split())
    if not limpio:
        return None
    return limpio if len(limpio) <= _DESCRIPCION_MAX else limpio[: _DESCRIPCION_MAX - 1] + "…"


def _corte(*textos: str | None) -> str | None:
    for t in textos:
        if t and (m := _CORTE.search(_texto(t) or "")):
            return m.group(1).strip()
    return None


def _valores_frecuentes(columna: str, contenido: dict[str, Any]) -> dict[str, int] | None:
    top = contenido.get("top") or []
    no_nulos = int(contenido.get("non_null") or 0)
    if not top or not no_nulos or _PERSONAS.search(columna):
        return None
    valores = {str(t["item"]): int(t["count"]) for t in top if "item" in t}
    if sum(valores.values()) / no_nulos < _COBERTURA_MINIMA:
        return None  # no es una categoría: los frecuentes no describen la columna
    return valores


# En texto libre, el mínimo o el máximo puede ser cualquier cosa: en el PAA de SECOP I, el máximo de
# `ppto_total` es el nombre, el teléfono y el correo de una alcaldesa. Solo se guarda si parece un
# código (corto y sin espacios), nunca una frase.
_CODIGO = re.compile(r"^[\w./:+-]{1,24}$")


def _extremo(valor: object, numerica: bool) -> str | None:
    if valor is None:
        return None
    texto = str(valor)
    return texto if numerica or _CODIGO.match(texto) else None


def de_socrata(fuente: Fuente, vista: dict[str, Any], hoy: date) -> Metadatos:
    """La ficha técnica desde `/api/views/<id>.json` de datos.gov.co."""
    campos: dict[str, CampoDeLaFuente] = {}
    geometria: Geometria | None = None
    for col in vista.get("columns") or []:
        nombre = col.get("fieldName")
        tipo = str(col.get("dataTypeName") or "")
        if tipo in _GEOMETRIAS_SOCRATA:
            geometria = geometria or _GEOMETRIAS_SOCRATA[tipo]
        if nombre not in fuente.campos:
            continue
        # de una columna que puede traer personas no sale ningún valor: el mínimo de un
        # `documento_proveedor` es una cédula
        contenido = {} if _PERSONAS.search(nombre) else col.get("cachedContents") or {}
        numerica = tipo in _NUMERICOS_SOCRATA
        campos[nombre] = CampoDeLaFuente(
            tipo_fuente=tipo,
            etiqueta=col.get("name"),
            descripcion=_texto(col.get("description")),
            nulos=int(contenido["null"]) if "null" in contenido else None,
            minimo=_extremo(contenido.get("smallest"), numerica),
            maximo=_extremo(contenido.get("largest"), numerica),
            comparacion=(
                ("numero" if numerica else "fecha" if "date" in tipo else "texto")
                if "smallest" in contenido
                else None
            ),
            valores=_valores_frecuentes(nombre, contenido),
        )
    filas = next(
        (
            int(c["cachedContents"]["count"])
            for c in vista.get("columns") or []
            if (c.get("cachedContents") or {}).get("count")
        ),
        None,
    )
    personal = (vista.get("metadata") or {}).get("custom_fields") or {}
    datos = personal.get("Información de Datos") or {}
    ident = vista.get("id")
    return Metadatos(
        fuente=fuente.id,
        metodo="cosechado",
        cosechado=hoy,
        origen=f"https://www.datos.gov.co/api/views/{ident}.json",
        pagina=f"https://www.datos.gov.co/d/{ident}",
        titulo=vista.get("name"),
        descripcion=_texto(vista.get("description")),
        publicado=_fecha(vista.get("publicationDate") or vista.get("createdAt")),
        datos_actualizados=_fecha(vista.get("rowsUpdatedAt")),
        frecuencia_declarada=datos.get("Frecuencia de Actualización"),
        cobertura_declarada=datos.get("Cobertura Geográfica"),
        corte=_corte(vista.get("description")),
        idioma=datos.get("Idioma"),
        categoria=vista.get("category"),
        etiquetas=list(vista.get("tags") or []),
        filas=filas,
        geografia=Geografia(geometria=geometria, crs="EPSG:4326") if geometria else None,
        campos=campos,
    )


def _a_wgs84(extension: dict[str, Any]) -> list[float] | None:
    """La extensión de una capa en EPSG:4326 (de Web Mercator o ya geográfica)."""
    sr = extension.get("spatialReference") or {}
    wkid = sr.get("latestWkid") or sr.get("wkid")
    try:
        x1, y1, x2, y2 = (float(extension[k]) for k in ("xmin", "ymin", "xmax", "ymax"))
    except (KeyError, TypeError, ValueError):
        return None
    if wkid == 4326:
        return [round(v, 6) for v in (x1, y1, x2, y2)]
    if wkid in (3857, 102100):
        radio = 6378137.0

        def lon(x: float) -> float:
            return math.degrees(x / radio)

        def lat(y: float) -> float:
            return math.degrees(2 * math.atan(math.exp(y / radio)) - math.pi / 2)

        return [round(lon(x1), 6), round(lat(y1), 6), round(lon(x2), 6), round(lat(y2), 6)]
    return None


def _union(a: list[float] | None, b: list[float] | None) -> list[float] | None:
    if a is None or b is None:
        return a or b
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def de_arcgis(
    fuente: Fuente,
    servicio: dict[str, Any],
    capas: dict[int, dict[str, Any]],
    conteos: dict[int, int],
    estadisticas: dict[int, dict[str, Any]],
    item: dict[str, Any] | None,
    hoy: date,
    valores: dict[str, dict[str, int]] | None = None,
) -> Metadatos:
    """La ficha técnica de un servicio ArcGIS: servicio, capas usadas, conteos e ítem.

    `valores` son los valores observados de los campos codificados (sumados entre capas): con
    ellos la ficha técnica dice qué códigos de los datos no define ninguna tabla."""
    valores = valores or {}
    campos: dict[str, CampoDeLaFuente] = {}
    geometrias: set[Geometria] = set()
    extension: list[float] | None = None
    editado: date | None = None
    for numero, capa in sorted(capas.items()):
        if (g := _GEOMETRIAS_ESRI.get(str(capa.get("geometryType")))) is not None:
            geometrias.add(g)
        extension = _union(extension, _a_wgs84(capa.get("extent") or {}))
        edicion = (capa.get("editingInfo") or {}).get("dataLastEditDate")
        if edicion and (e := _fecha(edicion / 1000)) and (editado is None or e > editado):
            editado = e
        stats = estadisticas.get(numero) or {}
        for campo in capa.get("fields") or []:
            nombre = campo.get("name")
            if nombre not in fuente.campos or nombre in campos:
                continue
            dominio = campo.get("domain") or {}
            codigos = {
                str(c["code"]): str(c["name"]) for c in dominio.get("codedValues") or []
            } or None
            tipo = str(campo.get("type") or "")
            minimo, maximo = stats.get(f"min_{nombre}"), stats.get(f"max_{nombre}")
            campos[nombre] = CampoDeLaFuente(
                tipo_fuente=tipo,
                etiqueta=campo.get("alias"),
                descripcion=_texto((campo.get("description") or {}).get("value"))
                if isinstance(campo.get("description"), dict)
                else None,
                minimo=None if minimo is None else str(minimo),
                maximo=None if maximo is None else str(maximo),
                comparacion=("numero" if tipo in _NUMERICOS_ESRI else "fecha")
                if minimo is not None
                else None,
                codigos=codigos,
                valores=valores.get(nombre),
            )
    if len(geometrias) > 1:
        raise ValueError(f"{fuente.id}: capas con geometrías distintas {sorted(geometrias)}")
    sr = (
        next(
            (
                c.get("extent", {}).get("spatialReference")
                for c in capas.values()
                if c.get("extent")
            ),
            None,
        )
        or {}
    )
    wkid = sr.get("latestWkid") or sr.get("wkid")
    item = item or {}
    if item.get("extent"):
        (x1, y1), (x2, y2) = item["extent"]
        extension = extension or [x1, y1, x2, y2]
    return Metadatos(
        fuente=fuente.id,
        metodo="cosechado",
        cosechado=hoy,
        origen=f"{fuente.url}?f=json",
        pagina=f"https://www.arcgis.com/home/item.html?id={item['id']}" if item.get("id") else None,
        titulo=item.get("title") or servicio.get("documentInfo", {}).get("Title") or None,
        descripcion=_texto(item.get("description") or servicio.get("serviceDescription")),
        publicado=_fecha(item["created"] / 1000) if item.get("created") else None,
        datos_actualizados=editado,
        corte=_corte(
            servicio.get("serviceDescription"), item.get("snippet"), item.get("description")
        ),
        etiquetas=list(item.get("tags") or []),
        filas=sum(conteos.values()) if conteos else None,
        geografia=Geografia(
            geometria=geometrias.pop(),
            crs=f"EPSG:{wkid}" if wkid else None,
            extension=extension,
            capas={n: str(c.get("name")) for n, c in sorted(capas.items())},
        )
        if geometrias
        else None,
        campos=campos,
    )


def capas_de(catalogo: Catalogo, fuente_id: str) -> list[int]:
    """Las capas que consultan las herramientas de una fuente o su conector propio."""
    return sorted(
        set(catalogo.fuentes[fuente_id].capas_servicio)
        | {
            c
            for h in catalogo.herramientas.values()
            if h.fuente == fuente_id
            for c in h.consulta.capas
            if isinstance(c, int)  # una capa por nombre no tiene definición numerada
        }
    )


def _get(http: httpx.Client, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    time.sleep(PAUSA_S)
    r = http.get(url, params=params, timeout=120)
    r.raise_for_status()
    datos: dict[str, Any] = r.json()
    if "error" in datos:
        raise httpx.HTTPError(f"{url}: {datos['error']}")
    return datos


def cosechar(catalogo: Catalogo, fuente_id: str, hoy: date | None = None) -> Metadatos:
    """Cosecha en vivo la ficha técnica de una fuente de datos.gov.co o ArcGIS."""
    fuente = catalogo.fuentes[fuente_id]
    hoy = hoy or date.today()
    with httpx.Client(headers={"User-Agent": USER_AGENT}, follow_redirects=True) as http:
        if fuente.protocolo == "socrata":
            conjunto = fuente.copia.conjunto if fuente.copia else None
            ident = conjunto or str(fuente.url).rsplit("/", 1)[-1]
            ident = ident.removesuffix(".json")
            return de_socrata(
                fuente, _get(http, f"https://www.datos.gov.co/api/views/{ident}.json"), hoy
            )
        if fuente.protocolo == "arcgis_rest":
            base = str(fuente.url).rstrip("/")
            servicio = _get(http, base, {"f": "json"})
            capas, conteos, estadisticas = {}, {}, {}
            valores: dict[str, dict[str, int]] = {}
            for n in capas_de(catalogo, fuente_id):
                capas[n] = _get(http, f"{base}/{n}", {"f": "json"})
                conteos[n] = int(
                    _get(
                        http,
                        f"{base}/{n}/query",
                        {"where": "1=1", "returnCountOnly": "true", "f": "json"},
                    ).get("count", 0)
                )
                estadisticas[n] = _estadisticas(http, base, n, capas[n], fuente)
                for campo, cuentas in _valores_codificados(http, base, n, capas[n], fuente).items():
                    destino = valores.setdefault(campo, {})
                    for valor, cuenta in cuentas.items():
                        destino[valor] = destino.get(valor, 0) + cuenta
            item = None
            if item_id := next(
                (c.get("serviceItemId") for c in capas.values() if c.get("serviceItemId")), None
            ):
                try:
                    item = _get(
                        http,
                        f"https://www.arcgis.com/sharing/rest/content/items/{item_id}",
                        {"f": "json"},
                    )
                except httpx.HTTPError:
                    item = None  # el ítem es opcional: un servidor propio no lo tiene
            return de_arcgis(fuente, servicio, capas, conteos, estadisticas, item, hoy, valores)
    raise ValueError(
        f"{fuente_id} ({fuente.protocolo}): la ficha técnica se escribe a mano (metodo: manual)"
    )


def _estadisticas(
    http: httpx.Client, base: str, capa: int, definicion: dict[str, Any], fuente: Fuente
) -> dict[str, Any]:
    """Mínimo y máximo de los campos numéricos y de fecha de la lista blanca, en una consulta."""
    pedidos = [
        {
            "statisticType": t,
            "onStatisticField": c["name"],
            "outStatisticFieldName": f"{t}_{c['name']}",
        }
        for c in definicion.get("fields") or []
        if c.get("name") in fuente.campos
        and (c.get("type") in _NUMERICOS_ESRI or c.get("type") == "esriFieldTypeDate")
        for t in ("min", "max")
    ]
    if not pedidos:
        return {}
    try:
        datos = _get(
            http,
            f"{base}/{capa}/query",
            {"where": "1=1", "outStatistics": json.dumps(pedidos), "f": "json"},
        )
    except httpx.HTTPError:
        return {}  # sin estadísticas la ficha técnica sigue siendo cierta: solo dice menos
    filas = datos.get("features") or [{}]
    atributos: dict[str, Any] = filas[0].get("attributes") or {}
    for clave, valor in list(atributos.items()):
        if any(
            c.get("name") == clave.split("_", 1)[-1] and c.get("type") == "esriFieldTypeDate"
            for c in definicion.get("fields") or []
        ) and isinstance(valor, (int, float)):
            atributos[clave] = _fecha(valor / 1000)
    return atributos


_MAX_CODIGOS = 100


def _valores_codificados(
    http: httpx.Client, base: str, capa: int, definicion: dict[str, Any], fuente: Fuente
) -> dict[str, dict[str, int]]:
    """Cuántas filas trae cada valor de los campos con dominio o con códigos en la ficha."""
    salida: dict[str, dict[str, int]] = {}
    for campo in definicion.get("fields") or []:
        nombre = campo.get("name")
        curado = fuente.campos.get(nombre)
        if curado is None or not (campo.get("domain") or curado.codigos):
            continue
        estadistica = [
            {"statisticType": "count", "onStatisticField": nombre, "outStatisticFieldName": "n"}
        ]
        try:
            datos = _get(
                http,
                f"{base}/{capa}/query",
                {
                    "where": "1=1",
                    "groupByFieldsForStatistics": nombre,
                    "outStatistics": json.dumps(estadistica),
                    "orderByFields": "n DESC",
                    "resultRecordCount": str(_MAX_CODIGOS),
                    "f": "json",
                },
            )
        except httpx.HTTPError:
            continue  # sin conteo la ficha sigue con los códigos: solo no dice cuáles faltan
        salida[nombre] = {
            str(f["attributes"][nombre]): int(f["attributes"]["n"])
            for f in datos.get("features") or []
            if f["attributes"].get(nombre) is not None
        }
    return salida


def diferencias(antes: Metadatos, ahora: Metadatos) -> list[str]:
    """Lo que cambió en la fuente entre dos cosechas (deriva): columnas, corte, capas, geometría."""
    cambios: list[str] = []
    if quitados := set(antes.campos) - set(ahora.campos):
        cambios.append(f"columnas que ya no están: {sorted(quitados)}")
    for nombre in sorted(set(antes.campos) & set(ahora.campos)):
        if antes.campos[nombre].tipo_fuente != ahora.campos[nombre].tipo_fuente:
            cambios.append(
                f"{nombre} cambió de tipo: {antes.campos[nombre].tipo_fuente} → "
                f"{ahora.campos[nombre].tipo_fuente}"
            )
    if antes.corte != ahora.corte:
        cambios.append(f"corte: {antes.corte} → {ahora.corte}")
    if (antes.geografia and antes.geografia.geometria) != (
        ahora.geografia and ahora.geografia.geometria
    ):
        cambios.append("cambió la geometría")
    if antes.geografia and ahora.geografia and antes.geografia.capas != ahora.geografia.capas:
        cambios.append(f"capas: {antes.geografia.capas} → {ahora.geografia.capas}")
    if (
        antes.datos_actualizados
        and ahora.datos_actualizados
        and ahora.datos_actualizados < antes.datos_actualizados
    ):
        cambios.append("la fecha de actualización retrocedió")
    return cambios
