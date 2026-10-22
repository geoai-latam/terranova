"""Medición (ADR-0010, F3.4): un evento de uso por solicitud en un outbox.

El `solicitud_id` es la clave: un evento repetido no se duplica. Las fallas y lo servido desde caché
quedan con 0 créditos. Escribir el evento nunca hace fallar la respuesta: si el outbox falla, se
registra en el log y se sigue. Los eventos alimentan las señales de uso de ADR-0020 (llaves activas,
consultas por llave, fuentes pedidas).
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

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


class OutboxSqlite:
    def __init__(self, ruta: str | Path) -> None:
        self._candado = threading.Lock()
        if str(ruta) != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self._bd = sqlite3.connect(str(ruta), check_same_thread=False, isolation_level=None)
        self._bd.execute(
            """CREATE TABLE IF NOT EXISTS eventos (
                solicitud_id TEXT PRIMARY KEY, org TEXT NOT NULL, llave_id TEXT NOT NULL,
                herramienta TEXT NOT NULL, creditos INTEGER NOT NULL, resultado TEXT NOT NULL,
                servido_desde TEXT, momento TEXT NOT NULL, enviado INTEGER NOT NULL DEFAULT 0)"""
        )

    def registrar(self, evento: Evento) -> None:
        d = asdict(evento)
        with self._candado:
            self._bd.execute(
                "INSERT OR IGNORE INTO eventos VALUES "
                "(:solicitud_id, :org, :llave_id, :herramienta, :creditos, :resultado, "
                ":servido_desde, :momento, 0)",
                d,
            )

    def eventos(self, org: str | None = None) -> list[Evento]:
        filas = self._bd.execute(
            "SELECT solicitud_id, org, llave_id, herramienta, creditos, resultado, servido_desde, "
            "momento FROM eventos" + (" WHERE org = ?" if org else "") + " ORDER BY momento",
            (org,) if org else (),
        ).fetchall()
        return [Evento(*f) for f in filas]


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
