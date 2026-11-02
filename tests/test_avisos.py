"""Los avisos de vencimiento y de saldo: uno por evento, y uno que no salió se reintenta."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from terranova.alta import Altas
from terranova.avisos import Avisos
from terranova.correos import Mensaje
from terranova.cuota import NIVELES
from terranova.identidad import RegistroSql

ORG = "alta-prueba"
CORREO = "ana@ejemplo.co"
LIMITE = NIVELES["prueba"]
HOY = datetime(2026, 11, 10, 14, tzinfo=UTC)


class CorreoFalso:
    def __init__(self) -> None:
        self.salidos: list[Mensaje] = []
        self.caido = False

    async def enviar(self, destino: str, mensaje: Mensaje) -> None:
        if self.caido:
            raise OSError("smtp caído")
        assert destino == CORREO
        self.salidos.append(mensaje)


class CuotaFija:
    def __init__(self) -> None:
        self.gastado = 0

    async def usados(self, org: str, en_mes: str | None = None) -> int:
        return self.gastado


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def e(tmp_path: Path) -> tuple[Avisos, RegistroSql, CuotaFija, CorreoFalso]:
    bd = tmp_path / "t.db"
    registro = RegistroSql(bd, "p" * 40)
    altas = Altas(bd, registro, "p" * 40, None)
    altas._bd.ejecutar(
        "INSERT INTO altas VALUES (?, ?, 'ana', '', '', ?, ?, '1.2.3.4')",
        (CORREO, ORG, HOY.isoformat(), HOY.isoformat()),
    )
    registro.fijar_nivel(ORG, "prueba")
    cuota, correo = CuotaFija(), CorreoFalso()
    return Avisos(bd, registro, cuota, correo), registro, cuota, correo  # type: ignore[arg-type]


def _llave(registro: RegistroSql, dias: int | None) -> None:
    expira = None if dias is None else HOY.date() + timedelta(days=dias)
    registro.crear(ORG, {"*"}, prueba=False, expira=expira)


@pytest.mark.anyio
async def test_avisa_el_vencimiento_una_sola_vez(e: Any) -> None:
    avisos, registro, _, correo = e
    _llave(registro, 3)
    assert await avisos.correr(HOY) == (1, 0)
    assert await avisos.correr(HOY + timedelta(days=1)) == (0, 0)
    assert "vence" in correo.salidos[0].asunto.lower()
    assert "13-11-2026" in correo.salidos[0].texto


@pytest.mark.anyio
@pytest.mark.parametrize("dias", [4, None, -1])
async def test_no_avisa_si_falta_o_no_vence_o_ya_vencio(e: Any, dias: int | None) -> None:
    avisos, registro, _, _ = e
    _llave(registro, dias)
    assert await avisos.correr(HOY) == (0, 0)


@pytest.mark.anyio
async def test_una_llave_revocada_no_recibe_avisos(e: Any) -> None:
    avisos, registro, cuota, _ = e
    _llave(registro, 2)
    registro.revocar(registro.listar(ORG)[0].llave_id)
    cuota.gastado = LIMITE
    assert await avisos.correr(HOY) == (0, 0)


@pytest.mark.anyio
async def test_saldo_bajo_y_luego_agotado_uno_de_cada_uno(e: Any) -> None:
    avisos, registro, cuota, correo = e
    _llave(registro, 10)
    cuota.gastado = LIMITE * 79 // 100
    assert await avisos.correr(HOY) == (0, 0)
    cuota.gastado = LIMITE * 8 // 10
    assert await avisos.correr(HOY) == (1, 0)
    assert await avisos.correr(HOY) == (0, 0)
    cuota.gastado = LIMITE
    assert await avisos.correr(HOY) == (1, 0)
    assert await avisos.correr(HOY) == (0, 0)
    assert "01-12-2026" in correo.salidos[-1].texto  # cuándo se renueva
    # otro mes, otro periodo
    assert await avisos.correr(datetime(2026, 12, 2, 14, tzinfo=UTC)) == (1, 0)


@pytest.mark.anyio
async def test_quien_salta_al_agotado_recibe_un_solo_aviso(e: Any) -> None:
    avisos, registro, cuota, _ = e
    _llave(registro, 10)
    cuota.gastado = LIMITE + 5
    assert await avisos.correr(HOY) == (1, 0)
    assert await avisos.correr(HOY) == (0, 0)


@pytest.mark.anyio
async def test_uno_que_no_salio_se_reintenta(e: Any) -> None:
    avisos, registro, _, correo = e
    _llave(registro, 1)
    correo.caido = True
    assert await avisos.correr(HOY) == (0, 1)
    correo.caido = False
    assert await avisos.correr(HOY) == (1, 0)


def test_las_fechas_del_aviso_no_inventan_datos() -> None:
    from terranova import correos

    m = correos.aviso_saldo(
        "Ana", usados=240, limite=300, reinicia=date(2026, 12, 1), soporte="s@t"
    )
    assert "240" in m.texto and "300" in m.texto and "ana" not in m.asunto.lower()
