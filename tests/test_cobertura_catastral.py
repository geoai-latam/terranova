"""Comprobar la cobertura solo explica un vacío: nunca tumba una respuesta que la capa ya dio.

Desde la VPS, `mapas.igac.gov.co` se cuelga: cada punto sin predio tardaba de 47 a 91 s y a veces
acababa en 504, y al tercero el cortacircuitos respondía 502 a todos.
"""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from terranova import ejecutor as modulo
from terranova.catalogo import cargar
from terranova.contrato import ahora
from terranova.ejecutor import AVISO_SIN_VERIFICAR, cobertura_catastral, fuera_de_colombia
from terranova.errores import ErrorEjecucion
from terranova.proteccion import Proteccion

CATALOGO = cargar()
H = CATALOGO.herramientas["igac_sector_en_punto"]
PUNTO = {"lon": -76.53, "lat": 3.44}


def _ejecutor(llamar: Any, proteccion: Proteccion | None = None) -> Any:
    return SimpleNamespace(
        catalogo=CATALOGO,
        proteccion=proteccion,
        llamar=llamar,
        indice=lambda _: {"municipios": {}},
    )


@pytest.mark.parametrize(
    ("herramienta", "entrada", "fuera"),
    [
        ("igac_sector_en_punto", {"lon": -3.7, "lat": 40.42}, True),  # Madrid
        ("igac_sector_en_punto", {"lon": -74.06, "lat": 4.86}, False),
        ("igac_sector_en_punto", {"lon": -81.7, "lat": 12.58}, False),  # San Andrés
        ("igac_sector_en_punto", {"lon": -78.5, "lat": -0.2}, False),  # Quito
        ("igac_vias_en_zona", {"bbox": [-3.8, 40.3, -3.6, 40.5]}, True),
        ("igac_vias_en_zona", {"bbox": [-83.0, 3.0, -74.0, 5.0]}, False),  # toca Colombia
        ("igac_predio_por_codigo", {"codigo": "2" * 30}, False),  # sin lugar
    ],
)
def test_fuera_de_colombia(herramienta: str, entrada: dict[str, Any], fuera: bool) -> None:
    assert fuera_de_colombia(CATALOGO.herramientas[herramienta], entrada) is fuera


def test_si_la_fuente_tarda_el_vacio_sigue_en_pie(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modulo, "TOPE_COBERTURA_S", 0.01)

    async def colgada(*_: Any, **__: Any) -> dict[str, Any]:
        await asyncio.sleep(30)
        return {}

    proteccion = Proteccion(umbral=1)
    veredicto = asyncio.run(cobertura_catastral(_ejecutor(colgada, proteccion), H, PUNTO, ahora()))
    assert veredicto.fuera is False
    assert veredicto.aviso == AVISO_SIN_VERIFICAR
    assert proteccion.abierto("igac.gestores_catastrales")  # la siguiente no vuelve a esperar


def test_si_la_fuente_cae_el_vacio_sigue_en_pie() -> None:
    async def caida(*_: Any, **__: Any) -> dict[str, Any]:
        raise ErrorEjecucion("fuente_lenta", "ReadTimeout")

    veredicto = asyncio.run(cobertura_catastral(_ejecutor(caida), H, PUNTO, ahora()))
    assert veredicto.fuera is False
    assert veredicto.aviso == AVISO_SIN_VERIFICAR
