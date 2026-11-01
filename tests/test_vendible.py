"""Lo que se anuncia y lo que ve una llave de producción es lo vendible (ADR-0007, enmienda del
2026-11-01): fuentes publicadas con uso comercial. Una llave de evaluación (`rt_test_`) ve además
lo que está por verificar, sin uso comercial o en borrador. El sitio cuenta lo mismo."""

from __future__ import annotations

import json
import re
import runpy
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from terranova import puerta
from terranova.app import Aplicacion, crear_api, crear_aplicacion
from terranova.catalogo import catalogo_vendible, vendible
from terranova.compuestas import COMPUESTAS
from terranova.identidad import RegistroSqlite

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = puerta.CATALOGO
NO_VENDIBLES = set(CATALOGO.herramientas) - set(puerta.VENDIBLE.herramientas)
SIEMPRE = {c.herramienta for c in COMPUESTAS.values()} | {"fuente_describir"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_lo_vendible_es_publicado_y_con_uso_comercial() -> None:
    assert puerta.VENDIBLE.herramientas, "el catálogo vendible no puede quedar vacío"
    for h in puerta.VENDIBLE.herramientas.values():
        f = CATALOGO.fuentes[h.fuente]
        assert f.estado == "publicada" and f.uso_comercial == "si", h.id
    for hid in NO_VENDIBLES:
        assert not vendible(CATALOGO.fuentes[CATALOGO.herramientas[hid].fuente]), hid
    # los dos casos que encontró la auditoría del sitio (2026-11-01)
    assert {"dian_usuario_aduanero_por_nit", "catalogo_buscar"} <= NO_VENDIBLES


def test_el_sitio_cuenta_lo_mismo_que_anuncia_la_puerta() -> None:
    """`web/construir.py` saca sus conteos con su propio filtro: deben ser los de la puerta."""
    sitio = runpy.run_path(str(RAIZ / "web" / "construir.py"))  # sin __main__: no escribe nada
    assert {h.id for h in sitio["HERR"]} == set(puerta.VENDIBLE.herramientas)
    assert sitio["N_HERR"] == len(puerta.VENDIBLE.herramientas)
    assert sitio["N_FUENTES"] == len(puerta.VENDIBLE.fuentes)


def test_las_fichas_anunciadas_solo_usan_fuentes_vendibles() -> None:
    """Las fichas se listan a toda llave: sus partes no pueden depender de lo no vendible."""
    from terranova import ficha, ficha_empresa

    for hid in ficha.HERRAMIENTAS | {p.herramienta for p in ficha_empresa.PARTES}:
        assert vendible(CATALOGO.fuentes[CATALOGO.herramientas[hid].fuente]), hid


def test_documentos_generados_solo_anuncian_lo_vendible() -> None:
    md = (RAIZ / "docs" / "HERRAMIENTAS.md").read_text(encoding="utf-8")
    for hid in NO_VENDIBLES:
        assert f"`{hid}`" not in md, hid
    assert catalogo_vendible(CATALOGO).herramientas.keys() == puerta.VENDIBLE.herramientas.keys()


# --- la aplicación con identidad: /mcp y /v1 según la llave ---------------------------------


def _herramientas_de(r: httpx.Response) -> set[str]:
    """Nombres de `tools/list` en una respuesta JSON o SSE de streamable HTTP."""
    assert r.status_code == 200, r.text
    cuerpo = r.text
    if r.headers.get("content-type", "").startswith("text/event-stream"):
        datos = [linea[5:].strip() for linea in cuerpo.splitlines() if linea.startswith("data:")]
        cuerpo = datos[-1]
    return {t["name"] for t in json.loads(cuerpo)["result"]["tools"]}


@pytest.fixture
async def app_con_llaves() -> AsyncIterator[tuple[httpx.AsyncClient, str, str]]:
    registro = RegistroSqlite(":memory:", "p" * 40)
    viva = registro.crear("acme", {"*"}, prueba=False, expira=None)
    prueba = registro.crear("interna", {"*"}, prueba=True, expira=None)
    puerta.ESTADO.registro = registro
    puerta.usar_conectores({})  # nada llega a una fuente: la compuerta corta antes
    aplicacion = crear_aplicacion()
    try:
        # sin el ciclo de la aplicación (conectores, Redis…): solo el de los servidores MCP
        async with contextos(aplicacion):
            transporte = httpx.ASGITransport(app=aplicacion)
            async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
                yield c, viva, prueba
    finally:
        puerta.ESTADO.registro = None
        puerta.usar_conectores(None)


class contextos:
    def __init__(self, aplicacion: Aplicacion) -> None:
        self.apps = list(aplicacion.mcp.values())
        self.abiertos: list[Any] = []

    async def __aenter__(self) -> None:
        for app in self.apps:
            ctx = app.router.lifespan_context(app)
            await ctx.__aenter__()
            self.abiertos.append(ctx)

    async def __aexit__(self, *exc: object) -> None:
        for ctx in reversed(self.abiertos):
            await ctx.__aexit__(None, None, None)


async def _listar(c: httpx.AsyncClient, ruta: str, llave: str) -> set[str]:
    r = await c.post(
        ruta,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        headers={
            "Authorization": f"Bearer {llave}",
            "Accept": "application/json, text/event-stream",
        },
    )
    return _herramientas_de(r)


@pytest.mark.anyio
async def test_mcp_a_una_llave_de_produccion_solo_lista_lo_vendible(
    app_con_llaves: tuple[httpx.AsyncClient, str, str],
) -> None:
    c, viva, prueba = app_con_llaves
    vistas = await _listar(c, "/mcp", viva)
    assert vistas == set(puerta.VENDIBLE.herramientas) | SIEMPRE
    assert not vistas & NO_VENDIBLES
    # los perfiles por familia, igual (la DIAN es de «empresas»; catalogo_buscar, de «meta»)
    for hid in NO_VENDIBLES:
        familia = CATALOGO.herramientas[hid].familia
        assert hid not in await _listar(c, f"/mcp/{familia}", viva), (familia, hid)
    # una llave de evaluación ve todo el catálogo (ADR-0007)
    assert await _listar(c, "/mcp", prueba) == set(CATALOGO.herramientas) | SIEMPRE


@pytest.mark.anyio
async def test_rest_a_una_llave_de_produccion_niega_lo_no_vendible(
    app_con_llaves: tuple[httpx.AsyncClient, str, str],
) -> None:
    c, viva, _ = app_con_llaves
    h = CATALOGO.herramientas["dian_usuario_aduanero_por_nit"]
    r = await c.post(
        f"/v1/co/{h.familia}/{h.id}",
        json=h.canario.entrada,
        headers={"Authorization": f"Bearer {viva}"},
    )
    assert r.status_code == 403 and r.json()["code"] == "licencia_no_habilitada", r.text
    # y el catálogo público no la anuncia
    publicas = {x["id"] for x in (await c.get("/v1/herramientas")).json()}
    assert publicas == set(puerta.VENDIBLE.herramientas)
    assert not publicas & NO_VENDIBLES
    fuentes = {x["id"] for x in (await c.get("/v1/fuentes")).json()}
    assert fuentes == set(puerta.VENDIBLE.fuentes)
    llms = (await c.get("/llms.txt")).text
    assert not any(f"/{hid})" in llms for hid in NO_VENDIBLES)
    tarjeta = (await c.get("/.well-known/mcp/server-card.json")).json()
    assert not {t["name"] for t in tarjeta["tools"]} & NO_VENDIBLES


def test_buscar_herramienta_no_ofrece_lo_no_vendible(monkeypatch: pytest.MonkeyPatch) -> None:
    """`/mcp/catalogo`: la búsqueda tampoco ofrece a una llave de producción lo que no usa."""
    pregunta = "habilitaciones aduaneras de una empresa ante la DIAN por NIT"
    monkeypatch.delenv("TERRANOVA_PLAN", raising=False)
    normal = {h["herramienta"] for h in puerta.buscar_herramienta(pregunta)["herramientas"]}
    assert "dian_usuario_aduanero_por_nit" not in normal
    monkeypatch.setenv("TERRANOVA_PLAN", "evaluacion")
    evaluacion = {h["herramienta"] for h in puerta.buscar_herramienta(pregunta)["herramientas"]}
    assert "dian_usuario_aduanero_por_nit" in evaluacion


# --- Caddy: las rutas de la puerta van a la puerta; lo demás es del sitio ---------------------


def _patrones(caddy: str, matcher: str) -> list[str]:
    linea = re.search(rf"^@{matcher} path (.+)$", caddy, re.M)
    assert linea, f"falta @{matcher} en el Caddyfile"
    return linea.group(1).split()


def _casa(ruta: str, patrones: list[str]) -> bool:
    return any(ruta.startswith(p[:-1]) if p.endswith("*") else ruta == p for p in patrones)


def test_caddy_lleva_a_la_puerta_todas_sus_rutas_y_nada_mas() -> None:
    caddy = (RAIZ / "docker" / "Caddyfile").read_text(encoding="utf-8")
    puerta_ = _patrones(caddy, "puerta")
    rutas = {getattr(r, "path", "") for r in crear_api().routes} | set(crear_aplicacion().mcp)
    rutas.discard("")
    for ruta in sorted(rutas):
        if ruta == "/metrics":  # de la red interna: por el borde es la 404 del sitio
            assert not _casa(ruta, puerta_)
            continue
        assert _casa(ruta, puerta_), f"{ruta} no está en @puerta del Caddyfile"
    for pagina in _patrones(caddy, "sitio"):
        assert not _casa(pagina.rstrip("*"), puerta_), pagina
    assert "handle_errors 404" in caddy and "rewrite * /404.html" in caddy
