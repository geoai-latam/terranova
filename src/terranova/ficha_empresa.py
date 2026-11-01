"""Ficha de una empresa por NIT (auditoría integral C22): herramientas del catálogo en paralelo.

Junta lo que una revisión de proveedor o de cliente mira primero, cada parte con su procedencia y
su licencia: registro mercantil y establecimientos (RUES), estados financieros y resultados
(Supersociedades), vigilancia de la Superfinanciera y contratos públicos como proveedor (SECOP II).
Si una parte falla, la ficha sale `parcial` con el error de esa parte, como `ficha_lugar`.

Solo empresas: el NIT va con el patrón `nit_empresa` (empieza por 8 o 9), así que no se puede
buscar por la cédula de una persona natural (ADR-0014). Solo fuentes con uso comercial: la DIAN de
usuarios aduaneros («sin fines de lucro») no es parte de la ficha.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

from terranova.catalogo import PATRONES_ENTRADA
from terranova.contrato import Sobre, ZonaUsada, ahora, huella, nueva_solicitud_id
from terranova.ejecutor import Ejecutor, Plan
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.ficha import Parte, _Acumulado, _seguir_en_segundo_plano, _sumar

HERRAMIENTA = "ficha_empresa"
VERSION = 1
FAMILIA = "empresas"
TOPE_S = 12.0
TOPE_CREDITOS = 30
PREGUNTA = "¿Qué dicen las fuentes oficiales de la empresa con este NIT?"
DESCRIPCION = (
    "Ficha de una empresa colombiana por NIT (9 dígitos, sin dígito de verificación; solo personas "
    "jurídicas): registro mercantil y establecimientos (RUES), estado de situación financiera y "
    "resultados (Supersociedades), si la vigila la Superfinanciera y sus contratos públicos como "
    "proveedor por año (SECOP II). Partes en paralelo, cada una con su procedencia y licencia; si "
    "una falla, la ficha sale «parcial» con el error de esa parte. Tope de 12 s. Para una sola "
    "fuente o más detalle (flujo de efectivo, carátula, otro resultado integral), use la "
    "herramienta de esa fuente."
)
ESQUEMA_ENTRADA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "nit": {
            "type": "string",
            "pattern": PATRONES_ENTRADA["nit_empresa"],
            "description": "NIT de la empresa, 9 dígitos sin dígito de verificación: 899999068",
        }
    },
    "required": ["nit"],
    "additionalProperties": False,
}


def _nit(nit: str) -> dict[str, Any]:
    return {"nit": nit}


PARTES = (
    Parte("registro_mercantil", "rues_empresa_por_nit", _nit),
    Parte("establecimientos", "rues_establecimientos_por_nit", _nit),
    Parte("situacion_financiera", "supersociedades_situacion_financiera", _nit),
    Parte("resultados", "supersociedades_resultado_integral", _nit),
    Parte("superfinanciera", "superfinanciera_vigilada_por_nit", _nit),
    Parte("contratos_publicos", "secop_contratos_proveedor", _nit),
)
HERRAMIENTAS = frozenset(p.herramienta for p in PARTES)


async def ficha(
    ej: Ejecutor,
    entrada: dict[str, Any],
    *,
    plan: Plan = "normal",
    puede: Callable[[str], bool] = lambda _familia: True,
    tope_s: float = TOPE_S,
    **_: Any,
) -> Sobre:
    """`entrada`: `{nit}` (texto, patrón `nit_empresa`)."""
    if set(entrada) != {"nit"}:
        raise ErrorEntrada("nit", "envíe solo {nit}")
    nit = entrada["nit"]
    if not isinstance(nit, str):
        raise ErrorEntrada("nit", "debe ser texto: el NIT de 9 dígitos entre comillas")
    import re

    if not re.fullmatch(PATRONES_ENTRADA["nit_empresa"], nit):
        raise ErrorEntrada("nit", "NIT de empresa: 9 dígitos que empiezan por 8 o 9")
    consultado_en = ahora()
    limite = time.monotonic() + tope_s
    acc = _Acumulado({}, [], [], [], [])

    async def una(parte: Parte) -> tuple[Parte, Sobre | ErrorEjecucion]:
        try:
            tarea = asyncio.ensure_future(ej.ejecutar(parte.herramienta, _nit(nit), plan=plan))
            _seguir_en_segundo_plano(tarea)  # lo que no llega a tiempo llena la caché
            resta = max(0.1, limite - time.monotonic())
            return parte, await asyncio.wait_for(asyncio.shield(tarea), resta)
        except TimeoutError:
            return parte, ErrorEjecucion("fuente_lenta", f"no llegó en el tope de {tope_s:.0f} s")
        except ErrorEjecucion as exc:
            return parte, exc

    tareas = []
    for p in PARTES:
        h = ej.catalogo.herramientas[p.herramienta]
        fuente = ej.catalogo.fuentes[h.fuente]
        if not puede(h.familia):
            acc.avisos.append(f"«{p.nombre}» no se consultó: la llave no tiene «{h.familia}».")
        elif fuente.uso_comercial == "por_verificar" and plan != "evaluacion":
            acc.avisos.append(f"«{p.nombre}» no se consultó: licencia de la fuente por verificar.")
        else:
            tareas.append(una(p))
    for parte, r in await asyncio.gather(*tareas):
        _sumar(ej, acc, parte, r, consultado_en)

    if not acc.datos:
        raise ErrorEjecucion("fuente_no_disponible", "ninguna parte de la ficha respondió")
    if all(d.get("estado") == "no_encontrado" for d in acc.datos.values()):
        estado = "no_encontrado"
    else:
        estado = "parcial" if acc.errores else "encontrado"
    return Sobre(
        solicitud_id=nueva_solicitud_id(),
        herramienta=f"{HERRAMIENTA}@{VERSION}",
        estado=estado,  # type: ignore[arg-type]
        entrada={"nit": nit},
        zona_usada=ZonaUsada(tipo="codigo", valor=nit),
        datos=acc.datos,
        huella=huella(acc.datos),
        geo_result=None,
        procedencia=acc.procedencia,
        avisos=acc.avisos,
        errores=acc.errores,
        creditos=min(acc.creditos, TOPE_CREDITOS),
    )
