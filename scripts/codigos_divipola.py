"""Arma las tablas DIVIPOLA de `catalogo/codigos/`: departamentos (2 dígitos) y municipios (5).

Uso:
    uv run python scripts/codigos_divipola.py <divipola.json>

El JSON es la respuesta de una sola petición al conjunto DIVIPOLA del DANE en datos.gov.co:
    https://www.datos.gov.co/resource/gdxc-w37w.json?$select=cod_dpto,dpto,cod_mpio,nom_mpio&$limit=5000

Los nombres salen como los publica el DANE (en mayúsculas y con tildes). Sirven para que un campo
que solo trae el código («27001») diga también qué es («QUIBDÓ»). Medido el 2026-11-04: 1 122
municipios y áreas no municipalizadas, 33 departamentos, con 27493 (Nuevo Belén de Bajirá, 2022).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

CODIGOS = Path(__file__).resolve().parents[1] / "catalogo" / "codigos"
NORMA = (
    "DANE, División Político-Administrativa de Colombia (DIVIPOLA), en datos.gov.co "
    "(https://www.datos.gov.co/resource/gdxc-w37w.json, CC BY-SA 4.0), leída el {fecha}"
)


def _escribir(nombre: str, codigos: dict[str, str], fecha: str) -> None:
    cuerpo = {"norma": NORMA.format(fecha=fecha), "codigos": dict(sorted(codigos.items()))}
    (CODIGOS / f"{nombre}.yaml").write_text(
        "# Generado por scripts/codigos_divipola.py. No se edita a mano.\n"
        + yaml.safe_dump(cuerpo, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"{len(codigos)} códigos en catalogo/codigos/{nombre}.yaml")


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    filas = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    fecha = sys.argv[2] if len(sys.argv) == 3 else "2026-11-04"
    departamentos = {f["cod_dpto"]: " ".join(f["dpto"].split()) for f in filas}
    municipios = {f["cod_mpio"]: " ".join(f["nom_mpio"].split()) for f in filas}
    if len(departamentos) < 33 or len(municipios) < 1100:
        print(f"Tabla incompleta: {len(departamentos)} departamentos, {len(municipios)} municipios")
        return 1
    _escribir("divipola_departamentos", departamentos, fecha)
    _escribir("divipola_municipios", municipios, fecha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
