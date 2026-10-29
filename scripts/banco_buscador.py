"""Banco del buscador de herramientas (ADR-0031): ¿la herramienta esperada sale entre las primeras k
de `buscar_herramienta` para cada pregunta del banco de verdades? Sin LLM: mide solo la
recuperación, que es lo que hace escalar el perfil «catálogo» (su costo no crece con el catálogo).

Por defecto busca en memoria por palabras (BM25). Con `--base` y `--llave` pregunta al
`/mcp/catalogo` desplegado, que es híbrido si el embebedor ya vectorizó: 60 llamadas a la puerta,
no a las fuentes.

Uso: `uv run scripts/banco_buscador.py [--base URL --llave LLAVE] [--k 6]`
"""

import argparse
import asyncio
import sys
from typing import Any

import yaml
from banco_agente import BANCO
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from terranova import perfil_catalogo, puerta

PAUSA_S = 1.5  # bajo la cuota por llave (60 por minuto, ráfaga de 20)


def _validas(v: dict[str, Any]) -> set[str]:
    return {v["herramienta"], *(v.get("alternativas") or [])}


async def _remotas(base: str, llave: str, preguntas: list[str], k: int) -> list[list[str]]:
    transporte = StreamableHttpTransport(
        base.rstrip("/") + "/mcp/catalogo", headers={"Authorization": f"Bearer {llave}"}
    )
    salida: list[list[str]] = []
    modo = None
    async with Client(transporte, timeout=120) as mcp:
        for p in preguntas:
            await asyncio.sleep(PAUSA_S)
            try:
                r = await mcp.call_tool("buscar_herramienta", {"pregunta": p})
            except Exception as exc:  # noqa: BLE001 — se cuenta como «fuera» y se dice
                print(f"error en «{p[:50]}»: {exc}")
                salida.append([])
                continue
            datos = r.structured_content or {}
            salida.append([h["herramienta"] for h in datos.get("herramientas", [])][:k])
            modo = datos.get("modo")
    print(f"modo del buscador desplegado: {modo}")
    return salida


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base")
    ap.add_argument("--llave")
    ap.add_argument("--k", type=int, default=perfil_catalogo.K_POR_DEFECTO)
    a = ap.parse_args(argv)
    verdades = [
        v
        for v in yaml.safe_load(BANCO.read_text(encoding="utf-8"))["verdades"]
        if v.get("herramienta")
    ]
    preguntas = [v["pregunta"] for v in verdades]
    if a.base:
        hallados = asyncio.run(_remotas(a.base, a.llave, preguntas, a.k))
    else:
        indice = perfil_catalogo.IndiceHerramientas(perfil_catalogo.documentos(puerta.CATALOGO))
        hallados = [[d.herramienta for d in indice.buscar(p, k=a.k)] for p in preguntas]
    en_1 = en_k = 0
    for v, h in zip(verdades, hallados, strict=True):
        pos = next((i for i, x in enumerate(h) if x in _validas(v)), None)
        en_1 += pos == 0
        en_k += pos is not None
        if pos is None or pos > 0:
            donde = "fuera" if pos is None else f"#{pos + 1}"
            print(f"{v['id']:<4} {donde:<6} {v['herramienta']:<42} ← {', '.join(h[:3])}")
    n = len(verdades)
    print(f"\n{n} preguntas: en el 1.º {en_1 / n:.0%}, entre los {a.k} primeros {en_k / n:.0%}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    sys.exit(main(sys.argv[1:]))
