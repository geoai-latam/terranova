"""Cosecha la ficha técnica de las fuentes (spec 08) y la guarda en `catalogo/metadatos/`.

Uso:
  `uv run scripts/cosechar_metadatos.py [fuente …]`             cosecha y escribe
  `uv run scripts/cosechar_metadatos.py --comprobar [fuente …]` solo compara (canario de deriva):
      sale con 1 si una fuente cambió de columnas, tipo, corte, capas o geometría.

Sin fuentes, todas las de datos.gov.co y ArcGIS. Son pocas peticiones por fuente, con pausa: no es
carga. Las demás fuentes (API propia, archivo) llevan su ficha técnica escrita a mano (`metodo:
manual`) y este script no las toca.
"""

import argparse
import sys
from pathlib import Path

import httpx
import yaml

from terranova.catalogo import RAIZ, Metadatos, cargar
from terranova.cosecha import cosechar, diferencias

DESTINO = RAIZ / "metadatos"
CABECERA = "# Generado por scripts/cosechar_metadatos.py (spec 08). No se edita a mano.\n"


def escribir(m: Metadatos) -> Path:
    ruta = DESTINO / f"{m.fuente}.yaml"
    datos = m.model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    datos = {"fuente": m.fuente, "metodo": m.metodo, "cosechado": str(m.cosechado), **datos}
    texto = yaml.safe_dump(datos, allow_unicode=True, sort_keys=False, width=100)
    ruta.write_text(CABECERA + texto, encoding="utf-8")
    return ruta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fuentes", nargs="*")
    parser.add_argument("--comprobar", action="store_true", help="solo comparar con lo guardado")
    a = parser.parse_args()
    catalogo = cargar()
    ids = a.fuentes or sorted(
        f.id for f in catalogo.fuentes.values() if f.protocolo in ("socrata", "arcgis_rest")
    )
    con_cambios = 0
    for fid in ids:
        try:
            nueva = cosechar(catalogo, fid)
        except (httpx.HTTPError, ValueError) as exc:
            print(f"✗ {fid}: {type(exc).__name__}: {exc}"[:300])
            con_cambios += 1
            continue
        if a.comprobar:
            guardada = catalogo.metadatos.get(fid)
            cambios = diferencias(guardada, nueva) if guardada else ["sin ficha técnica guardada"]
            print(f"{'≠' if cambios else '='} {fid}" + "".join(f"\n    {c}" for c in cambios))
            con_cambios += bool(cambios)
        else:
            escribir(nueva)
            datos = nueva.datos_actualizados
            print(f"✓ {fid}: {len(nueva.campos)} campos, filas {nueva.filas}, datos {datos}")
    return 1 if con_cambios else 0


if __name__ == "__main__":
    sys.exit(main())
