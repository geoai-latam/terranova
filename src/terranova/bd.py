"""Una conexión SQL para el registro de llaves y el outbox: SQLite (desarrollo, una réplica) o
Postgres (despliegue con varias réplicas, ADR-0015). El SQL se escribe una vez, con `?`, y con
`ON CONFLICT`, que los dos entienden."""

from __future__ import annotations

import importlib
import sqlite3
import threading
from pathlib import Path
from typing import Any


class Conexion:
    def __init__(self, destino: str | Path) -> None:
        self._candado = threading.Lock()
        texto = str(destino)
        self.postgres = texto.startswith(("postgresql://", "postgres://"))
        if self.postgres:
            psycopg: Any = importlib.import_module("psycopg")  # extra opcional `postgres`
            self._c: Any = psycopg.connect(texto, autocommit=True)
        else:
            if texto != ":memory:":
                Path(texto).parent.mkdir(parents=True, exist_ok=True)
            self._c = sqlite3.connect(texto, check_same_thread=False, isolation_level=None)

    def ejecutar(
        self, sql: str, parametros: tuple[Any, ...] = ()
    ) -> tuple[list[tuple[Any, ...]], int]:
        """(filas, filas afectadas)."""
        if self.postgres:
            sql = sql.replace("?", "%s")
        with self._candado:
            cursor = self._c.execute(sql, parametros)
            filas = cursor.fetchall() if cursor.description else []
            return [tuple(f) for f in filas], cursor.rowcount
