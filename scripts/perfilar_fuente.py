"""Perfil de una fuente de datos.gov.co (spec 07): qué es una fila y si su clave es única.

Mide sobre una muestra (`--donde`, un filtro concreto), nunca la tabla entera:

1. filas de la muestra y valores distintos de la clave;
2. nulos de cada columna de la lista blanca de la ficha;
3. segundos de filtrar, contar, ordenar y agrupar (300 s de tope, 3 s entre consultas).

Imprime el bloque `perfil:` con lo medido. `fila`, `hallazgos` y `decision` los completa una
persona: el script no sabe qué significa un código ni si un `nit` trae cédulas.

Uso: `uv run scripts/perfilar_fuente.py cce.secop2.ofertas --clave identificador_de_la_oferta \\
      --donde "id_del_proceso_de_compra = 'CO1.BDOS.6343828'"`
"""

import argparse
import sys
import time
from datetime import date
from typing import Any

import httpx

from terranova.catalogo import cargar

TOPE_S = 300.0
PAUSA_S = 3.0
API = "https://www.datos.gov.co/resource"


def _medir(http: httpx.Client, url: str, params: dict[str, str]) -> tuple[float | None, Any]:
    """(segundos, respuesta) o (None, None) si no respondió en el tope."""
    time.sleep(PAUSA_S)
    inicio = time.monotonic()
    try:
        r = http.get(url, params=params, timeout=TOPE_S)
        r.raise_for_status()
        return round(time.monotonic() - inicio, 1), r.json()
    except (httpx.TimeoutException, httpx.HTTPStatusError):
        return None, None


def perfilar(fuente_id: str, clave: str, donde: str) -> dict[str, Any]:
    fuente = cargar().fuentes[fuente_id]
    if fuente.protocolo != "socrata":
        raise SystemExit(f"{fuente_id} no es de datos.gov.co: este perfilador mide solo Socrata")
    url = str(fuente.url)
    columnas = list(fuente.campos)
    with httpx.Client(headers={"User-Agent": "terranova-perfil/1"}) as http:
        filtrar, _ = _medir(http, url, {"$where": donde, "$limit": "1"})
        conteos = ", ".join(
            ["count(*) AS filas", f"count(distinct {clave}) AS distintos"]
            + [f"count({c}) AS no_nulos_{i}" for i, c in enumerate(columnas)]
        )
        contar, filas = _medir(http, url, {"$select": conteos, "$where": donde})
        ordenar, _ = _medir(http, url, {"$where": donde, "$order": clave, "$limit": "1"})
        agrupar, _ = _medir(
            http,
            url,
            {"$select": f"{clave}, count(*) AS n", "$where": donde, "$group": clave, "$limit": "1"},
        )
    medida = (filas or [{}])[0]
    total, distintos = int(medida.get("filas", 0)), int(medida.get("distintos", 0))
    nulos = {
        c: total - int(medida.get(f"no_nulos_{i}", 0))
        for i, c in enumerate(columnas)
        if total and int(medida.get(f"no_nulos_{i}", 0)) < total
    }
    return {
        "medido": date.today().isoformat(),
        "muestra": donde,
        "filas": total,
        "clave": {
            "columna": clave,
            "unica": bool(total) and total == distintos,
            "distintos": distintos,
        },
        "nulos": nulos,
        "operaciones": {
            "filtrar": filtrar,
            "contar": contar,
            "ordenar": ordenar,
            "agrupar": agrupar,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fuente")
    parser.add_argument("--clave", required=True)
    parser.add_argument("--donde", required=True, help="filtro de la muestra (SoQL)")
    a = parser.parse_args()
    p = perfilar(a.fuente, a.clave, a.donde)
    c = p["clave"]
    print(f"# {a.fuente}: {p['filas']} filas en la muestra «{p['muestra']}»")
    print(f"# {c['distintos']} valores distintos de {c['columna']}")
    if p["nulos"]:
        print(f"# nulos: {p['nulos']}")
    print("perfil:")
    print(f"  medido: {p['medido']}")
    print('  fila: "COMPLETAR: qué representa una fila, con el ejemplo medido"')
    print(f"  clave: {{columna: {c['columna']}, unica: {str(c['unica']).lower()}}}")
    ops = ", ".join(f"{k}: {'null' if v is None else v}" for k, v in p["operaciones"].items())
    print(f"  operaciones: {{{ops}}}  # segundos; null = no respondió en {TOPE_S:.0f} s")
    print("  hallazgos: []")
    print('  decision: "COMPLETAR"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
