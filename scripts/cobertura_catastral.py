"""Regenera `catalogo/cobertura/cobertura_catastral.yaml`: qué cubre la base catastral pública IGAC.

Se cruzan dos cosas:

- **Gestor** de cada municipio: la capa «Municipio - Tipo prestación de servicio» del IGAC
  (`catastro/Gestores_Catastrales`). Solo se guardan campos públicos: el responsable y el contacto
  son datos de personas y no salen (ADR-0014).
- **Cobertura medida** en la propia base, por los sectores rurales y urbanos (capas R_SECTOR y
  U_SECTOR): los 5 primeros dígitos del código son el municipio. Hace falta medirla porque el gestor
  no basta: El Carmen de Viboral figura con gestor IGAC y no tiene predios en la base (2026-10-21).
  El campo `codigo_municipio` de la base tampoco sirve: Chía sale 23175.

Son 4 consultas, sin geometría. Uso: `uv run scripts/cobertura_catastral.py <MM_AAAA del corte>`.
"""

import json
import sys
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

GESTORES = (
    "https://mapas.igac.gov.co/server/rest/services/catastro/Gestores_Catastrales/MapServer/1"
)
BASE = (
    "https://services2.arcgis.com/RVvWzU3lgJISqdke/arcgis/rest/services/"
    "Base_Catastral_Publica_del_Gestor_IGAC_{corte}/FeatureServer"
)
SECTORES = {"rural": 16, "urbano": 8}  # R_SECTOR, U_SECTOR
DESTINO = Path(__file__).resolve().parents[1] / "catalogo/cobertura/cobertura_catastral.yaml"


def _consulta(url: str, **parametros: Any) -> list[dict[str, Any]]:
    """Todas las filas, paginando por `resultOffset`."""
    filas: list[dict[str, Any]] = []
    while True:
        q = urllib.parse.urlencode(
            {**parametros, "returnGeometry": "false", "resultOffset": len(filas), "f": "json"}
        )
        with urllib.request.urlopen(f"{url}/query?{q}", timeout=90) as respuesta:
            datos = json.load(respuesta)
        if "error" in datos:
            raise RuntimeError(f"{url}: {datos['error']}")
        filas += [f["attributes"] for f in datos.get("features", [])]
        if not datos.get("exceededTransferLimit"):
            return filas


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    corte = sys.argv[1]
    gestores = {}
    for a in _consulta(
        GESTORES, where="1=1", outFields="divipola,municipio,departamento,gestor_catastral"
    ):
        divipola = (a.get("divipola") or "").strip()
        if len(divipola) == 5 and divipola.isdigit():
            gestores[divipola] = a
    medidos: dict[str, set[str]] = {}
    for zona, capa in SECTORES.items():
        url = f"{BASE.format(corte=corte)}/{capa}"
        medidos[zona] = {
            str(a["CODIGO"])[:5] for a in _consulta(url, where="1=1", outFields="CODIGO")
        }

    municipios = {}
    for divipola in sorted(set(gestores) | medidos["rural"] | medidos["urbano"]):
        g = gestores.get(divipola, {})
        municipios[divipola] = {
            "municipio": (g.get("municipio") or "").strip() or None,
            "departamento": (g.get("departamento") or "").strip() or None,
            "gestor": (g.get("gestor_catastral") or "").strip() or None,
            "rural": divipola in medidos["rural"],
            "urbano": divipola in medidos["urbano"],
        }
    cubiertos = [m for m in municipios.values() if m["rural"] or m["urbano"]]
    igac_sin_datos = sorted(
        k
        for k, m in municipios.items()
        if m["gestor"] == "IGAC" and not (m["rural"] or m["urbano"])
    )
    otros_con_datos = sorted(
        k
        for k, m in municipios.items()
        if m["gestor"] not in (None, "IGAC") and (m["rural"] or m["urbano"])
    )
    indice = {
        "id": "cobertura_catastral",
        "descripcion": "Municipios con datos en la base catastral pública del gestor IGAC, medidos "
        "por sus sectores, y el gestor de cada uno. Sin datos ⇒ fuera_de_cobertura.",
        "fuentes": {"gestores": GESTORES, "base": BASE.format(corte=corte)},
        "corte": corte,
        "generado": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "resumen": {
            "municipios": len(municipios),
            "con_datos": len(cubiertos),
            "gestor_igac_sin_datos": len(igac_sin_datos),
            "otro_gestor_con_datos": len(otros_con_datos),
        },
        "municipios": municipios,
    }
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(
        yaml.safe_dump(indice, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(indice["resumen"], ensure_ascii=False))
    print("gestor IGAC sin datos (muestra):", igac_sin_datos[:10])
    print("otro gestor con datos (muestra):", otros_con_datos[:10])
    print(Counter(m["gestor"] for m in cubiertos).most_common(5))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    sys.exit(main())
