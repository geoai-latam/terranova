"""Las herramientas compuestas: fichas que juntan herramientas del catálogo en un solo sobre.

No son herramientas del catálogo (no tienen fuente propia): cada parte lleva su procedencia. La
puerta las sirve igual que a las demás (MCP, REST, perfil `catalogo`, créditos y scopes), con su
familia y un tope de créditos.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from terranova import ficha as ficha_lugar
from terranova import ficha_empresa
from terranova.contrato import Sobre


@dataclass(frozen=True)
class Compuesta:
    herramienta: str
    version: int
    familia: str
    pregunta: str
    descripcion: str
    esquema_entrada: dict[str, Any]
    tope_creditos: int
    ruta_rest: str
    correr: Callable[..., Awaitable[Sobre]]


COMPUESTAS: dict[str, Compuesta] = {
    c.herramienta: c
    for c in (
        Compuesta(
            ficha_lugar.HERRAMIENTA,
            ficha_lugar.VERSION,
            ficha_lugar.FAMILIA,
            ficha_lugar.PREGUNTA,
            ficha_lugar.DESCRIPCION,
            ficha_lugar.ESQUEMA_ENTRADA,
            ficha_lugar.TOPE_CREDITOS,
            "/v1/fichas",
            ficha_lugar.ficha,
        ),
        Compuesta(
            ficha_empresa.HERRAMIENTA,
            ficha_empresa.VERSION,
            ficha_empresa.FAMILIA,
            ficha_empresa.PREGUNTA,
            ficha_empresa.DESCRIPCION,
            ficha_empresa.ESQUEMA_ENTRADA,
            ficha_empresa.TOPE_CREDITOS,
            "/v1/fichas/empresa",
            ficha_empresa.ficha,
        ),
    )
}
