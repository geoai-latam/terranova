"""Banco de agente (spec 04 §11.6): un LLM real responde las preguntas del banco de verdades con las
herramientas de la puerta (`/mcp` completo o un perfil por familia) y se mide si eligió la
herramienta esperada, si la llamó con la entrada correcta y si la respuesta trae la verdad medida
en la fuente.

Corre en memoria (sin HTTP ni identidad) con los conectores reales: es una llamada por pregunta, no
carga. Cada resultado se revisa a mano (la respuesta queda en el informe), no solo el verde.

Necesita los conectores levantados y un servidor compatible con OpenAI:
`LLM_BASE_URL`, `LLM_API_KEY` y `LLM_MODEL` (para rutina, un modelo mini).

Uso: `uv run scripts/banco_agente.py [--familia F] [--perfil] [--salida informe.jsonl] [id …]`
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastmcp import Client

from terranova import ficha as ficha_lugar
from terranova import puerta
from terranova.conector import ConectorMCP, conectores_desde_entorno
from terranova.ejecutor import _municipios, municipio_por_nombre
from terranova.errores import ErrorEntrada

RAIZ = Path(__file__).resolve().parents[1]
BANCO = RAIZ / "catalogo" / "verdades_producto.yaml"
MAX_VUELTAS = 5
SISTEMA = (
    "Eres un asistente que responde preguntas sobre Colombia con las herramientas de Terrnova. "
    + puerta.INSTRUCCIONES
    + " Usa las herramientas; no inventes cifras. Si ninguna herramienta cubre la pregunta, dilo. "
    "Responde en español, en pocas líneas, con la cifra, el año y la fuente."
)


def _funciones(herramientas: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": f"{t.title or ''} {t.description or ''}".strip()[:1024],
                "parameters": t.input_schema,
            },
        }
        for t in herramientas
    ]


def _plano(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False, default=str)


def _aparece(valor: Any, texto: str) -> bool:
    """La verdad aparece en lo que devolvió la herramienta: un número con tolerancia de redondeo,
    una fecha también sin guiones (1967-09-01 / 19670901), un texto tal cual."""
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        return str(valor) in texto or str(valor).replace("-", "") in texto
    for n in re.findall(r"-?[0-9]+(?:\.[0-9]+)?", texto):
        if abs(float(n) - valor) <= max(0.005, 1e-9 * abs(valor)):
            return True
    return False


def _pisos(minimos: dict[str, Any], datos: dict[str, Any]) -> list[str]:
    """El piso se cumple arriba o en alguna fila de `elementos` (resultado lista)."""
    filas = [datos, *[e for e in datos.get("elementos") or [] if isinstance(e, dict)]]
    fallas = []
    for k, piso in minimos.items():
        valores: list[float] = [f[k] for f in filas if isinstance(f.get(k), int | float)]
        if not any(v >= piso for v in valores):
            fallas.append(f"{k}: {max(valores) if valores else None} < {piso}")
    return fallas


async def _llm(
    http: httpx.AsyncClient, mensajes: list[dict[str, Any]], funciones: list[dict[str, Any]]
) -> dict[str, Any]:
    cuerpo = {
        "model": os.environ["LLM_MODEL"],
        "messages": mensajes,
        "tools": funciones,
        "tool_choice": "auto",
    }
    for intento in range(3):
        r = await http.post("/chat/completions", json=cuerpo)
        if r.status_code in (429, 500, 502, 503) and intento < 2:
            await asyncio.sleep(5 * (intento + 1))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"LLM {r.status_code}: {r.text[:600]}")
        cuerpo_respuesta: dict[str, Any] = r.json()
        return cuerpo_respuesta
    raise RuntimeError("el LLM no respondió")


async def _pregunta(
    v: dict[str, Any], mcp: Client[Any], http: httpx.AsyncClient, funciones: list[dict[str, Any]]
) -> dict[str, Any]:
    mensajes: list[dict[str, Any]] = [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": v["pregunta"]},
    ]
    llamadas: list[dict[str, Any]] = []
    tokens, t0, respuesta = 0, time.perf_counter(), ""
    for _ in range(MAX_VUELTAS):
        r = await _llm(http, mensajes, funciones)
        tokens += (r.get("usage") or {}).get("total_tokens", 0)
        msj = r["choices"][0]["message"]
        pedidas = msj.get("tool_calls") or []
        if not pedidas:
            respuesta = msj.get("content") or ""
            break
        mensajes.append({"role": "assistant", "content": msj.get("content"), "tool_calls": pedidas})
        for tc in pedidas:
            nombre = tc["function"]["name"]
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
                res = await mcp.call_tool(nombre, args, raise_on_error=False)
                estructura = res.structured_content or {}
                texto = (
                    _plano(estructura)
                    if estructura
                    else " ".join(getattr(c, "text", "") for c in res.content)
                )
                error = res.is_error
            except Exception as exc:  # noqa: BLE001 — el agente ve el error, como lo vería por MCP
                args, estructura, texto, error = {}, {}, f"error: {exc}", True
            llamadas.append(
                {
                    "herramienta": nombre,
                    "argumentos": args,
                    "error": error,
                    "estado": estructura.get("estado"),
                    "datos": estructura.get("datos") or {},
                    "texto": texto,
                }
            )
            mensajes.append({"role": "tool", "tool_call_id": tc["id"], "content": texto[:8000]})
    return {
        **_evaluar(v, llamadas),
        "respuesta": respuesta,
        "tokens": tokens,
        "segundos": round(time.perf_counter() - t0, 1),
    }


# Una entrada equivalente también cuenta: el agente no tiene por qué adivinar el rectángulo exacto
# con que se midió la verdad («junto a la Universidad de La Sabana», «a ~55 km de Chía») ni si
# cierra el rango con el día pedido o con el siguiente. La verdad se sigue exigiendo en la
# respuesta: un rectángulo que cambia la cifra falla por la cifra, no por la entrada.
TOLERANCIA_BBOX = 0.1  # grados por borde, ~11 km
# opcionales de presentación (ADR-0032 y ADR-0033): no cambian la consulta a la fuente. El mini los
# manda con su valor por defecto (`geometria: false`, `pagina: 1`) y eso no es otra entrada.
PRESENTACION = frozenset({"geometria", "pagina"})
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _comparable(clave: str, valor: Any) -> Any:
    """Un valor como lo ve la puerta: sin distinguir mayúsculas («LEY» y «ley», la puerta usa
    upper), el número sin su forma (3 y 3.0) y el municipio dicho por su nombre resuelto a su
    código, como hace la puerta («Chía, Cundinamarca» es 25175: el banco de escala contaba como
    falla 13 llamadas que la puerta respondió bien)."""
    if "divipola" in clave and isinstance(valor, str) and not valor.isdigit():
        try:
            valor = municipio_por_nombre(clave, valor, _municipios())
        except ErrorEntrada:
            pass
    if isinstance(valor, int | float) and not isinstance(valor, bool):
        return float(valor)
    if isinstance(valor, list):
        return [_comparable(clave, x) for x in valor]
    return str(valor).casefold()


def _mismo_valor(clave: str, dado: Any, esperado: Any) -> bool:
    dado, esperado = _comparable(clave, dado), _comparable(clave, esperado)
    if clave == "bbox" and isinstance(dado, list) and isinstance(esperado, list):
        return len(dado) == len(esperado) and all(
            isinstance(a, float) and isinstance(b, float) and abs(a - b) <= TOLERANCIA_BBOX
            for a, b in zip(dado, esperado, strict=False)
        )
    if clave == "hasta" and isinstance(dado, str) and FECHA.match(dado) and FECHA.match(esperado):
        # «hasta el 22» se pide como 22 (incluido) o como 23 (el día siguiente, excluido)
        dia = date.fromisoformat(dado) - date.fromisoformat(esperado)
        return dia in (timedelta(0), timedelta(days=1))
    return bool(dado == esperado)


def _misma_entrada(dada: dict[str, Any], v: dict[str, Any]) -> bool:
    """La entrada del agente equivale a la de la verdad; las `libres` (p. ej. cuántas TRM pide
    para «los últimos días») valen con cualquier valor, o sin él."""
    libres = set(v.get("libres") or ()) | PRESENTACION
    esperada = v["entrada"]
    if set(dada) - libres != set(esperada) - libres:
        return False
    return all(_mismo_valor(k, dada[k], esperada[k]) for k in set(esperada) - libres)


def _evaluar(v: dict[str, Any], llamadas: list[dict[str, Any]]) -> dict[str, Any]:
    """La medida del banco sobre las llamadas que hizo el agente (herramienta, entrada, verdad)."""
    esperada = v["herramienta"]
    # una alternativa válida (misma verdad en otra herramienta) también cuenta
    validas = {esperada, *(v.get("alternativas") or [])}
    propias = [ll for ll in llamadas if ll["herramienta"] in validas]
    fallas: list[str] = []
    if esperada is None:
        ok_herramienta = True  # «no cubre»: se revisa que la respuesta no invente
        ok_entrada = True
    else:
        ok_herramienta = bool(propias)
        ok_entrada = any(
            ll["herramienta"] != esperada  # la alternativa tiene su propia entrada
            or _misma_entrada(ll["argumentos"], v)
            for ll in propias
        )
        if not ok_herramienta:
            fallas.append(f"herramienta: {[ll['herramienta'] for ll in llamadas] or 'ninguna'}")
        elif not ok_entrada:
            fallas.append(f"entrada: {[ll['argumentos'] for ll in propias]}")
        texto = " ".join(ll["texto"] for ll in propias)
        fallas += [
            f"{k}={valor} no aparece"
            for k, valor in (v.get("verdad") or {}).items()
            if not _aparece(valor, texto)
        ]
        if v.get("minimos") and propias:
            mejores = [_pisos(v["minimos"], ll["datos"]) for ll in propias]
            if all(mejores):
                fallas += mejores[0]
        if v.get("estado") and not any(ll["estado"] == v["estado"] for ll in propias):
            fallas.append(f"estado: se esperaba {v['estado']}")
    return {
        "id": v["id"],
        "familia": v["familia"],
        "pregunta": v["pregunta"],
        "esperada": esperada,
        "llamadas": [
            {k: ll[k] for k in ("herramienta", "argumentos", "estado", "error")} for ll in llamadas
        ],
        "herramienta_correcta": ok_herramienta,
        "entrada_correcta": ok_entrada,
        "exito": ok_herramienta and ok_entrada and not fallas,
        "fallas": fallas,
    }


def _familia(v: dict[str, Any]) -> str:
    """El perfil al que se conectaría quien hace la pregunta: el de la familia de su herramienta."""
    h = puerta.CATALOGO.herramientas.get(v["herramienta"] or "")
    if h is not None:
        return h.familia
    return ficha_lugar.FAMILIA if v["herramienta"] == ficha_lugar.HERRAMIENTA else v["familia"]


async def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--familia")
    ap.add_argument(
        "--perfil",
        action="store_true",
        help="cada pregunta en el perfil de la familia de su herramienta (ADR-0006)",
    )
    ap.add_argument("--salida", type=Path)
    ap.add_argument("ids", nargs="*")
    a = ap.parse_args(argv)
    verdades = yaml.safe_load(BANCO.read_text(encoding="utf-8"))["verdades"]
    verdades = [
        v
        for v in verdades
        if (not a.familia or v["familia"] == a.familia) and (not a.ids or v["id"] in a.ids)
    ]
    reales = conectores_desde_entorno(puerta.CATALOGO)
    for c in reales.values():
        if isinstance(c, ConectorMCP):
            await c.abrir()
    puerta.usar_conectores(reales)
    os.environ.setdefault("TERRANOVA_PLAN", "evaluacion")
    base = os.environ["LLM_BASE_URL"].rstrip("/")
    llave = os.environ["LLM_API_KEY"]
    cabeceras = {"Authorization": f"Bearer {llave}", "api-key": llave}
    resultados = []
    try:
        async with httpx.AsyncClient(base_url=base, headers=cabeceras, timeout=180) as http:
            print(
                f"{len(verdades)} preguntas, modelo {os.environ['LLM_MODEL']}, "
                f"{'perfiles' if a.perfil else '/mcp completo'}"
            )
            for v in verdades:
                perfil = _familia(v) if a.perfil else None
                async with Client(puerta.crear_servidor(perfil, con_ciclo=False)) as mcp:
                    r = await _pregunta(v, mcp, http, _funciones(await mcp.list_tools()))
                r["perfil"] = perfil
                resultados.append(r)
                marca = "✓" if r["exito"] else ("~" if r["herramienta_correcta"] else "✗")
                print(
                    f"{marca} {r['id']} [{r['segundos']} s, {r['tokens']} tok] "
                    f"{'; '.join(r['fallas'])}"
                )
                print(
                    "    "
                    + (" → ".join(ll["herramienta"] for ll in r["llamadas"]) or "(sin llamadas)")
                )
                print(f"    {' '.join(r['respuesta'].split())[:300]}")
                if a.salida:
                    with a.salida.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
    finally:
        puerta.usar_conectores(None)
        for c in reales.values():
            if isinstance(c, ConectorMCP):
                await c.cerrar()
    n = len(resultados) or 1

    def tasa(k: str) -> float:
        return 100.0 * sum(bool(r[k]) for r in resultados) / n

    llamadas = sum(len(r["llamadas"]) for r in resultados) / n
    print(
        f"\néxito {tasa('exito'):.0f} % · "
        f"herramienta correcta {tasa('herramienta_correcta'):.0f} % · "
        f"entrada correcta {tasa('entrada_correcta'):.0f} % · "
        f"{llamadas:.1f} llamadas por pregunta · "
        f"{sum(r['tokens'] for r in resultados) / n:.0f} tokens por pregunta"
    )
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    sys.exit(asyncio.run(main(sys.argv[1:])))
