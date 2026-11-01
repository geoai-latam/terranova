"""Métricas del embudo para el informe de cada viernes (spec 11, F8.5), leídas de la base.

Todo sale de tablas que ya existen: `altas` (llave de prueba con correo verificado, ADR-0034),
`llaves`, `eventos` (medición de cada llamada) y `contactos`. Nada se cuenta a mano.

- **Altas por semana:** pedidas (formulario enviado) y confirmadas (llave creada).
- **Tiempo hasta la primera llamada:** mediana, en horas, de las llaves nuevas que ya llamaron.
- **Activación:** de las llaves creadas hace al menos 7 días, cuántas hicieron 10 o más llamadas
  exitosas (sin error) en sus primeros 7 días.
- **Activas:** llaves con al menos una llamada en los últimos 7 y 28 días.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from terranova.bd import Conexion

# lo que no es un error del contrato rt/1: la llamada respondió (con o sin dato)
EXITOSOS = ("encontrado", "no_encontrado", "parcial", "fuera_de_cobertura")
LLAMADAS_PARA_ACTIVAR = 10


@dataclass
class Embudo:
    semanas: list[tuple[str, int, int, int]] = field(
        default_factory=list
    )  # (semana, pedidas, confirmadas, contactos)
    llaves_nuevas: int = 0
    horas_hasta_primera_llamada: float | None = None
    activadas: int = 0
    activables: int = 0
    activas_7: int = 0
    activas_28: int = 0


def _momento(texto: str) -> datetime:
    m = datetime.fromisoformat(texto)
    return m if m.tzinfo else m.replace(tzinfo=UTC)


def _semana(m: datetime) -> str:
    a, s, _ = m.isocalendar()
    return f"{a}-S{s:02d}"


def _tabla(bd: Conexion, sql: str, parametros: tuple[object, ...] = ()) -> list[tuple[object, ...]]:
    """Lee una tabla que puede no existir todavía (una base sin altas ni contactos)."""
    try:
        filas, _ = bd.ejecutar(sql, parametros)
    except Exception:  # noqa: BLE001 — tabla ausente: no hay nada que contar
        return []
    return filas


def medir(bd: Conexion, *, semanas: int = 8, ahora: datetime | None = None) -> Embudo:
    ahora = ahora or datetime.now(UTC)
    desde = ahora - timedelta(weeks=semanas)
    e = Embudo()

    por_semana: dict[str, list[int]] = {}
    for m in (ahora - timedelta(weeks=i) for i in range(semanas - 1, -1, -1)):
        por_semana[_semana(m)] = [0, 0, 0]
    for creada, confirmada in _tabla(bd, "SELECT creada, confirmada FROM altas"):
        c = _momento(str(creada))
        if c >= desde and _semana(c) in por_semana:
            por_semana[_semana(c)][0] += 1
        if confirmada:
            k = _momento(str(confirmada))
            if k >= desde and _semana(k) in por_semana:
                por_semana[_semana(k)][1] += 1
    for (creado,) in _tabla(bd, "SELECT creado FROM contactos"):
        c = _momento(str(creado))
        if c >= desde and _semana(c) in por_semana:
            por_semana[_semana(c)][2] += 1
    e.semanas = [(s, *v) for s, v in por_semana.items()]  # type: ignore[misc]

    llaves = [
        (str(i), _momento(str(c)))
        for i, c in _tabla(bd, "SELECT llave_id, creada FROM llaves WHERE revocada IS NULL")
    ]
    nuevas = [(i, c) for i, c in llaves if c >= desde]
    e.llaves_nuevas = len(nuevas)

    llamadas: dict[str, list[tuple[datetime, bool]]] = {}
    for llave_id, momento, resultado in _tabla(
        bd,
        "SELECT llave_id, momento, resultado FROM eventos WHERE momento >= ?",
        ((desde - timedelta(days=28)).isoformat(),),
    ):
        llamadas.setdefault(str(llave_id), []).append(
            (_momento(str(momento)), str(resultado) in EXITOSOS)
        )

    esperas = []
    for i, c in nuevas:
        propias = sorted(m for m, _ in llamadas.get(i, []))
        if propias:
            esperas.append((propias[0] - c).total_seconds() / 3600)
    e.horas_hasta_primera_llamada = round(statistics.median(esperas), 1) if esperas else None

    for i, c in nuevas:
        if ahora - c < timedelta(days=7):
            continue  # aún no se puede saber si se activa
        e.activables += 1
        exitosas = sum(1 for m, ok in llamadas.get(i, []) if ok and m - c <= timedelta(days=7))
        e.activadas += exitosas >= LLAMADAS_PARA_ACTIVAR

    for i, _ in llaves:
        propias = [m for m, _ in llamadas.get(i, [])]
        e.activas_7 += any(ahora - m <= timedelta(days=7) for m in propias)
        e.activas_28 += any(ahora - m <= timedelta(days=28) for m in propias)
    return e


def informe(e: Embudo) -> str:
    lineas = ["semana      pedidas  confirmadas  contactos"]
    lineas += [f"{s:10}  {p:>7}  {c:>11}  {m:>9}" for s, p, c, m in e.semanas]
    espera = (
        "sin datos"
        if e.horas_hasta_primera_llamada is None
        else f"{e.horas_hasta_primera_llamada} h"
    )
    tasa = f"{100 * e.activadas / e.activables:.0f} %" if e.activables else "sin datos"
    lineas += [
        "",
        f"llaves nuevas en el periodo: {e.llaves_nuevas}",
        f"mediana hasta la primera llamada: {espera}",
        f"activación (≥ {LLAMADAS_PARA_ACTIVAR} llamadas exitosas en 7 días): "
        f"{e.activadas} de {e.activables} ({tasa})",
        f"llaves activas: {e.activas_7} en 7 días, {e.activas_28} en 28 días",
    ]
    return "\n".join(lineas)
