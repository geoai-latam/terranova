"""Descripción de la puerta para personas y agentes (F3.6), generada del catálogo.

- `llms_txt()`: `/llms.txt` (formato llmstxt.org).
- `tarjeta_mcp()`: `/.well-known/mcp/server-card.json` (formato propio, con perfiles y
  herramientas).
- `tarjeta_estandar()`: `/mcp/server-card` (SEP-2127, sin herramientas) y `ai_catalogo()`:
  `/.well-known/ai-catalog.json`. Los mismos datos que `server.json` del registro oficial de MCP.
- `herramientas_md()`: `docs/HERRAMIENTAS.md`, versionado y comprobado en CI.
"""

from __future__ import annotations

from typing import Any

from terranova import __version__
from terranova import ficha as ficha_lugar
from terranova.catalogo import Catalogo, Fuente, Herramienta

FUENTE_DESCRIBIR = "fuente_describir"
DESCRIBIR = (
    "qué años cubre la fuente, si es geográfica (geometría, CRS, extensión, capas), qué significa "
    "cada campo, qué es una fila, cuándo se actualizó y sus alertas. Sale del catálogo: no gasta "
    "créditos (spec 08)."
)
PROTOCOLOS = ["2026-07-28", "2025-11-25"]


def _licencia(f: Fuente) -> str:
    return f.licencia.spdx or "por verificar"


def _familias(c: Catalogo) -> dict[str, list[Herramienta]]:
    familias: dict[str, list[Herramienta]] = {}
    for h in sorted(c.herramientas.values(), key=lambda x: (x.familia, x.id)):
        familias.setdefault(h.familia, []).append(h)
    return familias


def llms_txt(c: Catalogo) -> str:
    lineas = [
        "# Terrnova",
        "",
        "> Puerta única sobre fuentes oficiales colombianas y globales, con un plan gratis y "
        "planes de pago por créditos (ADR-0029). Cada respuesta es un sobre rt/1 con "
        "procedencia, licencia, completitud y `servido_desde`.",
        "",
        "Acceso: `Authorization: Bearer <llave>` (rt_live_… o rt_test_…).",
        "MCP por streamable HTTP en `/mcp` (todo) o `/mcp/<familia>`; REST en "
        "`POST /v1/co/<familia>/<herramienta>`, con el mismo sobre.",
        "Estados: `encontrado`, `no_encontrado`, `fuera_de_cobertura` (no descuenta), `parcial`. "
        "Errores en problem+json con un código estable (p. ej. `fuente_no_disponible`).",
        "Catálogo público en `/v1/fuentes`. Saldo del mes en `GET /v1/uso`; sin saldo, 402 "
        "`saldo_agotado`. Estado de las fuentes en `/estado`.",
        "",
        "## Ficha técnica de una fuente",
        "",
        f"- [{FUENTE_DESCRIBIR}](/v1/fuentes): {DESCRIBIR}",
        "",
        "## Ficha de un lugar",
        "",
        f"- [{ficha_lugar.HERRAMIENTA}](/v1/fichas): {ficha_lugar.DESCRIPCION} "
        f"Hasta {ficha_lugar.TOPE_CREDITOS} créditos (la suma de las partes).",
        "",
    ]
    for familia, hs in _familias(c).items():
        lineas.append(f"## {familia}")
        lineas.append("")
        for h in hs:
            f = c.fuentes[h.fuente]
            lineas.append(
                f"- [{h.id}](/v1/co/{familia}/{h.id}): {h.pregunta} "
                f"Fuente: {f.entidad}; licencia: {_licencia(f)}; {h.creditos} créditos."
            )
        lineas.append("")
    lineas += [
        "## Opcional",
        "",
        "- [Fuentes y sus licencias](/v1/fuentes): cada dato conserva la licencia de su fuente.",
        "- [OpenAPI](/openapi.json)",
        "- [Tarjeta MCP](/.well-known/mcp/server-card.json)",
        "",
    ]
    return "\n".join(lineas)


# Identidad del servidor en el registro oficial de MCP (espacio de nombres verificado por DNS en
# terrnova.com) y en su tarjeta estándar (SEP-2127). `server.json`, en la raíz del repo, dice lo
# mismo; una prueba los compara.
NOMBRE_REGISTRO = "com.terrnova/terrnova"
DESCRIPCION_CORTA = (
    "Datos oficiales de Colombia: predios, empresas, contratos y normas, con fuente y licencia"
)
URL_MCP = "https://terrnova.com/mcp"
CABECERA_LLAVE = {
    "name": "Authorization",
    "description": "La llave de Terrnova como Bearer (rt_live_… o rt_test_…)",
    "isRequired": True,
    "isSecret": True,
    "value": "Bearer {llave}",
    "variables": {
        "llave": {"description": "Tu llave de Terrnova", "isRequired": True, "isSecret": True}
    },
}


def tarjeta_estandar() -> dict[str, Any]:
    """La tarjeta del servidor según la SEP-2127: identidad y cómo conectarse, sin herramientas
    (esas se listan por `tools/list`)."""
    return {
        "$schema": "https://static.modelcontextprotocol.io/schemas/v1/server-card.schema.json",
        "name": NOMBRE_REGISTRO,
        "title": "Terrnova",
        "version": __version__,
        "description": DESCRIPCION_CORTA,
        "websiteUrl": "https://terrnova.com",
        "icons": [
            {
                "src": "https://terrnova.com/favicon.svg",
                "mimeType": "image/svg+xml",
                "sizes": ["any"],
            }
        ],
        "remotes": [
            {
                "type": "streamable-http",
                "url": URL_MCP,
                "headers": [CABECERA_LLAVE],
                "supportedProtocolVersions": PROTOCOLOS,
            }
        ],
    }


def ai_catalogo() -> dict[str, Any]:
    """`/.well-known/ai-catalog.json` (AI Catalog 1.0): apunta a la tarjeta estándar."""
    return {
        "specVersion": "1.0",
        "entries": [
            {
                "identifier": "urn:air:terrnova.com:mcp:terrnova",
                "type": "application/mcp-server-card+json",
                "url": f"{URL_MCP}/server-card",
            }
        ],
    }


def tarjeta_mcp(c: Catalogo) -> dict[str, Any]:
    familias = _familias(c)
    return {
        "name": "terranova",
        "title": "Terrnova",
        "version": __version__,
        "description": (
            "Fuentes oficiales colombianas y globales con procedencia y licencia en cada respuesta "
            "(contrato rt/1)."
        ),
        "transport": {"type": "streamable-http", "endpoint": "/mcp"},
        "profiles": [
            {
                "name": familia,
                "endpoint": f"/mcp/{familia}",
                "tools": len(hs) + (familia == ficha_lugar.FAMILIA),
            }
            for familia, hs in familias.items()
        ],
        "protocolVersions": PROTOCOLOS,
        "authentication": {"type": "bearer", "description": "llave rt_live_… o rt_test_…"},
        "capabilities": {"tools": {"listChanged": False}},
        "tools": [
            {"name": h.id, "title": h.pregunta, "family": h.familia, "credits": h.creditos}
            for hs in familias.values()
            for h in hs
        ]
        + [
            {
                "name": ficha_lugar.HERRAMIENTA,
                "title": ficha_lugar.PREGUNTA,
                "family": ficha_lugar.FAMILIA,
                "credits": ficha_lugar.TOPE_CREDITOS,
            }
        ],
    }


def herramientas_md(c: Catalogo) -> str:
    lineas = [
        "# Herramientas",
        "",
        "Generado del catálogo con `uv run scripts/descripcion.py`; no se edita a mano.",
        "",
    ]
    for familia, hs in _familias(c).items():
        lineas += [f"## {familia}", "", "| Herramienta | Pregunta | Fuente | Licencia | Créditos |"]
        lineas.append("|---|---|---|---|---|")
        for h in hs:
            f = c.fuentes[h.fuente]
            lineas.append(
                f"| `{h.id}` | {h.pregunta} | {f.entidad} | {_licencia(f)} | {h.creditos} |"
            )
        lineas.append("")
    lineas += [
        "## Ficha técnica de una fuente",
        "",
        f"`{FUENTE_DESCRIBIR}` (MCP en `/mcp`; REST en `GET /v1/fuentes/{{id}}`): {DESCRIBIR}",
        "",
        "## Ficha de un lugar",
        "",
        f"`{ficha_lugar.HERRAMIENTA}` (MCP en `/mcp` y `/mcp/{ficha_lugar.FAMILIA}`; REST en "
        f"`POST /v1/fichas`): {ficha_lugar.DESCRIPCION} Cuesta la suma de las partes que "
        f"respondieron, hasta {ficha_lugar.TOPE_CREDITOS} créditos.",
        "",
    ]
    return "\n".join(lineas)
