"""Construye el dataset de restricciones v0 (F4.1). Uso:
`uv run --extra datasets scripts/dataset_restricciones.py [--fuentes datos_locales/fuentes]
[--salida datos_locales/datasets]`"""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from terranova.datasets.restricciones import cargar_postgis, construir


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fuentes", type=Path, default=Path("datos_locales/fuentes"))
    p.add_argument("--salida", type=Path, default=Path("datos_locales/datasets"))
    p.add_argument("--postgis", help="postgresql://… para cargar la versión en curado.*")
    a = p.parse_args()
    manifiesto = construir(a.fuentes, a.salida)
    print(json.dumps(asdict(manifiesto), ensure_ascii=False, indent=2))
    if a.postgis:
        parquet = a.salida / f"restricciones_{manifiesto.version}.parquet"
        print("cargado en curado." + cargar_postgis(parquet, a.postgis, manifiesto))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    sys.exit(main())
