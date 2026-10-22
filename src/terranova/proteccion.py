"""Protección de las fuentes (F2.4): cortacircuitos, bulkhead y un reintento con jitter.

- **Cortacircuitos** por fuente: tras `umbral` caídas seguidas se abre `enfriamiento_s`; abierto,
  `fuente_no_disponible` sale al instante y sin tocar la fuente. Pasado el enfriamiento se deja un
  intento (medio abierto): si falla, se abre otra vez; si sale bien, se cierra.
- **Bulkhead**: como mucho `concurrencia` llamadas a la vez por fuente. Protege los servidores del
  Estado y evita que una fuente lenta acapare la puerta.
- **Reintento**: uno, con jitter, solo ante `fuente_no_disponible` (todas son lecturas). Un tiempo
  agotado no se reintenta: duplicaría la espera.
"""

from __future__ import annotations

import asyncio
import math
import random
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar

from terranova.errores import ErrorEjecucion

T = TypeVar("T")
CAIDAS = frozenset({"fuente_no_disponible", "fuente_lenta"})


@dataclass
class Circuito:
    fallos: int = 0
    abierto_hasta: float = 0.0


class Proteccion:
    def __init__(
        self,
        *,
        umbral: int = 3,
        enfriamiento_s: float = 30.0,
        concurrencia: int = 4,
        espera_cupo_s: float = 10.0,
        reloj: Callable[[], float] = time.monotonic,
        dormir: Callable[[float], Awaitable[None]] = asyncio.sleep,
        azar: Callable[[], float] = random.random,
    ) -> None:
        self.umbral = umbral
        self.enfriamiento_s = enfriamiento_s
        self.espera_cupo_s = espera_cupo_s
        self.reloj = reloj
        self.dormir = dormir
        self.azar = azar
        self.circuitos: dict[str, Circuito] = defaultdict(Circuito)
        self._cupos: dict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(concurrencia)
        )

    def abierto(self, fuente_id: str) -> bool:
        return self.circuitos[fuente_id].abierto_hasta > self.reloj()

    async def llamar(self, fuente_id: str, fn: Callable[[], Awaitable[T]]) -> T:
        c = self.circuitos[fuente_id]
        resta = c.abierto_hasta - self.reloj()
        if resta > 0:
            raise ErrorEjecucion(
                "fuente_no_disponible",
                f"{fuente_id}: falló {self.umbral} veces seguidas; se protege la fuente",
                math.ceil(resta),
            )
        cupo = self._cupos[fuente_id]
        try:
            await asyncio.wait_for(cupo.acquire(), timeout=self.espera_cupo_s)
        except TimeoutError as exc:
            raise ErrorEjecucion(
                "fuente_no_disponible", f"{fuente_id}: demasiadas consultas a la vez", 5
            ) from exc
        try:
            for intento in (1, 2):
                try:
                    resultado = await fn()
                except ErrorEjecucion as exc:
                    if exc.codigo not in CAIDAS:
                        raise
                    if intento == 1 and exc.codigo == "fuente_no_disponible":
                        await self.dormir(0.1 + 0.4 * self.azar())
                        continue
                    self._fallo(c)
                    raise
                c.fallos = 0
                return resultado
            raise AssertionError("inalcanzable")
        finally:
            cupo.release()

    def _fallo(self, c: Circuito) -> None:
        c.fallos += 1
        if c.fallos >= self.umbral:
            c.abierto_hasta = self.reloj() + self.enfriamiento_s
            # medio abierto: pasado el enfriamiento, un solo fallo más lo vuelve a abrir
            c.fallos = self.umbral - 1
