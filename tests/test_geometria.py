"""ADR-0032: la geometría completa bajo pedido; por defecto, cada polígono como su envolvente."""

from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from test_puerta import CHIA, PREDIO, PREDIO_CHIA, ConectorFalso

from terranova import puerta
from terranova.app import crear_api
from terranova.contrato import AVISO_GEOMETRIA, GEOMETRIA, Sobre, resumir_geometria

ANILLO = [[-74.03, 4.86], [-74.02, 4.86], [-74.02, 4.87], [-74.03, 4.87], [-74.03, 4.86]]
PREDIO_POLIGONO = PREDIO_CHIA | {"geometry": {"type": "Polygon", "coordinates": [ANILLO]}}
SIN_GEOMETRIA = next(
    h for h, f in sorted(puerta.CATALOGO.herramientas.items()) if not puerta.trae_geometria(f)
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def plan_evaluacion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERRANOVA_PLAN", "evaluacion")


@pytest.fixture
async def mcp() -> AsyncIterator[Client[Any]]:
    puerta.usar_conectores({"arcgis-mcp": ConectorFalso({14: [PREDIO_POLIGONO]})})
    try:
        async with Client(puerta.puerta) as cliente:
            yield cliente
    finally:
        puerta.usar_conectores(None)


def _rasgo(sobre: Sobre) -> dict[str, Any]:
    assert sobre.geo_result is not None
    rasgo: dict[str, Any] = sobre.geo_result.artifacts[0].data["features"][0]
    return rasgo


@pytest.mark.anyio
async def test_por_defecto_el_poligono_es_su_envolvente(mcp: Client[Any]) -> None:
    sobre = Sobre.model_validate((await mcp.call_tool(PREDIO, CHIA)).structured_content)
    rasgo = _rasgo(sobre)
    assert rasgo["geometry"] is None
    assert rasgo["bbox"] == [-74.03, 4.86, -74.02, 4.87]
    assert rasgo["properties"]["codigo_predial"] == sobre.datos["codigo_predial"]
    assert AVISO_GEOMETRIA in sobre.avisos


@pytest.mark.anyio
async def test_con_geometria_true_viene_completa(mcp: Client[Any]) -> None:
    r = await mcp.call_tool(PREDIO, CHIA | {GEOMETRIA: True})
    sobre = Sobre.model_validate(r.structured_content)
    assert _rasgo(sobre)["geometry"]["coordinates"] == [ANILLO]
    assert AVISO_GEOMETRIA not in sobre.avisos


@pytest.mark.anyio
async def test_geometria_solo_en_las_herramientas_que_la_traen(mcp: Client[Any]) -> None:
    esquemas = {t.name: t.input_schema for t in await mcp.list_tools()}
    assert GEOMETRIA in esquemas[PREDIO]["properties"]
    assert GEOMETRIA not in esquemas[PREDIO]["required"]
    assert GEOMETRIA in esquemas["ficha_lugar"]["properties"]
    assert GEOMETRIA not in esquemas[SIN_GEOMETRIA]["properties"]
    with pytest.raises(ToolError, match="parametro_invalido: geometria"):
        await mcp.call_tool(PREDIO, CHIA | {GEOMETRIA: "si"})


@pytest.mark.anyio
async def test_rest_resume_igual_que_mcp() -> None:
    puerta.usar_conectores({"arcgis-mcp": ConectorFalso({14: [PREDIO_POLIGONO]})})
    transporte = httpx.ASGITransport(app=crear_api())
    try:
        async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as rest:
            ruta = f"/v1/co/territorio/{PREDIO}"
            resumido = (await rest.post(ruta, json=CHIA)).json()
            completo = (await rest.post(ruta, json=CHIA | {GEOMETRIA: True})).json()
            otro = await rest.post(ruta, json=CHIA | {GEOMETRIA: 1})
    finally:
        puerta.usar_conectores(None)
    assert _rasgo(Sobre.model_validate(resumido))["bbox"] == [-74.03, 4.86, -74.02, 4.87]
    assert _rasgo(Sobre.model_validate(completo))["geometry"]["type"] == "Polygon"
    assert otro.status_code == 400


@pytest.mark.anyio
async def test_los_puntos_quedan_y_datos_no_cambia() -> None:
    puerta.usar_conectores({"arcgis-mcp": ConectorFalso({14: [PREDIO_CHIA]})})  # un punto
    try:
        punto = await puerta.ejecutar(PREDIO, CHIA)
        poligono_completo = await _completo()
    finally:
        puerta.usar_conectores(None)
    assert _rasgo(punto)["geometry"]["type"] == "Point"
    assert AVISO_GEOMETRIA not in punto.avisos
    resumido = resumir_geometria(poligono_completo)
    assert (resumido.datos, resumido.huella) == (poligono_completo.datos, poligono_completo.huella)
    assert resumir_geometria(resumido) == resumido  # resumir dos veces no cambia nada


async def _completo() -> Sobre:
    puerta.usar_conectores({"arcgis-mcp": ConectorFalso({14: [PREDIO_POLIGONO]})})
    return await puerta.ejecutar(PREDIO, CHIA | {GEOMETRIA: True})
