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
import json
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


def _recorta(sim: float) -> float:
    """El `parecido` al contrato [0,1]: el coseno de pgvector puede ser negativo (ortogonal/opuesto)
    y la rama FTS no aplica el piso, así que un match léxico podría traerlo bajo 0 (ADR-0028)."""
    return max(0.0, min(1.0, sim))


def _rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal Rank Fusion: combina varias listas ordenadas de ids en un puntaje por id, sin
    depender de la escala de cada una (el vector da coseno, el FTS da ts_rank). `1/(k+posición)`."""
    puntos: dict[str, float] = {}
    for ranking in rankings:
        for posicion, id_ in enumerate(ranking):
            puntos[id_] = puntos.get(id_, 0.0) + 1.0 / (k + posicion + 1)
    return puntos


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
        # huella del modelo: una fila con el nombre+dim del modelo que generó los vectores. Sin
        # esto, un cambio de modelo con la MISMA dimensión (p. ej. otro de 384) pasaría en silencio
        # y daría cosenos sin sentido (la columna vector(dim) solo detecta cambios de dimensión).
        self._c.execute(
            f"""CREATE TABLE IF NOT EXISTS {ESQUEMA}.modelo (
                unica boolean PRIMARY KEY DEFAULT true, modelo text NOT NULL, dim int NOT NULL)"""
        )
        # caché de vectores por huella (sha256 de modelo + texto): la ingesta retoma tras un corte
        # y la pasada diaria solo embebe lo nuevo o cambiado (ver `embeber_catalogo`).
        self._c.execute(
            f"""CREATE TABLE IF NOT EXISTS {ESQUEMA}.vectores (
                huella text PRIMARY KEY, embedding vector({self._dim}) NOT NULL)"""
        )

    def vectores_por_huella(self, huellas: list[str]) -> dict[str, tuple[float, ...]]:
        self.asegurar_esquema()
        cur = self._c.execute(
            f"SELECT huella, embedding::text FROM {ESQUEMA}.vectores WHERE huella = ANY(%s)",
            (huellas,),
        )
        return {h: tuple(float(x) for x in json.loads(v)) for h, v in cur.fetchall()}

    def guardar_vectores(self, pares: Mapping[str, tuple[float, ...]]) -> None:
        if not pares:
            return
        self.asegurar_esquema()
        with self._c.transaction(), self._c.cursor() as cur:
            cur.executemany(
                f"""INSERT INTO {ESQUEMA}.vectores (huella, embedding) VALUES (%s, %s::vector)
                    ON CONFLICT (huella) DO UPDATE SET embedding = EXCLUDED.embedding""",
                [(h, _vector_literal(v)) for h, v in pares.items()],
            )

    def modelo_indexado(self) -> tuple[str, int] | None:
        existe = self._c.execute(f"SELECT to_regclass('{ESQUEMA}.modelo')").fetchone()
        if not existe or existe[0] is None:
            return None
        fila = self._c.execute(f"SELECT modelo, dim FROM {ESQUEMA}.modelo").fetchone()
        return (fila[0], int(fila[1])) if fila else None

    def _fijar_modelo(self, modelo: str) -> None:
        """Graba/verifica la huella: mezclar modelos (o dim) en el mismo almacén es un error."""
        actual = self.modelo_indexado()
        if actual is not None and actual != (modelo, self._dim):
            raise ValueError(
                f"el almacén ya está indexado con {actual}, no se puede mezclar con "
                f"({modelo!r}, {self._dim}): re-embebe todo tras cambiar de modelo (ADR-0028)"
            )
        if actual is None:
            self._c.execute(
                f"INSERT INTO {ESQUEMA}.modelo (modelo, dim) VALUES (%s, %s)", (modelo, self._dim)
            )

    def reemplazar(
        self,
        fuente_catalogo: str,
        datasets: list[DatasetDescubrible],
        vectores: Mapping[str, tuple[float, ...]],
        *,
        modelo: str | None = None,
    ) -> int:
        """Refresca ENTERO el catálogo `fuente_catalogo` (ADR-0028): borra sus filas y mete las
        nuevas, en una transacción. El vector es opcional (una fila sin embedding no sale en la
        búsqueda vectorial, pero sí en el léxico). Con `modelo`, graba/verifica la huella (no deja
        mezclar modelos en el mismo almacén)."""
        self.asegurar_esquema()
        if modelo is not None:
            self._fijar_modelo(modelo)
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

    _COLS = (
        "id, titulo, descripcion, entidad, categoria, columnas, licencia, "
        "actualizado_en, vistas, descargas, url, protocolo"
    )

    def buscar(
        self,
        vector_consulta: tuple[float, ...],
        texto_consulta: str | None = None,
        *,
        limite: int = 20,
        piso: float = PISO_SIMILITUD,
        hoy: date | None = None,
    ) -> list[tuple[DatasetDescubrible, float]]:
        """Búsqueda **híbrida** (ADR-0028, medido el 2026-10-25): fusiona por RRF el parecido
        semántico (`<=>` de pgvector, dentro del piso) con el léxico (`ts_rank` del FTS en español,
        que pondera por IDF y evita que las palabras comunes inflen un falso positivo). Sin texto,
        es solo vectorial. A igual relevancia, desempata por valor (licencia, frescura). Devuelve
        cada candidato con su **parecido** (coseno de 0 a 1) para que el cliente juzgue."""
        hoy = hoy or date.today()
        lit = _vector_literal(vector_consulta)
        n = limite * 3
        por_id: dict[str, DatasetDescubrible] = {}
        sims: dict[str, float] = {}

        # 1) candidatos por vector, dentro del piso, de más a menos parecido
        cur = self._c.execute(
            f"""SELECT {self._COLS}, 1 - (embedding <=> %s::vector) AS sim
                FROM {ESQUEMA}.datasets
                WHERE embedding IS NOT NULL AND 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s""",
            (lit, lit, piso, lit, n),
        )
        rank_vec: list[str] = []
        for f in cur.fetchall():
            rank_vec.append(f[0])
            por_id[f[0]] = self._fila(f)
            sims[f[0]] = _recorta(float(f[12]))

        # 2) candidatos por FTS (si hay texto): plainto_tsquery exige todos los lexemas; ts_rank los
        #    ordena por IDF. Es la precisión léxica que el puro-vectorial no da. Se trae también su
        #    coseno (puede estar bajo el piso: el cliente ve que casó por palabra, no por sentido).
        rank_lex: list[str] = []
        if texto_consulta and texto_consulta.strip():
            curl = self._c.execute(
                f"""SELECT {self._COLS}, 1 - (embedding <=> %s::vector) AS sim
                    FROM {ESQUEMA}.datasets
                    WHERE _texto @@ plainto_tsquery('spanish', %s)
                    ORDER BY ts_rank(_texto, plainto_tsquery('spanish', %s)) DESC
                    LIMIT %s""",
                (lit, texto_consulta, texto_consulta, n),
            )
            for f in curl.fetchall():
                rank_lex.append(f[0])
                por_id.setdefault(f[0], self._fila(f))
                sims.setdefault(f[0], _recorta(float(f[12])) if f[12] is not None else 0.0)

        puntos = _rrf([rank_vec, rank_lex] if rank_lex else [rank_vec])
        ids = sorted(
            por_id,
            key=lambda i: (puntos.get(i, 0.0), por_id[i].con_licencia(), por_id[i].vivo(hoy)),
            reverse=True,
        )
        return [(por_id[i], sims.get(i, 0.0)) for i in ids[:limite]]

    def contar(
        self,
        vector_consulta: tuple[float, ...],
        texto_consulta: str | None = None,
        *,
        piso: float = PISO_SIMILITUD,
    ) -> int:
        """Cuántos candidatos coinciden en total (parecido sobre el piso **o** match del FTS): el
        `total` honesto de la completitud, ya que el buscador solo devuelve el top-N."""
        lit = _vector_literal(vector_consulta)
        if texto_consulta and texto_consulta.strip():
            fila = self._c.execute(
                f"""SELECT count(*) FROM {ESQUEMA}.datasets
                    WHERE (embedding IS NOT NULL AND 1 - (embedding <=> %s::vector) >= %s)
                       OR (_texto @@ plainto_tsquery('spanish', %s))""",
                (lit, piso, texto_consulta),
            ).fetchone()
        else:
            fila = self._c.execute(
                f"""SELECT count(*) FROM {ESQUEMA}.datasets
                    WHERE embedding IS NOT NULL AND 1 - (embedding <=> %s::vector) >= %s""",
                (lit, piso),
            ).fetchone()
        return int(fila[0]) if fila else 0

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
            hallados = await asyncio.to_thread(
                self._almacen.buscar, vector, consulta, limite=limite
            )
            total = await asyncio.to_thread(self._almacen.contar, vector, consulta)
        except Exception as exc:
            # servicio/base caídos (red, timeout, conexión) = fuente_no_disponible; un bug propio
            # (dimensión de vector, SQL) = error_interno (honestidad: no es que la fuente se cayera,
            # y así no recicla caché obsoleta ni abre el cortacircuitos de proteccion.py)
            raise ErrorConector(f"catalogo: {type(exc).__name__}", _codigo_catalogo(exc)) from exc
        filas = [
            {
                "id": d.id_socrata,
                "titulo": d.titulo,
                "entidad": d.entidad,
                "licencia": d.licencia or "",
                "actualizado_en": d.actualizado_en or "",
                "protocolo": d.protocolo,
                "url": d.url,
                # parecido semántico de 0 a 1: el cliente LLM juzga la confianza (si todo ~0.47 y
                # plano, probablemente no hay una fuente buena; ADR-0028, límite de calibración)
                "parecido": round(parecido, 3),
            }
            for d, parecido in hallados
        ]
        columnas = [
            "id",
            "titulo",
            "entidad",
            "licencia",
            "actualizado_en",
            "protocolo",
            "url",
            "parecido",
        ]
        # Completitud honesta: `vistos` = los que devuelve el top-N; `total` = cuántos coinciden en
        # total (contar sobre el piso + FTS); `truncado` = hay más de los mostrados. Así
        # `coincidencias` (derivado de total) siempre es un número y dice la verdad.
        return {
            "artifacts": [{"kind": "table", "columns": columnas, "rows": filas}],
            "facts": {
                "completitud": {
                    "vistos": len(filas),
                    "total": total,
                    "truncado": len(filas) < total,
                }
            },
        }


#: Excepciones (por nombre de clase) que significan «el servicio/base no está», no un bug nuestro.
_CAIDA = frozenset(
    {
        "OperationalError",
        "InterfaceError",
        "AdminShutdown",
        "CannotConnectNow",  # psycopg
        "ConnectError",
        "ConnectTimeout",
        "ReadTimeout",
        "PoolTimeout",
        "TransportError",  # httpx/pool
        "TimeoutError",
        "ConnectionError",  # stdlib
    }
)


def _codigo_catalogo(exc: Exception) -> str:
    """`fuente_no_disponible` si el servicio/base se cayó; si no, `error_interno` (bug propio)."""
    return "fuente_no_disponible" if type(exc).__name__ in _CAIDA else "error_interno"


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
    else:
        # sin microservicio: si el extra está, el modelo corre en el proceso (dev o un solo nodo);
        # si no, el conector queda sin embebedor y responde fuente_no_disponible (honesto).
        try:
            from terranova.descubrimiento import FastEmbedder

            embedder = FastEmbedder()
        except ImportError:
            embedder = None
    return ConectorCatalogo(AlmacenDescubrimiento(url), embedder)
