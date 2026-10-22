"""Cliente de los conectores MCP de GEO Copilot (ADR-0002: la puerta no importa su código)."""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any, Protocol

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

# Lo que la puerta puede atribuir a la fuente. Cualquier otro código del conector (p. ej.
# `parametro_invalido`) es un fallo nuestro: la puerta ya validó la entrada antes de llamar.
CODIGOS_DE_FUENTE = frozenset({"fuente_no_disponible", "fuente_lenta", "fuente_respuesta_invalida"})


class ErrorConector(Exception):
    """El conector respondió con error o no se pudo hablar con él.

    `codigo` es el código estable de `rt/1` que corresponde: los de la fuente pasan tal cual
    (kit de GEO Copilot, F1.3); si no se pudo hablar con el conector, `fuente_no_disponible`.
    """

    def __init__(
        self, mensaje: str, codigo: str = "fuente_no_disponible", reintentar_en_s: int | None = None
    ) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.reintentar_en_s = reintentar_en_s


class Conector(Protocol):
    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]: ...


class ConectorMCP:
    """Una sesión MCP por conector, abierta en el arranque y reutilizada en cada llamada."""

    def __init__(self, url: str, llave: str, timeout_s: float = 30) -> None:
        transporte = StreamableHttpTransport(url, headers={"Authorization": f"Bearer {llave}"})
        self.cliente: Client[StreamableHttpTransport] = Client(transporte, timeout=timeout_s)
        self._pila = AsyncExitStack()

    async def abrir(self) -> None:
        await self._pila.enter_async_context(self.cliente)

    async def cerrar(self) -> None:
        await self._pila.aclose()

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        try:
            resultado = await self.cliente.call_tool(herramienta, argumentos, raise_on_error=False)
        except Exception as exc:  # cualquier fallo de red o protocolo es «no se pudo»
            raise ErrorConector(f"{herramienta}: {type(exc).__name__}: {exc}") from exc
        sc = resultado.structured_content
        if resultado.is_error:
            texto = " ".join(getattr(b, "text", "") for b in resultado.content)[:500]
            codigo = sc.get("codigo") if isinstance(sc, dict) else None
            reintentar = sc.get("reintentar_en_s") if isinstance(sc, dict) else None
            raise ErrorConector(
                f"{herramienta}: {texto or 'error sin mensaje'}",
                codigo if codigo in CODIGOS_DE_FUENTE else "error_interno",
                reintentar if isinstance(reintentar, int) else None,
            )
        if not isinstance(sc, dict):
            raise ErrorConector(f"{herramienta}: respuesta sin structuredContent", "error_interno")
        return sc
