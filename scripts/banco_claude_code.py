"""Banco de escala con un cliente MCP real: Claude Code en modo headless (`claude -p`), una sesión
por pregunta, contra el MCP desplegado (ADR-0031, ADR-0032).

El banco de `banco_mcp_escala.py` arma la llamada al LLM a mano. Este usa el cliente tal cual lo
usa la gente: su búsqueda de herramientas diferidas (ToolSearch) y su forma de pasarle al modelo el
resultado (`structuredContent`, con tope de tamaño). Así salió que la geometría completa no le
llegaba al modelo. Se mide igual que el banco (`_evaluar`).

- **Aislado:** cada sesión carga solo el MCP de Terrnova (`--mcp-config` temporal,
  `--strict-mcp-config`). No usa herramientas integradas salvo ToolSearch y corre en una carpeta
  vacía, sin la configuración, el CLAUDE.md, la memoria ni los hooks del usuario.
- **Limpieza:** al terminar se borran los JSON con la llave y la carpeta de sesiones que Claude
  Code deja en `~/.claude/projects`.
- **Costo:** con Opus, unos USD 0,07 por pregunta, a cargo de la cuenta de Claude de quien lo
  corre. Una pregunta a la vez: nunca carga contra las fuentes.

Uso: `uv run scripts/banco_claude_code.py --llave rt_test_… --salida banco.jsonl
[--escenarios perfil,catalogo,plano] [--modelo claude-opus-5-5] [--ids t01,t02]`
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import yaml
from banco_agente import BANCO, SISTEMA, _evaluar, _plano
from banco_mcp_escala import SISTEMA_CATALOGO, _familia_pregunta

BASE = "https://terrnova.com"
PREFIJO = "mcp__terranova__"
ESCENARIOS = ("perfil", "catalogo", "plano")


def _ruta(escenario: str, v: dict[str, Any]) -> str:
    if escenario == "perfil":
        return f"/mcp/{_familia_pregunta(v)}"
    return "/mcp/catalogo" if escenario == "catalogo" else "/mcp"


def _config(trabajo: Path, base: str, ruta: str, llave: str) -> Path:
    p = trabajo / "cfg" / ((ruta.strip("/").replace("/", "_") or "mcp") + ".json")
    if not p.exists():
        p.parent.mkdir(exist_ok=True)
        servidor = {
            "type": "http",
            "url": base + ruta,
            "headers": {"Authorization": f"Bearer {llave}"},
        }
        p.write_text(json.dumps({"mcpServers": {"terranova": servidor}}), encoding="utf-8")
    return p


def _texto(contenido: Any) -> str:
    if isinstance(contenido, str):
        return contenido
    return " ".join(c.get("text", "") for c in contenido or [] if isinstance(c, dict))


def _llamada(nombre: str, args: Any, texto: str, error: bool) -> dict[str, Any] | None:
    """Una llamada del agente en el formato del banco; None para las búsquedas."""
    nombre = nombre.removeprefix(PREFIJO)
    if nombre in ("ToolSearch", "buscar_herramienta"):
        return None
    if nombre == "consultar" and isinstance(args, dict):  # el perfil catálogo
        nombre, args = str(args.get("herramienta")), args.get("entrada") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
    try:
        sobre = json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        sobre = {}
    sobre = sobre if isinstance(sobre, dict) else {}
    return {
        "herramienta": nombre,
        "argumentos": args if isinstance(args, dict) else {},
        "error": error,
        "estado": sobre.get("estado"),
        "datos": sobre.get("datos") or {},
        # sin sobre, lo que vio el modelo (p. ej. «el resultado excede el tope»)
        "texto": _plano(sobre) if sobre else texto,
    }


def correr(
    v: dict[str, Any], escenario: str, a: argparse.Namespace, trabajo: Path
) -> dict[str, Any]:
    vacia = trabajo / "vacia"
    vacia.mkdir(exist_ok=True)
    orden = [
        "claude", "-p", v["pregunta"], "--model", a.modelo,
        "--mcp-config", str(_config(trabajo, a.base, _ruta(escenario, v), a.llave)),
        "--strict-mcp-config", "--tools", "ToolSearch", "--allowedTools", "mcp__terranova",
        "--append-system-prompt", SISTEMA_CATALOGO if escenario == "catalogo" else SISTEMA,
        "--output-format", "stream-json", "--verbose", "--no-session-persistence",
        "--setting-sources", "",
    ]  # fmt: skip
    t0 = time.perf_counter()
    p = subprocess.run(
        orden, cwd=vacia, capture_output=True, text=True, encoding="utf-8", timeout=900
    )
    segundos = round(time.perf_counter() - t0, 1)
    usos: dict[str, dict[str, Any]] = {}
    final: dict[str, Any] = {}
    busquedas = 0
    for linea in p.stdout.splitlines():
        try:
            m = json.loads(linea)
        except json.JSONDecodeError:
            continue
        contenido = (m.get("message") or {}).get("content")
        if m.get("type") == "assistant":
            for c in contenido or []:
                if c.get("type") == "tool_use":
                    usos[c["id"]] = {"nombre": c["name"], "args": c.get("input") or {}}
        elif m.get("type") == "user" and isinstance(contenido, list):
            for c in contenido:
                if c.get("type") == "tool_result" and c.get("tool_use_id") in usos:
                    usos[c["tool_use_id"]] |= {
                        "texto": _texto(c.get("content")),
                        "error": bool(c.get("is_error")),
                    }
        elif m.get("type") == "result":
            final = m
    llamadas = []
    for u in usos.values():
        ll = _llamada(u["nombre"], u["args"], u.get("texto", ""), u.get("error", False))
        busquedas += ll is None
        if ll is not None:
            llamadas.append(ll)
    uso = final.get("usage") or {}
    entrada = sum(
        uso.get(k, 0)
        for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    )
    error = None
    if p.returncode != 0 or final.get("is_error") or not final:
        error = (p.stderr[-300:] or str(final.get("result", ""))[:300]) or "sin resultado"
    return _evaluar(v, llamadas) | {
        "escenario": escenario,
        "modelo": a.modelo,
        "respuesta": final.get("result", ""),
        "tokens_entrada": entrada,
        "tokens_salida": uso.get("output_tokens", 0),
        "costo_usd": final.get("total_cost_usd"),
        "vueltas_llm": final.get("num_turns"),
        "busquedas": busquedas,
        "segundos": segundos,
        "error_llm": error,
    }


def resumen(filas: list[dict[str, Any]]) -> None:
    titulos = f"{'n':>3} {'éxito':>6} {'herram.':>7} {'tok/preg':>9} {'seg':>5} {'USD':>6}"
    print(f"\n{'escenario':10} {titulos}")
    for e in dict.fromkeys(r["escenario"] for r in filas):
        x = [r for r in filas if r["escenario"] == e]
        n = len(x)
        print(
            f"{e:10} {n:3} {sum(r['exito'] for r in x) / n:6.0%}"
            f" {sum(r['herramienta_correcta'] for r in x) / n:7.0%}"
            f" {sum(r['tokens_entrada'] for r in x) // n:9}"
            f" {sum(r['segundos'] for r in x) / n:5.1f}"
            f" {sum(r['costo_usd'] or 0 for r in x):6.2f}"
        )


def _sesiones(vacia: Path) -> Path:
    """La carpeta donde Claude Code guarda lo de una carpeta de trabajo (resultados grandes)."""
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(vacia))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llave", required=True)
    ap.add_argument("--salida", required=True, type=Path)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--escenarios", default=",".join(ESCENARIOS))
    ap.add_argument("--modelo", default="claude-opus-5-5")
    ap.add_argument("--ids")
    a = ap.parse_args(argv)
    verdades = yaml.safe_load(BANCO.read_text(encoding="utf-8"))["verdades"]
    if a.ids:
        verdades = [v for v in verdades if v["id"] in a.ids.split(",")]
    hechas = set()
    if a.salida.exists():  # retoma donde quedó
        filas = [json.loads(x) for x in a.salida.read_text(encoding="utf-8").splitlines()]
        hechas = {(r["escenario"], r["id"]) for r in filas}
    trabajo = Path(tempfile.mkdtemp(prefix="tn-banco-cc-"))
    try:
        for e in a.escenarios.split(","):
            for v in verdades:
                if (e, v["id"]) in hechas:
                    continue
                r = correr(v, e, a, trabajo)
                with a.salida.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                marca = "✓" if r["exito"] else ("~" if r["herramienta_correcta"] else "✗")
                camino = " → ".join(ll["herramienta"] for ll in r["llamadas"]) or "(nada)"
                print(
                    f"{marca} {e} {v['id']} [{r['segundos']} s, {r['tokens_entrada']} tok, "
                    f"{r['busquedas']} búsq] {camino} {'; '.join(r['fallas'])[:160]}"
                    f" {r['error_llm'] or ''}",
                    flush=True,
                )
    finally:
        shutil.rmtree(_sesiones((trabajo / "vacia").resolve()), ignore_errors=True)
        shutil.rmtree(trabajo, ignore_errors=True)  # incluye los JSON con la llave
    resumen([json.loads(x) for x in a.salida.read_text(encoding="utf-8").splitlines()])
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    sys.exit(main(sys.argv[1:]))
