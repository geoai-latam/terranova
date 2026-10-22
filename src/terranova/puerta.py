"""La puerta MCP: una herramienta por ficha del catálogo (ADR-0006), todas sobre el ejecutor.

Nada aquí es propio de una fuente: el nombre, la descripción, el esquema de entrada y lo que se
llama salen del catálogo; el sobre `rt/1` y sus errores, del contrato.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.tools import Tool, ToolResult
from mcp.types import TextContent, ToolAnnotations
from pydantic import PrivateAttr

from terranova.catalogo import PATRONES_ENTRADA, Catalogo, Herramienta, cargar
from terranova.conector import Conector, ConectorMCP, conectores_desde_entorno
from terranova.contrato import Sobre
from terranova.ejecutor import Ejecutor, ErrorEjecucion, ErrorEntrada

CATALOGO: Catalogo = cargar()
ESQUEMA_SOBRE = Sobre.model_json_schema(mode="serialization")

_TIPOS_JSON: dict[str, dict[str, Any]] = {
    "float": {"type": "number"},
    "int": {"type": "integer"},
    "bool": {"type": "boolean"},
    "str": {"type": "string", "maxLength": 200},
    "bbox": {
        "type": "array",
        "items": {"type": "number"},
        "minItems": 4,
        "maxItems": 4,
        "description": "[lon_min, lat_min, lon_max, lat_max] EPSG:4326",
    },
    "geojson": {"type": "object"},
    **{tipo: {"type": "string", "pattern": patron} for tipo, patron in PATRONES_ENTRADA.items()},
}

_conectores: dict[str, Conector] | None = None


def usar_conectores(conectores: dict[str, Conector] | None) -> None:
    """Inyecta los conectores (las pruebas pasan unos falsos)."""
    global _conectores
    _conectores = conectores


def esquema_entrada(h: Herramienta) -> dict[str, Any]:
    propiedades = {}
    for nombre, tipo in h.entrada.items():
        esquema = dict(_TIPOS_JSON[tipo])
        if nombre == "lon":
            esquema |= {"minimum": -180, "maximum": 180, "description": "Longitud EPSG:4326"}
        elif nombre == "lat":
            esquema |= {"minimum": -90, "maximum": 90, "description": "Latitud EPSG:4326"}
        propiedades[nombre] = esquema
    return {
        "type": "object",
        "properties": propiedades,
        "required": list(h.entrada),
        "additionalProperties": False,
    }


class HerramientaDelCatalogo(Tool):
    """Una ficha del catálogo como herramienta MCP."""

    _ficha: str = PrivateAttr()

    @classmethod
    def desde(cls, h: Herramienta) -> HerramientaDelCatalogo:
        herramienta = cls(
            name=h.id,
            title=h.pregunta,
            description=" ".join(h.descripcion.split()),
            parameters=esquema_entrada(h),
            output_schema=ESQUEMA_SOBRE,
            annotations=ToolAnnotations(
                read_only_hint=True, idempotent_hint=True, open_world_hint=True
            ),
            tags={h.familia},
            meta={
                "terranova": {"familia": h.familia, "version": h.version, "creditos": h.creditos}
            },
        )
        herramienta._ficha = h.id
        return herramienta

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        if _conectores is None:
            raise ToolError("error_interno: la puerta no tiene conectores")
        try:
            sobre = await Ejecutor(CATALOGO, _conectores).ejecutar(self._ficha, arguments)
        except ErrorEntrada as exc:
            raise ToolError(f"parametro_invalido: {exc}") from exc
        except ErrorEjecucion as exc:
            raise ToolError(f"{exc.codigo}: {exc}") from exc
        pares = ", ".join(f"{k}={v}" for k, v in list(sobre.datos.items())[:6])
        return ToolResult(
            content=[TextContent(type="text", text=f"{sobre.estado}: {pares}"[:1000])],
            structured_content=sobre.model_dump(mode="json"),
        )


@asynccontextmanager
async def _ciclo(_servidor: FastMCP) -> AsyncIterator[None]:
    if _conectores is not None:
        yield
        return
    conectores = conectores_desde_entorno()
    for c in conectores.values():
        if isinstance(c, ConectorMCP):
            await c.abrir()
    usar_conectores(conectores)
    try:
        yield
    finally:
        usar_conectores(None)
        for c in conectores.values():
            if isinstance(c, ConectorMCP):
                await c.cerrar()


puerta = FastMCP(
    "terranova",
    instructions=(
        "Fuentes oficiales colombianas y globales con procedencia y licencia en cada respuesta "
        "(contrato rt/1). Una herramienta por pregunta; cada descripción dice la fuente y la "
        "licencia."
    ),
    lifespan=_ciclo,
)
for _h in CATALOGO.herramientas.values():
    puerta.add_tool(HerramientaDelCatalogo.desde(_h))


def main() -> None:
    puerta.run(
        transport="http",
        host="127.0.0.1",
        port=int(os.environ.get("TERRANOVA_PUERTO", "8100")),
    )
