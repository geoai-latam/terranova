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
import math
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Protocol

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
    """Cosecha el catálogo del dominio, en serie. Pagina con **`scroll_id`** (no `offset`, que topa
    en ~10.000): cada página pide los `id` mayores que el último visto, ordenados por `dataset_id`.
    `limite_paginas` acota (desarrollo)."""
    import httpx

    http = cliente or httpx.Client(
        timeout=120, headers={"User-Agent": "terranova-descubrimiento/1"}
    )
    cerrar = cliente is None
    datasets: list[DatasetDescubrible] = []
    scroll_id, pagina = "", 0
    try:
        while True:
            # `scroll_id` entra en modo scroll (ordena por dataset_id solo); `scroll_id` + `order`
            # da 400 en la API real, así que NO se manda `order`. En la primera página va vacío.
            params: dict[str, Any] = {
                "domains": dominio,
                "search_context": dominio,
                "limit": por_pagina,
                "scroll_id": scroll_id,
            }
            r = http.get(DISCOVERY_URL, params=params)
            r.raise_for_status()
            resultados = r.json().get("results") or []
            if not resultados:
                break
            for x in resultados:
                try:
                    datasets.append(de_socrata_catalog(x))
                except (KeyError, TypeError, ValueError):
                    continue  # un resultado malformado no tumba la cosecha
            ultimo = (resultados[-1].get("resource") or {}).get("id") or ""
            if not ultimo or ultimo == scroll_id:  # sin avance: corta (evita un bucle infinito)
                break
            scroll_id = ultimo
            pagina += 1
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


def ingerir_dcat_us(
    cliente: Any = None,
    *,
    url: str = ICDE_DCAT_URL,
    limite_paginas: int | None = None,
    max_paginas: int = 50,
) -> list[DatasetDescubrible]:
    """Cosecha un feed DCAT-US 1.1 (el Hub de la ICDE). El feed topa en ~10.000 ítems por página, y
    se **pagina** con `?page=N` hasta que una página no trae ítems nuevos (vacía o ya vistos), o
    hasta el tope de seguridad `max_paginas`. `limite_paginas` acota (desarrollo). Metadatos, no
    carga; un ítem malformado no tumba la cosecha."""
    import httpx

    http = cliente or httpx.Client(
        timeout=120, headers={"User-Agent": "terranova-descubrimiento/1"}
    )
    cerrar = cliente is None
    datasets: list[DatasetDescubrible] = []
    vistos: set[str] = set()
    tope = min(max_paginas, limite_paginas) if limite_paginas else max_paginas
    try:
        for pagina in range(1, tope + 1):
            r = http.get(url, params={"page": pagina}) if pagina > 1 else http.get(url)
            r.raise_for_status()
            crudos = r.json().get("dataset") or []
            nuevos = 0
            for x in crudos:
                try:
                    d = de_dcat_us(x)
                except (KeyError, TypeError, ValueError):
                    continue
                if d.id_socrata in vistos:  # el feed repite la página 1 si no soporta ?page: corta
                    continue
                vistos.add(d.id_socrata)
                datasets.append(d)
                nuevos += 1
            if nuevos == 0:  # página vacía o sin ítems nuevos: se acabó el catálogo
                break
    finally:
        if cerrar:
            http.close()
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


# --------------------------------------------------------------------------- embeddings (ADR-0028)
#: El modelo de embeddings: multilingüe (español), pequeño, ONNX en CPU, local y gratis (coherente
#: con «open source y gratuita» y con la poca memoria del equipo). Se FIJA para que el canario sea
#: reproducible; cambiarlo obliga a re-embeder todo. Es un modelo simétrico de sentence-transformers
#: (no e5): no lleva prefijos `query:`/`passage:`.
MODELO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DIM_EMBEDDING = 384
#: Debajo de este coseno, un candidato no se parece lo suficiente: no se muestra (honestidad —los
#: embeddings no empujan un «parecido pero falso» con confianza). Medido en vivo con este modelo
#: (2026-10-25): con 0,30 casi todo pasaba (cientos de 2000); con 0,40 el ruido baja y una consulta
#: sin respuesta («bitcoin») devuelve 0. Se afina con el banco de verdades al desplegar.
PISO_SIMILITUD = 0.40


class Embedder(Protocol):
    """Lo que necesita el buscador vectorial. El modelo real (fastembed) o uno falso en pruebas."""

    def consulta(self, texto: str) -> tuple[float, ...]: ...

    def documentos(self, textos: list[str]) -> list[tuple[float, ...]]: ...


def texto_para_embedding(d: DatasetDescubrible) -> str:
    """El texto que representa un dataset para buscarlo: título + descripción + entidad + categoría
    + keywords. Pura y estable (misma fila → mismo texto → mismo vector con el modelo fijado)."""
    partes = [d.titulo, d.descripcion, d.entidad, d.categoria or "", *d.columnas]
    return " · ".join(p.strip() for p in partes if p and p.strip())


def _coseno(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Similitud coseno. Lógica de referencia (la corrida grande va en pgvector/numpy)."""
    if len(a) != len(b):
        raise ValueError("vectores de distinta dimensión")
    punto = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return punto / (na * nb) if na and nb else 0.0


def buscar_vectorial(
    datasets: list[DatasetDescubrible],
    vector_consulta: tuple[float, ...],
    vectores: dict[str, tuple[float, ...]],
    *,
    limite: int = 20,
    piso: float = PISO_SIMILITUD,
    hoy: date | None = None,
) -> list[DatasetDescubrible]:
    """El buscador por **embeddings** (ADR-0028): ordena por parecido semántico con la pregunta, con
    un **piso** (lo poco parecido no se muestra). Dentro de un mismo nivel de parecido (redondeado a
    centésimas), rompe el empate por **valor** (licencia > vivo) para honrar la honestidad sin pisar
    la relevancia. Pura: recibe los vectores ya calculados (no toca red ni modelo)."""
    hoy = hoy or date.today()
    puntuados: list[tuple[DatasetDescubrible, float]] = []
    for d in datasets:
        v = vectores.get(d.id_socrata)
        if v is None:
            continue
        s = _coseno(vector_consulta, v)
        if s >= piso:
            puntuados.append((d, s))
    puntuados.sort(
        key=lambda p: (round(p[1], 2), p[0].con_licencia(), p[0].vivo(hoy), p[1]),
        reverse=True,
    )
    return [d for d, _ in puntuados[:limite]]


@dataclass(frozen=True)
class CandidatoPromocion:
    """Un dataset del catálogo que responde preguntas reales del producto (ADR-0026 §9.4): se
    promueve por valor MEDIDO (en cuántas preguntas del banco aparece), no por intuición."""

    dataset: DatasetDescubrible
    preguntas: int  # en cuántas preguntas del banco salió como candidato


def candidatos_a_promover(
    preguntas: list[str],
    buscar_fn: Any,
    *,
    por_pregunta: int = 5,
    hoy: date | None = None,
) -> list[CandidatoPromocion]:
    """Corre cada pregunta del banco por el buscador (`buscar_fn(consulta)`) y cuenta en cuántas
    aparece cada dataset; ordena la cola de promoción por **cobertura medida**, luego por licencia y
    frescura. Pura: recibe el buscador (no toca red ni base)."""
    hoy = hoy or date.today()
    conteo: dict[str, int] = {}
    ref: dict[str, DatasetDescubrible] = {}
    for pregunta in preguntas:
        for d in list(buscar_fn(pregunta))[:por_pregunta]:
            conteo[d.id_socrata] = conteo.get(d.id_socrata, 0) + 1
            ref[d.id_socrata] = d
    candidatos = [CandidatoPromocion(ref[i], n) for i, n in conteo.items()]
    candidatos.sort(
        key=lambda c: (c.preguntas, c.dataset.con_licencia(), c.dataset.vivo(hoy)), reverse=True
    )
    return candidatos


class FastEmbedder:
    """El `Embedder` real, con `fastembed` (ONNX, sin torch). Import perezoso: el núcleo no lo
    arrastra; se instala con el extra `descubrimiento`. El modelo es simétrico (sentence-
    transformers): la consulta y los documentos se embeben igual, sin prefijos."""

    def __init__(self, modelo: str = MODELO_EMBEDDING) -> None:
        from fastembed import TextEmbedding  # type: ignore[import-not-found]

        self._modelo = TextEmbedding(model_name=modelo)

    def _embeber(self, textos: list[str]) -> list[tuple[float, ...]]:
        return [tuple(float(x) for x in v) for v in self._modelo.embed(textos)]

    def consulta(self, texto: str) -> tuple[float, ...]:
        return self._embeber([texto])[0]

    def documentos(self, textos: list[str]) -> list[tuple[float, ...]]:
        return self._embeber(textos)


class EmbedderRemoto:
    """El `Embedder` que habla con el **microservicio** de embeddings por HTTP (ADR-0028, Q2): así
    el modelo vive en un solo contenedor y no se carga en cada réplica de la puerta. Misma interfaz
    que `FastEmbedder`."""

    def __init__(self, url: str, cliente: Any = None, timeout_s: float = 30) -> None:
        import httpx

        self._url = url.rstrip("/") + "/embed"
        self._http = cliente or httpx.Client(
            timeout=timeout_s, headers={"User-Agent": "terranova-descubrimiento/1"}
        )

    def _pedir(self, cuerpo: dict[str, Any]) -> list[tuple[float, ...]]:
        r = self._http.post(self._url, json=cuerpo)
        r.raise_for_status()
        return [tuple(float(x) for x in v) for v in r.json()["vectores"]]

    def consulta(self, texto: str) -> tuple[float, ...]:
        return self._pedir({"consulta": texto})[0]

    def documentos(self, textos: list[str]) -> list[tuple[float, ...]]:
        return self._pedir({"documentos": textos}) if textos else []


def embeber_catalogo(
    datasets: list[DatasetDescubrible], embedder: Embedder
) -> dict[str, tuple[float, ...]]:
    """Re-embebe **todo** el catálogo (ADR-0028: pasada completa, no incremental) → id → vector."""
    if not datasets:
        return {}
    vectores = embedder.documentos([texto_para_embedding(d) for d in datasets])
    return {d.id_socrata: v for d, v in zip(datasets, vectores, strict=True)}


def vectores_a_jsonl(vectores: dict[str, tuple[float, ...]]) -> str:
    """El índice de vectores como JSONL (una línea `{"id":…, "v":[…]}`), para dejarlo en disco."""
    return "\n".join(
        json.dumps({"id": k, "v": [round(x, 6) for x in v]}, ensure_ascii=False)
        for k, v in vectores.items()
    )


def cargar_vectores(texto: str) -> dict[str, tuple[float, ...]]:
    """Relee el índice de vectores de un JSONL (lo que dejó `vectores_a_jsonl`)."""
    salida: dict[str, tuple[float, ...]] = {}
    for linea in texto.splitlines():
        if not linea.strip():
            continue
        d = json.loads(linea)
        salida[d["id"]] = tuple(float(x) for x in d["v"])
    return salida
