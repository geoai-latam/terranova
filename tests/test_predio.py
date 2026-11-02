"""`predio_en_punto`: elige la base catastral sola y no disfraza un «no se pudo» de «no hay»."""

from typing import Any

import pytest

from terranova import predio as p
from terranova.catalogo import cargar
from terranova.contrato import Sobre
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.ficha import PREDIO_EN_PUNTO, PREDIO_SINIC

CATALOGO = cargar()
PUNTO = {"lon": -74.07, "lat": 4.71}
SINIC, IGAC = PREDIO_SINIC.herramienta, PREDIO_EN_PUNTO.herramienta
CAIDA = ErrorEjecucion("fuente_no_disponible", "se cayó")


def _sobre(estado: str, marca: str) -> Sobre:
    return Sobre.model_construct(herramienta="x@1", estado=estado, procedencia=[], avisos=[marca])


class Falso:
    catalogo = CATALOGO

    def __init__(self, **respuestas: Any) -> None:
        self.respuestas = respuestas
        self.llamadas: list[str] = []

    async def ejecutar(self, herramienta: str, entrada: dict[str, Any], **_: Any) -> Sobre:
        self.llamadas.append(herramienta)
        r = self.respuestas[herramienta]
        if isinstance(r, Exception):
            raise r
        assert isinstance(r, Sobre)
        return r


@pytest.mark.anyio
async def test_si_el_sinic_lo_tiene_no_se_consulta_el_igac() -> None:
    ej = Falso(**{SINIC: _sobre("encontrado", "sinic")})
    r = await p.ficha(ej, PUNTO)  # type: ignore[arg-type]
    assert r.herramienta == "predio_en_punto@1" and r.avisos == ["sinic"]
    assert ej.llamadas == [SINIC]


@pytest.mark.anyio
async def test_si_el_sinic_no_lo_tiene_responde_el_igac() -> None:
    ej = Falso(**{SINIC: _sobre("no_encontrado", "sinic"), IGAC: _sobre("encontrado", "igac")})
    r = await p.ficha(ej, PUNTO)  # type: ignore[arg-type]
    assert r.estado == "encontrado" and r.avisos == ["igac"] and ej.llamadas == [SINIC, IGAC]


@pytest.mark.anyio
async def test_sinic_caido_e_igac_con_predio_queda_en_la_procedencia() -> None:
    ej = Falso(**{SINIC: CAIDA, IGAC: _sobre("encontrado", "igac")})
    r = await p.ficha(ej, PUNTO)  # type: ignore[arg-type]
    assert r.estado == "encontrado"
    assert [x.fuente_id for x in r.procedencia] == [CATALOGO.herramientas[SINIC].fuente]


@pytest.mark.anyio
@pytest.mark.parametrize("estado", ["no_encontrado", "fuera_de_cobertura"])
async def test_sinic_caido_sin_predio_en_el_igac_es_no_se_pudo(estado: str) -> None:
    ej = Falso(**{SINIC: CAIDA, IGAC: _sobre(estado, "igac")})
    with pytest.raises(ErrorEjecucion, match="se cayó"):
        await p.ficha(ej, PUNTO)  # type: ignore[arg-type]


@pytest.mark.anyio
@pytest.mark.parametrize("entrada", [{"lon": 1.0}, {**PUNTO, "codigo": "1"}])
async def test_entrada_invalida(entrada: dict[str, Any]) -> None:
    with pytest.raises(ErrorEntrada):
        await p.ficha(Falso(), entrada)  # type: ignore[arg-type]
