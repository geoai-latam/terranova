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
