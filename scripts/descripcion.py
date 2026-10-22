"""Regenera `docs/HERRAMIENTAS.md` del catálogo. Con `--check` falla si quedó viejo (CI)."""

import argparse
import sys
from pathlib import Path

from terranova.catalogo import cargar
from terranova.descripcion import herramientas_md

DESTINO = Path(__file__).resolve().parents[1] / "docs" / "HERRAMIENTAS.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    nuevo = herramientas_md(cargar())
    actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else None
    if parser.parse_args().check:
        if actual != nuevo:
            print("docs/HERRAMIENTAS.md desactualizado: corre `uv run scripts/descripcion.py`")
            return 1
        return 0
    DESTINO.write_text(nuevo, encoding="utf-8", newline="\n")
    print(f"escrito {DESTINO.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
