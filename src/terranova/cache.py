"""Caché de sobres con frescura (ADR-0008, F2.3).

Clave: herramienta, versión y entrada normalizada. Mientras el sobre tiene menos edad que el
`ttl_cache_s` de su fuente, se sirve desde caché (`servido_desde: cache`, sin descontar). Se guarda
más tiempo (`RETENCION`) para un solo uso: si la fuente cae, servirlo como `obsoleto`, con su
`consultado_en` original y un aviso. Nunca como si fuera actual.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
import time
from typing import Any, Protocol

RETENCION_S = 30 * 24 * 3600  # una copia vieja sirve de respaldo hasta 30 días


class Almacen(Protocol):
    async def leer(self, clave: str) -> dict[str, Any] | None: ...

    async def guardar(self, clave: str, valor: dict[str, Any], vida_s: int) -> None: ...


class AlmacenMemoria:
    """Para pruebas y una sola réplica. `reloj` se puede cambiar para simular el paso del tiempo."""

    def __init__(self) -> None:
        self._datos: dict[str, tuple[float, dict[str, Any]]] = {}
        self.reloj = time.time

    async def leer(self, clave: str) -> dict[str, Any] | None:
        entrada = self._datos.get(clave)
        if entrada is None or entrada[0] < self.reloj():
            return None
        return json.loads(json.dumps(entrada[1]))  # type: ignore[no-any-return]

    async def guardar(self, clave: str, valor: dict[str, Any], vida_s: int) -> None:
        self._datos[clave] = (self.reloj() + vida_s, json.loads(json.dumps(valor)))


class AlmacenRedis:
    """Redis compartido entre réplicas (ADR-0015). Se importa solo si se usa."""

    def __init__(self, url: str) -> None:
        redis: Any = importlib.import_module("redis.asyncio")  # extra opcional, sin tipos
        self._r = redis.from_url(url, decode_responses=True)

    async def leer(self, clave: str) -> dict[str, Any] | None:
        crudo = await self._r.get(clave)
        return json.loads(crudo) if crudo else None

    async def guardar(self, clave: str, valor: dict[str, Any], vida_s: int) -> None:
        await self._r.set(clave, json.dumps(valor, ensure_ascii=False), ex=vida_s)

    async def ping(self) -> None:
        await self._r.ping()


class AlmacenTolerante:
    """La caché ayuda, pero no es requisito: si Redis falla, se lee como «no hay» y no se guarda,
    y la consulta sigue hacia la fuente (antes, un Redis caído tumbaba todas las herramientas)."""

    def __init__(self, almacen: Almacen) -> None:
        self._almacen = almacen

    async def leer(self, clave: str) -> dict[str, Any] | None:
        try:
            return await self._almacen.leer(clave)
        except Exception:  # noqa: BLE001 — cualquier falla de la caché se trata como un fallo de caché
            _fallo("leer")
            return None

    async def guardar(self, clave: str, valor: dict[str, Any], vida_s: int) -> None:
        try:
            await self._almacen.guardar(clave, valor, vida_s)
        except Exception:  # noqa: BLE001
            _fallo("guardar")

    async def ping(self) -> None:
        probar = getattr(self._almacen, "ping", None)
        if probar is not None:
            await probar()


def _fallo(operacion: str) -> None:
    from terranova import metricas

    metricas.CACHE_FALLOS.inc()
    logging.getLogger("terranova.cache").warning("la caché falló al %s; sigue sin caché", operacion)


def clave(herramienta: str, version: int, entrada: dict[str, Any]) -> str:
    canonico = json.dumps(
        {"h": herramienta, "v": version, "e": entrada}, sort_keys=True, separators=(",", ":")
    )
    return "terranova:sobre:" + hashlib.sha256(canonico.encode()).hexdigest()
