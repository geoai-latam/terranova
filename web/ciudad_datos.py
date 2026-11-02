"""Prepara la ciudad de la celda de Santa Marta para el mapa de cobertura (datos/ciudad-sm.bin).

La figura de cobertura entra cerca, con la ciudad real llenando su hexágono: un punto por terreno
de la copia SINIC del IGAC (copia.sinic_terreno, la del servidor) que cae dentro de la celda de
Santa Marta de datos/co.json. Solo puntos: sin códigos, sin dueños, sin áreas.

La consulta, de solo lectura, que da el CSV de entrada (lon, lat, área en m²):

    SELECT round(ST_X(p)::numeric, 6), round(ST_Y(p)::numeric, 6), round(ST_Area(g::geography))
    FROM (SELECT ST_PointOnSurface(_geom) AS p, _geom AS g
          FROM copia.sinic_terreno
          WHERE _geom && ST_MakeEnvelope(-74.24, 11.14, -74.04, 11.33, 4326)) s;

El binario: un encabezado de 4 float32 (lon y lat del centro de la celda, radio del hexágono en
grados, número de puntos) y luego dos uint16 por punto, x e y escalados de [-radio, radio].

    uv run python web/ciudad_datos.py <csv>
"""

from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "web" / "publico" / "datos"
LAT0, LON0 = 11.2211, -74.1572  # el punto del héroe
ESCALA = 0.9  # el hexágono dibujado mide 0,9 del radio de la celda (fig-cobertura.js)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    co = json.loads((DATOS / "co.json").read_text(encoding="utf-8"))
    cx, cy, _ = min(co["bins"], key=lambda b: (b[0] - LON0) ** 2 + (b[1] - LAT0) ** 2)
    r = co["R"] * ESCALA
    s3 = math.sqrt(3) / 2
    pts = []
    for linea in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
        lon, lat, _area = (float(v) for v in linea.split(","))
        dx, dy = lon - cx, lat - cy
        # hexágono con punta al norte y al sur (CylinderGeometry de seis lados en three.js)
        if abs(dx) <= r * s3 and abs(dy) <= r - abs(dx) / math.sqrt(3):
            q = lambda v: max(0, min(65535, round((v + r) / (2 * r) * 65535)))  # noqa: E731
            pts.append((q(dx), q(dy)))
    pts.sort()
    cuerpo = b"".join(struct.pack("<HH", x, y) for x, y in pts)
    salida = DATOS / "ciudad-sm.bin"
    salida.write_bytes(struct.pack("<ffff", cx, cy, r, len(pts)) + cuerpo)
    print(
        f"escrito {salida}: {len(pts)} terrenos en la celda ({cx}, {cy}), {16 + len(cuerpo)} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
