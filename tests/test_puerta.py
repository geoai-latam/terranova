"""La puerta por MCP en memoria, con un conector falso: nunca se llama a la fuente en pruebas."""

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
    return {
        "geo_result": "1",
        "artifacts": [
            {"kind": "feature_collection", "name": "R_TERRENO", "crs": "EPSG:4326", "data": fc}
        ],
        "facts": {"total_en_servicio": len(rasgos), "traidos": len(rasgos), "completo": True},
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


class ConectorFalso:
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
    puerta.usar_conector(request.param)
    try:
        async with Client(puerta.puerta) as cliente:
            yield cliente
    finally:
        puerta.usar_conector(None)


def _con(conector: ConectorFalso) -> pytest.MarkDecorator:
    return pytest.mark.parametrize("cliente_con", [conector], indirect=True)


@pytest.mark.anyio
@_con(ConectorFalso({14: [PREDIO_CHIA]}))
async def test_predio_rural_encontrado(cliente_con: Client[Any]) -> None:
    r = await cliente_con.call_tool("igac_predio_en_punto", {"lon": -74.0262, "lat": 4.8619})
    sobre = r.structured_content
    assert sobre is not None
    # la salida cumple el contrato completo (reglas 1-9)
    Sobre.model_validate(sobre)
    assert sobre["contrato"] == "rt/1" and sobre["creditos"] == 10
    assert sobre["estado"] == "encontrado"
    assert sobre["datos"] == {
        "codigo_predial": CODIGO_CHIA,
        "codigo_predial_anterior": "25175000000050067000",
        "zona": "rural",
        "municipio_divipola": "25175",
    }
    artefacto = sobre["geo_result"]["artifacts"][0]
    assert artefacto["kind"] == "feature_collection" and artefacto["crs"] == "EPSG:4326"
    # regla 10: la capa lleva solo la lista blanca, nunca los campos crudos de la fuente
    (rasgo,) = artefacto["data"]["features"]
    assert rasgo["properties"] == sobre["datos"]
    assert rasgo["geometry"] == PREDIO_CHIA["geometry"]
    # regla 3: toda fuente consultada aparece, aunque no haya encontrado nada
    assert {p["fuente_id"] for p in sobre["procedencia"]} == {
        "igac.catastro.terreno_rural",
        "igac.catastro.terreno_urbano",
    }
    for p in sobre["procedencia"]:
        assert p["licencia"] == {
            "spdx": "CC-BY-SA-4.0",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "uso_comercial": "si",
        }
        c = p["completitud"]
        assert c["vistos"] <= c["total"] and c["truncado"] == (c["vistos"] < c["total"])


@pytest.mark.anyio
@_con(ConectorFalso({}))
async def test_sin_predio_es_no_encontrado(cliente_con: Client[Any]) -> None:
    r = await cliente_con.call_tool("igac_predio_en_punto", {"lon": -75.0, "lat": 5.0})
    assert r.structured_content is not None
    assert r.structured_content["estado"] == "no_encontrado"
    assert r.structured_content["datos"] == {}
    assert r.structured_content["geo_result"] is None


@pytest.mark.anyio
@_con(ConectorFalso({}, falla="fuente_no_disponible"))
async def test_conector_caido_es_error_y_no_sobre(cliente_con: Client[Any]) -> None:
    with pytest.raises(ToolError, match="fuente_no_disponible"):
        await cliente_con.call_tool("igac_predio_en_punto", {"lon": -74.0262, "lat": 4.8619})


@pytest.mark.anyio
@_con(ConectorFalso({}))
async def test_entrada_fuera_de_rango_se_rechaza(cliente_con: Client[Any]) -> None:
    with pytest.raises(ToolError):
        await cliente_con.call_tool("igac_predio_en_punto", {"lon": -200, "lat": 4.8})


@pytest.mark.anyio
@_con(ConectorFalso({}))
async def test_la_herramienta_publica_output_schema(cliente_con: Client[Any]) -> None:
    (herramienta,) = await cliente_con.list_tools()
    assert herramienta.name == "igac_predio_en_punto"
    assert herramienta.output_schema is not None
    assert "procedencia" in herramienta.output_schema["properties"]


@pytest.mark.anyio
@_con(ConectorFalso({}, falla="fuente_lenta"))
async def test_el_codigo_del_conector_llega_al_cliente(cliente_con: Client[Any]) -> None:
    with pytest.raises(ToolError, match=r"^fuente_lenta: "):
        await cliente_con.call_tool("igac_predio_en_punto", {"lon": -74.0262, "lat": 4.8619})
