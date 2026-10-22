"""Cliente de los conectores MCP de GEO Copilot (ADR-0002: la puerta no importa su código)."""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any, Protocol

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

if TYPE_CHECKING:
    from terranova.catalogo import Catalogo

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
    """Una sesión MCP por conector, abierta en el arranque y reutilizada en cada llamada.

    Si la sesión se cae (un tiempo agotado la deja inservible), la siguiente llamada la reabre.
    """

    def __init__(self, url: str, llave: str, timeout_s: float = 30) -> None:
        self._url, self._llave, self._timeout_s = url, llave, timeout_s
        self.cliente: Client[StreamableHttpTransport] = self._nuevo_cliente()
        self._pila = AsyncExitStack()

    def _nuevo_cliente(self) -> Client[StreamableHttpTransport]:
        transporte = StreamableHttpTransport(
            self._url, headers={"Authorization": f"Bearer {self._llave}"}
        )
        # abrir la sesión no espera lo que una consulta: un conector caído se nota en segundos
        return Client(transporte, timeout=self._timeout_s, init_timeout=min(3, self._timeout_s))

    async def abrir(self) -> None:
        await self._pila.enter_async_context(self.cliente)

    async def cerrar(self) -> None:
        try:
            await self._pila.aclose()
        except Exception:  # noqa: BLE001 — una sesión ya rota no debe impedir cerrar el resto
            pass

    async def _reabrir(self) -> None:
        await self.cerrar()
        self._pila = AsyncExitStack()
        self.cliente = self._nuevo_cliente()
        await self.abrir()

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for intento in (1, 2):
            if not self.cliente.is_connected():
                try:
                    await self._reabrir()
                except Exception as exc:  # el conector no está: se dice ya, sin otro intento
                    raise ErrorConector(
                        f"{herramienta}: no se pudo abrir la sesión ({type(exc).__name__})"
                    ) from exc
            try:
                resultado = await self.cliente.call_tool(
                    herramienta, argumentos, raise_on_error=False
                )
                break
            except Exception as exc:  # cualquier fallo de red o protocolo es «no se pudo»
                lento = isinstance(exc, TimeoutError) or "timed out" in str(exc).lower()
                if intento == 1 and not lento and not self.cliente.is_connected():
                    continue  # la sesión murió en medio: se reabre y se intenta una vez más
                raise ErrorConector(
                    f"{herramienta}: {type(exc).__name__}: {exc}",
                    "fuente_lenta" if lento else "fuente_no_disponible",
                ) from exc
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
        for art in sc.get("artifacts") or []:
            if art.get("kind") == "feature_ref" and str(art.get("uri", "")).startswith("/"):
                # lo grande viaja como archivo del propio conector: se baja con la misma llave
                art["data"] = await self._descargar(str(art["uri"]))
                art["kind"] = "feature_collection"
        return sc

    async def _descargar(self, ruta: str) -> Any:
        import asyncio
        import json
        import urllib.request
        from urllib.parse import urlsplit

        base = urlsplit(self._url)
        url = f"{base.scheme}://{base.netloc}{ruta}"
        peticion = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._llave}"})

        def bajar() -> Any:
            with urllib.request.urlopen(peticion, timeout=self._timeout_s) as respuesta:
                return json.load(respuesta)

        try:
            return await asyncio.to_thread(bajar)
        except Exception as exc:  # sin el archivo no hay resultado: «no se pudo»
            raise ErrorConector(f"no se pudo bajar {ruta}: {type(exc).__name__}") from exc


# Dónde vive cada conector (red interna, ADR-0002). Se cambia con `TERRANOVA_CONECTORES` (JSON
# {nombre: url}); la llave de servicio, con `TERRANOVA_LLAVE_<NOMBRE>` o, si es una sola para todos,
# `TERRANOVA_CONECTOR_LLAVE`.
CONECTORES_POR_DEFECTO = {
    "arcgis-mcp": "http://127.0.0.1:9400/mcp",
    "datos-abiertos-mcp": "http://127.0.0.1:9900/mcp",
    "dane-mcp": "http://127.0.0.1:9920/mcp",
    "amenazas-mcp": "http://127.0.0.1:9930/mcp",
    "imagery-mcp": "http://127.0.0.1:9100/mcp",
}


def conectores_desde_entorno(catalogo: Catalogo | None = None) -> dict[str, Conector]:
    """Los conectores MCP de `TERRANOVA_CONECTORES` y, con el catálogo, el interno `copia`
    (ADR-0024) si hay base de copias."""
    import json
    import os

    # si se definen, reemplazan a los de por defecto (que apuntan a 127.0.0.1, solo para desarrollo)
    crudo = os.environ.get("TERRANOVA_CONECTORES")
    urls = json.loads(crudo) if crudo else dict(CONECTORES_POR_DEFECTO)
    comun = os.environ.get("TERRANOVA_CONECTOR_LLAVE", "")
    conectores: dict[str, Conector] = {}
    for nombre, url in urls.items():
        llave = os.environ.get("TERRANOVA_LLAVE_" + nombre.upper().replace("-", "_"), comun)
        if llave:
            conectores[nombre] = ConectorMCP(url, llave, timeout_s=90)
    if catalogo is not None:
        from terranova.copias import conector_desde_entorno

        if (copia := conector_desde_entorno(catalogo)) is not None:
            conectores["copia"] = copia
    return conectores
