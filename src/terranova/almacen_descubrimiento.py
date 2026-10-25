"""Almacén del catálogo de descubrimiento en PostGIS + pgvector (G6, ADR-0026/0028, spec 09).

Metadatos **sobre fuentes** (no datos en bulk: no es una copia, ADR-0024) + un **vector** por fila
para el buscador semántico. Una sola tabla `descubrimiento.datasets`, con una columna
`fuente_catalogo` (`socrata` / `icde`) para refrescar un catálogo sin tocar el otro. Se refresca
**entero por pasada** (ADR-0028): `reemplazar` borra las filas de ese catálogo y mete las nuevas.

- `reemplazar(fuente, datasets, vectores)` aterriza metadatos + embeddings (el job de ingesta).
- `buscar(vector_consulta, …)` hace la búsqueda vectorial con el operador `<=>` de pgvector (coseno)
  y reordena por valor, como `descubrimiento.buscar_vectorial` (misma cuenta, pero en la base).

El SQL va parametrizado y con vocabulario cerrado (ADR-0012): el vector se pasa como literal con el
cast `::vector`, nunca texto suelto. Las pruebas del almacén corren solo con `TERRANOVA_PG_PRUEBAS`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import date
from typing import TYPE_CHECKING, Any

from terranova.descubrimiento import (
    DIM_EMBEDDING,
    PISO_SIMILITUD,
    DatasetDescubrible,
)

if TYPE_CHECKING:
    from terranova.descubrimiento import Embedder

ESQUEMA = "descubrimiento"


def _vector_literal(v: tuple[float, ...]) -> str:
    """Un vector como literal de pgvector: `[0.1,0.2,…]`. Se pasa con cast `::vector`."""
    return "[" + ",".join(repr(float(x)) for x in v) + "]"


class AlmacenDescubrimiento:
    """La tabla `descubrimiento.datasets` (metadatos + vector), refrescada entera por catálogo."""

    def __init__(self, url: str, dim: int = DIM_EMBEDDING) -> None:
        self._url = url
        self._dim = dim
        self._conexion: Any = None

    @property
    def _c(self) -> Any:
        if self._conexion is None:
            import importlib

            psycopg: Any = importlib.import_module("psycopg")  # extra opcional `postgres`
            self._conexion = psycopg.connect(self._url, autocommit=True)
        return self._conexion

    def asegurar_esquema(self) -> None:
        self._c.execute("CREATE EXTENSION IF NOT EXISTS vector")
        self._c.execute(f"CREATE SCHEMA IF NOT EXISTS {ESQUEMA}")
        self._c.execute(
            f"""CREATE TABLE IF NOT EXISTS {ESQUEMA}.datasets (
                fuente_catalogo text NOT NULL,
                id text NOT NULL,
                titulo text NOT NULL DEFAULT '',
                descripcion text NOT NULL DEFAULT '',
                entidad text NOT NULL DEFAULT '',
                categoria text,
                columnas text[] NOT NULL DEFAULT '{{}}',
                licencia text,
                actualizado_en text,
                vistas bigint NOT NULL DEFAULT 0,
                descargas bigint NOT NULL DEFAULT 0,
                url text NOT NULL DEFAULT '',
                protocolo text NOT NULL DEFAULT 'socrata',
                embedding vector({self._dim}),
                _texto tsvector GENERATED ALWAYS AS (
                    to_tsvector('spanish', titulo || ' ' || descripcion || ' ' || entidad)
                ) STORED,
                PRIMARY KEY (fuente_catalogo, id))"""
        )
        self._c.execute(
            f"CREATE INDEX IF NOT EXISTS datasets_embedding ON {ESQUEMA}.datasets "
            "USING hnsw (embedding vector_cosine_ops)"
        )
        self._c.execute(
            f"CREATE INDEX IF NOT EXISTS datasets_texto ON {ESQUEMA}.datasets USING gin (_texto)"
        )

    def reemplazar(
        self,
        fuente_catalogo: str,
        datasets: list[DatasetDescubrible],
        vectores: Mapping[str, tuple[float, ...]],
    ) -> int:
        """Refresca ENTERO el catálogo `fuente_catalogo` (ADR-0028): borra sus filas y mete las
        nuevas, en una transacción. El vector es opcional (una fila sin embedding no sale en la
        búsqueda vectorial, pero sí en el léxico)."""
        self.asegurar_esquema()
        filas = [
            (
                fuente_catalogo,
                d.id_socrata,
                d.titulo,
                d.descripcion,
                d.entidad,
                d.categoria,
                list(d.columnas),
                d.licencia,
                d.actualizado_en,
                d.vistas,
                d.descargas,
                d.url,
                d.protocolo,
                _vector_literal(vectores[d.id_socrata]) if d.id_socrata in vectores else None,
            )
            for d in datasets
        ]
        with self._c.transaction():
            self._c.execute(
                f"DELETE FROM {ESQUEMA}.datasets WHERE fuente_catalogo = %s", (fuente_catalogo,)
            )
            with self._c.cursor() as cur:
                cur.executemany(
                    f"""INSERT INTO {ESQUEMA}.datasets (fuente_catalogo, id, titulo, descripcion,
                        entidad, categoria, columnas, licencia, actualizado_en, vistas, descargas,
                        url, protocolo, embedding)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)""",
                    filas,
                )
        return len(filas)

    def buscar(
        self,
        vector_consulta: tuple[float, ...],
        *,
        limite: int = 20,
        piso: float = PISO_SIMILITUD,
        hoy: date | None = None,
    ) -> list[DatasetDescubrible]:
        """Búsqueda vectorial con `<=>` (coseno) de pgvector, reordenada por valor igual que
        `descubrimiento.buscar_vectorial`: trae los más parecidos (sobre el piso) y, a igual
        parecido, antepone licencia y frescura."""
        hoy = hoy or date.today()
        lit = _vector_literal(vector_consulta)
        # `<=>` es distancia coseno (0 = idéntico); similitud = 1 - distancia. Se trae de más a
        # menos parecido un margen (el triple) y se reordena por valor, como buscar_vectorial.
        cur = self._c.execute(
            f"""SELECT id, titulo, descripcion, entidad, categoria, columnas, licencia,
                    actualizado_en, vistas, descargas, url, protocolo,
                    1 - (embedding <=> %s::vector) AS sim
                FROM {ESQUEMA}.datasets
                WHERE embedding IS NOT NULL AND 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s""",
            (lit, lit, piso, lit, limite * 3),
        )
        puntuados = [(self._fila(f), float(f[12])) for f in cur.fetchall()]
        puntuados.sort(
            key=lambda p: (round(p[1], 2), p[0].con_licencia(), p[0].vivo(hoy), p[1]),
            reverse=True,
        )
        return [d for d, _ in puntuados[:limite]]

    @staticmethod
    def _fila(f: Any) -> DatasetDescubrible:
        return DatasetDescubrible(
            id_socrata=f[0],
            titulo=f[1] or "",
            descripcion=f[2] or "",
            entidad=f[3] or "",
            categoria=f[4],
            columnas=tuple(f[5] or ()),
            licencia=f[6],
            actualizado_en=f[7],
            vistas=int(f[8] or 0),
            descargas=int(f[9] or 0),
            url=f[10] or "",
            protocolo=f[11] or "socrata",
        )


# --- el conector interno `catalogo_dcat` -------------------------------------------------------


class ConectorCatalogo:
    """Conector interno del catálogo (G6, ADR-0026/0028): misma interfaz que los conectores MCP.
    La herramienta `catalogo_buscar` embebe la consulta (con el microservicio) y busca en
    `descubrimiento.datasets`. La puerta no decide nada: solo recupera y surte procedencia."""

    def __init__(self, almacen: AlmacenDescubrimiento, embedder: Embedder | None) -> None:
        self._almacen = almacen
        self._embedder = embedder

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        from terranova.conector import ErrorConector

        if herramienta != "buscar_catalogo":
            raise ErrorConector(f"el conector catálogo no tiene «{herramienta}»", "error_interno")
        if self._embedder is None:
            raise ErrorConector("embeddings no configurados", "fuente_no_disponible")
        consulta = str(argumentos.get("consulta") or "").strip()
        if not consulta:
            raise ErrorConector("consulta vacía", "error_interno")
        limite = int(argumentos.get("limite") or 20)
        try:
            vector = await asyncio.to_thread(self._embedder.consulta, consulta)
            hallados = await asyncio.to_thread(self._almacen.buscar, vector, limite=limite)
        except Exception as exc:  # el microservicio o la base caídos = fuente caída
            raise ErrorConector(f"catalogo: {type(exc).__name__}", "fuente_no_disponible") from exc
        filas = [
            {
                "id": d.id_socrata,
                "titulo": d.titulo,
                "entidad": d.entidad,
                "licencia": d.licencia or "",
                "actualizado_en": d.actualizado_en or "",
                "protocolo": d.protocolo,
                "url": d.url,
            }
            for d in hallados
        ]
        columnas = ["id", "titulo", "entidad", "licencia", "actualizado_en", "protocolo", "url"]
        return {
            "artifacts": [{"kind": "table", "columns": columnas, "rows": filas}],
            "facts": {
                "completitud": {
                    "vistos": len(filas),
                    "total": None if len(filas) >= limite else len(filas),
                    "truncado": len(filas) >= limite,
                }
            },
        }


def conector_catalogo_desde_entorno() -> ConectorCatalogo | None:
    """El conector `catalogo_dcat` si hay base (`TERRANOVA_CURADO_URL`/`TERRANOVA_COPIAS_URL`). El
    embebedor habla con el microservicio (`TERRANOVA_EMBEDDINGS_URL`); sin él, el conector existe
    pero responde `fuente_no_disponible` (honesto: no hay con qué embeber)."""
    import os

    url = os.environ.get("TERRANOVA_CURADO_URL") or os.environ.get("TERRANOVA_COPIAS_URL")
    if not url:
        return None
    emb_url = os.environ.get("TERRANOVA_EMBEDDINGS_URL")
    embedder: Embedder | None = None
    if emb_url:
        from terranova.descubrimiento import EmbedderRemoto

        embedder = EmbedderRemoto(emb_url)
    return ConectorCatalogo(AlmacenDescubrimiento(url), embedder)
