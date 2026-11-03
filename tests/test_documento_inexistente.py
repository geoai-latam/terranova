"""Un documento que no existe es «no encontrado»: ni un éxito con relleno ni una caída."""

from typing import Any

import pytest

from terranova.catalogo import cargar
from terranova.conector import ErrorConector
from terranova.ejecutor import Ejecutor
from terranova.proteccion import Proteccion

CATALOGO = cargar()


class _Responde:
    def __init__(self, respuesta: dict[str, Any]) -> None:
        self.respuesta = respuesta

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        return self.respuesta


class _Rechaza:
    def __init__(self, http: int, codigo: str = "fuente_respuesta_invalida") -> None:
        self.http, self.codigo = http, codigo

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        raise ErrorConector(
            f"web_html: el servicio respondió HTTP {self.http}: <html>", self.codigo
        )


def _ejecutor(herramienta: str, conector: Any, **kwargs: Any) -> Ejecutor:
    fuente = CATALOGO.fuentes[CATALOGO.herramientas[herramienta].fuente]
    return Ejecutor(CATALOGO, {fuente.conector: conector}, **kwargs)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("herramienta", "entrada"),
    [
        ("corte_constitucional_texto_inicio", {"anio": 2007, "sentencia": "T-760-08"}),
        (
            "corte_constitucional_texto_buscar",
            {"anio": 2007, "sentencia": "T-760-08", "buscar": "salud"},
        ),
    ],
)
async def test_la_portada_de_la_corte_no_es_la_sentencia(
    herramienta: str, entrada: dict[str, Any]
) -> None:
    portada = {
        "artifacts": [{"kind": "table", "rows": [{"texto": "CORTE CONSTITUCIONAL DE COLOMBIA"}]}],
        "facts": {"titulo": "CORTE CONSTITUCIONAL DE COLOMBIA", "caracteres": 32},
    }
    sobre = await _ejecutor(herramienta, _Responde(portada)).ejecutar(herramienta, entrada)
    assert sobre.estado == "no_encontrado"
    assert not sobre.datos.get("titulo")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("herramienta", "entrada", "http", "codigo"),
    [
        (
            "creg_resolucion_buscar",
            {"documento": "resolucion_creg_999-999_2026", "buscar": "ARTÍCULO"},
            404,
            "fuente_respuesta_invalida",
        ),
        (
            "dian_normograma_buscar",
            {"documento": "decreto_9999_2099", "buscar": "ARTÍCULO"},
            404,
            "fuente_respuesta_invalida",
        ),
        ("funcionpublica_norma_inicio", {"norma": 99999999}, 302, "fuente_no_disponible"),
    ],
)
async def test_lo_que_la_fuente_dice_que_no_existe_no_corta_la_fuente(
    herramienta: str, entrada: dict[str, Any], http: int, codigo: str
) -> None:
    proteccion = Proteccion(umbral=1)
    ej = _ejecutor(herramienta, _Rechaza(http, codigo), proteccion=proteccion)
    sobre = await ej.ejecutar(herramienta, entrada)
    assert sobre.estado == "no_encontrado"
    assert not proteccion.abierto(CATALOGO.herramientas[herramienta].fuente)
    # dice que el documento no existe, no que «la fuente no dijo cuántos hay» (CREG 015 de 2018)
    assert any("documento no existe" in a for a in sobre.avisos), sobre.avisos
    assert not any("no dijo cuántos" in a for a in sobre.avisos)


@pytest.mark.anyio
async def test_otro_error_de_la_fuente_sigue_siendo_error() -> None:
    from terranova.errores import ErrorEjecucion

    herramienta = "creg_resolucion_buscar"
    ej = _ejecutor(herramienta, _Rechaza(500))
    with pytest.raises(ErrorEjecucion):
        await ej.ejecutar(
            herramienta, {"documento": "resolucion_creg_1-1_2026", "buscar": "ARTÍCULO"}
        )


@pytest.mark.anyio
async def test_una_busqueda_sin_resultados_no_es_un_hallazgo() -> None:
    herramienta = "funcionpublica_normas_buscar"
    vacia = {
        "artifacts": [{"kind": "table", "rows": []}],
        "facts": {"titulo": "Gestor Normativo", "caracteres": 77},
    }
    sobre = await _ejecutor(herramienta, _Responde(vacia)).ejecutar(
        herramienta, {"texto": "zzzqqqxxx"}
    )
    assert sobre.estado == "no_encontrado"
