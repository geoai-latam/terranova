"""Exporta el JSON Schema de `rt/1`. Con `--check` falla si el versionado no coincide con el código.

Uso: `uv run scripts/esquema.py` (escribe) · `uv run scripts/esquema.py --check` (CI).
"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from terranova.contrato import Problema, Sobre

DESTINO = Path(__file__).resolve().parents[1] / "esquemas"
ESQUEMAS: dict[str, type[BaseModel]] = {
    "rt1.sobre.schema.json": Sobre,
    "rt1.problema.schema.json": Problema,
}


def _generar(modelo: type[BaseModel]) -> str:
    esquema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **modelo.model_json_schema(mode="serialization"),
    }
    return json.dumps(esquema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    distintos = []
    for nombre, modelo in ESQUEMAS.items():
        ruta, nuevo = DESTINO / nombre, _generar(modelo)
        actual = ruta.read_text(encoding="utf-8") if ruta.exists() else None
        if actual == nuevo:
            continue
        if args.check:
            distintos.append(nombre)
        else:
            DESTINO.mkdir(exist_ok=True)
            ruta.write_text(nuevo, encoding="utf-8", newline="\n")
            print(f"escrito {ruta.name}")
    if distintos:
        print(f"esquema desactualizado: {', '.join(distintos)}. Corre `uv run scripts/esquema.py`.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
