"""Prepara los datos de las figuras de la portada: web/publico/datos/portada.json.

Todo sale de archivos locales, sin una sola consulta a servidores del Estado:

- criba y expediente: los 1.335 linderos del SINIC alrededor del predio del héroe
  (web/publico/datos/sm.json, IGAC SINIC, copia del 28-10-2026) cruzados con la copia de
  restricciones del repo (RUNAP de Parques Nacionales y resguardos de la ANT, versión del
  22-10-2026, huella 3696177c). Un predio va «a revisión» si su lindero se monta más de 2 m² sobre
  el de otro de la misma copia. La huella del expediente es un sha256 local de sus filas.
- indicadores de Chía (25175): las respuestas capturadas de tests/doradas (MinEducación, INS,
  Policía Nacional, IGAC; capturadas del 22 al 28-10-2026).
- Pitalito 2025: la respuesta capturada de secop_integrado_contratos_entidad (23-10-2026). La suma
  «tal cual» (174.000 millones) es la medida del perfil de la fuente del 22-10-2026.
- bitácora: el registro de modificaciones del contrato CO1.PCCNTR.3712964 de SECOP II, capturado
  el 02-11-2026 (tests/doradas/secop_modificaciones_contrato.json). Va sin nombres de personas: solo
  fecha, estado, días, propósito e identificador de cada modificación.

El índice del catálogo no va aquí: la figura lo arma con datos/catalogo.json, que escribe
construir.py.

La copia de restricciones no se versiona (datos_locales/, ver docs/ESTADO.md); por eso portada.json
sí va en el repo. Para regenerarlo, desde un checkout con datos_locales/:

    uv run --extra datasets python web/portada_datos.py                      # usa ./datos_locales
    uv run --extra datasets python web/portada_datos.py --copias <carpeta>   # otra carpeta

y luego `uv run python web/construir.py` (las páginas leen portada.json al construirse).
"""

from __future__ import annotations

import collections
import datetime
import hashlib
import json
import math
import sys
from pathlib import Path

import pyarrow.parquet as pq
import shapely
from shapely import Point, Polygon, make_valid, wkb
from shapely.strtree import STRtree

RAIZ = Path(__file__).resolve().parent.parent
PUBLICO = RAIZ / "web" / "publico"
SALIDA = PUBLICO / "datos" / "portada.json"
DORADAS = RAIZ / "tests" / "doradas"
RESTRICCIONES = "datasets/restricciones_v0-2026-10-22-3696177c.parquet"
VERSION, HUELLA_COPIA = "2026-10-22", "3696177c"
UMBRAL_M2 = 2.0
LAT0, LON0 = 11.2211, -74.1572  # el punto del héroe (sm.json está en metros alrededor de él)
MX, MY = 111320 * math.cos(math.radians(LAT0)), 110574


def corto(c: str) -> str:
    return f"{c[:5]}…{c[-4:]}"


def criba(copias: Path) -> dict:
    d = json.loads((PUBLICO / "datos" / "sm.json").read_text(encoding="utf-8"))
    codes, obj = d["codes"], d["obj"]
    pm = [make_valid(Polygon([(f[i], f[i + 1]) for i in range(0, len(f), 2)])) for f in d["polys"]]
    pg = [
        Polygon([(LON0 + f[i] / MX, LAT0 + f[i + 1] / MY) for i in range(0, len(f), 2)])
        for f in d["polys"]
    ]
    # RUNAP y ANT: cruce local contra la copia de restricciones
    tab = pq.read_table(copias / RESTRICCIONES).to_pylist()
    geoms = [make_valid(wkb.loads(r["geometry"])) for r in tab]
    arbol = STRtree(geoms)
    choques = {i for i, p in enumerate(pg) if any(geoms[j].intersects(p) for j in arbol.query(p))}
    pt = Point(LON0, LAT0)
    cerca = []
    for r, g in zip(tab, geoms, strict=True):
        km = g.distance(pt) * 111000
        if km < 8000:
            cerca.append(
                {
                    "km": round(km / 1000, 2),
                    "tipo": r["tipo"],
                    "nombre": r["nombre"],
                    "categoria": r["categoria"],
                    "id": r["id"],
                    "fuente": r["fuente_id"],
                }
            )
    cerca.sort(key=lambda c: c["km"])
    # IGAC: linderos que se montan sobre el de otro predio de la misma copia
    t2 = STRtree(pm)
    cruce: dict[int, list[tuple[int, float]]] = collections.defaultdict(list)
    for i, p in enumerate(pm):
        for j in t2.query(p):
            if j <= i:
                continue
            a = p.intersection(pm[j]).area
            if a > UMBRAL_M2:
                cruce[i].append((int(j), a))
                cruce[int(j)].append((i, a))
    rev = sorted(cruce)
    oc = pm[obj].centroid
    dud = min(rev, key=lambda i: pm[i].centroid.distance(oc))  # el dudoso más cercano al héroe
    vec, m2 = max(cruce[dud], key=lambda x: x[1])

    def local(g):  # a metros alrededor del punto, como sm.json
        return shapely.transform(g, lambda c: (c - [LON0, LAT0]) * [MX, MY])

    for c in cerca:
        g = geoms[next(k for k, r in enumerate(tab) if r["id"] == c["id"])]
        c["km_dudoso"] = round(local(g).distance(pm[dud]) / 1000, 2)
        c["km_heroe"] = round(local(g).distance(pm[obj]) / 1000, 2)
    expediente = [
        {"fuente": "pnn.runap", "estado": "no_encontrado", "copia": VERSION},
        {"fuente": "ant.resguardos_indigenas", "estado": "no_encontrado", "copia": VERSION},
        {"fuente": "sinchi.perdida_bosque", "estado": "fuera_de_cobertura"},
        {
            "fuente": "igac.sinic_terreno",
            "estado": "por_revisar",
            "copia": "2026-10-28",
            "motivo": "lindero_montado",
            "m2": round(m2, 1),
            "vecino": codes[vec],
        },
    ]
    assert dud not in choques, "el dudoso toca una restricción: el expediente ya no dice «ninguna»"
    huella = hashlib.sha256(
        json.dumps(
            {"predio": codes[dud], "filas": expediente}, sort_keys=True, ensure_ascii=False
        ).encode()
    ).hexdigest()
    return {
        "n": len(pm),
        "umbral_m2": UMBRAL_M2,
        "revision": rev,
        "dudoso": dud,
        "dudoso_codigo": codes[dud],
        "dudoso_corto": corto(codes[dud]),
        "dudoso_vecino": corto(codes[vec]),
        "dudoso_m2": round(m2, 1),
        "dudoso_area": round(pm[dud].area, 1),
        "dudoso_dist_heroe_m": round(pm[dud].centroid.distance(oc)),
        "heroe": obj,
        "heroe_codigo": codes[obj],
        "heroe_corto": corto(codes[obj]),
        "con_hallazgo": len(choques),
        "sin_poligono": 0,
        "cercanas": cerca[:5],
        "restricciones": {
            "RUNAP": sum(r["tipo"] == "area_protegida" for r in tab),
            "total": len(tab),
        },
        "version": VERSION,
        "huella_copia": HUELLA_COPIA,
        "expediente": expediente,
        "huella": huella,
        "cruce": datetime.date.today().isoformat(),
    }


def dorada(nombre: str) -> tuple[dict, list[dict]]:
    d = json.loads((DORADAS / f"{nombre}.json").read_text(encoding="utf-8"))
    return d, d["llamadas"][0]["respuesta"]["artifacts"][0]["rows"]


def indicadores() -> list[dict]:
    cat = json.loads((PUBLICO / "datos" / "catalogo.json").read_text(encoding="utf-8"))
    her = {h["id"]: h for h in cat["herramientas"]}

    def lic(tool: str) -> str:
        return cat["fuentes"][her[tool]["fuente"]]["licencia"]

    ind = []
    t = "men_educacion_municipio"
    d, r = dorada(t)
    ind.append(
        {
            "k": "Deserción escolar",
            "u": "%",
            "v": float(r[-1]["deserci_n"]),
            "antes": float(r[-2]["deserci_n"]),
            "corte": r[-1]["a_o"],
            "corte_antes": r[-2]["a_o"],
            "entidad": "MinEducación",
            "tool": t,
            "licencia": lic(t),
            "grabado": d["grabado"][:10],
        }
    )
    t = "ins_calidad_agua_municipio"
    d, r = dorada(t)
    ind.append(
        {
            "k": "Riesgo del agua (IRCA)",
            "u": "",
            "v": float(r[-1]["irca"]),
            "antes": float(r[-2]["irca"]),
            "corte": r[-1]["a_o"],
            "corte_antes": r[-2]["a_o"],
            "nota": r[-1]["nivel_de_riesgo"],
            "entidad": "INS",
            "tool": t,
            "licencia": lic(t),
            "grabado": d["grabado"][:10],
        }
    )
    t = "policia_hurto_comercio_residencias_municipio"
    d, r = dorada(t)
    ind.append(
        {
            "k": "Hurtos a residencias",
            "u": "",
            "v": sum(int(x["casos"]) for x in r if "RESIDENCIAS" in x["tipo_de_hurto"]),
            "corte": "2024",
            "entidad": "Policía Nacional",
            "tool": t,
            "licencia": lic(t),
            "grabado": d["grabado"][:10],
            "extra": {
                "comercio": sum(int(x["casos"]) for x in r if "COMERCIALES" in x["tipo_de_hurto"])
            },
        }
    )
    t = "igac_compraventas_municipio"
    d, r = dorada(t)
    ind.append(
        {
            "k": "Compraventas",
            "u": "",
            "v": int(r[-1]["compraventas"]),
            "antes": int(r[-2]["compraventas"]),
            "corte": r[-1]["year_radica"],
            "corte_antes": r[-2]["year_radica"],
            "entidad": "IGAC",
            "tool": t,
            "licencia": lic(t),
            "grabado": d["grabado"][:10],
        }
    )
    return ind


def pitalito() -> dict:
    d, r = dorada("secop_integrado_contratos_entidad")
    p25 = next(x for x in r if x.get("anio") == "2025" and x["origen"] == "SECOPII")
    return {
        "contratos": int(p25["contratos"]),
        "valor": int(p25["valor_total"]),
        "tal_cual_M": 174000,  # perfil de la fuente del 22-10-2026
        "grabado": d["grabado"][:10],
        "perfil": "2026-10-22",
        "nit": "891180077",  # la Alcaldía de Pitalito (una entidad, no una persona)
    }


def bitacora() -> dict:
    d, r = dorada("secop_modificaciones_contrato")
    mods = [
        {
            "f": x["fecha_creacion"][:10],
            "estado": x["estado_modificacion"],
            "dias": int(float(x["dias_extendidos"] or 0)),
            "prop": x["proposito_modificacion"],
            "id": x["identificador_modificacion"],
        }
        for x in r
    ]
    ds, _ = dorada("suin_norma")
    return {
        "contrato": "CO1.PCCNTR.3712964",
        "grabado": d["grabado"][:10],
        "mods": mods,
        "suin_grabado": ds["grabado"][:10],
    }


def main() -> int:
    copias = RAIZ / "datos_locales"
    if "--copias" in sys.argv:
        copias = Path(sys.argv[sys.argv.index("--copias") + 1])
    if not (copias / RESTRICCIONES).exists():
        print(f"Falta la copia de restricciones: {copias / RESTRICCIONES}")
        return 1
    out = {
        "criba": criba(copias),
        "indicadores": indicadores(),
        "municipio": {"nombre": "Chía", "divipola": "25175"},
        "pitalito": pitalito(),
        "bitacora": bitacora(),
    }
    texto = json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n"
    SALIDA.write_text(texto, encoding="utf-8", newline="\n")
    print(f"escrito {SALIDA} ({len(texto.encode())} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
