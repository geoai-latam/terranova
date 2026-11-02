"""Arma `catalogo/codigos/ciiu_rev4_ac.yaml`: las clases de 4 dígitos de la CIIU Rev. 4 A.C.

Uso:
    uv run --with openpyxl --with xlrd python scripts/codigos_ciiu.py \
        <2020.xls> <2021.xlsx> <2022.xlsx>

Los tres archivos son la «Estructura detallada» de cada actualización, en la página de la CIIU del
DANE. Se juntan porque el RUES mezcla ediciones: trae 3210 (2021) y 1030 (2020), que la de 2022 ya
partió. Medido el 2026-11-02: ninguna actualización cambió el significado de un código que siguió
existiendo, solo partió clases en códigos nuevos; el texto que manda es el de la más reciente.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterator
from pathlib import Path

import yaml

DESTINO = Path(__file__).resolve().parents[1] / "catalogo" / "codigos" / "ciiu_rev4_ac.yaml"
NORMA = (
    "DANE, CIIU Rev. 4 A.C., estructura detallada de las actualizaciones 2020 (Resolución 0549 "
    "de 2020), 2021 (Resolución 1505 de 2021) y 2022 (Resolución 2306 de 2022); manda la más "
    "reciente. "
    "https://www.dane.gov.co/files/sen/nomenclatura/ciiu/Estructura-detallada-CIIU-4AC-2022.xlsx"
)


def _filas(ruta: str) -> Iterator[list[str]]:
    if ruta.endswith(".xls"):
        import xlrd

        for hoja in xlrd.open_workbook(ruta).sheets():
            for i in range(hoja.nrows):
                yield [str(c).strip() for c in hoja.row_values(i)]
    else:
        import openpyxl

        for hoja in openpyxl.load_workbook(ruta, read_only=True, data_only=True).worksheets:
            for fila in hoja.iter_rows(values_only=True):
                yield [str(c).strip() if c is not None else "" for c in fila]


def clases(ruta: str) -> dict[str, str]:
    """Código de 4 dígitos → descripción, de una estructura detallada."""
    salida: dict[str, str] = {}
    for celdas in _filas(ruta):
        celdas = [re.sub(r"\.0$", "", c) for c in celdas]  # xlrd lee 111 como «111.0»
        codigo = next((c for c in celdas if re.fullmatch(r"\d{4}", c)), None)
        textos = [c for c in celdas if c and not re.fullmatch(r"[\d.]+", c) and len(c) > 3]
        if codigo and textos:
            salida.setdefault(codigo, " ".join(textos[-1].split()))
    return salida


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    juntas: dict[str, str] = {}
    for ruta in sys.argv[1:]:  # de la más vieja a la más reciente: la última manda
        juntas.update(clases(ruta))
    DESTINO.parent.mkdir(exist_ok=True)
    cuerpo = {"norma": NORMA, "codigos": dict(sorted(juntas.items()))}
    DESTINO.write_text(
        "# Generado por scripts/codigos_ciiu.py. No se edita a mano.\n"
        + yaml.safe_dump(cuerpo, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"{len(juntas)} clases en {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
