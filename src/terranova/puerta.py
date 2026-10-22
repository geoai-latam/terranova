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
from fastmcp.server.dependencies import get_http_request
from fastmcp.tools import Tool, ToolResult
from mcp.types import TextContent, ToolAnnotations
from pydantic import PrivateAttr

from terranova.cache import Almacen, AlmacenMemoria, AlmacenRedis
from terranova.catalogo import PATRONES_ENTRADA, Catalogo, Herramienta, cargar
from terranova.conector import Conector, ConectorMCP, conectores_desde_entorno
from terranova.contrato import Sobre
from terranova.ejecutor import Ejecutor, Plan
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.identidad import Principal, Registro, registro_desde_entorno
from terranova.proteccion import Proteccion

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
_almacen: Almacen | None = None
# El estado de los cortacircuitos vive lo que vive la puerta (una por réplica).
PROTECCION = Proteccion()


def usar_conectores(conectores: dict[str, Conector] | None) -> None:
    """Inyecta los conectores (las pruebas pasan unos falsos)."""
    global _conectores
    _conectores = conectores


def plan_actual() -> Plan:
    """El plan de quien llama. Hasta la identidad (F3.2) sale de `TERRANOVA_PLAN`; por defecto
    `normal`, el seguro: una fuente con licencia por verificar no responde."""
    return "evaluacion" if os.environ.get("TERRANOVA_PLAN") == "evaluacion" else "normal"


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
        try:
            sobre = await ejecutar(self._ficha, arguments, principal_de_la_peticion())
        except ErrorEntrada as exc:
            raise ToolError(f"parametro_invalido: {exc}") from exc
        except ErrorEjecucion as exc:
            raise ToolError(f"{exc.codigo}: {exc}") from exc
        pares = ", ".join(f"{k}={v}" for k, v in list(sobre.datos.items())[:6])
        return ToolResult(
            content=[TextContent(type="text", text=f"{sobre.estado}: {pares}"[:1000])],
            structured_content=sobre.model_dump(mode="json"),
        )


def principal_de_la_peticion() -> Principal | None:
    """El principal que dejó la aplicación en la petición HTTP (None en memoria, sin HTTP)."""
    try:
        principal = get_http_request().state.principal
    except (RuntimeError, AttributeError, LookupError):
        return None
    return principal if isinstance(principal, Principal) else None


async def ejecutar(
    ficha: str, entrada: dict[str, Any], principal: Principal | None = None
) -> Sobre:
    """El mismo camino para MCP y REST (ADR-0004): misma entrada, mismo sobre.

    Con identidad (la aplicación), el plan y los scopes salen de la llave; sin ella (pruebas en
    memoria), el plan sale de `TERRANOVA_PLAN`.
    """
    if _conectores is None:
        raise ErrorEjecucion("error_interno", "la puerta no tiene conectores")
    h = CATALOGO.herramientas.get(ficha)
    if registro is not None:
        if principal is None:
            raise ErrorEjecucion("no_autenticado", "falta una llave válida (Authorization: Bearer)")
        if h is not None and not principal.puede(h.familia):
            raise ErrorEjecucion("sin_permiso", f"la llave no tiene el scope «{h.familia}»")
    plan = principal.plan if principal is not None else plan_actual()
    ejecutor = Ejecutor(CATALOGO, _conectores, _almacen, proteccion=PROTECCION)
    return await ejecutor.ejecutar(ficha, entrada, plan=plan)


_iniciados: dict[str, Conector] = {}
registro: Registro | None = None  # None = sin identidad (solo pruebas en memoria)


async def iniciar() -> None:
    """Conectores, caché y protección para toda la puerta. Si ya hay conectores (las pruebas los
    inyectan), no hace nada."""
    global _almacen, registro
    if _conectores is not None:
        return
    registro = registro_desde_entorno()  # sin pimienta, la puerta no arranca
    redis_url = os.environ.get("TERRANOVA_REDIS_URL")
    _almacen = AlmacenRedis(redis_url) if redis_url else AlmacenMemoria()
    _iniciados.update(conectores_desde_entorno())
    for c in _iniciados.values():
        if isinstance(c, ConectorMCP):
            await c.abrir()
    usar_conectores(dict(_iniciados))


async def detener() -> None:
    global _almacen, registro
    if not _iniciados:
        return
    usar_conectores(None)
    _almacen = None
    registro = None
    for c in _iniciados.values():
        if isinstance(c, ConectorMCP):
            await c.cerrar()
    _iniciados.clear()


@asynccontextmanager
async def _ciclo(_servidor: FastMCP) -> AsyncIterator[None]:
    await iniciar()
    try:
        yield
    finally:
        await detener()


INSTRUCCIONES = (
    "Fuentes oficiales colombianas y globales con procedencia y licencia en cada respuesta "
    "(contrato rt/1). Una herramienta por pregunta; cada descripción dice la fuente y la licencia."
)


def crear_servidor(familia: str | None = None, *, con_ciclo: bool = True) -> FastMCP:
    """`/mcp` con todo o un perfil por familia (`/mcp/territorio`…, ADR-0006)."""
    nombre = "terranova" if familia is None else f"terranova-{familia}"
    servidor = FastMCP(nombre, instructions=INSTRUCCIONES, lifespan=_ciclo if con_ciclo else None)
    for h in CATALOGO.herramientas.values():
        if familia is None or h.familia == familia:
            servidor.add_tool(HerramientaDelCatalogo.desde(h))
    return servidor


FAMILIAS = sorted({h.familia for h in CATALOGO.herramientas.values()})
puerta = crear_servidor()
