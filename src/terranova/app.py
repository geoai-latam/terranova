"""La puerta completa: REST `/v1` y MCP (`/mcp` y un perfil por familia) en una sola aplicación.

Los dos adaptadores salen del mismo catálogo y llaman a la misma función (ADR-0004): misma entrada,
mismo sobre `rt/1`, mismos errores (RFC 9457 en REST, `isError` en MCP, ADR-0011).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import time
from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack
from datetime import UTC, datetime
from html import escape
from typing import Annotated, Any
from urllib.parse import parse_qs

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, create_model, model_validator
from pydantic.json_schema import SkipJsonSchema
from starlette.exceptions import HTTPException as StarletteHTTPException

from terranova import ficha as ficha_lugar
from terranova import ficha_empresa, metricas, puerta
from terranova.alta import NIVEL_ALTA, VIGENCIA_LLAVE, ErrorAlta
from terranova.catalogo import FORMAS_ENTRADA, PATRONES_ENTRADA, Herramienta, ids_parecidos
from terranova.contrato import (
    ESQUEMA_GEOMETRIA,
    ESQUEMA_PAGINA,
    GEOMETRIA,
    PAGINA,
    PATRON_TEXTO_LIMPIO,
    Problema,
    Sobre,
    nueva_solicitud_id,
    problema_de,
)
from terranova.cuota import NIVELES, mes, reinicio
from terranova.descripcion import ai_catalogo, llms_txt, tarjeta_estandar, tarjeta_mcp
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.ficha_tecnica import ficha_tecnica, resumen
from terranova.identidad import bearer
from terranova.pagina_estado import pagina_estado, pagina_simple
from terranova.vigilancia import estado_por_fuente

Scope = MutableMapping[str, Any]
logger = logging.getLogger("terranova.app")


def _tipo(nombre: str, tipo: str) -> Any:
    """El tipo Python (con sus restricciones) de una entrada del catálogo, para OpenAPI."""
    if tipo == "float":
        limite = {"lon": 180, "lat": 90}.get(nombre)
        return Annotated[float, Field(ge=-limite, le=limite)] if limite else float
    if tipo == "int":
        return int
    if tipo == "bool":
        return bool
    if tipo == "bbox":
        return Annotated[list[float], Field(min_length=4, max_length=4)]
    if tipo == "geojson":
        return dict[str, Any]
    if tipo in PATRONES_ENTRADA:
        forma, ejemplo = FORMAS_ENTRADA[tipo]
        return Annotated[
            str, Field(pattern=PATRONES_ENTRADA[tipo], description=f"{forma} (ej. {ejemplo})")
        ]
    return Annotated[str, Field(max_length=200, pattern=PATRON_TEXTO_LIMPIO)]


# opcional y sin `null` en el esquema (Schemathesis): ausente es la envolvente (ADR-0032)
_CAMPO_GEOMETRIA: Any = (
    bool | SkipJsonSchema[None],  # type: ignore[misc]  # un tipo como valor (create_model)
    Field(default=None, description=ESQUEMA_GEOMETRIA["description"]),
)


def _entero_exacto(valor: Any) -> Any:
    # 3.0 es un entero en JSON Schema (Schemathesis lo manda); 3.5 sigue siendo inválido
    return int(valor) if isinstance(valor, float) and valor.is_integer() else valor


_CAMPO_PAGINA: Any = (
    # el mínimo va en el tipo y antes del validador: en otro orden el esquema sale con `ge` y sin
    # `minimum`, y Schemathesis manda 0
    Annotated[int, Field(ge=1), BeforeValidator(_entero_exacto)] | SkipJsonSchema[None],  # type: ignore[misc]
    Field(default=None, description=ESQUEMA_PAGINA["description"]),
)


class _EntradaRest(BaseModel):
    # estricto: `false` no es 0.0 ni "1" es 1 (Schemathesis, F3.5)
    model_config = ConfigDict(extra="forbid", strict=True)

    @model_validator(mode="before")
    @classmethod
    def _sin_nulos(cls, datos: Any) -> Any:
        # un opcional ausente se omite: `null` no está en el esquema (Schemathesis)
        if isinstance(datos, dict) and (nulos := [k for k, v in datos.items() if v is None]):
            raise ValueError(f"{', '.join(nulos)}: se omite, no se manda null")
        return datos


def modelo_entrada(h: Herramienta) -> type[BaseModel]:
    campos: dict[str, Any] = {n: (_tipo(n, t), ...) for n, t in h.entrada.items()}
    if puerta.trae_geometria(h):
        campos[GEOMETRIA] = _CAMPO_GEOMETRIA
    if puerta.pagina_lista(h.id):
        campos[PAGINA] = _CAMPO_PAGINA  # ausente es la primera (ADR-0033)
    nombre = "".join(p.capitalize() for p in h.id.split("_")) + "Entrada"
    return create_model(nombre, __base__=_EntradaRest, **campos)


def problema(
    codigo: str, detalle: str, *, param: str | None = None, reintentar: int | None = None
) -> JSONResponse:
    p = problema_de(codigo, detalle, param=param, reintentar=reintentar)
    cabeceras = {"Retry-After": str(reintentar)} if reintentar else None
    return JSONResponse(
        p.model_dump(mode="json", exclude_none=True),
        status_code=p.status,
        media_type="application/problem+json",
        headers=cabeceras,
    )


class FichaEmpresaEntrada(_EntradaRest):
    """El NIT de una empresa: 9 dígitos que empiezan por 8 o 9, sin dígito de verificación."""

    nit: Annotated[str, Field(pattern=PATRONES_ENTRADA["nit_empresa"])]


class FichaEntrada(_EntradaRest):
    """Un punto (`lon`, `lat`) o un número predial (`codigo`), no los dos."""

    model_config = ConfigDict(json_schema_extra={"oneOf": ficha_lugar.ALTERNATIVAS_ENTRADA})
    # sin `null` en el esquema: un campo ausente se omite, no se manda vacío (Schemathesis)
    lon: Annotated[float, Field(ge=-180, le=180)] | SkipJsonSchema[None] = None
    lat: Annotated[float, Field(ge=-90, le=90)] | SkipJsonSchema[None] = None
    codigo: (
        Annotated[str, Field(pattern=PATRONES_ENTRADA["codigo_predial"])] | SkipJsonSchema[None]
    ) = None
    geometria: bool | SkipJsonSchema[None] = Field(
        default=None, description=ESQUEMA_GEOMETRIA["description"]
    )


def _ruta(ficha: str, Entrada: type[BaseModel]) -> Callable[..., Awaitable[Any]]:
    async def herramienta(entrada: Entrada, request: Request, response: Response) -> Any:  # type: ignore[valid-type]
        try:
            principal = getattr(request.state, "principal", None)
            sobre, repetido = await puerta.ejecutar_idempotente(
                ficha,
                entrada.model_dump(exclude_none=True),  # type: ignore[attr-defined]
                principal,
                request.headers.get("idempotency-key"),
            )
            if repetido:
                response.headers["Idempotent-Replayed"] = "true"
            return sobre
        except ErrorEntrada as exc:
            return problema("parametro_invalido", str(exc), param=exc.param)
        except ErrorEjecucion as exc:
            return problema(exc.codigo, str(exc), reintentar=exc.reintentar_en_s)

    # el modelo se crea en tiempo de ejecución: la anotación debe ser el tipo, no su nombre
    herramienta.__annotations__ = {
        "entrada": Entrada,
        "request": Request,
        "response": Response,
        "return": Any,
    }
    return herramienta


def crear_api() -> FastAPI:
    api = FastAPI(
        title="Terrnova",
        version="1",
        description=(
            "Puerta única sobre fuentes oficiales colombianas y globales. Cada respuesta es un "
            "sobre rt/1 con procedencia, licencia, completitud y `servido_desde`."
        ),
        lifespan=None,
    )

    @api.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Todo error HTTP de FastAPI/Starlette también sale como problem+json (ADR-0011)."""
        if exc.status_code == 400:
            return problema("parametro_invalido", str(exc.detail), param="body")
        if exc.status_code == 404:
            return problema("no_existe", str(exc.detail))
        return JSONResponse(
            {
                "type": "about:blank",
                "title": str(exc.detail),
                "status": exc.status_code,
                "code": "error_interno" if exc.status_code >= 500 else "parametro_invalido",
                "solicitud_id": nueva_solicitud_id(),
            },
            status_code=exc.status_code,
            media_type="application/problem+json",
            headers=getattr(exc, "headers", None),  # p. ej. `Allow` en un 405 (RFC 9110)
        )

    @api.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        primero = exc.errors()[0] if exc.errors() else {}
        ruta = [str(x) for x in primero.get("loc", []) if x != "body"]
        return problema(
            "parametro_invalido",
            str(primero.get("msg", "entrada inválida")),
            param=".".join(ruta) or "body",  # sin cuerpo, el parámetro que falta es el cuerpo
        )

    @api.exception_handler(Exception)
    async def _inesperado(_: Request, exc: Exception) -> JSONResponse:
        """Nada escapa como 500 text/plain (ADR-0011): cualquier error no previsto sale como
        problem+json `error_interno`, con su solicitud_id para rastrearlo en los logs."""
        logging.getLogger("terranova").exception("error interno no previsto")
        return problema("error_interno", "error interno")

    for h in puerta.CATALOGO.herramientas.values():
        api.add_api_route(
            f"/v1/co/{h.familia}/{h.id}",
            _ruta(h.id, modelo_entrada(h)),
            methods=["POST"],
            response_model=Sobre,
            operation_id=h.id,
            summary=h.pregunta,
            description=" ".join(h.descripcion.split()),
            tags=[h.familia],
            responses={
                c: {"model": Problema, "content": {"application/problem+json": {}}}
                for c in (400, 401, 402, 403, 404, 429, 500, 502, 504)
            },
            openapi_extra={"security": [{"llave": []}]},
        )

    api.add_api_route(
        "/v1/fichas",
        _ruta(ficha_lugar.HERRAMIENTA, FichaEntrada),
        methods=["POST"],
        response_model=Sobre,
        operation_id=ficha_lugar.HERRAMIENTA,
        summary=ficha_lugar.PREGUNTA,
        description=ficha_lugar.DESCRIPCION,
        tags=["fichas"],
        responses={
            c: {"model": Problema, "content": {"application/problem+json": {}}}
            for c in (400, 401, 402, 403, 429, 500, 502, 504)
        },
        openapi_extra={"security": [{"llave": []}]},
    )

    api.add_api_route(
        "/v1/fichas/empresa",
        _ruta(ficha_empresa.HERRAMIENTA, FichaEmpresaEntrada),
        methods=["POST"],
        response_model=Sobre,
        operation_id=ficha_empresa.HERRAMIENTA,
        summary=ficha_empresa.PREGUNTA,
        description=ficha_empresa.DESCRIPCION,
        tags=["fichas"],
        responses={
            c: {"model": Problema, "content": {"application/problem+json": {}}}
            for c in (400, 401, 402, 403, 429, 500, 502, 504)
        },
        openapi_extra={"security": [{"llave": []}]},
    )

    @api.get(
        "/v1/uso",
        tags=["cuenta"],
        operation_id="ver_uso",
        response_model=None,
        responses={401: {"model": Problema, "content": {"application/problem+json": {}}}},
        openapi_extra={"security": [{"llave": []}]},
    )
    async def uso(request: Request) -> dict[str, Any] | JSONResponse:
        """Saldo y consumo del mes de la organización de la llave (ADR-0010)."""
        principal = getattr(request.state, "principal", None)
        if principal is None:
            return problema("no_autenticado", "falta una llave válida (Authorization: Bearer)")
        ahora = time.time()
        usados = await puerta.ESTADO.cuota.usados(principal.org) if puerta.ESTADO.cuota else 0
        limite = NIVELES.get(principal.nivel, NIVELES["con_llave"])
        return {
            "org": principal.org,
            "nivel": principal.nivel,
            "plan": principal.plan,
            "mes": mes(ahora),
            "limite": limite,
            "usados": usados,
            "disponibles": max(0, limite - usados),
            # el saldo no se acumula: el día 1 vuelve a `limite` (ADR-0029)
            "reinicia": reinicio(ahora).isoformat(),
        }

    @api.get("/salud", include_in_schema=False)
    async def salud() -> dict[str, str]:
        """Para la sonda externa del SLA: responde si la puerta está viva, sin llamar a ninguna
        fuente ni a la base (nunca carga contra servidores del Estado)."""
        return {"estado": "ok"}

    @api.get("/listo", include_in_schema=False)
    async def listo() -> JSONResponse:
        """Para el balanceador y la sonda: la puerta está lista si responden la base (llaves y
        uso) y Redis (caché y créditos). `/salud` solo dice que el proceso vive. No llama a
        ninguna fuente."""
        partes = {
            "base": puerta.ESTADO.registro,
            "redis": puerta.ESTADO.almacen,
        }
        estado: dict[str, str] = {}
        for nombre, objeto in partes.items():
            probar = getattr(objeto, "ping", None)
            if probar is None:
                estado[nombre] = "sin_configurar"
                continue
            try:
                await asyncio.wait_for(probar(), timeout=2)
                estado[nombre] = "ok"
            except Exception:  # noqa: BLE001 — cualquier falla es «no listo», con su nombre
                estado[nombre] = "falla"
        listo = all(v != "falla" for v in estado.values())
        return JSONResponse(
            {"estado": "listo" if listo else "no_listo", **estado},
            status_code=200 if listo else 503,
        )

    @api.get("/llms.txt", include_in_schema=False)
    async def llms() -> PlainTextResponse:
        return PlainTextResponse(
            llms_txt(puerta.CATALOGO), media_type="text/markdown; charset=utf-8"
        )

    @api.get("/.well-known/mcp/server-card.json", include_in_schema=False)
    async def tarjeta() -> dict[str, Any]:
        return tarjeta_mcp(puerta.CATALOGO)

    @api.get("/mcp/server-card", include_in_schema=False)
    async def tarjeta_sep(request: Request) -> Response:
        """La tarjeta estándar (SEP-2127): identidad y cómo conectarse, sin herramientas."""
        return _descubrible(request, tarjeta_estandar(), "application/mcp-server-card+json")

    @api.get("/.well-known/ai-catalog.json", include_in_schema=False)
    async def catalogo_ia(request: Request) -> Response:
        return _descubrible(request, ai_catalogo(), "application/ai-catalog+json")

    @api.get("/v1/herramientas", tags=["catálogo"], operation_id="listar_herramientas")
    async def herramientas() -> list[dict[str, Any]]:
        return [
            {
                "id": h.id,
                "familia": h.familia,
                "pregunta": h.pregunta,
                "fuente": h.fuente,
                "creditos": h.creditos,
                "ruta": f"/v1/co/{h.familia}/{h.id}",
            }
            for h in puerta.CATALOGO.herramientas.values()
        ]

    @api.get("/metrics", include_in_schema=False)
    async def metricas_prometheus() -> Response:
        """Prometheus (F7.2). Caddy no lo deja salir a internet: solo la red interna."""
        return Response(generate_latest(metricas.REGISTRO), media_type=CONTENT_TYPE_LATEST)

    @api.get("/v1/estado", tags=["catálogo"], operation_id="ver_estado")
    async def estado() -> list[dict[str, Any]]:
        """Estado por fuente según el último canario de cada herramienta (F7.1): `verde`, `rojo`
        o `sin_datos`. Público, como el catálogo."""
        ultimos = puerta.ESTADO.canarios.ultimos() if puerta.ESTADO.canarios is not None else []
        return estado_por_fuente(ultimos, puerta.CATALOGO)

    # --- alta de la llave de prueba y contacto (ADR-0034): formularios del sitio, sin JS ------

    @api.post("/v1/alta", include_in_schema=False)
    async def alta(request: Request) -> HTMLResponse:
        f = await _formulario(request)
        if f.get("web"):  # campo trampa: lo llenan los robots, no las personas
            return _pagina_enviada()
        if puerta.ESTADO.altas is None:
            return _pagina_error("Alta", "El alta automática no está disponible.", 503)
        try:
            await puerta.ESTADO.altas.solicitar(
                f.get("correo", ""),
                f.get("nombre", ""),
                f.get("organizacion", ""),
                f.get("uso", ""),
                f.get("acepto") in ("si", "on"),
                _ip(request),
            )
        except ErrorAlta as exc:
            return _pagina_error("Alta", str(exc), 400)
        return _pagina_enviada()

    @api.get("/v1/alta/confirmar", include_in_schema=False)
    async def alta_confirmar_pagina(t: str = "") -> HTMLResponse:
        """Solo muestra un botón: abrir el enlace no crea la llave (los filtros de correo abren
        los enlaces para revisarlos)."""
        cuerpo = (
            "<p>Confirma para ver tu llave. Se muestra una sola vez: cópiala y guárdala en un "
            "lugar seguro.</p>"
            '<form method="post" action="/v1/alta/confirmar">'
            f'<input type="hidden" name="t" value="{escape(t)}">'
            '<button class="s-boton" type="submit">Ver mi llave</button></form>'
        )
        return HTMLResponse(pagina_simple("Tu llave de prueba", "Alta", cuerpo))

    @api.post("/v1/alta/confirmar", include_in_schema=False)
    async def alta_confirmar(request: Request) -> HTMLResponse:
        if puerta.ESTADO.altas is None:
            return _pagina_error("Alta", "El alta automática no está disponible.", 503)
        f = await _formulario(request)
        try:
            correo, llave = await puerta.ESTADO.altas.confirmar(f.get("t", ""))
        except ErrorAlta as exc:
            return _pagina_error("Alta", str(exc), 400)
        cuerpo = (
            f"<p>Esta es la llave de <b>{escape(correo)}</b>. No la volverás a ver aquí ni te "
            "llegará por correo.</p>"
            f'<code class="s-llave">{escape(llave)}</code>'
            f"<p>Trae {NIVELES[NIVEL_ALTA]} créditos y vence en {VIGENCIA_LLAVE.days} días: sirve "
            "para probar. Para más, escríbenos y "
            "te pasamos a un plan.</p>"
            '<p><a class="enlace" href="/desarrolladores">Cómo conectarla a tu agente o tu '
            "sistema</a></p>"
        )
        return HTMLResponse(
            pagina_simple("Tu llave de prueba", "Alta", cuerpo),
            headers={"Cache-Control": "no-store"},
        )

    @api.post("/v1/contacto", include_in_schema=False)
    async def contacto(request: Request) -> HTMLResponse:
        f = await _formulario(request)
        if f.get("web"):
            return _pagina_recibido()
        if puerta.ESTADO.altas is None:
            return _pagina_error("Contacto", "El formulario no está disponible.", 503)
        try:
            await puerta.ESTADO.altas.contactar(
                f.get("nombre", ""),
                f.get("correo", ""),
                f.get("organizacion", ""),
                f.get("asunto", "otro"),
                f.get("mensaje", ""),
                f.get("acepto") in ("si", "on"),
                _ip(request),
            )
        except ErrorAlta as exc:
            return _pagina_error("Contacto", str(exc), 400)
        return _pagina_recibido()

    @api.get("/estado", include_in_schema=False)
    async def pagina_de_estado() -> HTMLResponse:
        """Página pública de estado: la puerta y cada fuente según su último canario."""
        ultimos = puerta.ESTADO.canarios.ultimos() if puerta.ESTADO.canarios is not None else []
        return HTMLResponse(
            pagina_estado(ultimos, puerta.CATALOGO, datetime.now(UTC)),
            headers={"Cache-Control": "public, max-age=60"},
        )

    @api.get("/v1/fuentes", tags=["catálogo"], operation_id="listar_fuentes")
    async def fuentes() -> list[dict[str, Any]]:
        return [resumen(puerta.CATALOGO, fid) for fid in sorted(puerta.CATALOGO.fuentes)]

    @api.get(
        "/v1/fuentes/{fuente_id}",
        tags=["catálogo"],
        operation_id="ver_fuente",
        response_model=None,
        responses={404: {"model": Problema, "content": {"application/problem+json": {}}}},
    )
    async def fuente(fuente_id: str) -> dict[str, Any] | JSONResponse:
        if fuente_id not in puerta.CATALOGO.fuentes:
            parecidos = ids_parecidos(puerta.CATALOGO, fuente_id)
            pista = f"; ¿quiso decir {', '.join(parecidos)}?" if parecidos else ""
            return problema("no_existe", f"no hay fuente {fuente_id}{pista}")
        return ficha_tecnica(puerta.CATALOGO, fuente_id)

    def openapi() -> dict[str, Any]:
        if api.openapi_schema is None:
            esquema = get_openapi(
                title=api.title, version=api.version, description=api.description, routes=api.routes
            )
            esquema.setdefault("components", {})["securitySchemes"] = {
                "llave": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "rt_live_… o rt_test_…",
                }
            }
            api.openapi_schema = esquema
        return api.openapi_schema

    api.openapi = openapi  # type: ignore[method-assign]
    return api


def _descubrible(request: Request, cuerpo: dict[str, Any], tipo: str) -> Response:
    """Un documento de descubrimiento con lo que pide la SEP-2127: su tipo, CORS abierto para GET,
    caché de una hora y ETag (304 si no cambió)."""
    texto = json.dumps(cuerpo, ensure_ascii=False, separators=(",", ":"))
    etiqueta = '"' + hashlib.sha256(texto.encode()).hexdigest()[:32] + '"'
    cabeceras = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET",
        "Access-Control-Allow-Headers": "Content-Type, If-None-Match",
        "Access-Control-Expose-Headers": "ETag",
        "Cache-Control": "public, max-age=3600",
        "ETag": etiqueta,
    }
    if request.headers.get("if-none-match") == etiqueta:
        return Response(status_code=304, headers=cabeceras)
    return Response(texto, media_type=tipo, headers=cabeceras)


async def _formulario(request: Request) -> dict[str, str]:
    """Un formulario `application/x-www-form-urlencoded` (sin depender de python-multipart), con
    tope de tamaño: nunca pasa de unos KB."""
    cuerpo = await request.body()
    if len(cuerpo) > 20_000:
        return {}
    pares = parse_qs(cuerpo.decode("utf-8", errors="replace"), keep_blank_values=True)
    return {k: v[0] for k, v in pares.items() if v}


def _ip(request: Request) -> str:
    """La IP de quien llama: Caddy la pone primera en X-Forwarded-For. Solo se usa su HMAC."""
    reenviada = request.headers.get("x-forwarded-for", "")
    if reenviada:
        return reenviada.split(",")[0].strip()
    return request.client.host if request.client else "desconocida"


def _pagina_error(rotulo: str, mensaje: str, estado: int) -> HTMLResponse:
    cuerpo = (
        f'<p class="s-error">{escape(mensaje)}</p>'
        '<p><a class="enlace" href="javascript:history.back()">Volver</a></p>'
    )
    return HTMLResponse(pagina_simple("No se pudo", rotulo, cuerpo), status_code=estado)


def _pagina_enviada() -> HTMLResponse:
    cuerpo = (
        "<p>Si el correo es válido, te llegará en unos minutos un enlace para recibir tu llave. "
        "Vence en 24 horas. Revisa también el correo no deseado.</p>"
    )
    return HTMLResponse(pagina_simple("Revisa tu correo", "Alta", cuerpo))


def _pagina_recibido() -> HTMLResponse:
    cuerpo = "<p>Recibimos tu mensaje. Te respondemos al correo que dejaste.</p>"
    return HTMLResponse(pagina_simple("Mensaje recibido", "Contacto", cuerpo))


def _cabeceras_tasa(cuota: Any, quedan: int, espera: float) -> list[tuple[bytes, bytes]]:
    """Cabeceras RateLimit (draft IETF): política y lo que queda."""
    por_minuto = round(cuota.ritmo * 60)
    return [
        (
            b"ratelimit-policy",
            f'"rafaga";q={cuota.capacidad};w=60, "minuto";q={por_minuto};w=60'.encode(),
        ),
        (b"ratelimit", f'"rafaga";r={quedan};t={math.ceil(espera)}'.encode()),
    ]


def _con_cabeceras(send: Any, extra: list[tuple[bytes, bytes]]) -> Any:
    async def enviar(mensaje: dict[str, Any]) -> None:
        if mensaje["type"] == "http.response.start":
            mensaje = {**mensaje, "headers": [*mensaje.get("headers", []), *extra]}
        await send(mensaje)

    return enviar


# Un mensaje MCP es pequeño; uno más grande se cobra sin leerlo entero (por precaución).
_MAX_CUERPO_MCP = 1_000_000
# La entrada de una herramienta REST es un JSON diminuto (un punto, un código). Un cuerpo mayor es
# un error o un abuso: se corta antes de agotar la memoria (DoS) y se rechaza (ver `__call__`).
_MAX_CUERPO_REST = 256_000


async def _leer_cuerpo(receive: Any, tope: int = _MAX_CUERPO_MCP) -> tuple[bytes, Any]:
    """El cuerpo de la petición y un `receive` que lo vuelve a entregar intacto a quien siga.

    Deja de acumular en cuanto se pasa de `tope` (aunque falten trozos): así un cuerpo enorme no
    agota la memoria. Si `len(cuerpo) > tope`, el llamador sabe que se truncó."""
    partes: list[bytes] = []
    tamano = 0
    while True:
        mensaje = await receive()
        if mensaje["type"] != "http.request":
            break
        partes.append(mensaje.get("body", b""))
        tamano += len(partes[-1])
        if not mensaje.get("more_body") or tamano > tope:
            break
    cuerpo = b"".join(partes)
    entregado = False

    async def otra_vez() -> Any:
        nonlocal entregado
        if not entregado:
            entregado = True
            return {"type": "http.request", "body": cuerpo, "more_body": False}
        return await receive()

    return cuerpo, otra_vez


def _consulta_mcp(cuerpo: bytes) -> bool:
    """¿El mensaje MCP consulta una herramienta (`tools/call`)? Abrir la sesión, listar las
    herramientas o un ping no tocan ninguna fuente y no gastan cuota: un cliente que abre cuatro
    perfiles se quedaba sin cupo antes de preguntar nada (F6, GEO Copilot). Lo ilegible se cobra."""
    if len(cuerpo) > _MAX_CUERPO_MCP:
        return True
    try:
        mensaje = json.loads(cuerpo)
    except ValueError:
        return True
    mensajes = mensaje if isinstance(mensaje, list) else [mensaje]
    return any(not isinstance(m, dict) or m.get("method") == "tools/call" for m in mensajes)


class Aplicacion:
    """Reparte por ruta: las de MCP a su servidor; el resto, a la API. Un solo arranque."""

    def __init__(self, api: FastAPI, mcp: dict[str, Any]) -> None:
        self.api = api
        self.mcp = mcp  # ruta exacta → app ASGI de FastMCP

    async def __call__(self, scope: Scope, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await self._ciclo(receive, send)
            return
        if scope["type"] != "http":
            await self._atender(scope, receive, send)
            return
        # Lo que falle fuera de FastAPI (llave, tasa o créditos con Redis o Postgres caídos) sale
        # como problem+json `error_interno`, nunca como un 500 en texto plano (ADR-0011).
        iniciada = False

        async def enviar(mensaje: dict[str, Any]) -> None:
            nonlocal iniciada
            if mensaje["type"] == "http.response.start":
                iniciada = True
            await send(mensaje)

        try:
            await self._atender(scope, receive, enviar)
        except Exception:
            logger.exception("error interno en %s", scope.get("path"))
            metricas.ERRORES_INTERNOS.inc()
            if iniciada:
                raise
            await problema("error_interno", "error interno")(scope, receive, send)

    async def _atender(self, scope: Scope, receive: Any, send: Any) -> None:
        ruta = scope.get("path", "").rstrip("/") or "/"
        app = self.mcp.get(ruta, self.api)
        protegida = ruta.startswith(("/v1/co/", "/v1/fichas")) or ruta == "/v1/uso"
        if scope["type"] == "http" and (app is not self.api or protegida):
            # REST de herramientas y MCP piden llave; el catálogo público, no (ADR-0009)
            if puerta.ESTADO.registro is not None:
                cabeceras = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
                llave = bearer(cabeceras.get("authorization"))
                principal = (
                    await asyncio.to_thread(puerta.ESTADO.registro.verificar, llave)
                    if llave
                    else None
                )
                if principal is None:
                    await problema(
                        "no_autenticado", "falta una llave válida (Authorization: Bearer)"
                    )(scope, receive, send)
                    return
                scope.setdefault("state", {})["principal"] = principal
                cobrar = True
                if app is not self.api:
                    cuerpo, receive = await _leer_cuerpo(receive)
                    cobrar = scope.get("method") == "POST" and _consulta_mcp(cuerpo)
                elif scope.get("method") == "POST":
                    cuerpo, receive = await _leer_cuerpo(receive, tope=_MAX_CUERPO_REST)
                    if len(cuerpo) > _MAX_CUERPO_REST:
                        await problema(
                            "parametro_invalido",
                            "el cuerpo de la petición es demasiado grande",
                            param="body",
                        )(scope, receive, send)
                        return
                if puerta.ESTADO.cuota is not None and cobrar:
                    permitido, quedan, espera = await puerta.ESTADO.cuota.tomar_ficha(
                        principal.llave_id
                    )
                    tasa = _cabeceras_tasa(puerta.ESTADO.cuota, quedan, espera)
                    if not permitido:
                        await problema(
                            "limite_tasa",
                            "demasiadas consultas seguidas con esta llave",
                            reintentar=max(1, math.ceil(espera)),
                        )(scope, receive, _con_cabeceras(send, tasa))
                        return
                    send = _con_cabeceras(send, tasa)
        await app(scope, receive, send)

    async def _ciclo(self, receive: Any, send: Any) -> None:
        pila = AsyncExitStack()
        mensaje = await receive()
        if mensaje["type"] == "lifespan.startup":
            try:
                await puerta.iniciar()
                for app in self.mcp.values():
                    await pila.enter_async_context(app.router.lifespan_context(app))
            except Exception as exc:  # noqa: BLE001 — el servidor debe saber que no arrancó
                await send({"type": "lifespan.startup.failed", "message": str(exc)})
                return
            await send({"type": "lifespan.startup.complete"})
        mensaje = await receive()
        if mensaje["type"] == "lifespan.shutdown":
            await pila.aclose()
            await puerta.detener()
            await send({"type": "lifespan.shutdown.complete"})


# Sin estado: cada petición MCP se basta sola. Caddy reparte entre dos réplicas sin afinidad, y
# una sesión solo funcionaría si todas sus peticiones cayeran en la réplica que la abrió. La puerta
# solo lee: no hay nada que guardar entre peticiones.
OPCIONES_MCP: dict[str, Any] = {"stateless_http": True}


def crear_aplicacion() -> Aplicacion:
    mcp = {"/mcp": puerta.crear_servidor(con_ciclo=False).http_app(path="/mcp", **OPCIONES_MCP)}
    for familia in puerta.FAMILIAS:
        ruta = f"/mcp/{familia}"
        servidor = puerta.crear_servidor(familia, con_ciclo=False)
        mcp[ruta] = servidor.http_app(path=ruta, **OPCIONES_MCP)
    ruta = f"/mcp/{puerta.PERFIL_CATALOGO}"
    mcp[ruta] = puerta.crear_servidor_catalogo(con_ciclo=False).http_app(path=ruta, **OPCIONES_MCP)
    return Aplicacion(crear_api(), mcp)


app = crear_aplicacion()


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("TERRANOVA_HOST", "127.0.0.1"),
        port=int(os.environ.get("TERRANOVA_PUERTO", "8100")),
    )
