"""El predio de un punto, sin elegir la base: SINIC primero y, si no lo tiene, el IGAC.

Con dos herramientas, el agente tenía que saber qué gestor catastral atiende cada municipio y las
confundía, aunque sus descripciones se remiten entre sí. Esta elige sola, con la misma regla de
`ficha_lugar`. Devuelve el sobre de la base que respondió, con su procedencia y su licencia.
"""

from __future__ import annotations

from typing import Any

from terranova.contrato import GEOMETRIA, Sobre, ahora
from terranova.ejecutor import Ejecutor, Plan
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.ficha import PREDIO_EN_PUNTO, PREDIO_SINIC, _procedencia_fallida

HERRAMIENTA = "predio_en_punto"
VERSION = 1
FAMILIA = "territorio"
TOPE_CREDITOS = 10
PREGUNTA = "¿Qué predio hay en este punto de Colombia?"
DESCRIPCION = (
    "Predio que contiene un punto (lon, lat en EPSG:4326), en cualquier municipio de Colombia: no "
    "hace falta saber qué gestor catastral lo atiende. Mira primero el SINIC del IGAC (los 333 "
    "municipios con gestor propio, como Bogotá, Medellín y Cali) y, si no lo tiene, la base "
    "catastral pública del IGAC. Devuelve la respuesta de la base que lo tiene; la procedencia "
    "dice cuál fue. Use esta herramienta para el predio de un punto. Para todo lo demás de un "
    "lugar (restricciones, suelo, sismos), ficha_lugar."
)
ESQUEMA_ENTRADA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "lon": {"type": "number", "minimum": -180, "maximum": 180, "description": "longitud"},
        "lat": {"type": "number", "minimum": -90, "maximum": 90, "description": "latitud"},
        GEOMETRIA: {
            "type": "boolean",
            "description": "true para la forma completa del predio; por defecto, su envolvente",
        },
    },
    "required": ["lon", "lat"],
    "additionalProperties": False,
}


async def ficha(ej: Ejecutor, entrada: dict[str, Any], *, plan: Plan = "normal", **_: Any) -> Sobre:
    """`entrada`: `{lon, lat}`; la puerta atiende `geometria` antes de llegar aquí (ADR-0032)."""
    if set(entrada) != {"lon", "lat"}:
        raise ErrorEntrada("entrada", "envíe {lon, lat}")
    consultado_en = ahora()
    sinic: Sobre | None = None
    falla: ErrorEjecucion | None = None
    try:
        sinic = await ej.ejecutar(PREDIO_SINIC.herramienta, entrada, plan=plan)
    except ErrorEjecucion as exc:
        falla = exc
    if sinic is not None and sinic.estado == "encontrado":
        return sinic.model_copy(update={"herramienta": f"{HERRAMIENTA}@{VERSION}"})

    igac = await ej.ejecutar(PREDIO_EN_PUNTO.herramienta, entrada, plan=plan)
    # «no hay» solo vale si se pudo mirar en las dos: con el SINIC caído es «no se pudo»
    if falla is not None and igac.estado != "encontrado":
        raise falla
    consultada = (
        sinic.procedencia
        if sinic is not None
        else [_procedencia_fallida(ej, PREDIO_SINIC, consultado_en)]
    )
    return igac.model_copy(
        update={
            "herramienta": f"{HERRAMIENTA}@{VERSION}",
            "procedencia": [*igac.procedencia, *consultada],
        }
    )
