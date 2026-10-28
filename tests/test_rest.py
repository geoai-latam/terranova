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
    # Ya no hay fichas por_verificar reales (enmienda ADR-0019): se fuerza una sintética.
    fid = CATALOGO.herramientas["dane_poblacion_municipio"].fuente
    f = CATALOGO.fuentes[fid]
    sin_ver = f.model_copy(
        update={
            "uso_comercial": "por_verificar",
            "clasificacion_licencia": "verde",
            "licencia": f.licencia.model_copy(update={"spdx": None, "verificada": None}),
        }
    )
    cat = CATALOGO.model_copy(update={"fuentes": {**CATALOGO.fuentes, fid: sin_ver}})
    monkeypatch.setattr(puerta, "CATALOGO", cat)
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


@pytest.mark.anyio
async def test_mcp_sin_sesion_lo_atiende_cualquier_replica() -> None:
    """Dos réplicas tras Caddy, sin afinidad: una petición sin sesión previa (la que cae en la
    réplica que no la abrió) debe funcionar igual."""
    mcp = crear_aplicacion().mcp["/mcp/justicia"]
    async with mcp.router.lifespan_context(mcp):
        transporte = httpx.ASGITransport(app=mcp)
        async with httpx.AsyncClient(transport=transporte, base_url="http://127.0.0.1") as c:
            r = await c.post(
                "/mcp/justicia",
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                headers={"Accept": "application/json, text/event-stream"},
            )
    assert r.status_code == 200, r.text
    assert "dane_divipola_buscar" in r.text


@pytest.mark.anyio
async def test_llms_txt_y_tarjeta_mcp(rest: httpx.AsyncClient) -> None:
    llms = await rest.get("/llms.txt")
    assert llms.status_code == 200 and llms.text.startswith("# Terranova")
    for h in CATALOGO.herramientas.values():
        assert f"/v1/co/{h.familia}/{h.id}" in llms.text
    tarjeta = (await rest.get("/.well-known/mcp/server-card.json")).json()
    assert (
        tarjeta["transport"]["endpoint"] == "/mcp" and "2026-07-28" in tarjeta["protocolVersions"]
    )
    assert {t["name"] for t in tarjeta["tools"]} == set(CATALOGO.herramientas) | {"ficha_lugar"}
    assert {p["endpoint"] for p in tarjeta["profiles"]} == {f"/mcp/{f}" for f in puerta.FAMILIAS}


class ArcgisVacio:
    """ArcGIS responde sin rasgos; los demás conectores no están: la ficha sale `parcial`."""

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        return {
            "geo_result": "1",
            "artifacts": [
                {
                    "kind": "feature_collection",
                    "crs": "EPSG:4326",
                    "data": {"type": "FeatureCollection", "features": []},
                }
            ],
            "facts": {"total_en_servicio": 0, "completo": True},
        }


@pytest.mark.anyio
async def test_ficha_por_rest_igual_que_por_mcp(rest: httpx.AsyncClient) -> None:
    puerta.usar_conectores({"arcgis-mcp": ArcgisVacio()})
    try:
        r = await rest.post("/v1/fichas", json={"lon": -74.0262, "lat": 4.8619})
        async with Client(puerta.crear_servidor(con_ciclo=False)) as mcp:
            m = await mcp.call_tool("ficha_lugar", {"lon": -74.0262, "lat": 4.8619})
    finally:
        puerta.usar_conectores(None)
    assert r.status_code == 200, r.text
    sobre = r.json()
    assert sobre["estado"] == "parcial" and sobre["herramienta"] == "ficha_lugar@1"
    assert sobre["datos"]["predio"]["estado"] == "no_encontrado"
    caidas = {e["fuente_id"] for e in sobre["errores"]}
    assert "esa.worldcover" in caidas and "usgs.sismos" in caidas
    assert caidas <= {p["fuente_id"] for p in sobre["procedencia"]}  # regla 3
    assert m.structured_content is not None
    assert _sin_lo_propio_de_cada_llamada(m.structured_content) == _sin_lo_propio_de_cada_llamada(
        sobre
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"lon": -74.0},
        {"lon": -74.0, "lat": 4.8, "codigo": "1" * 30},
        {"lon": False, "lat": 4},
        {"codigo": "1" * 30, "lat": None},
    ],
)
async def test_ficha_entrada_invalida(rest: httpx.AsyncClient, cuerpo: dict[str, Any]) -> None:
    puerta.usar_conectores({})
    try:
        r = await rest.post("/v1/fichas", json=cuerpo)
    finally:
        puerta.usar_conectores(None)
    assert r.status_code == 400 and r.json()["code"] == "parametro_invalido"
