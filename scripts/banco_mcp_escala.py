"""Banco de escala MCP: ¿cómo debe exponer Terrnova cientos de herramientas? (investigación del
2026-10-28, `interno/investigacion/MCP_A_ESCALA_2026-10-28.md`).

Las mismas preguntas del banco de agente (`catalogo/verdades_producto.yaml`) se responden con un LLM
real (modelo mini) por la API Responses, contra la puerta desplegada por MCP remoto, en varios
escenarios de exposición:

- `plano`: las ~209 herramientas de `/mcp` a la vista (como un cliente sin búsqueda).
- `busqueda`: las mismas, diferidas en un solo espacio de nombres con la búsqueda de herramientas
  del cliente (`tool_search` alojado de OpenAI: lo que hace un cliente que busca, con `/mcp`).
- `busqueda_familias`: diferidas en un espacio de nombres por familia (como conectar los perfiles
  a la vez en un cliente que busca).
- `perfil`: el perfil de la familia de la herramienta esperada (`/mcp/<familia>`). Es una cota
  superior: supone que el usuario conectó justo el perfil que hacía falta.
- `catalogo`: el perfil catálogo (`/mcp/catalogo`: buscar_herramienta → consultar).
- `perfil+N` (p. ej. `perfil+90`): el perfil de la pregunta más herramientas de otras familias hasta
  sumar N, a la vista. Junto con `perfil` y `plano` da la curva de precisión contra tamaño: cuánto
  puede crecer un perfil antes de partirlo (ADR-0031). Las de relleno salen en un orden fijo (hash
  del nombre), las mismas en cada corrida.

Se mide lo mismo que el banco de agente (herramienta, entrada, verdad) más tokens, vueltas al LLM,
llamadas y segundos. Una pregunta a la vez (sin carga sobre las fuentes); retoma desde `--salida`.
Las respuestas se repiten entre escenarios, así que la caché de la puerta atenúa la latencia de las
fuentes: la latencia comparable es la del LLM.

Necesita `LLM_BASE_URL` (…/openai/v1), `LLM_API_KEY`, `LLM_MODEL` y una llave de evaluación.

Uso: `uv run scripts/banco_mcp_escala.py --base https://… --llave rt_test_… --salida f.jsonl
[--escenarios plano,busqueda,…] [id …]`
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

import httpx
import yaml
from banco_agente import BANCO, SISTEMA, _evaluar, _plano  # misma medida que el banco
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from terranova import perfil_catalogo, puerta
from terranova.catalogo import cargar
from terranova.ficha import FAMILIA as FAMILIA_FICHA
from terranova.ficha import HERRAMIENTA as FICHA

ESCENARIOS = ("plano", "busqueda", "busqueda_familias", "perfil", "catalogo")
MAX_VUELTAS = 6
CATALOGO = cargar()
SISTEMA_CATALOGO = (
    "Eres un asistente que responde preguntas sobre Colombia con las herramientas de Terrnova. "
    "Busca la herramienta con `buscar_herramienta` y llámala con `consultar`; no inventes cifras. "
    "Si ninguna herramienta cubre la pregunta, dilo. Responde en español, en pocas líneas, con la "
    "cifra, el año y la fuente."
)


def _familia_de(nombre: str) -> str:
    h = CATALOGO.herramientas.get(nombre)
    if h is not None:
        return h.familia
    return FAMILIA_FICHA if nombre == FICHA else "meta"


def _funcion(t: Any, diferida: bool = False) -> dict[str, Any]:
    f = {
        "type": "function",
        "name": t.name,
        "description": f"{t.title or ''} {t.description or ''}".strip()[:1024],
        "parameters": t.input_schema,
    }
    return f | {"defer_loading": True} if diferida else f


def _familia_pregunta(v: dict[str, Any]) -> str:
    return _familia_de(v["herramienta"]) if v.get("herramienta") else str(v["familia"])


def _tamano(escenario: str) -> int | None:
    """N de `perfil+N`; None en los demás escenarios."""
    base, _, n = escenario.partition("+")
    return int(n) if base == "perfil" and n.isdigit() else None


def seleccion(tools: list[Any], familia: str, n: int) -> list[Any]:
    """El perfil de `familia` (con las comunes y fuente_describir) y relleno de otras familias en
    orden fijo hasta sumar `n`."""
    comunes = puerta.HERRAMIENTAS_COMUNES | {"fuente_describir"}
    propias = [t for t in tools if _familia_de(t.name) == familia or t.name in comunes]
    otras = sorted(
        (t for t in tools if t not in propias),
        key=lambda t: hashlib.sha1(t.name.encode()).hexdigest(),
    )
    return propias + otras[: max(0, n - len(propias))]


def herramientas_responses(escenario: str, tools: list[Any]) -> list[dict[str, Any]]:
    if escenario in ("plano", "perfil", "catalogo") or _tamano(escenario):
        return [_funcion(t) for t in tools]
    if escenario == "busqueda":
        return [
            {"type": "tool_search"},
            {
                "type": "namespace",
                "name": "terranova",
                "description": "Fuentes oficiales colombianas (Terrnova). Familias: "
                + perfil_catalogo.mapa_de_familias(CATALOGO),
                "tools": [_funcion(t, diferida=True) for t in tools],
            },
        ]
    por_familia: dict[str, list[Any]] = defaultdict(list)
    for t in tools:
        por_familia[_familia_de(t.name)].append(t)
    return [{"type": "tool_search"}] + [
        {
            "type": "namespace",
            "name": f"terranova_{familia}",
            "description": f"Terrnova, {familia}: "
            + perfil_catalogo.TEMAS_FAMILIA.get(familia, ""),
            "tools": [_funcion(t, diferida=True) for t in lista],
        }
        for familia, lista in sorted(por_familia.items())
    ]


async def _llm(http: httpx.AsyncClient, cuerpo: dict[str, Any]) -> dict[str, Any]:
    for intento in range(3):
        r = await http.post("/responses", json=cuerpo)
        if r.status_code in (429, 500, 502, 503) and intento < 2:
            await asyncio.sleep(5 * (intento + 1))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"LLM {r.status_code}: {r.text[:600]}")
        respuesta: dict[str, Any] = r.json()
        return respuesta
    raise RuntimeError("el LLM no respondió")


async def _pregunta(
    v: dict[str, Any],
    escenario: str,
    mcp: Client[Any],
    http: httpx.AsyncClient,
    herramientas: list[dict[str, Any]],
) -> dict[str, Any]:
    cuerpo: dict[str, Any] = {
        "model": os.environ["LLM_MODEL"],
        "instructions": SISTEMA_CATALOGO if escenario == "catalogo" else SISTEMA,
        "input": [{"role": "user", "content": v["pregunta"]}],
        "tools": herramientas,
        "store": True,
    }
    llamadas: list[dict[str, Any]] = []
    entrada_tok = salida_tok = vueltas = busquedas = 0
    t0, respuesta, error_llm = time.perf_counter(), "", None
    try:
        for _ in range(MAX_VUELTAS):
            r = await _llm(http, cuerpo)
            vueltas += 1
            uso = r.get("usage") or {}
            entrada_tok += uso.get("input_tokens", 0)
            salida_tok += uso.get("output_tokens", 0)
            pedidas = []
            for item in r.get("output") or []:
                tipo = item.get("type")
                if tipo == "tool_search_call":
                    busquedas += 1
                elif tipo == "function_call":
                    pedidas.append(item)
                elif tipo == "message":
                    respuesta += " ".join(
                        c.get("text", "") for c in item.get("content") or [] if c.get("text")
                    )
            if not pedidas:
                break
            salidas = []
            for fc in pedidas:
                nombre = fc["name"]
                try:
                    args = json.loads(fc.get("arguments") or "{}")
                    res = await mcp.call_tool(nombre, args, raise_on_error=False)
                    estructura = res.structured_content or {}
                    texto = (
                        _plano(estructura)
                        if estructura
                        else " ".join(getattr(c, "text", "") for c in res.content)
                    )
                    error = res.is_error
                except Exception as exc:  # noqa: BLE001 — el agente ve el error, como por MCP
                    args, estructura, texto, error = {}, {}, f"error: {exc}", True
                if nombre == "buscar_herramienta":
                    busquedas += 1
                # en el perfil catálogo, `consultar(herramienta, entrada)` ES esa herramienta
                real, args_reales = nombre, args
                if nombre == "consultar" and isinstance(args, dict):
                    real = str(args.get("herramienta"))
                    args_reales = args.get("entrada") or {}
                    if isinstance(args_reales, str):
                        try:
                            args_reales = json.loads(args_reales)
                        except json.JSONDecodeError:
                            args_reales = {}
                llamadas.append(
                    {
                        "herramienta": real,
                        "argumentos": args_reales if isinstance(args_reales, dict) else {},
                        "error": error,
                        "estado": estructura.get("estado"),
                        "datos": estructura.get("datos") or {},
                        "texto": texto,
                    }
                )
                salida = {"type": "function_call_output", "call_id": fc["call_id"]}
                salidas.append(salida | {"output": texto[:8000]})
            cuerpo = cuerpo | {"previous_response_id": r["id"], "input": salidas}
    except RuntimeError as exc:
        error_llm = str(exc)[:300]
    evaluado = _evaluar(v, [ll for ll in llamadas if ll["herramienta"] != "buscar_herramienta"])
    if error_llm:
        evaluado |= {"exito": False, "fallas": [*evaluado["fallas"], f"llm: {error_llm}"]}
    return {
        **evaluado,
        "escenario": escenario,
        "respuesta": respuesta,
        "tokens_entrada": entrada_tok,
        "tokens_salida": salida_tok,
        "tokens": entrada_tok + salida_tok,
        "vueltas_llm": vueltas,
        "busquedas": busquedas,
        "segundos": round(time.perf_counter() - t0, 1),
        "error_llm": error_llm,
    }


def _ruta(escenario: str, v: dict[str, Any]) -> str:
    if escenario == "perfil":
        return f"/mcp/{_familia_pregunta(v)}"
    if escenario == "catalogo":
        return "/mcp/catalogo"
    return "/mcp"


def resumen(resultados: list[dict[str, Any]]) -> None:
    por: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in resultados:
        por[r["escenario"]].append(r)
    print(
        f"\n{'escenario':<18} {'n':>3} {'éxito':>6} {'herram.':>7} {'entrada':>7} "
        f"{'tok/preg':>9} {'vueltas':>7} {'llamadas':>8} {'seg':>6} {'err LLM':>7}"
    )
    for e, rs in por.items():
        n = len(rs)

        def pct(k: str, rs: list[dict[str, Any]] = rs, n: int = n) -> str:
            return f"{100 * sum(bool(r[k]) for r in rs) / n:.0f} %"

        llamadas = sum(
            len([ll for ll in r["llamadas"] if ll["herramienta"] != "buscar_herramienta"])
            for r in rs
        )
        print(
            f"{e:<18} {n:>3} {pct('exito'):>6} {pct('herramienta_correcta'):>7} "
            f"{pct('entrada_correcta'):>7} {sum(r['tokens'] for r in rs) / n:>9.0f} "
            f"{sum(r['vueltas_llm'] for r in rs) / n:>7.1f} {llamadas / n:>8.1f} "
            f"{sum(r['segundos'] for r in rs) / n:>6.1f} {sum(bool(r['error_llm']) for r in rs):>7}"
        )


async def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--llave", required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--escenarios", default=",".join(ESCENARIOS))
    ap.add_argument("--solo-resumen", action="store_true")
    ap.add_argument("ids", nargs="*")
    a = ap.parse_args(argv)
    hechos: list[dict[str, Any]] = []
    if a.salida.exists():
        hechos = [json.loads(linea) for linea in a.salida.read_text(encoding="utf-8").splitlines()]
    if a.solo_resumen:
        resumen(hechos)
        return 0
    listos = {(r["escenario"], r["id"]) for r in hechos}
    verdades = yaml.safe_load(BANCO.read_text(encoding="utf-8"))["verdades"]
    verdades = [v for v in verdades if not a.ids or v["id"] in a.ids]
    escenarios = [e for e in a.escenarios.split(",") if e]
    base_llm = os.environ["LLM_BASE_URL"].rstrip("/")
    llave_llm = os.environ["LLM_API_KEY"]
    cabeceras = {"Authorization": f"Bearer {llave_llm}", "api-key": llave_llm}
    clientes: dict[str, Client[Any]] = {}
    listas: dict[tuple[str, str], list[dict[str, Any]]] = {}

    async def cliente(ruta: str) -> Client[Any]:
        if ruta not in clientes:
            transporte = StreamableHttpTransport(
                a.base.rstrip("/") + ruta, headers={"Authorization": f"Bearer {a.llave}"}
            )
            clientes[ruta] = await pila.enter_async_context(Client(transporte, timeout=120))
        return clientes[ruta]

    async with (
        AsyncExitStack() as pila,
        httpx.AsyncClient(base_url=base_llm, headers=cabeceras, timeout=180) as http,
    ):
        for e in escenarios:
            modelo = os.environ["LLM_MODEL"]
            print(f"\n== {e} ({len(verdades)} preguntas, {modelo})", flush=True)
            for v in verdades:
                if (e, v["id"]) in listos:
                    continue
                ruta = _ruta(e, v)
                mcp = await cliente(ruta)
                n = _tamano(e)
                clave = (e, _familia_pregunta(v) if n else ruta)
                if clave not in listas:
                    tools = await mcp.list_tools()
                    if n:
                        tools = seleccion(tools, clave[1], n)
                    listas[clave] = herramientas_responses(e, tools)
                r = await _pregunta(v, e, mcp, http, listas[clave])
                hechos.append(r)
                with a.salida.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                marca = "✓" if r["exito"] else ("~" if r["herramienta_correcta"] else "✗")
                camino = " → ".join(ll["herramienta"] for ll in r["llamadas"]) or "(nada)"
                print(
                    f"{marca} {r['id']} [{r['segundos']} s, {r['tokens']} tok, "
                    f"{r['busquedas']} búsq] {camino} {'; '.join(r['fallas'])[:200]}",
                    flush=True,
                )
                if r["error_llm"] and e == "plano" and len(listos) + 1 == len(hechos):
                    print("    el LLM rechaza la lista de herramientas: se corta el escenario")
                    break
    resumen(hechos)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    sys.exit(asyncio.run(main(sys.argv[1:])))
