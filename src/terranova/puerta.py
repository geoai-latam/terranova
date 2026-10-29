"""La puerta MCP: una herramienta por ficha del catálogo (ADR-0006), todas sobre el ejecutor.

Nada aquí es propio de una fuente: el nombre, la descripción, el esquema de entrada y lo que se
llama salen del catálogo; el sobre `rt/1` y sus errores, del contrato.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from fastmcp.tools import Tool, ToolResult
from mcp.types import TextContent, ToolAnnotations
from pydantic import PrivateAttr, ValidationError

from terranova import ficha as ficha_lugar
from terranova import metricas, perfil_catalogo
from terranova.cache import Almacen, AlmacenMemoria, AlmacenRedis
from terranova.catalogo import (
    FORMAS_ENTRADA,
    PATRONES_ENTRADA,
    Catalogo,
    Herramienta,
    cargar,
    ids_parecidos,
)
from terranova.conector import Conector, ConectorMCP, conectores_desde_entorno
from terranova.contrato import PATRON_TEXTO_LIMPIO, Sobre, huella, nueva_solicitud_id
from terranova.cuota import Cuota, cuota_desde_entorno, reinicio, segundos_hasta_el_mes_siguiente
from terranova.curado import Restricciones, restricciones_desde_entorno
from terranova.ejecutor import Ejecutor, Plan
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.ficha_tecnica import ficha_tecnica
from terranova.identidad import Principal, Registro, registro_desde_entorno
from terranova.medicion import Evento, Outbox, OutboxSql, registrar_sin_fallar
from terranova.medicion import ahora as ahora_iso
from terranova.proteccion import Proteccion
from terranova.vigilancia import RegistroCanarios

if TYPE_CHECKING:
    from terranova.descubrimiento import Embedder

logger = logging.getLogger("terranova.puerta")
CATALOGO: Catalogo = cargar()
ESQUEMA_SOBRE = Sobre.model_json_schema(mode="serialization")

_TIPOS_JSON: dict[str, dict[str, Any]] = {
    "float": {"type": "number"},
    "int": {"type": "integer"},
    "bool": {"type": "boolean"},
    "str": {"type": "string", "maxLength": 200, "pattern": PATRON_TEXTO_LIMPIO},
    "bbox": {
        "type": "array",
        "items": {"type": "number"},
        "minItems": 4,
        "maxItems": 4,
        "description": "[lon_min, lat_min, lon_max, lat_max] EPSG:4326",
    },
    "geojson": {"type": "object"},
    **{
        tipo: {
            "type": "string",
            "pattern": patron,
            "description": f"{FORMAS_ENTRADA[tipo][0]} (ej. {FORMAS_ENTRADA[tipo][1]})",
        }
        for tipo, patron in PATRONES_ENTRADA.items()
    },
}


@dataclass
class EstadoPuerta:
    """Todo el estado mutable de una puerta (una por réplica), en un objeto en vez de variables de
    módulo sueltas: se construye, se reinicia (`detener`) y en pruebas se puede tener aislado.

    El proceso vivo usa una sola instancia (`ESTADO`): las herramientas MCP de FastMCP son llamadas
    sueltas, sin un asa a la aplicación ASGI, así que comparten este registro del módulo. Lo que
    gana la encapsulación es cohesión y aislamiento: dos `EstadoPuerta()` no comparten nada."""

    conectores: dict[str, Conector] | None = None
    almacen: Almacen | None = None
    registro: Registro | None = None  # None = sin identidad (solo pruebas en memoria)
    cuota: Cuota | None = None
    outbox: Outbox | None = None
    canarios: RegistroCanarios | None = None
    curado: Restricciones | None = None
    # El estado de los cortacircuitos vive lo que vive la puerta (una por réplica).
    proteccion: Proteccion = field(default_factory=Proteccion)
    iniciados: dict[str, Conector] = field(default_factory=dict)


ESTADO = EstadoPuerta()


def usar_conectores(conectores: dict[str, Conector] | None) -> None:
    """Inyecta los conectores (las pruebas pasan unos falsos)."""
    ESTADO.conectores = conectores


def plan_actual() -> Plan:
    """El plan de quien llama. Hasta la identidad (F3.2) sale de `TERRANOVA_PLAN`; por defecto
    `normal`, el seguro: una fuente con licencia por verificar no responde."""
    return "evaluacion" if os.environ.get("TERRANOVA_PLAN") == "evaluacion" else "normal"


def mensaje_saldo_agotado(org: str, ahora: float) -> str:
    """Igual por REST y por MCP (ADR-0004): cuándo se renueva y, si hay, dónde subir de plan."""
    mensaje = (
        f"la organización {org} agotó sus créditos del mes; "
        f"se renuevan el {reinicio(ahora).date().isoformat()} (UTC)"
    )
    if url := os.environ.get("TERRANOVA_URL_PLANES"):
        mensaje += f" o al subir de plan: {url}"
    return mensaje


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
                "terranova": {
                    "familia": h.familia,
                    "version": h.version,
                    "creditos": h.creditos,
                    "fuente": h.fuente,
                }
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
        return await _correr(self._ficha, arguments)


async def _correr(ficha: str, arguments: dict[str, Any]) -> ToolResult:
    """Una herramienta del catálogo como resultado MCP: el sobre en `structured_content`."""
    try:
        sobre = await ejecutar(ficha, arguments, principal_de_la_peticion())
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
    etiqueta = (
        ficha if ficha in CATALOGO.herramientas or ficha == ficha_lugar.HERRAMIENTA else "otra"
    )
    inicio = time.monotonic()
    try:
        sobre = await _ejecutar(ficha, entrada, principal)
    except ValidationError as exc:
        # datos de la fuente que no cumplen el contrato rt/1 (p. ej. vistos>total, CRS mal
        # rotulado): es la fuente la que respondió algo inválido, no un error nuestro ni «no hay».
        logging.getLogger("terranova").warning("fuente_respuesta_invalida en %s: %s", ficha, exc)
        await _medir(principal, ficha, nueva_solicitud_id(), 0, "fuente_respuesta_invalida", None)
        metricas.SOLICITUDES.labels(etiqueta, "error", "fuente_respuesta_invalida").inc()
        raise ErrorEjecucion(
            "fuente_respuesta_invalida", "la fuente respondió algo inválido"
        ) from exc
    except (ErrorEjecucion, ErrorEntrada) as exc:
        codigo = exc.codigo if isinstance(exc, ErrorEjecucion) else "parametro_invalido"
        await _medir(principal, ficha, nueva_solicitud_id(), 0, codigo, None)
        metricas.SOLICITUDES.labels(etiqueta, "error", codigo).inc()
        raise
    servido = _servido(sobre)
    await _medir(principal, ficha, sobre.solicitud_id, sobre.creditos, sobre.estado, servido)
    metricas.SOLICITUDES.labels(etiqueta, sobre.estado, "").inc()
    metricas.LATENCIA.labels(etiqueta, servido or "ninguno").observe(time.monotonic() - inicio)
    return sobre


# De la más lenta a la más rápida: una solicitud de varias partes (la ficha) cuenta como la peor
_ORDEN_SERVIDO = ("fuente", "obsoleto", "copia", "curado", "cache")


def _servido(sobre: Sobre) -> str | None:
    """De dónde salió la respuesta, para medirla: si UNA parte fue a la fuente, fue en vivo.

    F7.2: con solo la primera procedencia, una ficha de 20 s con el predio en caché contaba como
    caché y disparaba `LatenciaConCacheAlta`.
    """
    vistos = {p.servido_desde for p in sobre.procedencia}
    return next((s for s in _ORDEN_SERVIDO if s in vistos), None)


async def _medir(
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
    # el INSERT del outbox va fuera del event loop (no bloquea la ruta caliente)
    await asyncio.to_thread(registrar_sin_fallar, ESTADO.outbox, evento)


async def ejecutar_idempotente(
    ficha: str, entrada: dict[str, Any], principal: Principal | None, clave: str | None
) -> tuple[Sobre, bool]:
    """Con `Idempotency-Key`, la misma llave y clave devuelven el mismo sobre sin volver a ejecutar,
    cobrar ni medir (E2E-10). (sobre, repetido)."""
    if not clave or principal is None or ESTADO.almacen is None:
        return await ejecutar(ficha, entrada, principal), False
    if len(clave) > 128:
        raise ErrorEntrada("Idempotency-Key", "hasta 128 caracteres")
    k = "terranova:idem:" + hashlib.sha256(f"{principal.llave_id}\n{clave}".encode()).hexdigest()
    pedido = huella({"herramienta": ficha, "entrada": entrada})
    previo = await ESTADO.almacen.leer(k)
    if previo is not None:
        if previo["pedido"] != pedido:
            raise ErrorEntrada("Idempotency-Key", "ya se usó con otra herramienta o entrada")
        return Sobre.model_validate(previo["sobre"]), True
    sobre = await ejecutar(ficha, entrada, principal)
    await ESTADO.almacen.guardar(
        k, {"pedido": pedido, "sobre": sobre.model_dump(mode="json")}, 24 * 3600
    )
    return sobre, False


async def _ejecutar(ficha: str, entrada: dict[str, Any], principal: Principal | None) -> Sobre:
    if ESTADO.conectores is None:
        raise ErrorEjecucion("error_interno", "la puerta no tiene conectores")
    h = CATALOGO.herramientas.get(ficha)
    es_ficha = ficha == ficha_lugar.HERRAMIENTA
    familia = ficha_lugar.FAMILIA if es_ficha else h.familia if h is not None else None
    if ESTADO.registro is not None:
        if principal is None:
            raise ErrorEjecucion("no_autenticado", "falta una llave válida (Authorization: Bearer)")
        if familia is not None and not principal.puede(familia):
            raise ErrorEjecucion("sin_permiso", f"la llave no tiene el scope «{familia}»")
    plan = principal.plan if principal is not None else plan_actual()
    ejecutor = Ejecutor(CATALOGO, ESTADO.conectores, ESTADO.almacen, proteccion=ESTADO.proteccion)

    async def correr() -> Sobre:
        if es_ficha:
            # las partes fuera de los scopes de la llave no se consultan (salen en avisos)
            puede = principal.puede if principal is not None else (lambda _f: True)
            return await ficha_lugar.ficha(
                ejecutor, entrada, plan=plan, puede=puede, curado=ESTADO.curado
            )
        return await ejecutor.ejecutar(ficha, entrada, plan=plan)

    costo = ficha_lugar.TOPE_CREDITOS if es_ficha else h.creditos if h is not None else None
    if ESTADO.cuota is None or principal is None or costo is None:
        return await correr()
    cuota = ESTADO.cuota
    # ADR-0010: se reserva el costo antes de llamar y se devuelve lo que no se cobró
    reservado, _ = await cuota.reservar(principal.org, principal.nivel, costo)
    if not reservado:
        ahora = time.time()
        raise ErrorEjecucion(
            "saldo_agotado",
            mensaje_saldo_agotado(principal.org, ahora),
            segundos_hasta_el_mes_siguiente(ahora),
        )
    try:
        sobre = await correr()
    except BaseException:
        await cuota.devolver(principal.org, costo)
        raise
    await cuota.devolver(principal.org, costo - sobre.creditos)
    metricas.CREDITOS.labels(principal.nivel).inc(sobre.creditos)
    return sobre


async def iniciar() -> None:
    """Conectores, caché, cuota y protección para toda la puerta. Si ya hay conectores (las pruebas
    los inyectan), no hace nada."""
    if ESTADO.conectores is not None:
        return
    ESTADO.registro = registro_desde_entorno()  # sin pimienta, la puerta no arranca
    redis_url = os.environ.get("TERRANOVA_REDIS_URL")
    ESTADO.almacen = AlmacenRedis(redis_url) if redis_url else AlmacenMemoria()
    ESTADO.cuota = cuota_desde_entorno(redis_url)
    bd = os.environ.get("TERRANOVA_BD", "datos_locales/terranova.db")
    ESTADO.outbox = OutboxSql(bd)
    ESTADO.canarios = RegistroCanarios(bd)
    ESTADO.curado = restricciones_desde_entorno()
    _medir_al_raspar()
    ESTADO.iniciados.update(conectores_desde_entorno(CATALOGO))
    for nombre, c in ESTADO.iniciados.items():
        if isinstance(c, ConectorMCP):
            try:
                await c.abrir()
            except Exception:
                # su primera llamada reabre la sesión; mientras, sus herramientas responden
                # fuente_no_disponible y el cortacircuitos protege
                logger.warning("conector %s no disponible al arrancar", nombre, exc_info=True)
    usar_conectores(dict(ESTADO.iniciados))


def _medir_al_raspar() -> None:
    """Lo que `/metrics` lee al momento: circuitos, último canario y outbox pendiente."""
    metricas.AL_RASPAR.circuitos = lambda: [
        (f, ESTADO.proteccion.abierto(f)) for f in sorted(ESTADO.proteccion.circuitos)
    ]
    metricas.AL_RASPAR.canarios = lambda: (
        [(r.fuente_id, r.ok) for r in ESTADO.canarios.ultimos()]
        if ESTADO.canarios is not None
        else []
    )
    metricas.AL_RASPAR.outbox = lambda: (
        ESTADO.outbox.pendientes() if isinstance(ESTADO.outbox, OutboxSql) else None
    )


async def detener() -> None:
    if not ESTADO.iniciados:
        return
    usar_conectores(None)
    ESTADO.almacen = None
    ESTADO.registro = None
    ESTADO.cuota = None
    ESTADO.outbox = None
    ESTADO.canarios = None
    ESTADO.curado = None
    for c in ESTADO.iniciados.values():
        if isinstance(c, ConectorMCP):
            await c.cerrar()
    ESTADO.iniciados.clear()


@asynccontextmanager
async def _ciclo(_servidor: FastMCP) -> AsyncIterator[None]:
    await iniciar()
    try:
        yield
    finally:
        await detener()


INSTRUCCIONES = (
    "Fuentes oficiales colombianas y globales con procedencia y licencia en cada respuesta "
    "(contrato rt/1). Una herramienta por pregunta; cada descripción dice la fuente y la licencia. "
    "Antes de responder sobre años, cobertura, unidades o códigos, `fuente_describir` "
    "da la ficha técnica de la fuente de una herramienta."
)


def fuente_describir(fuente: str) -> dict[str, Any]:
    """Ficha técnica de una fuente (spec 08): qué años cubre, si es geográfica (geometría, CRS,
    extensión, capas), qué significa cada campo (tipo, mínimo, máximo, códigos), qué es una fila,
    cuándo se actualizó y qué alertas tiene (datos atrasados, filas repetidas, licencia). Acepta el
    id de una fuente (`icfes.saber11`) o de una de sus herramientas (`icfes_saber11_municipio`).
    Sale del catálogo: no consulta la fuente ni gasta créditos."""
    h = CATALOGO.herramientas.get(fuente)
    fuente_id = h.fuente if h is not None else fuente
    if fuente_id not in CATALOGO.fuentes:
        parecidos = ids_parecidos(CATALOGO, fuente)
        pista = f"; ¿quiso decir {', '.join(parecidos)}?" if parecidos else ""
        raise ToolError(f"no_existe: no hay fuente ni herramienta «{fuente}»{pista}")
    return ficha_tecnica(CATALOGO, fuente_id)


# De nombre a código, en todos los perfiles: sin ellas el agente supone los códigos (en el banco de
# agente mandó 25095 como DIVIPOLA de Chía, que es 25175, y un NIT inventado para su alcaldía).
HERRAMIENTAS_COMUNES = frozenset({"dane_divipola_buscar", "secop_entidades_municipio"})


def crear_servidor(familia: str | None = None, *, con_ciclo: bool = True) -> FastMCP:
    """`/mcp` con todo o un perfil por familia (`/mcp/territorio`…, ADR-0006)."""
    nombre = "terranova" if familia is None else f"terranova-{familia}"
    servidor = FastMCP(nombre, instructions=INSTRUCCIONES, lifespan=_ciclo if con_ciclo else None)
    for h in CATALOGO.herramientas.values():
        if familia is None or h.familia == familia or h.id in HERRAMIENTAS_COMUNES:
            servidor.add_tool(HerramientaDelCatalogo.desde(h))
    if familia in (None, ficha_lugar.FAMILIA):
        servidor.add_tool(HerramientaDelCatalogo.ficha_de_lugar())
    servidor.tool(
        fuente_describir,
        annotations=ToolAnnotations(
            read_only_hint=True, idempotent_hint=True, open_world_hint=False
        ),
        tags={"catalogo"},
    )
    return servidor


FAMILIAS = sorted({h.familia for h in CATALOGO.herramientas.values()})
puerta = crear_servidor()


# Perfil «catálogo» (`/mcp/catalogo`): buscar → consultar, para los clientes que no buscan
# herramientas por su cuenta. Las herramientas de siempre siguen siendo el contrato: `consultar`
# corre el mismo `ejecutar` (misma validación, mismo sobre, mismos créditos y scopes).
PERFIL_CATALOGO = "catalogo"
_INDICE: perfil_catalogo.IndiceHerramientas | None = None


def _embedder_herramientas() -> Embedder | None:
    url = os.environ.get("TERRANOVA_EMBEDDINGS_URL")
    if not url:
        return None
    from terranova.descubrimiento import EmbedderRemoto

    return EmbedderRemoto(url, timeout_s=60, intentos=2)


def indice_herramientas() -> perfil_catalogo.IndiceHerramientas:
    global _INDICE
    if _INDICE is None:
        _INDICE = perfil_catalogo.indice_desde_entorno(CATALOGO, _embedder_herramientas)
        _INDICE.vectorizar_en_segundo_plano()
    return _INDICE


def _resumen_herramienta(id_: str) -> dict[str, Any]:
    if id_ == ficha_lugar.HERRAMIENTA:
        return {
            "herramienta": id_,
            "familia": ficha_lugar.FAMILIA,
            "pregunta": ficha_lugar.PREGUNTA,
            "descripcion": " ".join(ficha_lugar.DESCRIPCION.split())[:600],
            "entrada": ficha_lugar.ESQUEMA_ENTRADA,
        }
    h = CATALOGO.herramientas[id_]
    esquema = esquema_entrada(h)
    return {
        "herramienta": h.id,
        "familia": h.familia,
        "pregunta": h.pregunta,
        "descripcion": " ".join(h.descripcion.split())[:600],
        "entrada": {"properties": esquema["properties"], "required": esquema["required"]},
        "creditos": h.creditos,
    }


def buscar_herramienta(pregunta: str, familia: str | None = None) -> dict[str, Any]:
    """Busca en el catálogo de Terranova las herramientas que responden una pregunta y devuelve
    las mejores con su entrada (propiedades y obligatorias), lista para `consultar`. Familias:
    {familias}. Si ninguna sirve, busque de nuevo con otras palabras (el tema, la entidad o el
    dato que se pide) o filtre por `familia`. Sale del catálogo: no consulta fuentes ni gasta
    créditos."""
    if familia is not None and familia not in FAMILIAS:
        raise ToolError(
            f"parametro_invalido: familia «{familia}»; use una de {', '.join(FAMILIAS)}"
        )
    indice = indice_herramientas()
    hallados = indice.buscar(pregunta, familia)
    return {
        "modo": indice.modo,
        "herramientas": [_resumen_herramienta(d.herramienta) for d in hallados],
    }


async def consultar(herramienta: str, entrada: dict[str, Any] | str) -> ToolResult:
    """Ejecuta una herramienta del catálogo de Terranova (la que dio `buscar_herramienta`) con su
    entrada. Responde el sobre rt/1: estado (encontrado, no_encontrado, parcial), datos y
    procedencia con la licencia. Gasta los créditos de esa herramienta."""
    if herramienta not in CATALOGO.herramientas and herramienta != ficha_lugar.HERRAMIENTA:
        parecidos = ids_parecidos(CATALOGO, herramienta)
        pista = f"; ¿quiso decir {', '.join(parecidos)}?" if parecidos else ""
        raise ToolError(f"no_existe: no hay herramienta «{herramienta}»{pista}")
    if isinstance(entrada, str):  # algunos modelos mandan el objeto como texto JSON
        try:
            entrada = json.loads(entrada or "{}")
        except json.JSONDecodeError as exc:
            raise ToolError("parametro_invalido: `entrada` debe ser un objeto JSON") from exc
    if not isinstance(entrada, dict):
        raise ToolError("parametro_invalido: `entrada` debe ser un objeto JSON")
    return await _correr(herramienta, entrada)


def crear_servidor_catalogo(*, con_ciclo: bool = True) -> FastMCP:
    """`/mcp/catalogo`: buscar_herramienta, consultar, fuente_describir y los resolvedores."""
    servidor = FastMCP(
        f"terranova-{PERFIL_CATALOGO}",
        instructions=INSTRUCCIONES_CATALOGO,
        lifespan=_ciclo if con_ciclo else None,
    )
    solo_lectura = ToolAnnotations(read_only_hint=True, idempotent_hint=True)
    servidor.tool(
        buscar_herramienta,
        description=" ".join(buscar_herramienta.__doc__.split()).format(  # type: ignore[union-attr]
            familias=perfil_catalogo.mapa_de_familias(CATALOGO)
        ),
        annotations=solo_lectura.model_copy(update={"open_world_hint": False}),
        tags={"catalogo"},
    )
    servidor.tool(
        consultar,
        annotations=solo_lectura.model_copy(update={"open_world_hint": True}),
        tags={"catalogo"},
    )
    for id_ in sorted(HERRAMIENTAS_COMUNES):
        servidor.add_tool(HerramientaDelCatalogo.desde(CATALOGO.herramientas[id_]))
    servidor.tool(
        fuente_describir,
        annotations=solo_lectura.model_copy(update={"open_world_hint": False}),
        tags={"catalogo"},
    )
    indice_herramientas()
    return servidor


INSTRUCCIONES_CATALOGO = (
    "Fuentes oficiales colombianas con procedencia y licencia en cada respuesta (contrato rt/1). "
    "Para responder: 1) `buscar_herramienta` con la pregunta; 2) `consultar` con el id y la "
    "entrada que trae el resultado. Si el resultado no sirve, busque otra vez con otras palabras. "
    "Para pasar un nombre de municipio a su código DIVIPOLA use `dane_divipola_buscar`; para el "
    "NIT de una entidad pública, `secop_entidades_municipio`. No suponga códigos."
)
