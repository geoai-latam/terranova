"""E2E con LLM real de TODAS las herramientas contra la puerta desplegada (spec 04 §11.6).

Una pregunta por herramienta del catálogo: su `pregunta` + los datos de la entrada de su canario
(sin nombrar la herramienta). El agente se conecta por MCP **remoto** (TLS + llave) al perfil de la
familia de la herramienta, como lo haría un cliente, y se mide lo mismo que en el banco de agente:
eligió la herramienta, la llamó con la entrada del canario y la respuesta trae la verdad medida en
la fuente (o cumple el piso). Es una pregunta a la vez (sin carga) y retoma desde `--salida`.

Cada resultado se revisa a mano (la respuesta queda en el informe), no solo el verde.

Necesita `LLM_BASE_URL`, `LLM_API_KEY` y `LLM_MODEL` (modelo mini para rutina) y una llave de
evaluación (`rt_test_`, ve las fuentes con licencia por verificar).

Uso: `uv run scripts/e2e_agente.py --base https://… --llave rt_test_… [--salida f.jsonl] [id …]`
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from banco_agente import _funciones, _pregunta  # mismo agente y misma medida que el banco
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from terranova.catalogo import cargar


def _pregunta_de(h: Any) -> str:
    """La pregunta del catálogo con los datos del canario, sin nombres de parámetro crudos."""
    datos = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in (h.canario.entrada or {}).items())
    return f"{h.pregunta} ({datos})" if datos else h.pregunta


def _verdad(h: Any) -> dict[str, Any]:
    c = h.canario
    return {
        "id": h.id,
        "familia": h.familia,
        "pregunta": _pregunta_de(h),
        "herramienta": h.id,
        "entrada": c.entrada or {},
        "verdad": c.verdad or {},
        "minimos": c.minimos or {},
        "estado": getattr(c, "estado", None),
    }


def _categoria(r: dict[str, Any]) -> str:
    """Separa de quién es la falla: `exito`; `fuente` (el agente acertó herramienta y entrada pero
    todas sus llamadas dieron error: la fuente no respondió, no es culpa del agente); `dato` (la
    llamada salió pero la verdad del canario no aparece: deriva de la fuente o bug de la puerta,
    se revisa a mano); `agente` (herramienta o entrada equivocada, o la corrida falló)."""
    if r["exito"]:
        return "exito"
    if not (r["herramienta_correcta"] and r["entrada_correcta"]):
        return "agente"
    propias = [ll for ll in r["llamadas"] if ll["herramienta"] == r.get("esperada")]
    if propias and all(ll["error"] for ll in propias):
        return "fuente"
    return "dato"


async def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="la puerta desplegada, p. ej. https://…")
    ap.add_argument("--llave", required=True, help="llave de evaluación rt_test_…")
    ap.add_argument("--salida", type=Path, help="informe JSONL (retoma: salta lo ya medido)")
    ap.add_argument("--familia")
    ap.add_argument("ids", nargs="*")
    a = ap.parse_args(argv)

    catalogo = cargar()
    herramientas = [
        h
        for h in sorted(catalogo.herramientas.values(), key=lambda h: (h.familia, h.id))
        if h.canario and (not a.familia or h.familia == a.familia) and (not a.ids or h.id in a.ids)
    ]
    hechas: set[str] = set()
    if a.salida and a.salida.exists():
        hechas = {json.loads(x)["id"] for x in a.salida.read_text(encoding="utf-8").splitlines()}
    pendientes = [h for h in herramientas if h.id not in hechas]
    print(
        f"{len(herramientas)} herramientas ({len(hechas)} ya medidas, "
        f"{len(pendientes)} por medir), modelo {os.environ['LLM_MODEL']}, puerta {a.base}"
    )
    base_llm = os.environ["LLM_BASE_URL"].rstrip("/")
    llave_llm = os.environ["LLM_API_KEY"]
    cab_llm = {"Authorization": f"Bearer {llave_llm}", "api-key": llave_llm}
    cab_puerta = {"Authorization": f"Bearer {a.llave}"}
    funciones: dict[str, list[dict[str, Any]]] = {}
    async with httpx.AsyncClient(base_url=base_llm, headers=cab_llm, timeout=180) as http:
        for h in pendientes:
            url = f"{a.base.rstrip('/')}/mcp/{h.familia}"
            async with Client(StreamableHttpTransport(url, headers=cab_puerta)) as mcp:
                if h.familia not in funciones:
                    funciones[h.familia] = _funciones(await mcp.list_tools())
                try:
                    r = await _pregunta(_verdad(h), mcp, http, funciones[h.familia])
                except Exception as exc:  # noqa: BLE001 — una falla del LLM no tumba la corrida
                    r = {
                        "id": h.id,
                        "familia": h.familia,
                        "exito": False,
                        "herramienta_correcta": False,
                        "entrada_correcta": False,
                        "fallas": [f"corrida: {type(exc).__name__}: {str(exc)[:200]}"],
                        "llamadas": [],
                        "respuesta": "",
                        "tokens": 0,
                        "segundos": 0,
                    }
            r["perfil"] = h.familia
            r["categoria"] = _categoria(r)
            marca = {"exito": "✓", "fuente": "·", "dato": "~"}.get(r["categoria"], "✗")
            print(
                f"{marca} {r['categoria']:7} {h.id} [{r['segundos']} s, {r['tokens']} tok] "
                f"{'; '.join(r['fallas'])}"
            )
            if a.salida:
                with a.salida.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

    if a.salida:
        todos = [json.loads(x) for x in a.salida.read_text(encoding="utf-8").splitlines()]
        n = len(todos) or 1

        def tasa(k: str) -> float:
            return 100.0 * sum(bool(r[k]) for r in todos) / n

        cats = {c: sum(r.get("categoria") == c for r in todos) for c in ("exito", "fuente", "dato")}
        print(
            f"\npor categoría: {cats['exito']} éxito · {cats['fuente']} fuente caída · "
            f"{cats['dato']} dato a revisar · {len(todos) - sum(cats.values())} falla del agente"
        )
        print(
            f"{len(todos)} herramientas · éxito {tasa('exito'):.0f} % · "
            f"herramienta correcta {tasa('herramienta_correcta'):.0f} % · "
            f"entrada correcta {tasa('entrada_correcta'):.0f} % · "
            f"{sum(len(r['llamadas']) for r in todos) / n:.1f} llamadas · "
            f"{sum(r['tokens'] for r in todos) / n:.0f} tokens por pregunta"
        )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    sys.exit(asyncio.run(main(sys.argv[1:])))
