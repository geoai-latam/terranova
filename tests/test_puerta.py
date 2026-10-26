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
async def test_los_esquemas_mcp_los_acepta_un_cliente_openai(cliente_con: Client[Any]) -> None:
    """OpenAI rechaza la lista ENTERA si un esquema trae combinadores arriba (banco de agente)."""
    prohibidos = {"oneOf", "anyOf", "allOf", "enum", "const", "not"}
    for t in await cliente_con.list_tools():
        assert t.input_schema.get("type") == "object", t.name
        assert not prohibidos & set(t.input_schema), t.name


@pytest.mark.anyio
async def test_cada_perfil_cabe_en_un_cliente_openai() -> None:
    """OpenAI acepta hasta 128 herramientas por llamada: `/mcp` completo ya no cabe (150), cada
    perfil por familia sí (ADR-0006)."""
    for familia in puerta.FAMILIAS:
        async with Client(puerta.crear_servidor(familia, con_ciclo=False)) as c:
            nombres = {t.name for t in await c.list_tools()}
        assert len(nombres) <= 128, familia
        assert puerta.HERRAMIENTAS_COMUNES <= nombres, familia  # de nombre a código, en todos


@pytest.mark.anyio
@_con(ConectorFalso({}))
async def test_una_herramienta_mcp_por_ficha_del_catalogo(cliente_con: Client[Any]) -> None:
    herramientas = {t.name: t for t in await cliente_con.list_tools()}
    # ficha_lugar compone herramientas; fuente_describir es GET /v1/fuentes/{id} (spec 08)
    assert set(herramientas) == set(puerta.CATALOGO.herramientas) | {
        "ficha_lugar",
        "fuente_describir",
    }
    describir = herramientas["fuente_describir"]
    assert describir.annotations is not None and describir.annotations.open_world_hint is False
    ficha = herramientas["ficha_lugar"]
    assert "lon" in ficha.input_schema["properties"] and ficha.annotations is not None
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
    # WS3: la procedencia cita la fuente REAL del catálogo con su licencia verdadera (CC-BY-SA-4.0
    # de su ficha), no un id fantasma con `por-verificar` fijado a mano
    gestores = next(
        p for p in sobre["procedencia"] if p["fuente_id"] == "igac.gestores_catastrales"
    )
    assert gestores["licencia"]["spdx"] == "CC-BY-SA-4.0"
    assert "igac.catastro.gestores" not in {p["fuente_id"] for p in sobre["procedencia"]}


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


class ConectorIntermitente(ConectorFalso):
    """Responde vacío las primeras `vacias` veces, como el proxy de la ANT (~25 %)."""

    def __init__(self, rasgos: list[dict[str, Any]], vacias: int) -> None:
        super().__init__({0: rasgos})
        self.vacias = vacias

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        if len(self.llamadas) < self.vacias:
            self.llamadas.append({"herramienta": herramienta, **argumentos})
            return _respuesta([])
        return await super().llamar(herramienta, argumentos)


ZRC = "ant_zonas_reserva_campesina_en_punto"
CABRERA = {"type": "Feature", "geometry": None, "properties": {"NOMBRE_ZON": "Cabrera"}}


@pytest.mark.anyio
@_con(ConectorIntermitente([CABRERA], vacias=2))
async def test_un_vacio_falso_se_reintenta_antes_de_decir_no_encontrado(
    cliente_con: Client[Any],
) -> None:
    """«No se pudo» no es «no hay»: la fuente marcada se vuelve a preguntar si responde vacío."""
    r = await cliente_con.call_tool(ZRC, {"lon": -74.46, "lat": 3.88})
    assert r.structured_content is not None
    assert r.structured_content["estado"] == "encontrado"
    assert r.structured_content["datos"]["nombre"] == "Cabrera"


@pytest.mark.anyio
@_con(ConectorIntermitente([CABRERA], vacias=10))
async def test_vacio_tras_los_reintentos_lo_dice(cliente_con: Client[Any]) -> None:
    r = await cliente_con.call_tool(ZRC, {"lon": -74.46, "lat": 3.88})
    assert r.structured_content is not None
    assert r.structured_content["estado"] == "no_encontrado"
    assert any("4 veces" in a for a in r.structured_content["avisos"])


@pytest.mark.anyio
async def test_datos_de_fuente_invalidos_son_fuente_respuesta_invalida(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WS2: datos de la fuente que rompen el contrato rt/1 (vistos>total) no escapan como 500;
    se mapean a `fuente_respuesta_invalida` (ADR-0011), no a «no hay» ni a error interno."""
    from terranova.contrato import Completitud
    from terranova.errores import ErrorEjecucion

    async def _boom(*a: Any, **k: Any) -> Any:
        Completitud(vistos=5, total=2, truncado=False)  # dispara la regla 4 → ValidationError

    monkeypatch.setattr(puerta, "_ejecutar", _boom)
    with pytest.raises(ErrorEjecucion) as exc:
        await puerta.ejecutar("igac_predio_en_punto", {"lon": -74.0, "lat": 4.8})
    assert exc.value.codigo == "fuente_respuesta_invalida"
