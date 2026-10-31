"""Distribución MCP (auditoría C13): `server.json` del registro oficial, la tarjeta estándar
(SEP-2127) y el catálogo de IA dicen lo mismo, con los límites del registro."""

import json
import re
from pathlib import Path

import httpx
import pytest

from terranova.app import crear_api
from terranova.descripcion import ai_catalogo, tarjeta_estandar

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_server_json_coincide_con_la_tarjeta() -> None:
    s = json.loads((RAIZ / "server.json").read_text(encoding="utf-8"))
    t = tarjeta_estandar()
    for campo in ("name", "title", "description", "version", "websiteUrl", "icons"):
        assert s[campo] == t[campo], campo
    assert re.fullmatch(r"[a-zA-Z0-9.-]+/[a-zA-Z0-9._-]+", s["name"])
    assert s["name"].startswith("com.terrnova/")  # espacio de nombres verificado por DNS
    assert 1 <= len(s["description"]) <= 100 and 1 <= len(s["title"]) <= 100
    (remoto,) = s["remotes"]
    assert remoto["type"] == "streamable-http" and remoto["url"] == t["remotes"][0]["url"]
    (cabecera,) = remoto["headers"]
    assert cabecera["name"] == "Authorization" and cabecera["isSecret"] and cabecera["isRequired"]
    assert "tools" not in t  # SEP-2127: la tarjeta no lista herramientas


@pytest.mark.anyio
async def test_tarjeta_y_catalogo_se_sirven_como_pide_la_sep() -> None:
    transporte = httpx.ASGITransport(app=crear_api())
    async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
        r = await c.get("/mcp/server-card")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/mcp-server-card+json")
        assert r.headers["access-control-allow-origin"] == "*"
        assert r.headers["cache-control"] == "public, max-age=3600"
        assert r.json() == tarjeta_estandar()
        igual = await c.get("/mcp/server-card", headers={"If-None-Match": r.headers["etag"]})
        assert igual.status_code == 304
        cat = await c.get("/.well-known/ai-catalog.json")
        assert cat.headers["content-type"].startswith("application/ai-catalog+json")
        assert cat.json() == ai_catalogo()
        assert cat.json()["entries"][0]["url"].endswith("/mcp/server-card")
