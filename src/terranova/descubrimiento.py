"""Descubrimiento de la cola larga de datos.gov.co (G6, ADR-0026, spec 09).

Ingiere el **catálogo DCAT** de datos.gov.co (la Discovery API de Socrata) como metadatos: por cada
dataset, su id 4x4, título, descripción, entidad, categoría, columnas, licencia declarada, fecha de
actualización y señal de uso (vistas, descargas). No baja datos; es una cosecha de metadatos, no
carga (el mismo espíritu de `cosecha.py` y del job de copias).

- `de_socrata_catalog` interpreta UN resultado de la Discovery API: es pura, se prueba sin red.
- `metricas` resume el catálogo para la compuerta de G6 (cuántos, con licencia, vivos, por entidad).
- `ingerir` hace las peticiones paginadas (en serie, con `User-Agent` propio, filtradas al dominio),
  nunca por pregunta. Un resultado malformado no tumba la cosecha.
- `cargar_jsonl` relee el catálogo del disco; `buscar` es el **buscador** (`catalogo_buscar`, spec
  09): casa una pregunta contra título + descripción + columnas + entidad y ordena por valor.

Hay un **segundo catálogo DCAT**, el de **capas** (geoservicios): el Hub de la ICDE
(`datos.icde.gov.co`), un **DCAT-US 1.1** (ArcGIS Hub, casi todo IGAC). `de_dcat_us` lo interpreta
a la misma `DatasetDescubrible` (con `protocolo=arcgis_rest` y la `url` del endpoint REST), así que
el buscador y la promoción son los mismos: un solo buscador sobre dos catálogos (tablas de Socrata y
capas de ArcGIS). Ojo: ese catálogo es grande pero ~99 % es la **restitución cartográfica del IGAC**
(mapa base troceado), no dato de decisión —`_clase_icde` lo marca para que la promoción se centre en
el resto.

La promoción a herramientas curadas se monta sobre esto (spec 09).
"""

from __future__ import annotations

import json
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

#: El endpoint federado de la Discovery API de Socrata y el dominio de Colombia.
DISCOVERY_URL = "https://api.us.socrata.com/api/catalog/v1"
DOMINIO = "www.datos.gov.co"

#: El feed DCAT-US 1.1 del Hub de datos abiertos de la ICDE (ArcGIS Hub, sobre todo IGAC).
#: El catálogo autoritativo de **capas** (geoservicios), el análogo ArcGIS del DCAT de Socrata.
ICDE_DCAT_URL = "https://datos.icde.gov.co/api/feed/dcat-us/1.1.json"

#: Keywords de la restitución cartográfica del IGAC: marcan «mapa base», no dato de decisión.
#: Se comparan ya normalizadas (`_sin_acentos`), así que van en minúscula y sin tildes.
_KW_CARTOGRAFIA_BASE = {
    "restitucion",
    "fotogrametria",
    "planimetria",
    "altimetria",
    "toponimia",
}


@dataclass(frozen=True)
class DatasetDescubrible:
    """Un dataset del catálogo, con lo que decide si se consulta y si se promueve."""

    id_socrata: str
    titulo: str
    descripcion: str
    entidad: str
    categoria: str | None
    columnas: tuple[str, ...]
    licencia: str | None
    actualizado_en: str | None
    vistas: int
    descargas: int
    url: str
    protocolo: str = "socrata"

    def con_licencia(self) -> bool:
        """¿Declara una licencia? (verificarla es un paso manual aparte, ADR-0019.)"""
        return bool(self.licencia and self.licencia.strip())

    def vivo(self, hoy: date, meses: int = 12) -> bool:
        """¿Se actualizó en los últimos `meses`? Sin fecha, no se cuenta como vivo."""
        f = _fecha(self.actualizado_en)
        return f is not None and (hoy.year - f.year) * 12 + (hoy.month - f.month) < meses


@dataclass(frozen=True)
class MetricasCatalogo:
    """El resumen que mide la compuerta de la ingesta (spec 09 §9.2)."""

    total: int
    con_licencia: int
    vivos: int
    entidades: int
    top_entidades: tuple[tuple[str, int], ...]


def _texto(v: Any) -> str:
    return v.strip() if isinstance(v, str) else ""


def _fecha(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def de_socrata_catalog(resultado: dict[str, Any]) -> DatasetDescubrible:
    """Interpreta un resultado de la Discovery API. Pura: no toca la red."""
    res = resultado.get("resource") or {}
    clasif = resultado.get("classification") or {}
    meta = resultado.get("metadata") or {}
    dueno = resultado.get("owner") or {}
    id_socrata = _texto(res.get("id"))
    if not id_socrata:
        raise KeyError("resource.id ausente")
    columnas = res.get("columns_field_name") or res.get("columns_name") or []
    vistas = res.get("page_views") or {}
    return DatasetDescubrible(
        id_socrata=id_socrata,
        titulo=_texto(res.get("name")),
        descripcion=_texto(res.get("description")),
        entidad=(
            _texto(res.get("attribution"))
            or _texto(dueno.get("display_name"))
            or _texto(meta.get("domain"))
        ),
        categoria=(clasif.get("domain_category") or None),
        columnas=tuple(c for c in columnas if isinstance(c, str)),
        licencia=(meta.get("license") or None),
        actualizado_en=(res.get("data_updated_at") or res.get("updatedAt") or None),
        vistas=int(vistas.get("page_views_total") or 0) if isinstance(vistas, dict) else 0,
        descargas=int(res.get("download_count") or 0),
        url=f"https://{DOMINIO}/resource/{id_socrata}.json",
    )


def metricas(
    datasets: list[DatasetDescubrible], hoy: date | None = None, top: int = 10
) -> MetricasCatalogo:
    """El resumen de la compuerta. Pura."""
    hoy = hoy or date.today()
    por_entidad = Counter(d.entidad for d in datasets if d.entidad)
    return MetricasCatalogo(
        total=len(datasets),
        con_licencia=sum(1 for d in datasets if d.con_licencia()),
        vivos=sum(1 for d in datasets if d.vivo(hoy)),
        entidades=len(por_entidad),
        top_entidades=tuple(por_entidad.most_common(top)),
    )


def ingerir(
    cliente: Any = None,
    *,
    limite_paginas: int | None = None,
    por_pagina: int = 1000,
    dominio: str = DOMINIO,
) -> list[DatasetDescubrible]:
    """Cosecha el catálogo del dominio, paginado y en serie. `limite_paginas` acota (desarrollo)."""
    import httpx

    http = cliente or httpx.Client(
        timeout=120, headers={"User-Agent": "terranova-descubrimiento/1"}
    )
    cerrar = cliente is None
    datasets: list[DatasetDescubrible] = []
    offset, pagina = 0, 0
    try:
        while True:
            r = http.get(
                DISCOVERY_URL,
                params={
                    "domains": dominio,
                    "search_context": dominio,
                    "limit": por_pagina,
                    "offset": offset,
                    "order": "dataset_id",
                },
            )
            r.raise_for_status()
            resultados = r.json().get("results") or []
            if not resultados:
                break
            for x in resultados:
                try:
                    datasets.append(de_socrata_catalog(x))
                except (KeyError, TypeError, ValueError):
                    continue  # un resultado malformado no tumba la cosecha
            pagina += 1
            offset += por_pagina
            if len(resultados) < por_pagina or (limite_paginas and pagina >= limite_paginas):
                break
    finally:
        if cerrar:
            http.close()
    return datasets


def _item_arcgis(identifier: str) -> str:
    """El id estable de un ítem del Hub: `<itemid>` (+ `:<sublayer>` si lo trae). El `identifier`
    del DCAT-US es una URL `…item.html?id=<32hex>&sublayer=N`; si no casa, se usa tal cual."""
    import re

    m = re.search(r"id=([0-9a-fA-F]{32})", identifier or "")
    if not m:
        return _texto(identifier)
    sub = re.search(r"sublayer=(\d+)", identifier or "")
    return f"{m.group(1)}:{sub.group(1)}" if sub else m.group(1)


def _rest_url_arcgis(distribuciones: list[dict[str, Any]]) -> str | None:
    """De las distribuciones DCAT, el endpoint **ArcGIS REST** (lo que consume el conector), no la
    página del Hub. Se prefiere la que se declara GeoService/REST."""
    for y in distribuciones:
        marca = f"{_texto(y.get('format'))} {_texto(y.get('title'))}"
        if "GeoService" in marca or "REST" in marca:
            u = _texto(y.get("accessURL")) or _texto(y.get("downloadURL"))
            if u:
                return u
    return None


def _clase_icde(keywords: tuple[str, ...]) -> str:
    """Clasifica un ítem del Hub ICDE: la restitución cartográfica del IGAC («Cartografía base»,
    la cola larga de primitivas por plancha) vs. el resto («Dato temático»). Es la señal que
    separa el mapa base del dato de decisión (spec 09: el valor está en el resto, no en las 9k
    primitivas de restitución)."""
    kws = {_sin_acentos(k) for k in keywords}
    return "Cartografía base" if len(_KW_CARTOGRAFIA_BASE & kws) >= 3 else "Dato temático"


def de_dcat_us(dataset: dict[str, Any]) -> DatasetDescubrible:
    """Interpreta un dataset de un feed **DCAT-US 1.1** (ArcGIS Hub de la ICDE). Pura: no toca la
    red. El `protocolo` queda `arcgis_rest` y la `url` es el endpoint REST (no la página del Hub).
    El Hub no publica señal de uso (vistas/descargas), así que quedan en 0: el orden se decide por
    licencia y frescura."""
    ident = _texto(dataset.get("identifier"))
    id_item = _item_arcgis(ident)
    if not id_item:
        raise KeyError("identifier ausente")
    keywords = tuple(k for k in (dataset.get("keyword") or []) if isinstance(k, str))
    pub = dataset.get("publisher") or {}
    dists = [y for y in (dataset.get("distribution") or []) if isinstance(y, dict)]
    rest = _rest_url_arcgis(dists)
    return DatasetDescubrible(
        id_socrata=id_item,  # el campo es el id genérico del catálogo; aquí, el item de ArcGIS
        titulo=_texto(dataset.get("title")),
        descripcion=_texto(dataset.get("description")) or _texto(dataset.get("summary")),
        entidad=_texto(pub.get("name")),
        categoria=_clase_icde(keywords),
        columnas=keywords,  # las keywords hacen de «campos» para casar la pregunta
        licencia=(_texto(dataset.get("license")) or None),
        actualizado_en=(_texto(dataset.get("modified")) or _texto(dataset.get("issued")) or None),
        vistas=0,
        descargas=0,
        url=(rest or _texto(dataset.get("landingPage")) or ident),
        protocolo="arcgis_rest",
    )


def ingerir_dcat_us(cliente: Any = None, *, url: str = ICDE_DCAT_URL) -> list[DatasetDescubrible]:
    """Cosecha un feed DCAT-US 1.1 (el Hub de la ICDE). Es **un solo documento** (no paginado como
    Socrata); hoy el feed topa en ~10.000 ítems, casi todos cartografía base del IGAC. Metadatos,
    no carga. Un ítem malformado no tumba la cosecha."""
    import httpx

    http = cliente or httpx.Client(
        timeout=120, headers={"User-Agent": "terranova-descubrimiento/1"}
    )
    cerrar = cliente is None
    try:
        r = http.get(url)
        r.raise_for_status()
        crudos = r.json().get("dataset") or []
    finally:
        if cerrar:
            http.close()
    datasets: list[DatasetDescubrible] = []
    for x in crudos:
        try:
            datasets.append(de_dcat_us(x))
        except (KeyError, TypeError, ValueError):
            continue
    return datasets


def a_jsonl(datasets: list[DatasetDescubrible]) -> str:
    """El catálogo como JSONL (una línea por dataset), para dejarlo en disco."""
    return "\n".join(json.dumps(asdict(d), ensure_ascii=False) for d in datasets)


def cargar_jsonl(texto: str) -> list[DatasetDescubrible]:
    """Relee el catálogo de un JSONL (lo que dejó `a_jsonl`)."""
    salida: list[DatasetDescubrible] = []
    for linea in texto.splitlines():
        if not linea.strip():
            continue
        d = json.loads(linea)
        salida.append(
            DatasetDescubrible(
                id_socrata=d["id_socrata"],
                titulo=d.get("titulo", ""),
                descripcion=d.get("descripcion", ""),
                entidad=d.get("entidad", ""),
                categoria=d.get("categoria"),
                columnas=tuple(d.get("columnas") or []),
                licencia=d.get("licencia"),
                actualizado_en=d.get("actualizado_en"),
                vistas=int(d.get("vistas") or 0),
                descargas=int(d.get("descargas") or 0),
                url=d.get("url", ""),
                protocolo=d.get("protocolo", "socrata"),
            )
        )
    return salida


def _sin_acentos(s: str) -> str:
    sin = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return sin.lower()


def buscar(
    datasets: list[DatasetDescubrible],
    consulta: str,
    *,
    entidad: str | None = None,
    limite: int = 20,
    hoy: date | None = None,
) -> list[DatasetDescubrible]:
    """El buscador (`catalogo_buscar`, spec 09): los datasets que casan TODAS las palabras de la
    consulta (sin tildes, sin importar mayúsculas) en título + descripción + columnas + entidad +
    categoría, ordenados por señal de valor: con licencia declarada > vivo > uso (vistas+descargas).
    Pura: no toca la red ni la base."""
    hoy = hoy or date.today()
    palabras = [p for p in _sin_acentos(consulta).split() if p]
    ent = _sin_acentos(entidad) if entidad else None
    candidatos: list[DatasetDescubrible] = []
    for d in datasets:
        if ent and ent not in _sin_acentos(d.entidad):
            continue
        heno = _sin_acentos(
            " ".join([d.titulo, d.descripcion, d.entidad, d.categoria or "", *d.columnas])
        )
        if all(p in heno for p in palabras):
            candidatos.append(d)
    candidatos.sort(
        key=lambda d: (d.con_licencia(), d.vivo(hoy), d.vistas + d.descargas), reverse=True
    )
    return candidatos[:limite]
