"""Cliente de los conectores MCP de GEO Copilot (ADR-0002: la puerta no importa su código)."""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any, Protocol

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport


class ErrorConector(Exception):
    """El conector respondió con error o no se pudo hablar con él."""


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
        if resultado.is_error or not isinstance(resultado.structured_content, dict):
            texto = " ".join(getattr(b, "text", "") for b in resultado.content)[:500]
            raise ErrorConector(f"{herramienta}: {texto or 'respuesta sin structuredContent'}")
        return resultado.structured_content
