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
    codigo: str  # "verde", "verdad_distinta", "esquema_cambiado", "lento", "vencido" o el de rt/1
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

    def historial(self, dias: int = 7) -> list[tuple[str, str, str, str]]:
        """(herramienta, fuente_id, día, código) de los últimos `dias`, con hoy (UTC); si un día
        hubo varias corridas, la última."""
        desde = (date.fromisoformat(ahora()[:10]) - timedelta(days=dias - 1)).isoformat()
        filas, _ = self._bd.ejecutar(
            "SELECT herramienta, fuente_id, momento, codigo FROM canarios WHERE momento >= ? "
            "ORDER BY momento",
            (desde,),
        )
        por_dia = {(f[0], f[2][:10]): (f[1], f[3]) for f in filas}
        return [(h, f, dia, c) for (h, dia), (f, c) in sorted(por_dia.items())]

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
            elif any(p.servido_desde == "obsoleto" for p in sobre.procedencia):
                # la verdad coincide, pero la copia pasó su plazo de frescura (ADR-0008): no es
                # verde, aunque la respuesta al cliente sí lo diga con su aviso
                codigo, detalle = "vencido", "la copia pasó su plazo de frescura"
            elif ms > h.canario.latencia_max_ms:
                codigo, detalle = "lento", f"{ms} ms > {h.canario.latencia_max_ms} ms"
            else:
                codigo, detalle = "verde", sobre.estado
        except (ErrorEjecucion, ErrorEntrada) as exc:
            ms = int((reloj() - t) * 1000)
            codigo = exc.codigo if isinstance(exc, ErrorEjecucion) else "parametro_invalido"
            detalle = str(exc)
        except Exception as exc:  # un error inesperado en UNA herramienta no aborta el resto
            ms = int((reloj() - t) * 1000)
            codigo, detalle = "error_interno", f"{type(exc).__name__}: {exc}"
            logger.exception("canario %s reventó inesperadamente", h.id)
        resultados.append(
            Resultado(h.id, h.fuente, ahora(), codigo == "verde", codigo, detalle[:500], ms)
        )
    return resultados


# Fallas que no son caídas: la fuente responde bien pero lenta, o la copia está vencida.
DEGRADADOS = frozenset({"lento", "vencido"})


def _estado(rs: list[Resultado]) -> str:
    """`verde` si todas pasan; `degradada` si lo único que falla es lentitud o una copia vencida;
    `rojo` si hay una falla de verdad."""
    if not rs:
        return "sin_datos"
    if all(r.ok for r in rs):
        return "verde"
    return "degradada" if all(r.ok or r.codigo in DEGRADADOS for r in rs) else "rojo"


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
                "estado": _estado(rs),
                "herramientas": [
                    {k: v for k, v in asdict(r).items() if k != "fuente_id"} for r in rs
                ],
            }
        )
    return salida


def historial_por_herramienta(
    filas: list[tuple[str, str, str, str]], catalogo: Catalogo, dias: int
) -> dict[str, Any]:
    """`GET /v1/estado/historial`: las herramientas que fallaron en la ventana, día por día, para
    distinguir un rojo de una noche de uno que se repite. Las verdes solo se cuentan."""
    por_herramienta: dict[str, list[tuple[str, str, str]]] = {}
    for h, f, dia, codigo in filas:
        if f in catalogo.fuentes and h in catalogo.herramientas:
            por_herramienta.setdefault(h, []).append((f, dia, codigo))
    con_fallas = [
        {
            "herramienta": h,
            "fuente_id": rs[-1][0],
            "dias_con_falla": sum(c != "verde" for _, _, c in rs),
            "dias_medidos": len(rs),
            "dias": [{"dia": d, "codigo": c} for _, d, c in rs],
        }
        for h, rs in sorted(por_herramienta.items())
        if any(c != "verde" for _, _, c in rs)
    ]
    return {
        "dias": dias,
        "herramientas_medidas": len(por_herramienta),
        "herramientas_siempre_verdes": len(por_herramienta) - len(con_fallas),
        "con_fallas": con_fallas,
    }


def alertar(resultados: list[Resultado], url: str | None) -> bool:
    """POST JSON con los rojos. Sin URL o sin rojos, nada. Un fallo al avisar no se propaga."""
    rojos = [asdict(r) for r in resultados if not r.ok]
    if not url or not rojos:
        return False
    cuerpo = json.dumps({"servicio": "terranova", "canarios_rojos": rojos}).encode()
    try:
        # construir el Request DENTRO del try: una URL mal formada lanza ValueError (no OSError)
        # y no debe estallar el job justo cuando hay rojos que avisar
        peticion = urllib.request.Request(
            url, data=cuerpo, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(peticion, timeout=10):
            return True
    except Exception:  # avisar es best-effort; nunca tumba el canario
        logger.exception("no se pudo mandar la alerta de canarios")
        return False
