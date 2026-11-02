"""`geometria: true` da la forma guardada; lo que no puede darla, lo dice."""

from typing import Any

import pytest

from terranova.catalogo import cargar
from terranova.ejecutor import AVISO_SIMPLIFICADA, Ejecutor

CATALOGO = cargar()
EN_PUNTO = "pnn_areas_protegidas_en_punto"  # limite 20, geometria simplificada
EN_ZONA = "pnn_areas_protegidas_en_zona"  # limite 1000
AGROLOGIA = "igac_capacidad_uso_en_punto"  # copia simplificada al ingerir
ZONA = {"bbox": [-74.5, 4.0, -73.5, 5.0]}
PUNTO = {"lon": -73.75, "lat": 4.55}


class Copia:
    def __init__(self) -> None:
        self.argumentos: list[dict[str, Any]] = []

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        self.argumentos.append(argumentos)
        hechos = {"servido_desde": "copia", "consultado_en": "2026-10-22T00:00:00+00:00"}
        return {"artifacts": [{"kind": "table", "rows": []}], "facts": hechos}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_una_lista_corta_pide_la_forma_guardada() -> None:
    copia = Copia()
    ej = Ejecutor(CATALOGO, {"copia": copia})
    await ej.ejecutar(EN_PUNTO, PUNTO, plan="evaluacion")
    await ej.ejecutar(EN_PUNTO, PUNTO, plan="evaluacion", geometria_completa=True)
    assert [a["geometria"] for a in copia.argumentos] == ["simplificada", "completa"]


@pytest.mark.anyio
async def test_una_lista_larga_sigue_simplificada_y_lo_avisa() -> None:
    copia = Copia()
    ej = Ejecutor(CATALOGO, {"copia": copia})
    s = await ej.ejecutar(EN_ZONA, ZONA, plan="evaluacion", geometria_completa=True)
    assert copia.argumentos[0]["geometria"] == "simplificada" and AVISO_SIMPLIFICADA in s.avisos
    assert AVISO_SIMPLIFICADA not in (await ej.ejecutar(EN_ZONA, ZONA, plan="evaluacion")).avisos


@pytest.mark.anyio
async def test_lo_simplificado_al_copiar_lo_dice_la_respuesta() -> None:
    ej = Ejecutor(CATALOGO, {"copia": Copia()})
    s = await ej.ejecutar(AGROLOGIA, PUNTO, plan="evaluacion")
    assert any("unos 11 m" in a for a in s.avisos)
    assert any("unos 11 m" in t for t in s.procedencia[0].transformaciones)
    r = await ej.ejecutar(EN_PUNTO, PUNTO, plan="evaluacion")
    assert not any("simplificó" in a for a in r.avisos)  # el RUNAP se copia entero
