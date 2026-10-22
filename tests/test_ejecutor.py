"""Piezas del ejecutor: entrada, plantillas, saneamiento y conversión de tipos."""

from typing import Any

import pytest

from terranova.catalogo import cargar
from terranova.contrato import MAX_TEXTO, texto_es_limpio
from terranova.ejecutor import convertir, renderizar, sanear, validar_entrada
from terranova.errores import ErrorEntrada

CATALOGO = cargar()


@pytest.mark.parametrize(
    ("herramienta", "entrada", "param"),
    [
        ("igac_predio_en_punto", {"lon": "-74", "lat": 4.8}, "lon"),
        ("igac_predio_en_punto", {"lon": True, "lat": 4.8}, "lon"),
        ("igac_predio_en_punto", {"lon": float("nan"), "lat": 4.8}, "lon"),
        ("igac_predio_en_punto", {"lon": -74.0, "lat": 95}, "lat"),
        ("igac_predio_en_punto", {"lon": -74.0, "lat": 4.8, "x": 1}, "x"),
        ("igac_predio_por_codigo", {"codigo": "25175000000000005006700000000"}, "codigo"),
        (
            "secop_contratos_municipio",
            {"municipio": "Chía' OR '1'='1", "departamento": "C"},
            "municipio",
        ),
        ("pnn_areas_protegidas_en_zona", {"bbox": [-74, 4, -75, 5]}, "bbox"),
        ("pnn_areas_protegidas_en_zona", {"bbox": [-74, 4, -73]}, "bbox"),
    ],
)
def test_entrada_invalida(herramienta: str, entrada: dict[str, Any], param: str) -> None:
    with pytest.raises(ErrorEntrada) as exc:
        validar_entrada(CATALOGO.herramientas[herramienta], entrada)
    assert exc.value.param == param


def test_entrada_valida_se_normaliza() -> None:
    h = CATALOGO.herramientas["pnn_areas_protegidas_en_zona"]
    assert validar_entrada(h, {"bbox": [-74, 4, -73, 5]}) == {"bbox": [-74.0, 4.0, -73.0, 5.0]}
    h = CATALOGO.herramientas["secop_contratos_municipio"]
    assert validar_entrada(h, {"municipio": "Chía", "departamento": "Cundinamarca"})


def test_renderizar_conserva_tipos_y_arma_texto() -> None:
    plantilla = {
        "bbox": ["{lon}", "{lat}", "{lon}", "{lat}"],
        "where": "CODIGO = '{codigo}'",
        "n": 5,
    }
    valores = {"lon": -74.0262, "lat": 4.8619, "codigo": "251750000000000050067000000000"}
    assert renderizar(plantilla, valores) == {
        "bbox": [-74.0262, 4.8619, -74.0262, 4.8619],
        "where": "CODIGO = '251750000000000050067000000000'",
        "n": 5,
    }


@pytest.mark.parametrize("sucio", ["a\u202eb", "a\x00b", "x\u2066y\u2069", "\x1b[31mrojo\x07"])
def test_sanear_quita_control_y_bidi(sucio: str) -> None:
    assert texto_es_limpio(sanear(sucio))


def test_sanear_conserva_saltos_y_corta_lo_largo() -> None:
    assert sanear("línea\ncon\ttab") == "línea\ncon\ttab"
    largo = sanear("a" * (MAX_TEXTO + 50))
    assert len(largo) == MAX_TEXTO and largo.endswith("…")


@pytest.mark.parametrize(
    ("valor", "tipo", "esperado"),
    [
        ("12149", "int", 12149),
        ("1289946058879.80", "float", 1289946058879.8),
        ("no es número", "int", None),
        (1592265600000, "date", "2020-06-16"),
        ("2023-06-26T00:00:00.000", "date", "2023-06-26"),
        ({"url": "https://www.secop.gov.co/x"}, "str", "https://www.secop.gov.co/x"),
        (None, "str", None),
        ("true", "bool", True),
    ],
)
def test_convertir(valor: Any, tipo: str, esperado: Any) -> None:
    assert convertir(valor, tipo) == esperado
