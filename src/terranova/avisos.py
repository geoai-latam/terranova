"""Los avisos por correo a quien tiene una llave del alta: vence pronto o se le acaba el saldo.

Corren una vez al día (`terranova avisos`). Cada evento sale una sola vez: la tabla
`avisos_enviados` lo recuerda por correo, evento y periodo. Si un correo no sale, no se anota y se
intenta al otro día. Solo cubre las altas del sitio: son las que dejaron un correo verificado.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from terranova import correos
from terranova.alta import Correo
from terranova.bd import Conexion
from terranova.cuota import NIVELES, Cuota, mes, reinicio
from terranova.identidad import Registro

DIAS_ANTES_DE_VENCER = 3
PORCENTAJE_SALDO = 80

_log = logging.getLogger("terranova.avisos")


@dataclass(frozen=True)
class Alta:
    correo: str
    org: str
    nombre: str


class Avisos:
    def __init__(
        self,
        bd: Conexion | str | Path,
        registro: Registro,
        cuota: Cuota,
        correo: Correo,
        *,
        soporte: str = "soporte@terrnova.com",
    ) -> None:
        self._bd = bd if isinstance(bd, Conexion) else Conexion(bd)
        self._registro = registro
        self._cuota = cuota
        self._correo = correo
        self._soporte = soporte
        self._bd.ejecutar(
            """CREATE TABLE IF NOT EXISTS avisos_enviados (
                correo TEXT NOT NULL, evento TEXT NOT NULL, periodo TEXT NOT NULL,
                enviado TEXT NOT NULL, PRIMARY KEY (correo, evento, periodo))"""
        )

    def _altas(self) -> list[Alta]:
        filas, _ = self._bd.ejecutar(
            "SELECT correo, org, nombre FROM altas WHERE confirmada IS NOT NULL ORDER BY correo"
        )
        return [Alta(str(f[0]), str(f[1]), str(f[2])) for f in filas]

    def _enviado(self, correo: str, evento: str, periodo: str) -> bool:
        filas, _ = self._bd.ejecutar(
            "SELECT 1 FROM avisos_enviados WHERE correo = ? AND evento = ? AND periodo = ?",
            (correo, evento, periodo),
        )
        return bool(filas)

    def _anotar(self, correo: str, evento: str, periodo: str, ahora: datetime) -> None:
        self._bd.ejecutar(
            "INSERT INTO avisos_enviados VALUES (?, ?, ?, ?)",
            (correo, evento, periodo, ahora.isoformat()),
        )

    async def _mandar(
        self, alta: Alta, evento: str, periodo: str, mensaje: correos.Mensaje, ahora: datetime
    ) -> bool:
        try:
            await self._correo.enviar(alta.correo, mensaje)
        except Exception:  # noqa: BLE001 (un correo que no sale no detiene a los demás)
            _log.exception("no salió el aviso %s de %s", evento, alta.org)
            return False
        self._anotar(alta.correo, evento, periodo, ahora)
        return True

    def _vence(self, org: str, hoy: date) -> date | None:
        """La fecha más lejana entre las llaves vigentes; None si ya no tiene o una no vence."""
        fechas: list[date] = []
        for llave in self._registro.listar(org):
            if llave.revocada:
                continue
            if llave.expira is None:
                return None
            fechas.append(date.fromisoformat(llave.expira[:10]))
        vigentes = [f for f in fechas if f >= hoy]
        return max(vigentes) if vigentes else None

    async def correr(self, ahora: datetime | None = None) -> tuple[int, int]:
        """Revisa todas las altas y devuelve (avisos enviados, avisos que no salieron)."""
        ahora = ahora or datetime.now(UTC)
        hoy = ahora.date()
        en_mes = mes(ahora.timestamp())
        enviados = fallidos = 0
        niveles = {org: nivel for org, nivel, _ in self._registro.listar_orgs()}

        async def uno(alta: Alta, evento: str, periodo: str, mensaje: correos.Mensaje) -> None:
            nonlocal enviados, fallidos
            if await self._mandar(alta, evento, periodo, mensaje, ahora):
                enviados += 1
            else:
                fallidos += 1

        for alta in self._altas():
            vence = self._vence(alta.org, hoy)
            if vence is None:
                vigente = any(
                    not ll.revocada and ll.expira is None for ll in self._registro.listar(alta.org)
                )
                if not vigente:
                    continue  # sin llave vigente no hay nada que avisar
            elif vence - hoy <= timedelta(days=DIAS_ANTES_DE_VENCER):
                periodo = vence.isoformat()
                if not self._enviado(alta.correo, "vencimiento", periodo):
                    mensaje = correos.aviso_vencimiento(alta.nombre, vence, soporte=self._soporte)
                    await uno(alta, "vencimiento", periodo, mensaje)

            limite = NIVELES.get(niveles.get(alta.org, "con_llave"), NIVELES["con_llave"])
            usados = await self._cuota.usados(alta.org, en_mes)
            agotado = usados >= limite
            if not agotado and usados * 100 < limite * PORCENTAJE_SALDO:
                continue
            # el agotado reemplaza al de 80 %: quien saltó de 70 a 100 recibe uno solo
            evento = "saldo_agotado" if agotado else "saldo_bajo"
            ya = self._enviado(alta.correo, evento, en_mes)
            if ya or (not agotado and self._enviado(alta.correo, "saldo_agotado", en_mes)):
                continue
            mensaje = correos.aviso_saldo(
                alta.nombre,
                usados=min(usados, limite),
                limite=limite,
                reinicia=reinicio(ahora.timestamp()).date(),
                soporte=self._soporte,
            )
            await uno(alta, evento, en_mes, mensaje)
        return enviados, fallidos
