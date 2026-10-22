"""El catálogo real valida, y cada regla de la spec 02 y de las ADR rompe con una ficha mala."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from terranova.catalogo import RAIZ, CatalogoInvalido, cargar

FUENTE = "fuentes/igac.catastro.terreno.yaml"
HERRAMIENTA = "herramientas/igac_predio_en_punto.yaml"


def test_el_catalogo_versionado_es_valido() -> None:
    catalogo = cargar()
    assert "igac_predio_en_punto" in catalogo.herramientas


def _catalogo_con(tmp_path: Path, ruta: str, cambio: Callable[[dict[str, Any]], None]) -> Path:
    raiz = tmp_path / "catalogo"
    for carpeta in ("fuentes", "herramientas"):
        shutil.copytree(RAIZ / carpeta, raiz / carpeta)
    archivo = raiz / ruta
    ficha = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    cambio(ficha)
    archivo.write_text(yaml.safe_dump(ficha, allow_unicode=True), encoding="utf-8")
    return raiz


def _set(**valores: Any) -> Callable[[dict[str, Any]], None]:
    def cambio(ficha: dict[str, Any]) -> None:
        for ruta, valor in valores.items():
            *padres, hoja = ruta.split("__")
            destino = ficha
            for p in padres:
                destino = destino[p]
            if valor is _BORRAR:
                del destino[hoja]
            else:
                destino[hoja] = valor

    return cambio


_BORRAR = object()

CASOS = [
    # (archivo, cambio, mensaje esperado)
    (FUENTE, _set(licencia__spdx=None), "ADR-0019"),
    (FUENTE, _set(licencia__verificada=None), "ADR-0007"),
    (FUENTE, _set(licencia__evidencia=None), "evidencia"),
    (FUENTE, _set(clase_acceso="interno_con_permiso"), "ADR-0018"),
    (FUENTE, _set(datos_personales="presentes"), "ADR-0014"),
    (FUENTE, _set(url="http://inseguro.gov.co"), "url"),
    (FUENTE, _set(campos={}), "campos"),
    (
        FUENTE,
        _set(campos__CODIGO_ANTERIOR={"nombre": "codigo_predial", "tipo": "str", "desc": "x"}),
        "mismo nombre",
    ),
    (FUENTE, _set(frescura__sla_actualizacion="mensual"), "sla_actualizacion"),
    (FUENTE, _set(campo_inventado=1), "campo_inventado"),
    (FUENTE, _set(id="igac.otra"), "debe llamarse"),
    (HERRAMIENTA, _set(fuente="igac.no_existe"), "no existe"),
    (HERRAMIENTA, _set(consulta__campos=["CODIGO", "GLOBALID"]), "lista blanca"),
    (
        HERRAMIENTA,
        _set(consulta__argumentos={"where": "MUNICIPIO = '{municipio}'"}),
        "marcadores sin entrada",
    ),
    (HERRAMIENTA, _set(consulta__capas=[]), "no declara capas"),
    (HERRAMIENTA, _set(consulta__tool="Arcgis Query"), "tool"),
    (HERRAMIENTA, _set(canario__verdad={"propietario": "x"}), "no salen"),
    (HERRAMIENTA, _set(descripcion="Predio en un punto."), "cerrar con"),
    (
        HERRAMIENTA,
        _set(descripcion="Predio. (Fuente: IGAC; licencia: CC BY 4.0.)"),
        "fuente es «CC BY-SA 4.0»",
    ),
    (HERRAMIENTA, _set(canario__entrada={"lon": -74.0}), "entrada del canario"),
    (HERRAMIENTA, _set(familia="deportes"), "familia"),
    (HERRAMIENTA, _set(canario__verdad={}), "verdad"),
]


@pytest.mark.parametrize(("ruta", "cambio", "mensaje"), CASOS)
def test_regla_rota_rompe_el_catalogo(
    tmp_path: Path, ruta: str, cambio: Callable[[dict[str, Any]], None], mensaje: str
) -> None:
    raiz = _catalogo_con(tmp_path, ruta, cambio)
    with pytest.raises(CatalogoInvalido, match=mensaje):
        cargar(raiz)


def test_junta_todos_los_errores(tmp_path: Path) -> None:
    raiz = _catalogo_con(
        tmp_path, HERRAMIENTA, _set(consulta__campos=["X"], canario__verdad={"y": 1})
    )
    with pytest.raises(CatalogoInvalido) as exc:
        cargar(raiz)
    assert len(exc.value.errores) == 2


def test_permiso_escrito_habilita_backend_interno(tmp_path: Path) -> None:
    permiso = {"fecha": "2026-11-01", "evidencia": "radicado 2026-000123"}
    raiz = _catalogo_con(
        tmp_path, FUENTE, _set(clase_acceso="interno_con_permiso", permiso=permiso)
    )
    assert cargar(raiz).fuentes["igac.catastro.terreno"].permiso is not None
