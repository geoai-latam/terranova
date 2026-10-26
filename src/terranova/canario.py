"""Comparación de un sobre con la verdad medida del catálogo (canario y prueba dorada)."""

from __future__ import annotations

import math
from typing import Any

from terranova.catalogo import Herramienta
from terranova.contrato import Sobre


def _buscar(datos: dict[str, Any], clave: str) -> Any:
    """El valor en `datos` o, si la herramienta da una lista, en su primer elemento."""
    if clave in datos:
        return datos[clave]
    elementos = datos.get("elementos")
    if isinstance(elementos, list) and elementos and isinstance(elementos[0], dict):
        return elementos[0].get(clave)
    return None


def _igual(esperado: Any, obtenido: Any) -> bool:
    if isinstance(esperado, float) or isinstance(obtenido, float):
        try:
            return math.isclose(float(esperado), float(obtenido), rel_tol=1e-6, abs_tol=0.005)
        except (TypeError, ValueError):
            return False
    return bool(esperado == obtenido) or str(esperado) == str(obtenido)


PREFIJO_ESQUEMA = "ya no llega el campo"


def campos_presentes(sobre: Sobre) -> set[str]:
    """Los campos que trajo el sobre: los de `datos` y los de cualquiera de sus elementos."""
    presentes = {k for k in sobre.datos if k != "elementos"}
    for e in sobre.datos.get("elementos") or []:
        if isinstance(e, dict):
            presentes |= set(e)
    return presentes


def comprobar(h: Herramienta, sobre: Sobre) -> list[str]:
    """Las diferencias con la verdad del canario; vacío si coincide."""
    problemas = []
    if sobre.estado not in ("encontrado", "parcial"):
        problemas.append(f"estado {sobre.estado}, se esperaba encontrado")
    for clave, esperado in h.canario.verdad.items():
        obtenido = _buscar(sobre.datos, clave)
        if not _igual(esperado, obtenido):
            problemas.append(f"{clave}: se esperaba {esperado!r}, vino {obtenido!r}")
    for clave, minimo in h.canario.minimos.items():
        # `elementos` es un piso de CONTEO de la lista (no un escalar de elementos[0]): una
        # fuente de lista que devuelve menos resultados de los medidos sale roja (antes solo
        # se miraba el 1º)
        if clave == "elementos":
            obtenido = len(sobre.datos.get("elementos") or [])
        else:
            obtenido = _buscar(sobre.datos, clave)
        if not isinstance(obtenido, int | float) or obtenido < minimo:
            problemas.append(f"{clave}: se esperaba ≥ {minimo}, vino {obtenido!r}")
    # F7.3: un campo renombrado en la fuente sale de la lista blanca sin error; aquí se nota
    presentes = campos_presentes(sobre)
    for campo in h.canario.campos:
        if campo not in presentes:
            problemas.append(f"{PREFIJO_ESQUEMA} «{campo}»: ¿la fuente cambió su esquema?")
    return problemas
