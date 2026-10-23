"""F3.3: tasa por llave y saldo mensual por organización (ADR-0010)."""

import asyncio
import json
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import fakeredis
import httpx
import pytest

from terranova import cuota as modulo_cuota
from terranova import puerta
from terranova.app import crear_aplicacion
from terranova.conector import ErrorConector
from terranova.cuota import CuotaMemoria, CuotaRedis, mes, segundos_hasta_el_mes_siguiente
from terranova.identidad import RegistroSqlite


class Reloj:
    def __init__(self, t: float = datetime(2026, 10, 22, tzinfo=UTC).timestamp()) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _cuotas(reloj: Reloj) -> list[Any]:
    return [
        CuotaMemoria(capacidad=3, por_minuto=60, reloj=reloj),
        CuotaRedis(fakeredis.FakeAsyncRedis(), capacidad=3, por_minuto=60, reloj=reloj),
    ]


@pytest.mark.anyio
@pytest.mark.parametrize("cual", [0, 1], ids=["memoria", "redis"])
async def test_token_bucket(cual: int) -> None:
    reloj = Reloj()
    c = _cuotas(reloj)[cual]
    resultados = [await c.tomar_ficha("llv_a") for _ in range(4)]
    assert [ok for ok, _, _ in resultados] == [True, True, True, False]
    assert resultados[3][2] == pytest.approx(1.0, abs=0.01)  # 60/min: una ficha por segundo
    assert (await c.tomar_ficha("llv_b"))[0]  # otra llave, otra cubeta
    reloj.t += 1.0
    assert (await c.tomar_ficha("llv_a"))[0]


@pytest.mark.anyio
@pytest.mark.parametrize("cual", [0, 1], ids=["memoria", "redis"])
async def test_saldo_sin_sobreconsumo_con_50_llamadas_simultaneas(
    cual: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(modulo_cuota.NIVELES, "con_llave", 200)
    c = _cuotas(Reloj())[cual]
    resultados = await asyncio.gather(*(c.reservar("geoai", "con_llave", 10) for _ in range(50)))
    assert sum(ok for ok, _ in resultados) == 20  # 200 / 10, ni una más
    ok, queda = await c.reservar("geoai", "con_llave", 10)
    assert not ok and queda == 0
    await c.devolver("geoai", 10)
    assert (await c.reservar("geoai", "con_llave", 10))[0]


@pytest.mark.anyio
@pytest.mark.parametrize("cual", [0, 1], ids=["memoria", "redis"])
async def test_el_saldo_vuelve_con_el_mes(cual: int, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(modulo_cuota.NIVELES, "con_llave", 10)
    reloj = Reloj(datetime(2026, 10, 31, 23, 59, tzinfo=UTC).timestamp())
    c = _cuotas(reloj)[cual]
    assert (await c.reservar("geoai", "con_llave", 10))[0]
    assert not (await c.reservar("geoai", "con_llave", 10))[0]
    assert segundos_hasta_el_mes_siguiente(reloj.t) == 60
    reloj.t += 61
    assert mes(reloj.t) == "2026-11" and (await c.reservar("geoai", "con_llave", 10))[0]


def test_segundos_hasta_enero() -> None:
    diciembre = datetime(2026, 12, 31, 23, 0, tzinfo=UTC).timestamp()
    assert segundos_hasta_el_mes_siguiente(diciembre) == 3600


# --- por la aplicación ---------------------------------------------------------------------

DORADA = json.loads(
    (Path(__file__).parent / "doradas" / "igac_predio_en_punto.json").read_text(encoding="utf-8")
)
PREDIO = "/v1/co/territorio/igac_predio_en_punto"
CHIA = {"lon": -74.0262, "lat": 4.8619}


class Fuente:
    def __init__(self) -> None:
        self.caida = False

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        if self.caida:
            raise ErrorConector("HTTP 503", "fuente_no_disponible", 5)
        for ll in DORADA["llamadas"]:
            if ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise AssertionError(argumentos)


@pytest.fixture
def montaje(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[RegistroSqlite, Fuente]]:
    monkeypatch.setitem(modulo_cuota.NIVELES, "con_llave", 15)  # alcanza para una consulta de 10
    registro, fuente = RegistroSqlite(":memory:", "p" * 40), Fuente()
    puerta.usar_conectores({"arcgis-mcp": fuente})
    puerta.registro = registro
    puerta.cuota = CuotaMemoria(capacidad=3, por_minuto=60)
    try:
        yield registro, fuente
    finally:
        puerta.registro, puerta.cuota = None, None
        puerta.usar_conectores(None)


@pytest.fixture
async def cliente() -> AsyncIterator[httpx.AsyncClient]:
    transporte = httpx.ASGITransport(app=crear_aplicacion())
    async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
        yield c


@pytest.mark.anyio
async def test_saldo_agotado_es_429_y_una_falla_no_descuenta(
    montaje: tuple[RegistroSqlite, Fuente], cliente: httpx.AsyncClient
) -> None:
    registro, fuente = montaje
    cabecera = {
        "Authorization": f"Bearer {registro.crear('geoai', {'*'}, prueba=False, expira=None)}"
    }
    fuente.caida = True
    r = await cliente.post(PREDIO, json=CHIA, headers=cabecera)
    assert r.status_code == 502  # falló: no descuenta
    fuente.caida = False
    r = await cliente.post(PREDIO, json=CHIA, headers=cabecera)
    assert r.status_code == 200 and r.json()["creditos"] == 10
    assert "ratelimit" in r.headers and "ratelimit-policy" in r.headers
    r = await cliente.post(PREDIO, json=CHIA, headers=cabecera)
    assert r.status_code == 429 and r.json()["code"] == "saldo_agotado"
    assert int(r.headers["retry-after"]) > 0


@pytest.mark.anyio
async def test_limite_de_tasa_es_429_con_retry_after(
    montaje: tuple[RegistroSqlite, Fuente], cliente: httpx.AsyncClient
) -> None:
    registro, _ = montaje
    cabecera = {
        "Authorization": f"Bearer {registro.crear('otra', {'*'}, prueba=False, expira=None)}"
    }
    # cada petición consume una ficha, aunque sea inválida (400): la tasa protege la puerta
    codigos = [
        (await cliente.post(PREDIO, json={}, headers=cabecera)).status_code for _ in range(4)
    ]
    assert codigos == [400, 400, 400, 429]
    r = await cliente.post(PREDIO, json=CHIA, headers=cabecera)
    assert r.status_code == 429 and r.json()["code"] == "limite_tasa"
    assert r.headers["retry-after"] == "1" and "ratelimit" in r.headers


@pytest.mark.anyio
async def test_uso_del_mes(
    montaje: tuple[RegistroSqlite, Fuente], cliente: httpx.AsyncClient
) -> None:
    registro, _ = montaje
    cabecera = {
        "Authorization": f"Bearer {registro.crear('uso', {'*'}, prueba=False, expira=None)}"
    }
    assert (await cliente.get("/v1/uso")).status_code == 401
    antes = (await cliente.get("/v1/uso", headers=cabecera)).json()
    assert antes["usados"] == 0 and antes["limite"] == 15 and antes["org"] == "uso"
    assert (await cliente.post(PREDIO, json=CHIA, headers=cabecera)).status_code == 200
    despues = (await cliente.get("/v1/uso", headers=cabecera)).json()
    assert despues["usados"] == 10 and despues["disponibles"] == 5


@pytest.mark.anyio
async def test_abrir_y_listar_por_mcp_no_gasta_la_tasa(
    montaje: tuple[RegistroSqlite, Fuente],
) -> None:
    """Solo `tools/call` consulta una fuente: un cliente que abre varios perfiles (initialize,
    tools/list) no debe quedarse sin cupo antes de preguntar (F6, GEO Copilot)."""
    registro, _ = montaje
    cabecera = {
        "Authorization": f"Bearer {registro.crear('mcp', {'*'}, prueba=False, expira=None)}",
        "Accept": "application/json, text/event-stream",
    }
    aplicacion = crear_aplicacion()
    mcp = aplicacion.mcp["/mcp/territorio"]
    lista = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    llamada = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "igac_predio_en_punto", "arguments": {"lon": -74.0262, "lat": 4.8619}},
    }
    async with mcp.router.lifespan_context(mcp):
        transporte = httpx.ASGITransport(app=aplicacion)
        async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
            listas = [
                (await c.post("/mcp/territorio", json=lista, headers=cabecera)).status_code
                for _ in range(6)
            ]
            llamadas = [
                (await c.post("/mcp/territorio", json=llamada, headers=cabecera)).status_code
                for _ in range(4)
            ]
    assert listas == [200] * 6  # la cubeta es de 3: listar no la gasta
    assert llamadas[-1] == 429  # consultar sí
