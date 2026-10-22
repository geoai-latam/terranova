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
        obtenido = _buscar(sobre.datos, clave)
        if not isinstance(obtenido, int | float) or obtenido < minimo:
            problemas.append(f"{clave}: se esperaba ≥ {minimo}, vino {obtenido!r}")
    return problemas
