"""Medición (ADR-0010, F3.4): un evento de uso por solicitud en un outbox.

El `solicitud_id` es la clave: un evento repetido no se duplica. Las fallas y lo servido desde caché
quedan con 0 créditos. Escribir el evento nunca hace fallar la respuesta: si el outbox falla, se
registra en el log y se sigue. Los eventos alimentan las señales de uso de ADR-0020 (llaves activas,
consultas por llave, fuentes pedidas).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from terranova.bd import Conexion

logger = logging.getLogger("terranova.medicion")


@dataclass(frozen=True)
class Evento:
    solicitud_id: str
    org: str
    llave_id: str
    herramienta: str
    creditos: int
    resultado: str  # estado del sobre o código de error
    servido_desde: str | None
    momento: str


class Outbox(Protocol):
    def registrar(self, evento: Evento) -> None: ...
    def eventos(self, org: str | None = None) -> list[Evento]: ...


class OutboxSql:
    """Outbox en SQLite o Postgres (la misma `Conexion` que el registro de llaves)."""

    def __init__(self, destino: str | Path) -> None:
        self._bd = Conexion(destino)
        self._bd.ejecutar(
            """CREATE TABLE IF NOT EXISTS eventos (
                solicitud_id TEXT PRIMARY KEY, org TEXT NOT NULL, llave_id TEXT NOT NULL,
                herramienta TEXT NOT NULL, creditos INTEGER NOT NULL, resultado TEXT NOT NULL,
                servido_desde TEXT, momento TEXT NOT NULL, enviado INTEGER NOT NULL DEFAULT 0)"""
        )

    def registrar(self, evento: Evento) -> None:
        e = evento
        self._bd.ejecutar(
            "INSERT INTO eventos VALUES (?,?,?,?,?,?,?,?,0) ON CONFLICT(solicitud_id) DO NOTHING",
            (
                e.solicitud_id,
                e.org,
                e.llave_id,
                e.herramienta,
                e.creditos,
                e.resultado,
                e.servido_desde,
                e.momento,
            ),
        )

    def pendientes(self) -> int:
        filas, _ = self._bd.ejecutar("SELECT COUNT(*) FROM eventos WHERE enviado = 0")
        return int(filas[0][0])

    def eventos(self, org: str | None = None) -> list[Evento]:
        filas, _ = self._bd.ejecutar(
            "SELECT solicitud_id, org, llave_id, herramienta, creditos, resultado, servido_desde, "
            "momento FROM eventos" + (" WHERE org = ?" if org else "") + " ORDER BY momento",
            (org,) if org else (),
        )
        return [Evento(*f) for f in filas]


OutboxSqlite = OutboxSql  # nombre de F3.4


def ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def registrar_sin_fallar(outbox: Outbox | None, evento: Evento) -> None:
    """La medición nunca hace fallar la respuesta (ADR-0010)."""
    if outbox is None:
        return
    try:
        outbox.registrar(evento)
    except Exception:
        logger.exception("no se pudo registrar el evento de uso %s", evento.solicitud_id)
