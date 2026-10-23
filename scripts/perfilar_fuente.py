"""Perfil de una fuente (spec 07): qué es una fila y si su clave es única.

Mide sobre una muestra (`--donde`, un filtro concreto), nunca la tabla entera:

1. filas de la muestra y valores distintos de la clave;
2. nulos de cada columna de la lista blanca de la ficha (solo datos.gov.co);
3. segundos de filtrar, contar, ordenar y agrupar (300 s de tope, 3 s entre consultas);
4. en ArcGIS, con `--punto lon,lat`, cuántos elementos tocan ese punto: un «en punto» que trae
   varios polígonos (vigencias que se solapan, bordes) no es una respuesta única.

Imprime el bloque `perfil:` con lo medido. `fila`, `hallazgos` y `decision` los completa una
persona: el script no sabe qué significa un código ni si un `nit` trae cédulas.

Uso: `uv run scripts/perfilar_fuente.py cce.secop2.ofertas --clave identificador_de_la_oferta \\
      --donde "id_del_proceso_de_compra = 'CO1.BDOS.6343828'"`
     `uv run scripts/perfilar_fuente.py igac.catastro.terreno --clave CODIGO \\
      --donde "CODIGO LIKE '25175%'" --punto -74.0262,4.8619`
"""

import argparse
import sys
import time
from datetime import date
from typing import Any

import httpx

from terranova.catalogo import Fuente, cargar

TOPE_S = 300.0
PAUSA_S = 3.0


def _medir(http: httpx.Client, url: str, params: dict[str, str]) -> tuple[float | None, Any]:
    """(segundos, respuesta) o (None, None) si no respondió en el tope o respondió con error."""
    time.sleep(PAUSA_S)
    inicio = time.monotonic()
    try:
        r = http.get(url, params=params, timeout=TOPE_S)
        r.raise_for_status()
        datos = r.json()
    except (httpx.TimeoutException, httpx.HTTPStatusError, ValueError):
        return None, None
    if isinstance(datos, dict) and "error" in datos:  # ArcGIS responde 200 con el error adentro
        return None, None
    return round(time.monotonic() - inicio, 1), datos


def _perfil_socrata(http: httpx.Client, fuente: Fuente, clave: str, donde: str) -> dict[str, Any]:
    url = str(fuente.url)
    columnas = list(fuente.campos)
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
    operaciones = {"filtrar": filtrar, "contar": contar, "ordenar": ordenar, "agrupar": agrupar}
    return {"filas": total, "distintos": distintos, "nulos": nulos, "operaciones": operaciones}


def _perfil_arcgis(
    http: httpx.Client, fuente: Fuente, capa: int, clave: str, donde: str, punto: str | None
) -> dict[str, Any]:
    url = f"{fuente.url}/{capa}/query"
    base = {"where": donde, "f": "json"}
    filtrar, _ = _medir(http, url, {**base, "outFields": clave, "resultRecordCount": "1"})
    contar, cuenta = _medir(http, url, {**base, "returnCountOnly": "true"})
    _, distintos = _medir(
        http,
        url,
        {**base, "outFields": clave, "returnDistinctValues": "true", "returnCountOnly": "true"},
    )
    ordenar, _ = _medir(
        http, url, {**base, "outFields": clave, "orderByFields": clave, "resultRecordCount": "1"}
    )
    # una clave compuesta («A,B») se agrupa entera y se cuenta sobre su primera columna
    primera = clave.split(",")[0]
    estadistica = (
        f'[{{"statisticType":"count","onStatisticField":"{primera}","outStatisticFieldName":"n"}}]'
    )
    agrupar, _ = _medir(
        http, url, {**base, "groupByFieldsForStatistics": clave, "outStatistics": estadistica}
    )
    medida: dict[str, Any] = {
        "filas": int((cuenta or {}).get("count", 0)),
        # None: el servidor no sabe contar distintos (MapServer viejo); lo dice el perfil
        "distintos": (distintos or {}).get("count"),
        "nulos": {},
        "operaciones": {
            "filtrar": filtrar,
            "contar": contar,
            "ordenar": ordenar,
            "agrupar": agrupar,
        },
    }
    if punto:
        lon, lat = punto.split(",")
        _, en_punto = _medir(
            http,
            url,
            {
                "where": "1=1",
                "geometry": f"{lon},{lat}",
                "geometryType": "esriGeometryPoint",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "returnCountOnly": "true",
                "f": "json",
            },
        )
        medida["en_punto"] = (en_punto or {}).get("count")
    return medida


def perfilar(
    fuente_id: str, clave: str, donde: str, *, capa: int | None = None, punto: str | None = None
) -> dict[str, Any]:
    fuente = cargar().fuentes[fuente_id]
    with httpx.Client(headers={"User-Agent": "terranova-perfil/1"}) as http:
        if fuente.protocolo == "socrata":
            medida = _perfil_socrata(http, fuente, clave, donde)
        elif fuente.protocolo == "arcgis_rest":
            if capa is None:
                raise SystemExit(f"{fuente_id} es ArcGIS: hace falta --capa")
            medida = _perfil_arcgis(http, fuente, capa, clave, donde, punto)
        else:
            raise SystemExit(
                f"{fuente_id} ({fuente.protocolo}): este perfilador mide Socrata y ArcGIS"
            )
    total, distintos = medida.pop("filas"), medida.pop("distintos")
    return {
        "medido": date.today().isoformat(),
        "muestra": donde,
        "filas": total,
        "clave": {
            "columna": clave,
            "unica": None if distintos is None else bool(total) and total == distintos,
            "distintos": distintos,
        },
        **medida,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fuente")
    parser.add_argument("--clave", required=True)
    parser.add_argument(
        "--donde", required=True, help="filtro de la muestra (SoQL o where de ArcGIS)"
    )
    parser.add_argument("--capa", type=int, help="ArcGIS: número de la capa")
    parser.add_argument("--punto", help="ArcGIS: lon,lat para contar cuántos elementos lo tocan")
    a = parser.parse_args()
    p = perfilar(a.fuente, a.clave, a.donde, capa=a.capa, punto=a.punto)
    c = p["clave"]
    print(f"# {a.fuente}: {p['filas']} filas en la muestra «{p['muestra']}»")
    print(f"# {c['distintos']} valores distintos de {c['columna']}")
    if p["nulos"]:
        print(f"# nulos: {p['nulos']}")
    if "en_punto" in p:
        print(f"# elementos en el punto {a.punto}: {p['en_punto']}")
    unica = "null" if c["unica"] is None else str(c["unica"]).lower()
    print("perfil:")
    print(f"  medido: {p['medido']}")
    print('  fila: "COMPLETAR: qué representa una fila, con el ejemplo medido"')
    print(f"  clave: {{columna: {c['columna']}, unica: {unica}}}")
    ops = ", ".join(f"{k}: {'null' if v is None else v}" for k, v in p["operaciones"].items())
    print(f"  operaciones: {{{ops}}}  # segundos; null = no respondió en {TOPE_S:.0f} s")
    print("  hallazgos: []")
    print('  decision: "COMPLETAR"')
    return 0


if __name__ == "__main__":
    sys.exit(main())
