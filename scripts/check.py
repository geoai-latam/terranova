"""Corre las mismas comprobaciones que el CI. Uso: `uv run scripts/check.py` (o `make check`)."""

import subprocess
import sys

PASOS: list[list[str]] = [
    ["ruff", "check", "."],
    ["ruff", "format", "--check", "."],
    ["mypy"],
    [sys.executable, "scripts/esquema.py", "--check"],
    [sys.executable, "scripts/validar_catalogo.py"],
    [sys.executable, "scripts/descripcion.py", "--check"],
    [sys.executable, "scripts/sin_invisibles.py"],
    # Cobertura en la misma corrida (sin coste extra de RAM): term-missing para ver qué falta y un
    # piso que no debe bajar. El piso vale para esta suite (sin extras), la que corre `make check`.
    ["pytest", "--cov=terranova", "--cov-report=term-missing", "--cov-fail-under=70"],
]


def main() -> int:
    for paso in PASOS:
        print(f"\n> {' '.join(paso)}", flush=True)
        if subprocess.run(paso, check=False).returncode != 0:
            print(f"\nx fallo: {' '.join(paso)}")
            return 1
    print("\nok: check verde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
