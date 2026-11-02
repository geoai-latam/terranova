"""`scripts/nueva_fuente.py`: una ficha nueva sale válida, en borrador y sin decidir por nadie."""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

from terranova.catalogo import Fuente


def _script() -> Any:
    ruta = Path(__file__).resolve().parents[1] / "scripts" / "nueva_fuente.py"
    spec = importlib.util.spec_from_file_location("nueva_fuente", ruta)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    sys.modules["nueva_fuente"] = modulo
    spec.loader.exec_module(modulo)
    return modulo


VISTA = {
    "name": "Hurtos de prueba",
    "attribution": "Policía Nacional",
    "license": {"name": "Creative Commons Attribution | Share Alike 4.0 International"},
    "columns": [
        {"fieldName": "municipio", "dataTypeName": "text", "name": "Municipio"},
        {"fieldName": "cantidad", "dataTypeName": "number", "description": "casos"},
        {"fieldName": "fecha", "dataTypeName": "calendar_date", "name": "Fecha"},
        {"fieldName": "cedula_victima", "dataTypeName": "text", "name": "Cédula"},
        {"fieldName": "nombre_del_denunciante", "dataTypeName": "text", "name": "Nombre"},
        {"fieldName": "ubicacion", "dataTypeName": "point", "name": "Ubicación"},
    ],
}


def test_la_ficha_es_valida_y_no_decide_lo_que_decide_una_persona() -> None:
    ficha = Fuente.model_validate(_script().ficha_socrata("policia.prueba", "abcd-1234", VISTA))
    assert ficha.estado == "borrador"
    assert ficha.uso_comercial == "por_verificar"
    assert ficha.licencia.verificada is None and ficha.licencia.spdx is None
    assert ficha.datos_personales == "presentes"
    assert (ficha.licencia.cita or "").startswith("Creative Commons")


def test_las_columnas_de_personas_no_entran_a_la_lista_blanca() -> None:
    ficha = _script().ficha_socrata("policia.prueba", "abcd-1234", VISTA)
    assert sorted(ficha["campos"]) == ["cantidad", "fecha", "municipio"]
    assert ficha["campos"]["cantidad"]["tipo"] == "float"


def test_una_ficha_existente_no_se_pisa(tmp_path: Path) -> None:
    ruta = tmp_path / "x.yaml"
    ruta.write_text("ya", encoding="utf-8")
    with pytest.raises(ValueError, match="no se pisa"):
        _script().crear("policia.prueba", "abcd-1234", destino=ruta)
    assert ruta.read_text(encoding="utf-8") == "ya"


@pytest.mark.parametrize(
    ("fuente", "conjunto"), [("SinPunto", "abcd-1234"), ("policia.prueba", "../../etc")]
)
def test_rechaza_identificadores_raros(fuente: str, conjunto: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _script().crear(fuente, conjunto, destino=tmp_path / "x.yaml")


def test_las_horas_se_suman_al_registro(tmp_path: Path) -> None:
    archivo = tmp_path / "horas.csv"
    modulo = _script()
    modulo.horas("policia.prueba", 1.5, "perfil", archivo)
    modulo.horas("policia.prueba", 0.5, "canario", archivo)
    lineas = archivo.read_text(encoding="utf-8").splitlines()
    assert lineas[0] == "fecha,fuente,horas,nota"
    assert len(lineas) == 3
    with pytest.raises(ValueError, match="mayor que cero"):
        modulo.horas("policia.prueba", 0, "", archivo)
