"""Falla si hay caracteres invisibles (bidi o de control) en el código o el catálogo.

Un carácter bidi literal puede hacer que el código se lea distinto de como corre («Trojan Source»,
CVE-2021-42574). En el código van como escape (`\\u202e`), nunca literales.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CARPETAS = ("src", "tests", "scripts", "catalogo", "esquemas", "docs")
EXTENSIONES = {".py", ".md", ".yaml", ".yml", ".json", ".toml"}
INVISIBLES = (
    set(range(0x202A, 0x202F))
    | set(range(0x2066, 0x206A))
    | {0x200E, 0x200F, 0x061C}
    | (set(range(0, 32)) - {9, 10, 13})
)


def main() -> int:
    hallados = []
    for carpeta in CARPETAS:
        for ruta in sorted((RAIZ / carpeta).rglob("*")):
            if ruta.suffix not in EXTENSIONES or "__pycache__" in ruta.parts:
                continue
            for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                malos = sorted({f"U+{ord(c):04X}" for c in linea if ord(c) in INVISIBLES})
                if malos:
                    hallados.append(f"{ruta.relative_to(RAIZ)}:{n}: {', '.join(malos)}")
    if hallados:
        print("caracteres invisibles (usa escapes):")
        print("\n".join(f"  {h}" for h in hallados))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
