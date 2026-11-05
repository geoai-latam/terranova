"""Alertas integradas de deforestación de Global Forest Watch (GFW Data API), lo medido el 2026-11-05.

- Dataset `gfw_integrated_alerts` (GLAD-L, GLAD-S2 y RADD juntas; píxel de 10 m; trópicos 30° N a 30° S),
  CC BY 4.0. Hay una versión nueva cada día (`v20261105`); `latest` responde 307 a la del día.
- La consulta es SQL sobre el ráster dentro de una geometría (POST `query/json`): una petición da los
  conteos por fecha y confianza de todo el periodo. El rectángulo de Colombia y sus vecinos, un año
  entero, tardó 19,5 s; un rectángulo de 0,5° y un mes, 3 s.
- Cada fila del ráster es un PÍXEL de alerta (~0,012 ha), no un evento: un claro de 1 ha son ~80.
- Confianza: nominal, high, highest (2, 3, 4 en el ráster). Las alertas recientes son sobre todo
  nominales y pueden subir de confianza o desaparecer; las de 2024 no cambiaron entre las versiones
  v20260701 y v20261105 (medido).
- Hay alertas desde el 2019-01-01 (antes, la consulta da vacío).
- La llave va en la cabecera `x-api-key` (variable GFW_API_KEY), nunca en la URL ni en un mensaje.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import date
from typing import Any

import httpx
from geo_mcp_kit import red

GFW = "https://data-api.globalforestwatch.org"
DATASET = "gfw_integrated_alerts"
UA = "terrnova-amenazas-mcp/1"
PRIMERA_FECHA = date(2019, 1, 1)
MAX_DIAS = 366
MAX_LADO_GRADOS = 20.0  # el rectángulo de Colombia mide 12,3° × 17,8°
_version: dict[str, Any] = {"en": 0.0, "valor": ""}
# la API de GFW no publica su cupo: de este conector sale una petición a la vez
_una_a_la_vez = threading.Lock()


class ErrorGfw(Exception):
    """Un fallo de GFW, sin la llave en el texto."""


def _pedir(metodo: str, ruta: str, cuerpo: dict | None = None, timeout: float = 150) -> httpx.Response:
    llave = os.environ.get("GFW_API_KEY", "")
    if not llave:
        raise ErrorGfw("falta GFW_API_KEY: la API de datos de Global Forest Watch pide una llave (gratis)")
    url = f"{GFW}{ruta}"
    try:
        with _una_a_la_vez, red.cliente(url, timeout=timeout, user_agent=UA) as c:
            return c.request(metodo, url, json=cuerpo, headers={"x-api-key": llave})
    except red.UrlNoPermitida:
        raise
    except Exception as exc:  # el mensaje no lleva la llave (va en la cabecera), pero no se arriesga
        raise ErrorGfw(f"Global Forest Watch no respondió: {type(exc).__name__}") from None


def version() -> str:
    """La versión del día (`latest` responde 307 a ella); se pregunta una vez por hora."""
    if time.monotonic() - _version["en"] > 3600 or not _version["valor"]:
        r = _pedir("GET", f"/dataset/{DATASET}/latest", timeout=30)
        destino = r.headers.get("location", "") if r.status_code in (301, 302, 307, 308) else ""
        v = destino.rstrip("/").rsplit("/", 1)[-1]
        if not v.startswith("v"):
            raise ErrorGfw(f"Global Forest Watch no dijo cuál es su versión vigente (HTTP {r.status_code})")
        _version.update(en=time.monotonic(), valor=v)
    return _version["valor"]


def _rectangulo(bbox: list[float]) -> dict:
    x0, y0, x1, y1 = bbox
    return {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}


def alertas(geometria: dict | None, bbox: list[float], desde: str, hasta: str) -> tuple[list[dict], str]:
    """(filas por fecha y confianza con píxeles y hectáreas, versión consultada). `hasta` es exclusivo."""
    try:
        inicio, fin = date.fromisoformat(desde), date.fromisoformat(hasta)
    except ValueError:
        raise ErrorGfw("`desde` y `hasta` van como AAAA-MM-DD") from None
    if inicio < PRIMERA_FECHA:
        raise ErrorGfw(f"las alertas integradas empiezan el {PRIMERA_FECHA.isoformat()}")
    if not 1 <= (fin - inicio).days <= MAX_DIAS:
        raise ErrorGfw(f"el periodo va de 1 a {MAX_DIAS} días (`hasta` es exclusivo)")
    if max(bbox[2] - bbox[0], bbox[3] - bbox[1]) > MAX_LADO_GRADOS:
        raise ErrorGfw(f"la zona pasa de {MAX_LADO_GRADOS:g}° de lado: divídala en partes")
    v = version()
    sql = ("SELECT gfw_integrated_alerts__date, gfw_integrated_alerts__confidence, COUNT(*), SUM(area__ha) "
           f"FROM results WHERE gfw_integrated_alerts__date >= '{inicio.isoformat()}' "
           f"AND gfw_integrated_alerts__date < '{fin.isoformat()}' "
           "GROUP BY gfw_integrated_alerts__date, gfw_integrated_alerts__confidence")
    r = _pedir("POST", f"/dataset/{DATASET}/{v}/query/json",
               {"sql": sql, "geometry": geometria or _rectangulo(bbox)})
    if r.status_code != 200:
        try:
            motivo = str(r.json().get("message") or "")[:200]
        except ValueError:
            motivo = ""
        raise ErrorGfw(f"Global Forest Watch respondió HTTP {r.status_code}" + (f": {motivo}" if motivo else ""))
    cuerpo = r.json()
    if cuerpo.get("status") != "success" or not isinstance(cuerpo.get("data"), list):
        raise ErrorGfw("Global Forest Watch no devolvió los conteos")
    filas = [{"fecha": f.get("gfw_integrated_alerts__date"), "confianza": f.get("gfw_integrated_alerts__confidence"),
              "alertas": int(f.get("count") or 0), "area_ha": round(float(f.get("area__ha") or 0), 4)}
             for f in cuerpo["data"]]
    filas.sort(key=lambda f: (str(f["fecha"]), str(f["confianza"])))
    return filas, v
