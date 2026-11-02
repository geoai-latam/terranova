"""La ficha de un lote: qué restricciones tocan un polígono.

Es la pregunta de negocio de la ADR-0035. Junta las herramientas `…_en_poligono`, todas sobre copias
en PostGIS, así que no carga servidores del Estado ni depende de que respondan. Lo que no tiene
copia no se cruza, y la ficha lo dice en cada respuesta.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from terranova.catalogo import motivo_no_vendible, vendible
from terranova.contrato import (
    ESQUEMA_POLIGONO,
    Estado,
    GeoResult,
    Sobre,
    ZonaUsada,
    ahora,
    huella,
    nueva_solicitud_id,
)
from terranova.ejecutor import Ejecutor, Plan, validar_entrada
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.ficha import Parte, _Acumulado, _sumar

HERRAMIENTA = "ficha_lote"
VERSION = 1
FAMILIA = "territorio"
TOPE_S = 12.0
TOPE_CREDITOS = 50
PREGUNTA = "¿Qué restricciones tocan este lote?"
DESCRIPCION = (
    "Ficha de un lote o una finca de Colombia: las capas que toca un polígono (GeoJSON Polygon en "
    "EPSG:4326, hasta 500 vértices y 1 grado de lado). Áreas protegidas (RUNAP), microzonas de "
    "restitución de tierras (URT), capacidad de uso del suelo (IGAC) y, en Bogotá, área de "
    "actividad y tratamiento urbanístico del POT. Cada parte lleva su procedencia y su licencia; "
    "si una falla, la ficha sale «parcial» con el error de esa parte. Toca es que comparten aunque "
    "sea un borde. No cruza resguardos, reservas campesinas, vocación ni conflictos de uso, "
    "pérdida de bosque ni amenaza por movimiento en masa: para esos, ficha_lugar o la herramienta "
    "de la capa en un punto del lote."
)
AVISO_FUERA = (
    "Esta ficha no cruza resguardos, reservas campesinas, vocación ni conflictos de uso, pérdida "
    "de bosque ni amenaza por movimiento en masa. Consúltelos en un punto del lote."
)


def _sin_entrada(*_: Any) -> dict[str, Any] | None:
    return None  # todas las partes reciben el mismo polígono


PARTES = tuple(
    Parte(nombre, herramienta, _sin_entrada)
    for nombre, herramienta in (
        ("areas_protegidas", "pnn_areas_protegidas_en_poligono"),
        ("microzonas_restitucion", "urt_microzona_en_poligono"),
        ("capacidad_uso", "igac_capacidad_uso_en_poligono"),
        ("area_actividad", "sdp_area_actividad_en_poligono"),
        ("tratamiento_urbanistico", "sdp_tratamiento_urbanistico_en_poligono"),
    )
)
HERRAMIENTAS = frozenset(p.herramienta for p in PARTES)
ESQUEMA_ENTRADA: dict[str, Any] = {
    "type": "object",
    "properties": {"poligono": ESQUEMA_POLIGONO},
    "required": ["poligono"],
    "additionalProperties": False,
}


async def ficha(
    ej: Ejecutor,
    entrada: dict[str, Any],
    *,
    plan: Plan = "normal",
    puede: Callable[[str], bool] = lambda _familia: True,
    tope_s: float = TOPE_S,
    **_: Any,
) -> Sobre:
    """`entrada`: `{poligono}`, validado una vez para todas las partes."""
    if set(entrada) != {"poligono"}:
        raise ErrorEntrada("entrada", "envíe {poligono}")
    valores = validar_entrada(ej.catalogo.herramientas[PARTES[0].herramienta], entrada)
    consultado_en = ahora()
    acc = _Acumulado({}, [], [], [], [AVISO_FUERA])

    async def una(parte: Parte) -> tuple[Parte, Sobre | ErrorEjecucion]:
        try:
            tarea = ej.ejecutar(parte.herramienta, valores, plan=plan)
            return parte, await asyncio.wait_for(tarea, tope_s)
        except TimeoutError:
            return parte, ErrorEjecucion("fuente_lenta", f"no llegó en el tope de {tope_s:.0f} s")
        except ErrorEjecucion as exc:
            return parte, exc

    tareas = []
    for parte in PARTES:
        h = ej.catalogo.herramientas[parte.herramienta]
        fuente = ej.catalogo.fuentes[h.fuente]
        if not puede(h.familia):
            acc.avisos.append(f"«{parte.nombre}» no se consultó: falta el scope «{h.familia}».")
        elif plan != "evaluacion" and not vendible(fuente):
            acc.avisos.append(f"«{parte.nombre}» no se consultó: {motivo_no_vendible(fuente)}.")
        else:
            tareas.append(una(parte))
    for parte, r in await asyncio.gather(*tareas):
        _sumar(ej, acc, parte, r, consultado_en)

    if not acc.datos:
        raise ErrorEjecucion("fuente_no_disponible", "ninguna parte de la ficha respondió")
    hallado = any(parte.get("estado") == "encontrado" for parte in acc.datos.values())
    estado: Estado = "parcial" if acc.errores else "encontrado" if hallado else "no_encontrado"
    return Sobre(
        solicitud_id=nueva_solicitud_id(),
        herramienta=f"{HERRAMIENTA}@{VERSION}",
        estado=estado,
        entrada=dict(entrada),
        zona_usada=ZonaUsada(tipo="poligono", valor=valores["poligono"], crs="EPSG:4326"),
        datos=acc.datos,
        huella=huella(acc.datos),
        geo_result=GeoResult(artifacts=acc.artefactos) if acc.artefactos else None,
        procedencia=acc.procedencia,
        avisos=acc.avisos,
        errores=acc.errores,
        creditos=min(acc.creditos, TOPE_CREDITOS),
    )
