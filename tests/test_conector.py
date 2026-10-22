"""`ConectorMCP` traduce el error del conector (kit F1.3) a un código de `rt/1`."""

from types import SimpleNamespace
from typing import Any

import pytest

from terranova.conector import ConectorMCP, ErrorConector


class ClienteFalso:
    def __init__(self, resultado: Any = None, excepcion: Exception | None = None) -> None:
        self.resultado = resultado
        self.excepcion = excepcion

    def is_connected(self) -> bool:
        return True

    async def call_tool(self, *_: Any, **__: Any) -> Any:
        if self.excepcion is not None:
            raise self.excepcion
        return self.resultado


def _conector(cliente: ClienteFalso) -> ConectorMCP:
    conector = ConectorMCP("http://127.0.0.1:1/mcp", "llave")
    conector.cliente = cliente  # type: ignore[assignment]
    return conector


def _error(sc: Any) -> Any:
    return SimpleNamespace(
        is_error=True, structured_content=sc, content=[SimpleNamespace(text="falló")]
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("sc", "codigo", "reintentar"),
    [
        (
            {"error": "x", "codigo": "fuente_no_disponible", "reintentar_en_s": 5},
            "fuente_no_disponible",
            5,
        ),
        ({"error": "x", "codigo": "fuente_lenta"}, "fuente_lenta", None),
        ({"error": "x", "codigo": "fuente_respuesta_invalida"}, "fuente_respuesta_invalida", None),
        # la puerta validó la entrada: un parámetro inválido en el conector es fallo nuestro
        ({"error": "x", "codigo": "parametro_invalido"}, "error_interno", None),
        ({"error": "conector viejo, sin código"}, "error_interno", None),
        (None, "error_interno", None),
    ],
)
async def test_error_del_conector_lleva_su_codigo(
    sc: Any, codigo: str, reintentar: int | None
) -> None:
    with pytest.raises(ErrorConector) as exc:
        await _conector(ClienteFalso(_error(sc))).llamar("t", {})
    assert (exc.value.codigo, exc.value.reintentar_en_s) == (codigo, reintentar)


@pytest.mark.anyio
async def test_sin_conexion_es_fuente_no_disponible() -> None:
    with pytest.raises(ErrorConector) as exc:
        await _conector(ClienteFalso(excepcion=ConnectionError("rechazada"))).llamar("t", {})
    assert exc.value.codigo == "fuente_no_disponible"


@pytest.mark.anyio
async def test_respuesta_buena_pasa_tal_cual() -> None:
    bueno = SimpleNamespace(is_error=False, structured_content={"geo_result": "1"}, content=[])
    assert await _conector(ClienteFalso(bueno)).llamar("t", {}) == {"geo_result": "1"}


@pytest.mark.anyio
async def test_tiempo_agotado_es_fuente_lenta() -> None:
    with pytest.raises(ErrorConector) as exc:
        await _conector(
            ClienteFalso(excepcion=TimeoutError("Request 'tools/call' timed out"))
        ).llamar("t", {})
    assert exc.value.codigo == "fuente_lenta"


def test_conectores_del_entorno_reemplazan_los_de_por_defecto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from terranova.conector import CONECTORES_POR_DEFECTO, conectores_desde_entorno

    monkeypatch.setenv("TERRANOVA_CONECTOR_LLAVE", "x")
    monkeypatch.delenv("TERRANOVA_CONECTORES", raising=False)
    assert set(conectores_desde_entorno()) == set(CONECTORES_POR_DEFECTO)
    monkeypatch.setenv("TERRANOVA_CONECTORES", '{"arcgis-mcp": "http://arcgis-mcp:9400/mcp"}')
    assert set(conectores_desde_entorno()) == {"arcgis-mcp"}


@pytest.mark.anyio
async def test_un_conector_caido_no_tumba_el_arranque(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """En el compose, la puerta entraba en un ciclo de reinicios si un conector no respondía."""
    from terranova import puerta

    monkeypatch.setenv("TERRANOVA_PIMIENTA", "p" * 40)
    monkeypatch.setenv("TERRANOVA_BD", str(tmp_path / "t.db"))
    monkeypatch.setenv("TERRANOVA_CONECTOR_LLAVE", "x")
    monkeypatch.setenv("TERRANOVA_CONECTORES", '{"arcgis-mcp": "http://127.0.0.1:1/mcp"}')
    monkeypatch.delenv("TERRANOVA_REDIS_URL", raising=False)
    await puerta.iniciar()
    try:
        assert puerta.registro is not None and "arcgis-mcp" in (puerta._conectores or {})
    finally:
        await puerta.detener()
