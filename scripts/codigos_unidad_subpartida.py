"""Arma `catalogo/codigos/unidad_subpartida.yaml`: la unidad física de la cantidad de cada
subpartida arancelaria, como la trae el microdato de comercio exterior del DANE.

Uso:
    uv run python scripts/codigos_unidad_subpartida.py <zip> [<zip> …]

Cada ZIP es uno de los que copia Terrnova (ANDA 859 exportaciones, 856 importaciones): trae un ZIP
por mes con un CSV separado por «;». La subpartida está en POSAR (expo) o NABAN (impo) y la unidad,
en CODUNI2 (expo) o CODA (impo). Medido el 2026-11-02: en las exportaciones y las importaciones de
2025 y 2026, cada una de las 7 007 subpartidas tiene una sola unidad. Si una subpartida trae dos, el
script falla: no se elige una a ciegas.
"""

from __future__ import annotations

import collections
import io
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path

import yaml

DESTINO = Path(__file__).resolve().parents[1] / "catalogo" / "codigos" / "unidad_subpartida.yaml"
NORMA = (
    "DANE, microdato de exportaciones (ANDA 859) e importaciones (ANDA 856), columnas CODUNI2 y "
    "CODA: la unidad física de la cantidad de cada subpartida NANDINA. "
    "https://microdatos.dane.gov.co/index.php/catalog/859"
)
# Las siglas que traen CODUNI2 y CODA. Comprobadas con el peso: el crudo en M3 da 0,92 kg por
# unidad; las esmeraldas en C/T, 0,2 g (un quilate); las medias en 2U, pares.
NOMBRES = {
    "KG": "kilogramos",
    "U": "unidades",
    "M2": "metros cuadrados",
    "M3": "metros cúbicos",
    "L": "litros",
    "2U": "pares",
    "MIL": "millares",
    "C/T": "quilates",
    "KWH": "kilovatios hora",
    "CM3": "centímetros cúbicos",
}


def _csvs(ruta: str) -> Iterator[io.TextIOWrapper]:
    """Los CSV de un ZIP, también los que vienen dentro de otro ZIP (uno por mes)."""
    pila = [zipfile.ZipFile(ruta)]
    while pila:
        z = pila.pop()
        for nombre in z.namelist():
            if nombre.lower().endswith(".zip"):
                pila.append(zipfile.ZipFile(io.BytesIO(z.read(nombre))))
            elif nombre.lower().endswith(".csv"):
                yield io.TextIOWrapper(z.open(nombre), encoding="latin-1")


def unidades(rutas: list[str]) -> dict[str, collections.Counter[str]]:
    vistas: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for ruta in rutas:
        for texto in _csvs(ruta):
            encabezado = [c.strip() for c in next(texto).lstrip("﻿").split(";")]
            i_sub = encabezado.index("POSAR" if "POSAR" in encabezado else "NABAN")
            i_uni = encabezado.index("CODUNI2" if "CODUNI2" in encabezado else "CODA")
            for linea in texto:
                fila = linea.split(";")
                vistas[fila[i_sub].strip()][fila[i_uni].strip()] += 1
    return vistas


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    vistas = unidades(sys.argv[1:])
    dobles = {s: dict(u) for s, u in vistas.items() if len(u) > 1}
    if dobles:
        print(f"{len(dobles)} subpartidas con más de una unidad, p. ej. {list(dobles.items())[:5]}")
        return 1
    sin_nombre = {next(iter(u)) for u in vistas.values()} - set(NOMBRES)
    if sin_nombre:
        print(f"unidades sin nombre: {sorted(sin_nombre)}")
        return 1
    codigos = {s: NOMBRES[next(iter(u))] for s, u in sorted(vistas.items())}
    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(
        "# Generado por scripts/codigos_unidad_subpartida.py. No se edita a mano.\n"
        + yaml.safe_dump(
            {"norma": NORMA, "codigos": codigos}, allow_unicode=True, sort_keys=False, width=100
        ),
        encoding="utf-8",
    )
    print(f"{len(codigos)} subpartidas en {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
