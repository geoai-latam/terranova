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
