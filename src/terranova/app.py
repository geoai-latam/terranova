"""La puerta completa: REST `/v1` y MCP (`/mcp` y un perfil por familia) en una sola aplicación.

Los dos adaptadores salen del mismo catálogo y llaman a la misma función (ADR-0004): misma entrada,
mismo sobre `rt/1`, mismos errores (RFC 9457 en REST, `isError` en MCP, ADR-0011).
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import AsyncExitStack
from typing import Annotated, Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, create_model

from terranova import puerta
from terranova.catalogo import PATRONES_ENTRADA, Herramienta
from terranova.contrato import HTTP_DE, Problema, Sobre, nueva_solicitud_id
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.identidad import bearer

Scope = MutableMapping[str, Any]

TITULOS = {
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
    return create_model(nombre, __config__=ConfigDict(extra="forbid"), **campos)


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


def _ruta(h: Herramienta) -> Callable[..., Awaitable[Any]]:
    Entrada = modelo_entrada(h)

    async def herramienta(entrada: Entrada, request: Request) -> Any:  # type: ignore[valid-type]
        try:
            principal = getattr(request.state, "principal", None)
            return await puerta.ejecutar(h.id, entrada.model_dump(), principal)  # type: ignore[attr-defined]
        except ErrorEntrada as exc:
            return problema("parametro_invalido", str(exc), param=exc.param)
        except ErrorEjecucion as exc:
            return problema(exc.codigo, str(exc), reintentar=exc.reintentar_en_s)

    # el modelo se crea en tiempo de ejecución: la anotación debe ser el tipo, no su nombre
    herramienta.__annotations__ = {"entrada": Entrada, "request": Request, "return": Any}
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

    @api.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
        primero = exc.errors()[0] if exc.errors() else {}
        ruta = [str(x) for x in primero.get("loc", []) if x != "body"]
        return problema(
            "parametro_invalido",
            str(primero.get("msg", "entrada inválida")),
            param=".".join(ruta) or None,
        )

    for h in puerta.CATALOGO.herramientas.values():
        api.add_api_route(
            f"/v1/co/{h.familia}/{h.id}",
            _ruta(h),
            methods=["POST"],
            response_model=Sobre,
            operation_id=h.id,
            summary=h.pregunta,
            description=" ".join(h.descripcion.split()),
            tags=[h.familia],
            responses={
                c: {"model": Problema, "content": {"application/problem+json": {}}}
                for c in (400, 403, 404, 429, 500, 502, 504)
            },
        )

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

    @api.get("/v1/fuentes", tags=["catálogo"], operation_id="listar_fuentes")
    async def fuentes() -> list[dict[str, Any]]:
        return [_publica(fid) for fid in sorted(puerta.CATALOGO.fuentes)]

    @api.get(
        "/v1/fuentes/{fuente_id}", tags=["catálogo"], operation_id="ver_fuente", response_model=None
    )
    async def fuente(fuente_id: str) -> dict[str, Any] | JSONResponse:
        if fuente_id not in puerta.CATALOGO.fuentes:
            return problema("no_existe", f"no hay fuente {fuente_id}")
        return _publica(fuente_id)

    return api


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
        if scope["type"] == "http" and (app is not self.api or ruta.startswith("/v1/co/")):
            # REST de herramientas y MCP piden llave; el catálogo público, no (ADR-0009)
            if puerta.registro is not None:
                cabeceras = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
                llave = bearer(cabeceras.get("authorization"))
                principal = puerta.registro.verificar(llave) if llave else None
                if principal is None:
                    await problema(
                        "no_autenticado", "falta una llave válida (Authorization: Bearer)"
                    )(scope, receive, send)
                    return
                scope.setdefault("state", {})["principal"] = principal
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
