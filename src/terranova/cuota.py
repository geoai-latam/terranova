"""Cuota (ADR-0010, F3.3): tasa por llave y saldo mensual de créditos por organización.

- **Tasa**: token bucket por llave (`capacidad` de ráfaga, `por_minuto` de reposición). Sin fichas,
  429 `limite_tasa` con `Retry-After`.
- **Saldo**: créditos del mes por organización según su nivel. El costo se RESERVA de forma atómica
  antes de llamar a la fuente y se devuelve lo que no se cobró (error, caché, fuera de cobertura):
  con llamadas simultáneas no hay sobreconsumo. Sin saldo, 402 `saldo_agotado` hasta el mes
  siguiente (ADR-0029).

El saldo se entrega el día 1 de cada mes (UTC) y no se acumula: lo no gastado se pierde.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol

# Créditos al mes por nivel (ADR-0029). `con_llave` es el gratis; `ampliado`, el de entidades
# públicas, academia y uso interno; los demás, los planes de pago.
NIVELES = {
    "con_llave": 1_500,
    "basico": 25_000,
    "pro": 110_000,
    "empresa": 375_000,
    "escala": 1_100_000,
    "ampliado": 200_000,
}


def mes(ahora: float) -> str:
    return datetime.fromtimestamp(ahora, UTC).strftime("%Y-%m")


def reinicio(ahora: float) -> datetime:
    """Cuándo se renueva el saldo: el día 1 del mes siguiente, a las 00:00 UTC."""
    d = datetime.fromtimestamp(ahora, UTC)
    return datetime(d.year + (d.month == 12), d.month % 12 + 1, 1, tzinfo=UTC)


def segundos_hasta_el_mes_siguiente(ahora: float) -> int:
    return max(1, math.ceil(reinicio(ahora).timestamp() - ahora))


class Cuota(Protocol):
    async def tomar_ficha(self, llave_id: str) -> tuple[bool, int, float]:
        """(permitido, fichas que quedan, segundos hasta la próxima ficha)."""
        ...

    async def reservar(self, org: str, nivel: str, creditos: int) -> tuple[bool, int]:
        """(reservado, saldo que queda)."""
        ...

    async def devolver(self, org: str, creditos: int) -> None: ...

    async def usados(self, org: str, en_mes: str | None = None) -> int:
        """Créditos usados por la organización en `en_mes` (AAAA-MM; por defecto, este mes)."""
        ...


class CuotaMemoria:
    """Una réplica (y pruebas). `reloj` se puede cambiar."""

    def __init__(
        self, *, capacidad: int = 20, por_minuto: int = 60, reloj: Callable[[], float] = time.time
    ) -> None:
        self.capacidad = capacidad
        self.ritmo = por_minuto / 60.0
        self.reloj = reloj
        self._cubetas: dict[str, tuple[float, float]] = {}
        self._usados: dict[str, int] = {}
        self._candado = asyncio.Lock()

    async def tomar_ficha(self, llave_id: str) -> tuple[bool, int, float]:
        async with self._candado:
            ahora = self.reloj()
            fichas, antes = self._cubetas.get(llave_id, (float(self.capacidad), ahora))
            fichas = min(self.capacidad, fichas + (ahora - antes) * self.ritmo)
            if fichas < 1:
                self._cubetas[llave_id] = (fichas, ahora)
                return False, 0, (1 - fichas) / self.ritmo
            self._cubetas[llave_id] = (fichas - 1, ahora)
            return True, int(fichas - 1), 0.0

    async def reservar(self, org: str, nivel: str, creditos: int) -> tuple[bool, int]:
        async with self._candado:
            clave = f"{org}:{mes(self.reloj())}"
            usados = self._usados.get(clave, 0)
            limite = NIVELES.get(nivel, NIVELES["con_llave"])
            if usados + creditos > limite:
                return False, limite - usados
            self._usados[clave] = usados + creditos
            return True, limite - usados - creditos

    async def devolver(self, org: str, creditos: int) -> None:
        if creditos <= 0:
            return
        async with self._candado:
            clave = f"{org}:{mes(self.reloj())}"
            self._usados[clave] = max(0, self._usados.get(clave, 0) - creditos)

    async def usados(self, org: str, en_mes: str | None = None) -> int:
        return self._usados.get(f"{org}:{en_mes or mes(self.reloj())}", 0)


# Atómicos en Redis: compartidos entre réplicas.
_FICHA = """
local cap, ritmo, ahora = tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
local d = redis.call('HMGET', KEYS[1], 'f', 't')
local f, t = tonumber(d[1]) or cap, tonumber(d[2]) or ahora
f = math.min(cap, f + (ahora - t) * ritmo)
local ok = 0
if f >= 1 then f = f - 1; ok = 1 end
redis.call('HSET', KEYS[1], 'f', f, 't', ahora)
redis.call('EXPIRE', KEYS[1], 3600)
return {ok, tostring(f)}
"""
_RESERVA = """
local usados = tonumber(redis.call('GET', KEYS[1]) or '0')
local limite, c = tonumber(ARGV[1]), tonumber(ARGV[2])
if usados + c > limite then return {0, limite - usados} end
redis.call('INCRBY', KEYS[1], c)
redis.call('EXPIRE', KEYS[1], 40 * 24 * 3600)
return {1, limite - usados - c}
"""


class CuotaRedis:
    def __init__(
        self,
        redis: Any,
        *,
        capacidad: int = 20,
        por_minuto: int = 60,
        reloj: Callable[[], float] = time.time,
    ) -> None:
        self._r = redis
        self.capacidad = capacidad
        self.ritmo = por_minuto / 60.0
        self.reloj = reloj

    async def tomar_ficha(self, llave_id: str) -> tuple[bool, int, float]:
        ok, fichas = await self._r.eval(
            _FICHA, 1, f"terranova:tasa:{llave_id}", self.capacidad, self.ritmo, self.reloj()
        )
        f = float(fichas)
        return bool(ok), int(f), 0.0 if ok else (1 - f) / self.ritmo

    async def reservar(self, org: str, nivel: str, creditos: int) -> tuple[bool, int]:
        limite = NIVELES.get(nivel, NIVELES["con_llave"])
        clave = f"terranova:saldo:{org}:{mes(self.reloj())}"
        ok, queda = await self._r.eval(_RESERVA, 1, clave, limite, creditos)
        return bool(ok), int(queda)

    async def devolver(self, org: str, creditos: int) -> None:
        if creditos > 0:
            await self._r.decrby(f"terranova:saldo:{org}:{mes(self.reloj())}", creditos)

    async def usados(self, org: str, en_mes: str | None = None) -> int:
        # el saldo de un mes vive 40 días en Redis; después, solo queda la medición
        return int(await self._r.get(f"terranova:saldo:{org}:{en_mes or mes(self.reloj())}") or 0)


def cuota_desde_entorno(redis_url: str | None) -> Cuota:
    """Redis si hay `TERRANOVA_REDIS_URL` (compartida entre réplicas); si no, en memoria."""
    import importlib
    import os

    capacidad = int(os.environ.get("TERRANOVA_RAFAGA", "20"))
    por_minuto = int(os.environ.get("TERRANOVA_POR_MINUTO", "60"))
    if redis_url:
        redis: Any = importlib.import_module("redis.asyncio")  # extra opcional, sin tipos
        return CuotaRedis(redis.from_url(redis_url), capacidad=capacidad, por_minuto=por_minuto)
    return CuotaMemoria(capacidad=capacidad, por_minuto=por_minuto)
