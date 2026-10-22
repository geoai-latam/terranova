"""Datasets curados servidos por la puerta (ADR-0008, `servido_desde: curado`).

Hoy, las restricciones de F4.1 en PostGIS: la vista `curado.restricciones` (versión vigente) y su
manifiesto en `curado.versiones`, que cargan `scripts/dataset_restricciones.py --postgis`. La puerta
solo lee; sin `TERRANOVA_CURADO_URL`, la ficha consulta RUNAP y ANT en vivo como antes.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from terranova.bd import Conexion
from terranova.errores import ErrorEjecucion

CAMPOS = ("id", "tipo", "nombre", "categoria", "acto", "fecha", "fuente_id", "url")


@dataclass(frozen=True)
class Consulta:
    filas: list[dict[str, Any]]
    manifiesto: dict[str, Any]


class Restricciones(Protocol):
    async def en_punto(self, lon: float, lat: float) -> Consulta: ...


class RestriccionesPostgis:
    def __init__(self, url: str) -> None:
        self._url = url
        self._bd: Conexion | None = None

    def _consultar(self, lon: float, lat: float) -> Consulta:
        if self._bd is None:
            self._bd = Conexion(self._url)
        cargada, _ = self._bd.ejecutar("SELECT to_regclass('curado.versiones') IS NOT NULL")
        if not cargada[0][0]:
            raise ErrorEjecucion("no_existe", "no hay dataset curado cargado")
        filas, _ = self._bd.ejecutar(
            f"SELECT {', '.join(CAMPOS)} FROM curado.restricciones "
            "WHERE ST_Intersects(geom, ST_SetSRID(ST_MakePoint(?, ?), 4326)) ORDER BY tipo, id",
            (lon, lat),
        )
        version, _ = self._bd.ejecutar(
            "SELECT manifiesto FROM curado.versiones WHERE dataset = 'restricciones' AND vigente"
        )
        if not version:
            raise ErrorEjecucion("no_existe", "no hay una versión vigente del dataset curado")
        manifiesto = version[0][0]
        if isinstance(manifiesto, str):
            manifiesto = json.loads(manifiesto)
        return Consulta([dict(zip(CAMPOS, f, strict=True)) for f in filas], manifiesto)

    async def en_punto(self, lon: float, lat: float) -> Consulta:
        try:
            return await asyncio.to_thread(self._consultar, lon, lat)
        except ErrorEjecucion:
            raise
        except Exception as exc:  # la base curada caída es una fuente caída, no un 500
            self._bd = None  # la próxima vez se reconecta
            raise ErrorEjecucion(
                "fuente_no_disponible", f"base curada: {type(exc).__name__}"
            ) from exc


def restricciones_desde_entorno() -> Restricciones | None:
    url = os.environ.get("TERRANOVA_CURADO_URL")
    return RestriccionesPostgis(url) if url else None
