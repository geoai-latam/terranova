"""La puerta MCP: una herramienta por ficha del catálogo (ADR-0006), todas sobre el ejecutor.

Nada aquí es propio de una fuente: el nombre, la descripción, el esquema de entrada y lo que se
llama salen del catálogo; el sobre `rt/1` y sus errores, del contrato.
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.tools import Tool, ToolResult
from mcp.types import TextContent, ToolAnnotations
from pydantic import PrivateAttr

from terranova import ficha as ficha_lugar
from terranova.cache import Almacen, AlmacenMemoria, AlmacenRedis
from terranova.catalogo import PATRONES_ENTRADA, Catalogo, Herramienta, cargar
from terranova.conector import Conector, ConectorMCP, conectores_desde_entorno
from terranova.contrato import Sobre, huella, nueva_solicitud_id
from terranova.cuota import Cuota, cuota_desde_entorno, segundos_hasta_el_mes_siguiente
from terranova.ejecutor import Ejecutor, Plan
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.identidad import Principal, Registro, registro_desde_entorno
from terranova.medicion import Evento, Outbox, OutboxSql, registrar_sin_fallar
from terranova.medicion import ahora as ahora_iso
from terranova.proteccion import Proteccion
from terranova.vigilancia import RegistroCanarios

logger = logging.getLogger("terranova.puerta")
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

    @classmethod
    def ficha_de_lugar(cls) -> HerramientaDelCatalogo:
        """`ficha_lugar` (spec 03 §8.3): compone herramientas del catálogo, no es una ficha."""
        herramienta = cls(
            name=ficha_lugar.HERRAMIENTA,
            title=ficha_lugar.PREGUNTA,
            description=ficha_lugar.DESCRIPCION,
            parameters=ficha_lugar.ESQUEMA_ENTRADA,
            output_schema=ESQUEMA_SOBRE,
            annotations=ToolAnnotations(
                read_only_hint=True, idempotent_hint=True, open_world_hint=True
            ),
            tags={ficha_lugar.FAMILIA},
            meta={
                "terranova": {
                    "familia": ficha_lugar.FAMILIA,
                    "version": ficha_lugar.VERSION,
                    "creditos": ficha_lugar.TOPE_CREDITOS,
                }
            },
        )
        herramienta._ficha = ficha_lugar.HERRAMIENTA
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
    memoria), el plan sale de `TERRANOVA_PLAN`. Cada solicitud deja un evento de uso (F3.4).
    """
    try:
        sobre = await _ejecutar(ficha, entrada, principal)
    except (ErrorEjecucion, ErrorEntrada) as exc:
        codigo = exc.codigo if isinstance(exc, ErrorEjecucion) else "parametro_invalido"
        _medir(principal, ficha, nueva_solicitud_id(), 0, codigo, None)
        raise
    servido = sobre.procedencia[0].servido_desde if sobre.procedencia else None
    _medir(principal, ficha, sobre.solicitud_id, sobre.creditos, sobre.estado, servido)
    return sobre


def _medir(
    principal: Principal | None,
    ficha: str,
    solicitud_id: str,
    creditos: int,
    resultado: str,
    servido_desde: str | None,
) -> None:
    if principal is None:
        return
    evento = Evento(
        solicitud_id=solicitud_id,
        org=principal.org,
        llave_id=principal.llave_id,
        herramienta=ficha,
        creditos=creditos,
        resultado=resultado,
        servido_desde=servido_desde,
        momento=ahora_iso(),
    )
    registrar_sin_fallar(outbox, evento)


async def ejecutar_idempotente(
    ficha: str, entrada: dict[str, Any], principal: Principal | None, clave: str | None
) -> tuple[Sobre, bool]:
    """Con `Idempotency-Key`, la misma llave y clave devuelven el mismo sobre sin volver a ejecutar,
    cobrar ni medir (E2E-10). (sobre, repetido)."""
    if not clave or principal is None or _almacen is None:
        return await ejecutar(ficha, entrada, principal), False
    if len(clave) > 128:
        raise ErrorEntrada("Idempotency-Key", "hasta 128 caracteres")
    k = "terranova:idem:" + hashlib.sha256(f"{principal.llave_id}\n{clave}".encode()).hexdigest()
    pedido = huella({"herramienta": ficha, "entrada": entrada})
    previo = await _almacen.leer(k)
    if previo is not None:
        if previo["pedido"] != pedido:
            raise ErrorEntrada("Idempotency-Key", "ya se usó con otra herramienta o entrada")
        return Sobre.model_validate(previo["sobre"]), True
    sobre = await ejecutar(ficha, entrada, principal)
    await _almacen.guardar(k, {"pedido": pedido, "sobre": sobre.model_dump(mode="json")}, 24 * 3600)
    return sobre, False


async def _ejecutar(ficha: str, entrada: dict[str, Any], principal: Principal | None) -> Sobre:
    if _conectores is None:
        raise ErrorEjecucion("error_interno", "la puerta no tiene conectores")
    h = CATALOGO.herramientas.get(ficha)
    es_ficha = ficha == ficha_lugar.HERRAMIENTA
    familia = ficha_lugar.FAMILIA if es_ficha else h.familia if h is not None else None
    if registro is not None:
        if principal is None:
            raise ErrorEjecucion("no_autenticado", "falta una llave válida (Authorization: Bearer)")
        if familia is not None and not principal.puede(familia):
            raise ErrorEjecucion("sin_permiso", f"la llave no tiene el scope «{familia}»")
    plan = principal.plan if principal is not None else plan_actual()
    ejecutor = Ejecutor(CATALOGO, _conectores, _almacen, proteccion=PROTECCION)

    async def correr() -> Sobre:
        if es_ficha:
            # las partes fuera de los scopes de la llave no se consultan (salen en avisos)
            puede = principal.puede if principal is not None else (lambda _f: True)
            return await ficha_lugar.ficha(ejecutor, entrada, plan=plan, puede=puede)
        return await ejecutor.ejecutar(ficha, entrada, plan=plan)

    costo = ficha_lugar.TOPE_CREDITOS if es_ficha else h.creditos if h is not None else None
    if cuota is None or principal is None or costo is None:
        return await correr()
    # ADR-0010: se reserva el costo antes de llamar y se devuelve lo que no se cobró
    reservado, _ = await cuota.reservar(principal.org, principal.nivel, costo)
    if not reservado:
        raise ErrorEjecucion(
            "saldo_agotado",
            f"la organización {principal.org} agotó sus créditos del mes",
            segundos_hasta_el_mes_siguiente(time.time()),
        )
    try:
        sobre = await correr()
    except BaseException:
        await cuota.devolver(principal.org, costo)
        raise
    await cuota.devolver(principal.org, costo - sobre.creditos)
    return sobre


_iniciados: dict[str, Conector] = {}
registro: Registro | None = None  # None = sin identidad (solo pruebas en memoria)
cuota: Cuota | None = None
outbox: Outbox | None = None
canarios: RegistroCanarios | None = None


async def iniciar() -> None:
    """Conectores, caché, cuota y protección para toda la puerta. Si ya hay conectores (las pruebas
    los inyectan), no hace nada."""
    global _almacen, registro, cuota, outbox, canarios
    if _conectores is not None:
        return
    registro = registro_desde_entorno()  # sin pimienta, la puerta no arranca
    redis_url = os.environ.get("TERRANOVA_REDIS_URL")
    _almacen = AlmacenRedis(redis_url) if redis_url else AlmacenMemoria()
    cuota = cuota_desde_entorno(redis_url)
    bd = os.environ.get("TERRANOVA_BD", "datos_locales/terranova.db")
    outbox = OutboxSql(bd)
    canarios = RegistroCanarios(bd)
    _iniciados.update(conectores_desde_entorno())
    for nombre, c in _iniciados.items():
        if isinstance(c, ConectorMCP):
            try:
                await c.abrir()
            except Exception:
                # su primera llamada reabre la sesión; mientras, sus herramientas responden
                # fuente_no_disponible y el cortacircuitos protege
                logger.warning("conector %s no disponible al arrancar", nombre, exc_info=True)
    usar_conectores(dict(_iniciados))


async def detener() -> None:
    global _almacen, registro, cuota, outbox, canarios
    if not _iniciados:
        return
    usar_conectores(None)
    _almacen = None
    registro = None
    cuota = None
    outbox = None
    canarios = None
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
    if familia in (None, ficha_lugar.FAMILIA):
        servidor.add_tool(HerramientaDelCatalogo.ficha_de_lugar())
    return servidor


FAMILIAS = sorted({h.familia for h in CATALOGO.herramientas.values()})
puerta = crear_servidor()
