"""Una conexión SQL para el registro de llaves y el outbox: SQLite (desarrollo, una réplica) o
Postgres (despliegue con varias réplicas, ADR-0015). El SQL se escribe una vez, con `?`, y con
`ON CONFLICT`, que los dos entienden.

En Postgres se usa un **pool con reconexión** (`psycopg_pool`): un blip/failover/idle de la base no
tumba la autenticación (antes, una sola conexión en `__init__` sin reintento la dejaba inservible),
y el tráfico deja de serializar en una única conexión bajo lock. El arranque no bloquea si la base
aún no está (`open(wait=False)`). SQLite (un solo proceso) mantiene su conexión con candado."""

from __future__ import annotations

import importlib
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any


class Conexion:
    def __init__(self, destino: str | Path) -> None:
        texto = str(destino)
        self.postgres = texto.startswith(("postgresql://", "postgres://"))
        if self.postgres:
            pool_mod: Any = importlib.import_module("psycopg_pool")  # extra opcional `postgres`
            maximo = int(os.environ.get("TERRANOVA_PG_POOL", "8"))
            self._pool: Any = pool_mod.ConnectionPool(
                texto,
                min_size=1,
                max_size=maximo,
                kwargs={"autocommit": True},
                check=pool_mod.ConnectionPool.check_connection,  # revalida/reconecta antes de usar
                open=False,
            )
            self._pool.open(wait=False)  # no bloquea el arranque si la base aún no responde
        else:
            self._candado = threading.Lock()
            if texto != ":memory:":
                Path(texto).parent.mkdir(parents=True, exist_ok=True)
            self._c = sqlite3.connect(texto, check_same_thread=False, isolation_level=None)

    def ejecutar(
        self, sql: str, parametros: tuple[Any, ...] = ()
    ) -> tuple[list[tuple[Any, ...]], int]:
        """(filas, filas afectadas)."""
        if self.postgres:
            sql = sql.replace("?", "%s")
            with self._pool.connection() as conexion:  # del pool, ya revalidada (reconecta sola)
                cursor = conexion.execute(sql, parametros)
                filas = cursor.fetchall() if cursor.description else []
                return [tuple(f) for f in filas], cursor.rowcount
        with self._candado:
            cursor = self._c.execute(sql, parametros)
            filas = cursor.fetchall() if cursor.description else []
            return [tuple(f) for f in filas], cursor.rowcount
