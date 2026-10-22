"""F3.1: el adaptador REST generado del catálogo y la paridad REST ≡ MCP (ADR-0004, ADR-0011)."""

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastmcp import Client

from terranova import puerta
from terranova.app import Aplicacion, crear_api, crear_aplicacion
from terranova.conector import ErrorConector

DORADAS = Path(__file__).parent / "doradas"
CATALOGO = puerta.CATALOGO
API = crear_api()


class Grabado:
    def __init__(self, nombre: str, llamadas: list[dict[str, Any]]) -> None:
        self.grabadas = [ll for ll in llamadas if ll["conector"] == nombre]

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.grabadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise AssertionError(f"no grabada: {herramienta} {argumentos}")


def _con_grabacion(herramienta: str) -> dict[str, Any]:
    llamadas = json.loads((DORADAS / f"{herramienta}.json").read_text(encoding="utf-8"))["llamadas"]
    return {n: Grabado(n, llamadas) for n in {ll["conector"] for ll in llamadas}}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def rest() -> AsyncIterator[httpx.AsyncClient]:
    transporte = httpx.ASGITransport(app=API)
    async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as cliente:
        yield cliente


@pytest.fixture(autouse=True)
def plan_evaluacion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERRANOVA_PLAN", "evaluacion")


def _sin_lo_propio_de_cada_llamada(sobre: dict[str, Any]) -> dict[str, Any]:
    copia: dict[str, Any] = json.loads(json.dumps(sobre))
    copia.pop("solicitud_id")
    for p in copia["procedencia"]:
        p.pop("consultado_en")
    return copia


@pytest.mark.anyio
@pytest.mark.parametrize("herramienta", sorted(CATALOGO.herramientas))
async def test_paridad_rest_mcp(rest: httpx.AsyncClient, herramienta: str) -> None:
    h = CATALOGO.herramientas[herramienta]
    puerta.usar_conectores(_con_grabacion(herramienta))
    try:
        r = await rest.post(f"/v1/co/{h.familia}/{h.id}", json=h.canario.entrada)
        assert r.status_code == 200, r.text
        async with Client(puerta.puerta) as mcp:
            m = await mcp.call_tool(h.id, h.canario.entrada)
    finally:
        puerta.usar_conectores(None)
    assert m.structured_content is not None
    assert _sin_lo_propio_de_cada_llamada(r.json()) == _sin_lo_propio_de_cada_llamada(
        m.structured_content
    )


@pytest.mark.anyio
async def test_openapi_una_operacion_por_herramienta_con_su_esquema(
    rest: httpx.AsyncClient,
) -> None:
    doc = (await rest.get("/openapi.json")).json()
    operaciones = {
        op["operationId"]: (ruta, op)
        for ruta, metodos in doc["paths"].items()
        for op in metodos.values()
    }
    assert set(CATALOGO.herramientas) <= set(operaciones)
    ruta, op = operaciones["igac_predio_por_codigo"]
    assert ruta == "/v1/co/territorio/igac_predio_por_codigo"
    esquema = op["requestBody"]["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[1]
    codigo = doc["components"]["schemas"][esquema]["properties"]["codigo"]
    assert codigo["pattern"] == "^[0-9]{30}$"
    assert (
        "502" in op["responses"] and "application/problem+json" in op["responses"]["502"]["content"]
    )


@pytest.mark.anyio
async def test_entrada_invalida_es_problem_json_400(rest: httpx.AsyncClient) -> None:
    r = await rest.post("/v1/co/territorio/igac_predio_por_codigo", json={"codigo": "' OR 1=1 --"})
    assert r.status_code == 400 and r.headers["content-type"] == "application/problem+json"
    p = r.json()
    assert p["code"] == "parametro_invalido" and p["param"] == "codigo" and p["status"] == 400
    assert p["solicitud_id"].startswith("req_")


@pytest.mark.anyio
async def test_licencia_por_verificar_con_llave_normal_es_403(
    rest: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TERRANOVA_PLAN", "normal")
    puerta.usar_conectores({})
    try:
        r = await rest.post(
            "/v1/co/estadisticas/dane_poblacion_municipio", json={"municipio_divipola": "11001"}
        )
    finally:
        puerta.usar_conectores(None)
    assert r.status_code == 403 and r.json()["code"] == "licencia_no_habilitada"


class Caido:
    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        raise ErrorConector("HTTP 503", "fuente_no_disponible", 5)


@pytest.mark.anyio
async def test_fuente_caida_es_502_con_retry_after(rest: httpx.AsyncClient) -> None:
    puerta.usar_conectores({"arcgis-mcp": Caido()})
    try:
        r = await rest.post(
            "/v1/co/territorio/igac_predio_en_punto", json={"lon": -74.0, "lat": 4.8}
        )
    finally:
        puerta.usar_conectores(None)
    assert r.status_code == 502 and r.headers["retry-after"] == "5"
    assert r.json()["code"] == "fuente_no_disponible"


@pytest.mark.anyio
async def test_catalogo_publico(rest: httpx.AsyncClient) -> None:
    fuentes = (await rest.get("/v1/fuentes")).json()
    assert {f["id"] for f in fuentes} == set(CATALOGO.fuentes)
    runap = (await rest.get("/v1/fuentes/pnn.runap")).json()
    assert runap["licencia"]["spdx"] == "CC-BY-SA-4.0" and runap["uso_comercial"] == "si"
    assert (await rest.get("/v1/fuentes/no.existe")).status_code == 404
    herramientas = (await rest.get("/v1/herramientas")).json()
    assert {h["id"] for h in herramientas} == set(CATALOGO.herramientas)


@pytest.mark.anyio
async def test_la_aplicacion_reparte_mcp_y_rest() -> None:
    llegadas: list[str] = []

    def marca(nombre: str) -> Any:
        async def app(scope: Any, receive: Any, send: Any) -> None:
            llegadas.append(nombre)

        return app

    aplicacion = Aplicacion(
        marca("api"), {"/mcp": marca("mcp"), "/mcp/territorio": marca("territorio")}
    )
    for ruta in ("/mcp", "/mcp/", "/mcp/territorio", "/v1/fuentes", "/mcpx"):
        await aplicacion({"type": "http", "path": ruta}, None, None)
    assert llegadas == ["mcp", "mcp", "territorio", "api", "api"]
    rutas = set(crear_aplicacion().mcp)
    assert rutas == {"/mcp"} | {f"/mcp/{f}" for f in puerta.FAMILIAS}
