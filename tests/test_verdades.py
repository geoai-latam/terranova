"""F0.7: el banco de verdades del producto está bien formado y no contradice a los canarios."""

from collections import Counter
from pathlib import Path
from typing import Any

import pytest
import yaml

from terranova import ficha
from terranova.catalogo import cargar
from terranova.ejecutor import validar_entrada

RUTA = Path(__file__).resolve().parents[1] / "catalogo" / "verdades_producto.yaml"
BANCO: dict[str, Any] = yaml.safe_load(RUTA.read_text(encoding="utf-8"))
VERDADES: list[dict[str, Any]] = BANCO["verdades"]
CATALOGO = cargar()
FAMILIAS = {"territorio", "contratacion", "empresas", "normativa", "justicia", "estadisticas"}
ESTADOS = {"no_encontrado", "fuera_de_cobertura"}
CAMPOS = {"id", "familia", "pregunta", "herramienta", "entrada", "fuente", "verdad", "minimos"}
CAMPOS |= {"estado", "medicion", "nota", "alternativas"}


def test_sesenta_preguntas_en_seis_familias() -> None:
    assert len(VERDADES) == 60
    assert len({v["id"] for v in VERDADES}) == 60
    familias = Counter(v["familia"] for v in VERDADES)
    assert set(familias) == FAMILIAS and min(familias.values()) >= 5


@pytest.mark.parametrize("v", VERDADES, ids=lambda v: v["id"])
def test_cada_verdad_esta_bien_formada(v: dict[str, Any]) -> None:
    assert set(v) <= CAMPOS, set(v) - CAMPOS
    assert v["pregunta"].strip() and v["medicion"].strip()
    # algo que comprobar: valores, un piso o el estado honesto («no hay», «no cubre»)
    assert v.get("verdad") or v.get("minimos") or v.get("estado") in ESTADOS
    if "estado" in v:
        assert v["estado"] in ESTADOS and not v.get("verdad")
    h = v["herramienta"]
    if h is None:
        assert v.get("fuente") and "." in v["fuente"]  # fuente objetivo (M2)
        return
    assert h in CATALOGO.herramientas or h == ficha.HERRAMIENTA
    if h in CATALOGO.herramientas:
        validar_entrada(CATALOGO.herramientas[h], v["entrada"])  # la entrada es invocable tal cual


@pytest.mark.parametrize(
    "v",
    [v for v in VERDADES if v["herramienta"] in CATALOGO.herramientas],
    ids=lambda v: v["id"],
)
def test_no_contradice_al_canario(v: dict[str, Any]) -> None:
    """Con la misma entrada que el canario, la verdad del banco es la del canario."""
    canario = CATALOGO.herramientas[v["herramienta"]].canario
    if canario.entrada != v["entrada"]:
        return
    for k, valor in (v.get("verdad") or {}).items():
        if k in canario.verdad:
            assert canario.verdad[k] == valor, k
    for k, piso in (v.get("minimos") or {}).items():
        if k in canario.minimos:
            assert canario.minimos[k] == piso, k


def test_sin_datos_de_personas_naturales() -> None:
    """ADR-0014: nada por cédula ni por nombre de una persona."""
    personales = {"primer_nombre", "primer_apellido", "numero_identificacion", "cedula"}
    for v in VERDADES:
        claves = set(v.get("verdad") or {}) | set(v.get("entrada") or {})
        assert not personales & claves, v["id"]
