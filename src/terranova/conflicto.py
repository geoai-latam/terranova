"""El conflicto armado en un municipio: las once modalidades del CNMH en una sola respuesta.

Quien pregunta «¿qué tan golpeado fue este municipio por el conflicto?» necesitaba once llamadas, y
con una sola caía en la trampa de la tipología: la masacre de Bojayá de 2002 no está en
«masacres» sino en «acciones bélicas». Esta ficha corre las once herramientas `cnmh_*_municipio`
en paralelo y da, por modalidad, víctimas, casos, años y pico, más el total y los años con más
víctimas. Solo conteos (ADR-0014). Si una modalidad falla, la ficha sale `parcial` y lo dice: su
cifra no entra en el total, que entonces es un mínimo.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections import Counter
from collections.abc import Callable
from typing import Any

from terranova.catalogo import PATRONES_ENTRADA, motivo_no_vendible, vendible
from terranova.contrato import Sobre, ZonaUsada, ahora, huella, nueva_solicitud_id
from terranova.ejecutor import Ejecutor, Plan
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.ficha import Parte, _Acumulado, _seguir_en_segundo_plano, _sumar

HERRAMIENTA = "cnmh_conflicto_municipio"
VERSION = 1
FAMILIA = "justicia"
TOPE_S = 20.0
TOPE_CREDITOS = 20
PREGUNTA = "¿Qué tan golpeado fue este municipio por el conflicto armado?"
DESCRIPCION = (
    "Las víctimas del conflicto armado en un municipio (DIVIPOLA o nombre) en las once modalidades "
    "del Observatorio de Memoria y Conflicto del CNMH, en una sola respuesta: masacres, asesinatos "
    "selectivos, desaparición forzada, secuestro, acciones bélicas, ataques a poblados, atentados, "
    "daño a bienes, minas, reclutamiento y violencia sexual. Por modalidad: víctimas, casos, "
    "víctimas sin año, primer y último año y el año pico; además el total y los años con más "
    "víctimas. Las modalidades son excluyentes (Bojayá 2002 está en acciones bélicas, no en "
    "masacres), así que el total suma hechos sin contar dos veces el mismo; una persona víctima de "
    "dos hechos cuenta dos veces. Solo conteos, nunca el registro de una persona. Tope de 20 s. "
    "Para la serie por año de una modalidad, use su herramienta cnmh_*_municipio."
)
ESQUEMA_ENTRADA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "municipio_divipola": {
            "type": "string",
            "pattern": PATRONES_ENTRADA["divipola"],
            "description": "Código DIVIPOLA de 5 dígitos (05313) o nombre del municipio",
        }
    },
    "required": ["municipio_divipola"],
    "additionalProperties": False,
}


def _entrada(municipio: str) -> dict[str, Any]:
    return {"municipio_divipola": municipio}


MODALIDADES = (
    "masacres",
    "asesinatos_selectivos",
    "desaparicion_forzada",
    "secuestro",
    "acciones_belicas",
    "ataques_poblados",
    "atentados",
    "dano_bienes",
    "minas",
    "reclutamiento",
    "violencia_sexual",
)
NOMBRES = {
    "masacres": "masacres",
    "asesinatos_selectivos": "asesinatos selectivos",
    "desaparicion_forzada": "desaparición forzada",
    "secuestro": "secuestro",
    "acciones_belicas": "acciones bélicas",
    "ataques_poblados": "ataques a poblados",
    "atentados": "atentados",
    "dano_bienes": "daño a bienes civiles",
    "minas": "minas",
    "reclutamiento": "reclutamiento",
    "violencia_sexual": "violencia sexual",
}
PARTES = tuple(Parte(m, f"cnmh_{m}_municipio", _entrada) for m in MODALIDADES)
HERRAMIENTAS = frozenset(p.herramienta for p in PARTES)

# El aviso que trae cada parte: aquí va una sola vez, en el de la ficha.
EXCLUYENTES = "Las modalidades del CNMH son excluyentes"
FIN_EXCLUYENTES = "cnmh_conflicto_municipio."
NO_REGISTRA = "El CNMH no registra víctimas"
AVISO_SUMA = (
    "El total suma las once modalidades del CNMH, que son excluyentes: cada hecho cuenta en una "
    "sola (las víctimas de Bojayá del 2 de mayo de 2002 están en acciones bélicas, no en "
    "masacres). Una persona víctima de dos hechos distintos, por ejemplo secuestrada y luego "
    "asesinada, cuenta dos veces. El CNMH revisa casos con cada corte: las cifras son un mínimo."
)
ANIOS_PICO = 5


def _resumen(datos: dict[str, Any]) -> dict[str, Any]:
    """Lo de una modalidad, sin la serie: víctimas, casos, sin año, primer y último año, pico."""
    filas = [f for f in datos.get("elementos", []) if isinstance(f, dict)]
    con_anio = [f for f in filas if f.get("anio")]
    pico = max(con_anio, key=lambda f: (f.get("victimas") or 0, -f["anio"]), default=None)
    return {
        "estado": datos.get("estado"),
        "victimas": sum(f.get("victimas") or 0 for f in filas),
        "casos": sum(f.get("casos") or 0 for f in filas),
        "victimas_sin_anio": sum(f.get("victimas") or 0 for f in filas if not f.get("anio")),
        "primer_anio": min((f["anio"] for f in con_anio), default=None),
        "ultimo_anio": max((f["anio"] for f in con_anio), default=None),
        "anio_pico": pico["anio"] if pico else None,
        "victimas_anio_pico": pico.get("victimas") if pico else None,
    }


def _avisos(avisos: list[str]) -> list[str]:
    """Una sola vez cada aviso repetido en las partes (el del homónimo sale en las once), sin el de
    las modalidades excluyentes, que la ficha da una vez; lo que una parte añade a ese aviso queda
    con su nombre."""
    de_partes: list[tuple[str, str]] = []
    propios: list[str] = []
    for a in avisos:
        parte, _, texto = a.partition(": ")
        if parte not in MODALIDADES:
            propios.append(a)
            continue
        if texto.startswith(EXCLUYENTES):
            texto = texto.partition(FIN_EXCLUYENTES)[2].strip()
        if texto.startswith(NO_REGISTRA):
            continue  # la ficha lo dice una vez, con las modalidades sin víctimas
        if texto:
            de_partes.append((parte, texto))
    veces = Counter(t for _, t in de_partes)
    salida: list[str] = []
    for parte, texto in de_partes:
        a = texto if veces[texto] > 1 else f"{parte}: {texto}"
        if a not in salida:
            salida.append(a)
    return propios + salida


async def ficha(
    ej: Ejecutor,
    entrada: dict[str, Any],
    *,
    plan: Plan = "normal",
    puede: Callable[[str], bool] = lambda _familia: True,
    tope_s: float = TOPE_S,
    **_: Any,
) -> Sobre:
    """`entrada`: `{municipio_divipola}` (código DIVIPOLA o nombre)."""
    if set(entrada) != {"municipio_divipola"}:
        raise ErrorEntrada("municipio_divipola", "envíe solo {municipio_divipola}")
    municipio = entrada["municipio_divipola"]
    if not isinstance(municipio, str) or not re.fullmatch(
        PATRONES_ENTRADA["divipola"], municipio.strip()
    ):
        raise ErrorEntrada(
            "municipio_divipola", "código DIVIPOLA de 5 dígitos o nombre del municipio"
        )
    municipio = municipio.strip()
    consultado_en = ahora()
    limite = time.monotonic() + tope_s
    acc = _Acumulado({}, [], [], [], [])

    async def una(parte: Parte) -> tuple[Parte, Sobre | ErrorEjecucion]:
        try:
            tarea = asyncio.ensure_future(
                ej.ejecutar(parte.herramienta, _entrada(municipio), plan=plan)
            )
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
        elif plan != "evaluacion" and not vendible(fuente):
            acc.avisos.append(f"«{p.nombre}» no se consultó: {motivo_no_vendible(fuente)}.")
        else:
            tareas.append(una(p))
    zona = municipio
    por_anio: Counter[int] = Counter()
    for parte, r in await asyncio.gather(*tareas):
        _sumar(ej, acc, parte, r, consultado_en)
        if isinstance(r, Sobre):
            zona = r.zona_usada.valor if r.zona_usada else zona
            for f in r.datos.get("elementos", []):
                if isinstance(f, dict) and f.get("anio"):
                    por_anio[f["anio"]] += f.get("victimas") or 0

    if not acc.datos:
        raise ErrorEjecucion("fuente_no_disponible", "ninguna modalidad del CNMH respondió")
    por_modalidad = {m: _resumen(d) for m, d in acc.datos.items()}
    por_modalidad = dict(sorted(por_modalidad.items(), key=lambda kv: -kv[1]["victimas"]))
    if all(d.get("estado") == "no_encontrado" for d in acc.datos.values()):
        estado = "no_encontrado"
    else:
        estado = "parcial" if acc.errores else "encontrado"
    datos: dict[str, Any] = {
        "total_victimas": sum(m["victimas"] for m in por_modalidad.values()),
        "total_casos": sum(m["casos"] for m in por_modalidad.values()),
        "modalidades_con_victimas": sum(m["victimas"] > 0 for m in por_modalidad.values()),
        "anios_con_mas_victimas": {
            str(a): v
            for a, v in sorted(por_anio.items(), key=lambda kv: (-kv[1], kv[0]))[:ANIOS_PICO]
        },
        "por_modalidad": por_modalidad,
    }
    avisos = _avisos(acc.avisos)
    sin = [NOMBRES[m] for m, r in por_modalidad.items() if r["estado"] == "no_encontrado"]
    if sin:
        avisos.insert(
            0,
            f"Sin víctimas registradas en {', '.join(sin)}. No quiere decir que no hubo "
            "violencia: el hecho puede estar en otra modalidad.",
        )
    if estado != "no_encontrado":
        avisos.insert(0, AVISO_SUMA)
    if acc.errores:
        avisos.insert(0, "Faltan modalidades que no respondieron: el total es un mínimo.")
    return Sobre(
        solicitud_id=nueva_solicitud_id(),
        herramienta=f"{HERRAMIENTA}@{VERSION}",
        estado=estado,  # type: ignore[arg-type]
        entrada={"municipio_divipola": municipio},
        zona_usada=ZonaUsada(tipo="codigo", valor=zona),
        datos=datos,
        huella=huella(datos),
        geo_result=None,
        procedencia=acc.procedencia,
        avisos=avisos,
        errores=acc.errores,
        creditos=min(acc.creditos, TOPE_CREDITOS),
    )
