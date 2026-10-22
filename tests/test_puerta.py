"""La puerta por MCP en memoria, con conectores falsos: nunca se llama a la fuente en pruebas."""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from terranova import puerta
from terranova.conector import ErrorConector
from terranova.contrato import Sobre

CODIGO_CHIA = "251750000000000050067000000000"


def _respuesta(rasgos: list[dict[str, Any]]) -> dict[str, Any]:
    fc = {"type": "FeatureCollection", "features": rasgos}
    total = len(rasgos)
    return {
        "geo_result": "1",
        "artifacts": [
            {"kind": "feature_collection", "name": "capa", "crs": "EPSG:4326", "data": fc}
        ],
        "facts": {"completitud": {"vistos": total, "total": total, "truncado": False}},
    }


PREDIO_CHIA = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-74.0262, 4.8619]},
    "properties": {
        "CODIGO": CODIGO_CHIA,
        "CODIGO_ANTERIOR": "25175000000050067000",
        "codigo_municipio": "23175",
        "GLOBALID": "no-debe-salir",
    },
}


def _municipio(divipola: str) -> dict[str, Any]:
    return {"type": "Feature", "geometry": None, "properties": {"divipola": divipola}}


class ConectorFalso:
    """Responde por la capa de la url (14 R_TERRENO, 7 U_TERRENO, 1 gestores)."""

    def __init__(self, por_capa: dict[int, list[dict[str, Any]]], falla: str | None = None) -> None:
        self.por_capa = por_capa
        self.falla = falla
        self.llamadas: list[dict[str, Any]] = []

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        self.llamadas.append({"herramienta": herramienta, **argumentos})
        if self.falla:
            raise ErrorConector("la fuente no respondió", self.falla)
        capa = int(argumentos["url"].rsplit("/", 1)[1])
        return _respuesta(self.por_capa.get(capa, []))


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def cliente_con(request: pytest.FixtureRequest) -> AsyncIterator[Client[Any]]:
    puerta.usar_conectores({"arcgis-mcp": request.param})
    try:
        async with Client(puerta.puerta) as cliente:
            yield cliente
    finally:
        puerta.usar_conectores(None)


def _con(conector: ConectorFalso) -> pytest.MarkDecorator:
    return pytest.mark.parametrize("cliente_con", [conector], indirect=True)


PREDIO = "igac_predio_en_punto"
CHIA = {"lon": -74.0262, "lat": 4.8619}


@pytest.mark.anyio
@_con(ConectorFalso({}))
async def test_una_herramienta_mcp_por_ficha_del_catalogo(cliente_con: Client[Any]) -> None:
    herramientas = {t.name: t for t in await cliente_con.list_tools()}
    assert set(herramientas) == set(puerta.CATALOGO.herramientas)
    t = herramientas[PREDIO]
    assert t.output_schema is not None and "procedencia" in t.output_schema["properties"]
    assert t.annotations is not None and t.annotations.read_only_hint is True
    assert t.description is not None and t.description.endswith("licencia: CC BY-SA 4.0.)")
    por_codigo = herramientas["igac_predio_por_codigo"].input_schema["properties"]["codigo"]
    assert por_codigo["pattern"] == "^[0-9]{30}$"


@pytest.mark.anyio
@_con(ConectorFalso({14: [PREDIO_CHIA]}))
async def test_predio_rural_encontrado(cliente_con: Client[Any]) -> None:
    r = await cliente_con.call_tool(PREDIO, CHIA)
    sobre = r.structured_content
    assert sobre is not None
    Sobre.model_validate(sobre)
    assert sobre["estado"] == "encontrado" and sobre["creditos"] == 10
    assert sobre["datos"] == {
        "codigo_predial": CODIGO_CHIA,
        "codigo_predial_anterior": "25175000000050067000",
        "zona": "rural",
        "municipio_divipola": "25175",
    }
    (rasgo,) = sobre["geo_result"]["artifacts"][0]["data"]["features"]
    assert rasgo["properties"] == sobre["datos"]  # regla 10: nada de GLOBALID ni codigo_municipio
    assert {p["licencia"]["spdx"] for p in sobre["procedencia"]} == {"CC-BY-SA-4.0"}


@pytest.mark.anyio
@_con(ConectorFalso({1: [_municipio("25175")]}))
async def test_sin_predio_en_municipio_cubierto_es_no_encontrado(cliente_con: Client[Any]) -> None:
    r = await cliente_con.call_tool(PREDIO, {"lon": -74.03, "lat": 4.86})
    assert r.structured_content is not None
    assert r.structured_content["estado"] == "no_encontrado"
    assert r.structured_content["datos"] == {} and r.structured_content["creditos"] == 10


@pytest.mark.anyio
@_con(ConectorFalso({1: [_municipio("11001")]}))
async def test_bogota_esta_fuera_de_cobertura_y_no_descuenta(cliente_con: Client[Any]) -> None:
    """F1.5: Bogotá la gestiona la UAECD; la base pública del IGAC no la cubre."""
    r = await cliente_con.call_tool(PREDIO, {"lon": -74.0817, "lat": 4.6097})
    sobre = r.structured_content
    assert sobre is not None
    Sobre.model_validate(sobre)
    assert sobre["estado"] == "fuera_de_cobertura" and sobre["creditos"] == 0
    assert any("UAECD" in a for a in sobre["avisos"])
    assert "igac.catastro.gestores" in {p["fuente_id"] for p in sobre["procedencia"]}


@pytest.mark.anyio
@_con(ConectorFalso({}, falla="fuente_lenta"))
async def test_el_codigo_del_conector_llega_al_cliente(cliente_con: Client[Any]) -> None:
    with pytest.raises(ToolError, match=r"^fuente_lenta: "):
        await cliente_con.call_tool(PREDIO, CHIA)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("herramienta", "entrada"),
    [
        (PREDIO, {"lon": -200, "lat": 4.8}),
        (PREDIO, {"lon": -74.0}),
        ("igac_predio_por_codigo", {"codigo": "' OR 1=1 --"}),
        ("pnn_areas_protegidas_en_zona", {"bbox": [-73, 5, -74, 4]}),
    ],
)
@_con(ConectorFalso({}))
async def test_entrada_invalida_no_llega_a_la_fuente(
    cliente_con: Client[Any], herramienta: str, entrada: dict[str, Any]
) -> None:
    with pytest.raises(ToolError):
        await cliente_con.call_tool(herramienta, entrada)
