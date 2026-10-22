"""Valida todas las fichas de `catalogo/`. Uso: `uv run scripts/validar_catalogo.py`."""

import sys

from terranova.catalogo import CatalogoInvalido, cargar


def main() -> int:
    try:
        catalogo = cargar()
    except CatalogoInvalido as exc:
        print(f"catálogo inválido ({len(exc.errores)} errores):")
        for error in exc.errores:
            print(f"  - {error}")
        return 1
    fuentes, herramientas = len(catalogo.fuentes), len(catalogo.herramientas)
    print(f"catálogo válido: {fuentes} fuentes, {herramientas} herramientas")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    sys.exit(main())
