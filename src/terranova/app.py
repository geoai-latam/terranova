"""La puerta completa: REST `/v1` y MCP (`/mcp` y un perfil por familia) en una sola aplicación.

Los dos adaptadores salen del mismo catálogo y llaman a la misma función (ADR-0004): misma entrada,
mismo sobre `rt/1`, mismos errores (RFC 9457 en REST, `isError` en MCP, ADR-0011).
"""

from __future__ import annotations

import asyncio
import math
import os
import time
from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack
from typing import Annotated, Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator
from pydantic.json_schema import SkipJsonSchema
from starlette.exceptions import HTTPException as StarletteHTTPException

from terranova import ficha as ficha_lugar
from terranova import puerta
from terranova.catalogo import PATRONES_ENTRADA, Herramienta
from terranova.contrato import HTTP_DE, Problema, Sobre, nueva_solicitud_id
from terranova.cuota import NIVELES, mes
from terranova.descripcion import llms_txt, tarjeta_mcp
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.identidad import bearer
from terranova.vigilancia import estado_por_fuente

Scope = MutableMapping[str, Any]

TITULOS = {
    "limite_tasa": "Demasiadas consultas seguidas",
    "saldo_agotado": "Créditos del mes agotados",
    "no_autenticado": "Falta una llave válida",
    "sin_permiso": "La llave no tiene permiso para esta familia",
    "parametro_invalido": "Parámetro inválido",
    "licencia_no_habilitada": "Licencia no habilitada para esta llave",
    "no_existe": "No existe",
    "fuente_no_disponible": "La fuente no está disponible",
    "fuente_lenta": "La fuente no respondió a tiempo",
    "fuente_respuesta_invalida": "La fuente respondió algo inválido",
    "error_interno": "Error interno",
}


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
        return Annotated[str, Field(pattern=PATRONES_ENTRADA[tipo])]
    return Annotated[str, Field(max_length=200)]


def modelo_entrada(h: Herramienta) -> type[BaseModel]:
    campos: dict[str, Any] = {n: (_tipo(n, t), ...) for n, t in h.entrada.items()}
    nombre = "".join(p.capitalize() for p in h.id.split("_")) + "Entrada"
    # estricto: `false` no es 0.0 ni "1" es 1 (Schemathesis, F3.5)
    return create_model(nombre, __config__=ConfigDict(extra="forbid", strict=True), **campos)


def problema(
    codigo: str, detalle: str, *, param: str | None = None, reintentar: int | None = None
) -> JSONResponse:
    p = Problema(
        title=TITULOS.get(codigo, codigo),
        status=HTTP_DE[codigo],
        code=codigo,  # type: ignore[arg-type]
        detail=detalle[:500],
        param=param,
        reintentar_en_s=reintentar,
        solicitud_id=nueva_solicitud_id(),
    )
    cabeceras = {"Retry-After": str(reintentar)} if reintentar else None
    return JSONResponse(
        p.model_dump(mode="json", exclude_none=True),
        status_code=p.status,
        media_type="application/problem+json",
        headers=cabeceras,
    )


class FichaEntrada(BaseModel):
    """Un punto (`lon`, `lat`) o un número predial (`codigo`), no los dos."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={"oneOf": ficha_lugar.ESQUEMA_ENTRADA["oneOf"]},
    )
    # sin `null` en el esquema: un campo ausente se omite, no se manda vacío (Schemathesis)
    lon: Annotated[float, Field(ge=-180, le=180)] | SkipJsonSchema[None] = None
    lat: Annotated[float, Field(ge=-90, le=90)] | SkipJsonSchema[None] = None
    codigo: (
        Annotated[str, Field(pattern=PATRONES_ENTRADA["codigo_predial"])] | SkipJsonSchema[None]
    ) = None

    @model_validator(mode="before")
    @classmethod
    def _sin_nulos(cls, datos: Any) -> Any:
        if isinstance(datos, dict) and (nulos := [k for k, v in datos.items() if v is None]):
            raise ValueError(f"{', '.join(nulos)}: se omite, no se manda null")
        return datos


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
        title="Terranova",
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
                for c in (400, 401, 403, 404, 429, 500, 502, 504)
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
            for c in (400, 401, 403, 429, 500, 502, 504)
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
        usados = await puerta.cuota.usados(principal.org) if puerta.cuota else 0
        limite = NIVELES.get(principal.nivel, NIVELES["con_llave"])
        return {
            "org": principal.org,
            "nivel": principal.nivel,
            "plan": principal.plan,
            "mes": mes(time.time()),
            "limite": limite,
            "usados": usados,
            "disponibles": max(0, limite - usados),
        }

    @api.get("/llms.txt", include_in_schema=False)
    async def llms() -> PlainTextResponse:
        return PlainTextResponse(
            llms_txt(puerta.CATALOGO), media_type="text/markdown; charset=utf-8"
        )

    @api.get("/.well-known/mcp/server-card.json", include_in_schema=False)
    async def tarjeta() -> dict[str, Any]:
        return tarjeta_mcp(puerta.CATALOGO)

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

    def _publica(fid: str) -> dict[str, Any]:
        f = puerta.CATALOGO.fuentes[fid]
        return {
            "id": f.id,
            "titulo": f.titulo,
            "entidad": f.entidad,
            "licencia": {
                "spdx": f.licencia.spdx,
                "url": f.licencia.url,
                "verificada": f.licencia.verificada,
            },
            "uso_comercial": f.uso_comercial,
            "atribucion": f.atribucion,
            "cobertura": f.cobertura.model_dump(),
            "modo": f.modo,
            "estado": f.estado,
        }

    @api.get("/v1/estado", tags=["catálogo"], operation_id="ver_estado")
    async def estado() -> list[dict[str, Any]]:
        """Estado por fuente según el último canario de cada herramienta (F7.1): `verde`, `rojo`
        o `sin_datos`. Público, como el catálogo."""
        ultimos = puerta.canarios.ultimos() if puerta.canarios is not None else []
        return estado_por_fuente(ultimos, puerta.CATALOGO)

    @api.get("/v1/fuentes", tags=["catálogo"], operation_id="listar_fuentes")
    async def fuentes() -> list[dict[str, Any]]:
        return [_publica(fid) for fid in sorted(puerta.CATALOGO.fuentes)]

    @api.get(
        "/v1/fuentes/{fuente_id}",
        tags=["catálogo"],
        operation_id="ver_fuente",
        response_model=None,
        responses={404: {"model": Problema, "content": {"application/problem+json": {}}}},
    )
    async def fuente(fuente_id: str) -> dict[str, Any] | JSONResponse:
        if fuente_id not in puerta.CATALOGO.fuentes:
            return problema("no_existe", f"no hay fuente {fuente_id}")
        return _publica(fuente_id)

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


class Aplicacion:
    """Reparte por ruta: las de MCP a su servidor; el resto, a la API. Un solo arranque."""

    def __init__(self, api: FastAPI, mcp: dict[str, Any]) -> None:
        self.api = api
        self.mcp = mcp  # ruta exacta → app ASGI de FastMCP

    async def __call__(self, scope: Scope, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await self._ciclo(receive, send)
            return
        ruta = scope.get("path", "").rstrip("/") or "/"
        app = self.mcp.get(ruta, self.api)
        protegida = ruta.startswith("/v1/co/") or ruta in ("/v1/uso", "/v1/fichas")
        if scope["type"] == "http" and (app is not self.api or protegida):
            # REST de herramientas y MCP piden llave; el catálogo público, no (ADR-0009)
            if puerta.registro is not None:
                cabeceras = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
                llave = bearer(cabeceras.get("authorization"))
                principal = (
                    await asyncio.to_thread(puerta.registro.verificar, llave) if llave else None
                )
                if principal is None:
                    await problema(
                        "no_autenticado", "falta una llave válida (Authorization: Bearer)"
                    )(scope, receive, send)
                    return
                scope.setdefault("state", {})["principal"] = principal
                if puerta.cuota is not None:
                    permitido, quedan, espera = await puerta.cuota.tomar_ficha(principal.llave_id)
                    tasa = _cabeceras_tasa(puerta.cuota, quedan, espera)
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


def crear_aplicacion() -> Aplicacion:
    mcp = {"/mcp": puerta.crear_servidor(con_ciclo=False).http_app(path="/mcp")}
    for familia in puerta.FAMILIAS:
        ruta = f"/mcp/{familia}"
        mcp[ruta] = puerta.crear_servidor(familia, con_ciclo=False).http_app(path=ruta)
    return Aplicacion(crear_api(), mcp)


app = crear_aplicacion()


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("TERRANOVA_HOST", "127.0.0.1"),
        port=int(os.environ.get("TERRANOVA_PUERTO", "8100")),
    )
