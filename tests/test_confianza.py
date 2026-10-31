"""Lo que rompería la confianza de un cliente que paga (auditoría integral, 2026-10-31): nada
sale como un 500 en texto plano, `/listo` dice qué falla, la caché no tumba las herramientas y
las copias se reconectan solas."""

from typing import Any

import httpx
import pytest

from terranova import metricas, puerta
from terranova.app import Aplicacion, crear_api
from terranova.cache import AlmacenMemoria, AlmacenTolerante
from terranova.copias import AlmacenCopias


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class RegistroRoto:
    """Un registro de llaves cuya base no responde (Postgres caído)."""

    def verificar(self, llave: str) -> Any:
        raise ConnectionError("la base no responde")

    async def ping(self) -> None:
        raise ConnectionError("la base no responde")


class RegistroSano:
    async def ping(self) -> None:
        return None


@pytest.fixture
def registro_roto() -> Any:
    antes = puerta.ESTADO.registro
    puerta.ESTADO.registro = RegistroRoto()  # type: ignore[assignment]
    yield
    puerta.ESTADO.registro = antes


@pytest.mark.anyio
async def test_con_la_base_caida_la_llave_da_problem_json(registro_roto: Any) -> None:
    antes = metricas.ERRORES_INTERNOS._value.get()
    app = Aplicacion(crear_api(), {})
    transporte = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
        r = await c.post(
            "/v1/co/territorio/igac_predio_en_punto",
            json={"lon": -74.0, "lat": 4.8},
            headers={"Authorization": "Bearer rt_live_x"},
        )
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/problem+json")
    cuerpo = r.json()
    assert cuerpo["code"] == "error_interno" and cuerpo["solicitud_id"].startswith("req_")
    assert metricas.ERRORES_INTERNOS._value.get() == antes + 1


@pytest.mark.anyio
async def test_listo_dice_que_parte_falla(registro_roto: Any) -> None:
    transporte = httpx.ASGITransport(app=crear_api())
    async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
        r = await c.get("/listo")
    assert r.status_code == 503
    assert r.json()["estado"] == "no_listo" and r.json()["base"] == "falla"


@pytest.mark.anyio
async def test_listo_con_todo_arriba() -> None:
    antes = puerta.ESTADO.registro, puerta.ESTADO.almacen
    puerta.ESTADO.registro = RegistroSano()  # type: ignore[assignment]
    puerta.ESTADO.almacen = AlmacenTolerante(AlmacenMemoria())
    try:
        transporte = httpx.ASGITransport(app=crear_api())
        async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
            r = await c.get("/listo")
    finally:
        puerta.ESTADO.registro, puerta.ESTADO.almacen = antes
    assert r.status_code == 200 and r.json()["estado"] == "listo"


class CacheRota:
    async def leer(self, clave: str) -> dict[str, Any] | None:
        raise ConnectionError("redis caído")

    async def guardar(self, clave: str, valor: dict[str, Any], vida_s: int) -> None:
        raise ConnectionError("redis caído")


@pytest.mark.anyio
async def test_la_cache_caida_deja_pasar() -> None:
    antes = metricas.CACHE_FALLOS._value.get()
    cache = AlmacenTolerante(CacheRota())
    assert await cache.leer("k") is None
    await cache.guardar("k", {"x": 1}, 60)
    assert metricas.CACHE_FALLOS._value.get() == antes + 2


class ConexionFalsa:
    def __init__(self) -> None:
        self.closed = False
        self.broken = False


def test_las_copias_se_reconectan(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un reinicio de Postgres ya no deja las copias caídas hasta reiniciar la puerta."""
    abiertas: list[dict[str, Any]] = []

    class Psycopg:
        @staticmethod
        def connect(url: str, **kw: Any) -> ConexionFalsa:
            abiertas.append(kw)
            return ConexionFalsa()

    import importlib

    real = importlib.import_module
    monkeypatch.setattr(
        importlib, "import_module", lambda n: Psycopg if n == "psycopg" else real(n)
    )
    almacen = AlmacenCopias("postgresql://x", timeout_ms=15000)
    primera = almacen._c
    assert almacen._c is primera and len(abiertas) == 1
    assert abiertas[0]["autocommit"] is True
    assert abiertas[0]["options"] == "-c statement_timeout=15000"
    primera.broken = True
    assert almacen.rota()
    segunda = almacen._c
    assert segunda is not primera and len(abiertas) == 2 and not almacen.rota()
