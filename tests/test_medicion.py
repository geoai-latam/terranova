"""F3.4: un evento de uso por solicitud; idempotencia (E2E-10); medir nunca tumba la respuesta."""

import json
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from terranova import puerta
from terranova.app import crear_aplicacion
from terranova.cache import AlmacenMemoria
from terranova.conector import ErrorConector
from terranova.cuota import CuotaMemoria
from terranova.identidad import RegistroSqlite
from terranova.medicion import Evento, OutboxSqlite

DORADA = json.loads(
    (Path(__file__).parent / "doradas" / "igac_predio_en_punto.json").read_text(encoding="utf-8")
)
PREDIO = "/v1/co/territorio/igac_predio_en_punto"
CHIA = {"lon": -74.0262, "lat": 4.8619}


class Fuente:
    def __init__(self) -> None:
        self.caida = False
        self.llamadas = 0

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        self.llamadas += 1
        if self.caida:
            raise ErrorConector("HTTP 503", "fuente_no_disponible", 5)
        for ll in DORADA["llamadas"]:
            if ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise AssertionError(argumentos)


class OutboxRoto:
    def registrar(self, evento: Evento) -> None:
        raise OSError("disco lleno")

    def eventos(self, org: str | None = None) -> list[Evento]:
        return []


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def montaje() -> Iterator[tuple[str, Fuente, OutboxSqlite, CuotaMemoria]]:
    registro, fuente = RegistroSqlite(":memory:", "p" * 40), Fuente()
    outbox, cuota = OutboxSqlite(":memory:"), CuotaMemoria(capacidad=100)
    puerta.usar_conectores({"arcgis-mcp": fuente})
    puerta.ESTADO.registro, puerta.ESTADO.cuota, puerta.ESTADO.outbox = registro, cuota, outbox
    puerta.ESTADO.almacen = AlmacenMemoria()
    llave = registro.crear("geoai", {"*"}, prueba=False, expira=None)
    try:
        yield llave, fuente, outbox, cuota
    finally:
        puerta.ESTADO.registro = puerta.ESTADO.cuota = puerta.ESTADO.outbox = (
            puerta.ESTADO.almacen
        ) = None
        puerta.usar_conectores(None)


@pytest.fixture
async def cliente() -> AsyncIterator[httpx.AsyncClient]:
    transporte = httpx.ASGITransport(app=crear_aplicacion())
    async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
        yield c


@pytest.mark.anyio
async def test_un_evento_por_solicitud_con_lo_cobrado(
    montaje: tuple[str, Fuente, OutboxSqlite, CuotaMemoria], cliente: httpx.AsyncClient
) -> None:
    llave, fuente, outbox, _ = montaje
    cab = {"Authorization": f"Bearer {llave}"}
    r = await cliente.post(PREDIO, json=CHIA, headers=cab)
    assert r.status_code == 200
    r2 = await cliente.post(PREDIO, json=CHIA, headers=cab)  # caché: no cobra
    fuente.caida = True
    r3 = await cliente.post(PREDIO, json={"lon": -75.0, "lat": 5.0}, headers=cab)  # falla
    assert r3.status_code == 502
    e = outbox.eventos("geoai")
    assert [(x.creditos, x.resultado, x.servido_desde) for x in e] == [
        (10, "encontrado", "fuente"),
        (0, "encontrado", "cache"),
        (0, "fuente_no_disponible", None),
    ]
    assert (
        e[0].solicitud_id == r.json()["solicitud_id"]
        and e[1].solicitud_id == r2.json()["solicitud_id"]
    )
    assert len({x.solicitud_id for x in e}) == 3


@pytest.mark.anyio
async def test_reintento_con_idempotency_key_un_solo_evento(
    montaje: tuple[str, Fuente, OutboxSqlite, CuotaMemoria], cliente: httpx.AsyncClient
) -> None:
    """E2E-10: el mismo Idempotency-Key no vuelve a ejecutar, cobrar ni medir."""
    llave, fuente, outbox, cuota = montaje
    cab = {"Authorization": f"Bearer {llave}", "Idempotency-Key": "pedido-123"}
    r1 = await cliente.post(PREDIO, json=CHIA, headers=cab)
    llamadas = fuente.llamadas
    r2 = await cliente.post(PREDIO, json=CHIA, headers=cab)
    assert r1.json() == r2.json() and r2.headers["idempotent-replayed"] == "true"
    assert fuente.llamadas == llamadas and len(outbox.eventos("geoai")) == 1
    assert cuota._usados and sum(cuota._usados.values()) == 10
    otra = await cliente.post(PREDIO, json={"lon": -74.0, "lat": 4.0}, headers=cab)
    assert otra.status_code == 400 and otra.json()["param"] == "Idempotency-Key"


@pytest.mark.anyio
async def test_si_el_outbox_falla_la_respuesta_sale_igual(
    montaje: tuple[str, Fuente, OutboxSqlite, CuotaMemoria], cliente: httpx.AsyncClient
) -> None:
    llave, _, _, _ = montaje
    puerta.ESTADO.outbox = OutboxRoto()
    r = await cliente.post(PREDIO, json=CHIA, headers={"Authorization": f"Bearer {llave}"})
    assert r.status_code == 200 and r.json()["estado"] == "encontrado"


def test_el_mismo_solicitud_id_no_se_duplica() -> None:
    o = OutboxSqlite(":memory:")
    e = Evento("req_x", "geoai", "llv_1", "h", 10, "encontrado", "fuente", "2026-10-22T00:00:00Z")
    o.registrar(e)
    o.registrar(e)
    assert len(o.eventos()) == 1
