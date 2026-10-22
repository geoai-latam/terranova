"""Canarios diarios (F7.1): cada herramienta del catálogo contra su verdad medida, en vivo.

Uno detrás de otro y sin caché (`frescura=estricta`): son 20 consultas al día, no carga. Plan
`evaluacion`, para que también se vigilen las fuentes con licencia por verificar. Cada resultado se
guarda (SQLite o Postgres, la misma `Conexion` que llaves y medición) y alimenta `GET /v1/estado`.
Si algo sale rojo y hay `TERRANOVA_ALERTA_URL`, se manda un POST JSON con lo que falló; sin esa
variable no sale nada de la máquina.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from terranova.bd import Conexion
from terranova.canario import PREFIJO_ESQUEMA, comprobar
from terranova.catalogo import Catalogo
from terranova.ejecutor import Ejecutor
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.medicion import ahora

logger = logging.getLogger("terranova.vigilancia")


@dataclass(frozen=True)
class Resultado:
    herramienta: str
    fuente_id: str
    momento: str
    ok: bool
    codigo: str  # "verde", "verdad_distinta", "esquema_cambiado", "lento" o el código rt/1
    detalle: str
    latencia_ms: int


class RegistroCanarios:
    def __init__(self, destino: str | Path) -> None:
        self._bd = Conexion(destino)
        self._bd.ejecutar(
            """CREATE TABLE IF NOT EXISTS canarios (
                herramienta TEXT NOT NULL, fuente_id TEXT NOT NULL, momento TEXT NOT NULL,
                ok INTEGER NOT NULL, codigo TEXT NOT NULL, detalle TEXT NOT NULL,
                latencia_ms INTEGER NOT NULL, PRIMARY KEY (herramienta, momento))"""
        )

    def registrar(self, r: Resultado) -> None:
        self._bd.ejecutar(
            "INSERT INTO canarios VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(herramienta, momento) DO NOTHING",
            (r.herramienta, r.fuente_id, r.momento, int(r.ok), r.codigo, r.detalle, r.latencia_ms),
        )

    def ultimos(self) -> list[Resultado]:
        """El último resultado de cada herramienta."""
        filas, _ = self._bd.ejecutar(
            "SELECT c.herramienta, c.fuente_id, c.momento, c.ok, c.codigo, c.detalle, "
            "c.latencia_ms FROM canarios c JOIN (SELECT herramienta, MAX(momento) AS m "
            "FROM canarios GROUP BY herramienta) u ON c.herramienta = u.herramienta "
            "AND c.momento = u.m ORDER BY c.herramienta"
        )
        return [Resultado(f[0], f[1], f[2], bool(f[3]), f[4], f[5], f[6]) for f in filas]

    def dias_seguidos(self, herramienta: str) -> int:
        """Días (UTC) consecutivos hasta hoy con al menos un resultado registrado."""
        filas, _ = self._bd.ejecutar(
            "SELECT DISTINCT substr(momento, 1, 10) FROM canarios WHERE herramienta = ? "
            "ORDER BY 1 DESC",
            (herramienta,),
        )
        dia, seguidos = date.fromisoformat(ahora()[:10]), 0
        for (d,) in filas:
            if date.fromisoformat(d) != dia - timedelta(days=seguidos):
                break
            seguidos += 1
        return seguidos


async def correr(
    catalogo: Catalogo,
    ejecutor: Ejecutor,
    *,
    reloj: Callable[[], float] = time.monotonic,
) -> list[Resultado]:
    resultados = []
    for h in catalogo.herramientas.values():
        t = reloj()
        try:
            sobre = await ejecutor.ejecutar(
                h.id, h.canario.entrada, plan="evaluacion", frescura="estricta"
            )
            diferencias = comprobar(h, sobre)
            ms = int((reloj() - t) * 1000)
            if diferencias:
                esquema = all(d.startswith(PREFIJO_ESQUEMA) for d in diferencias)
                codigo = "esquema_cambiado" if esquema else "verdad_distinta"
                detalle = "; ".join(diferencias)
            elif ms > h.canario.latencia_max_ms:
                codigo, detalle = "lento", f"{ms} ms > {h.canario.latencia_max_ms} ms"
            else:
                codigo, detalle = "verde", sobre.estado
        except (ErrorEjecucion, ErrorEntrada) as exc:
            ms = int((reloj() - t) * 1000)
            codigo = exc.codigo if isinstance(exc, ErrorEjecucion) else "parametro_invalido"
            detalle = str(exc)
        resultados.append(
            Resultado(h.id, h.fuente, ahora(), codigo == "verde", codigo, detalle[:500], ms)
        )
    return resultados


def estado_por_fuente(ultimos: list[Resultado], catalogo: Catalogo) -> list[dict[str, Any]]:
    """`GET /v1/estado`: por fuente, verde si todas sus herramientas lo están."""
    por_fuente: dict[str, list[Resultado]] = {}
    for r in ultimos:
        por_fuente.setdefault(r.fuente_id, []).append(r)
    salida = []
    for f in sorted(catalogo.fuentes):
        rs = por_fuente.get(f, [])
        salida.append(
            {
                "fuente_id": f,
                "estado": "sin_datos" if not rs else "verde" if all(r.ok for r in rs) else "rojo",
                "herramientas": [
                    {k: v for k, v in asdict(r).items() if k != "fuente_id"} for r in rs
                ],
            }
        )
    return salida


def alertar(resultados: list[Resultado], url: str | None) -> bool:
    """POST JSON con los rojos. Sin URL o sin rojos, nada. Un fallo al avisar no se propaga."""
    rojos = [asdict(r) for r in resultados if not r.ok]
    if not url or not rojos:
        return False
    cuerpo = json.dumps({"servicio": "terranova", "canarios_rojos": rojos}).encode()
    peticion = urllib.request.Request(
        url, data=cuerpo, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(peticion, timeout=10):
            return True
    except OSError:
        logger.exception("no se pudo mandar la alerta de canarios")
        return False
