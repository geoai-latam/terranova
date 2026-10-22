"""Spike F0.3: mide el salto puerta → conector y valida la salida de la puerta.

Necesita el conector `arcgis-mcp` y la puerta levantados (ver docs/spikes/F0.3-protocolo.md).
El salto se mide con `ping` y `tools/list`, que no tocan la fuente; a la fuente solo van
`--llamadas` consultas (5 por defecto): nunca se hace carga contra servidores del Estado.

Uso: TERRANOVA_CONECTOR_LLAVE=… uv run scripts/medir_salto.py
"""

import argparse
import asyncio
import os
import statistics
import sys
import time
from collections.abc import Awaitable, Callable
from typing import Any

import jsonschema
from fastmcp import Client

from terranova.conector import ConectorMCP


def _percentil(muestras: list[float], p: float) -> float:
    return statistics.quantiles(muestras, n=100, method="inclusive")[int(p) - 1]


async def _medir(n: int, operacion: Callable[[], Awaitable[Any]]) -> list[float]:
    await operacion()  # calentamiento
    muestras = []
    for _ in range(n):
        t0 = time.perf_counter()
        await operacion()
        muestras.append((time.perf_counter() - t0) * 1000)
    return muestras


def _informe(nombre: str, muestras: list[float]) -> None:
    print(
        f"{nombre:<34} n={len(muestras):<4} p50={statistics.median(muestras):7.1f} ms  "
        f"p95={_percentil(muestras, 95):7.1f} ms  max={max(muestras):7.1f} ms"
    )


async def main(args: argparse.Namespace) -> int:
    conector = ConectorMCP(args.conector, os.environ["TERRANOVA_CONECTOR_LLAVE"])
    await conector.abrir()
    try:
        print(f"puerta → conector: protocolo {conector.cliente.protocol_version}")
        ping = await _medir(args.n, conector.cliente.ping)
        listado = await _medir(args.n // 4, conector.cliente.list_tools)
    finally:
        await conector.cerrar()
    _informe("salto ping (puerta → conector)", ping)
    _informe("salto tools/list", listado)

    entrada = {"lon": -74.0262, "lat": 4.8619}
    async with Client(args.puerta) as cliente:
        print(f"cliente → puerta: protocolo {cliente.protocol_version}")
        (herramienta,) = await cliente.list_tools()
        esquema = herramienta.output_schema
        assert esquema is not None, "la herramienta no publica outputSchema"
        extremo: list[float] = []
        for _ in range(args.llamadas):
            t0 = time.perf_counter()
            r = await cliente.call_tool(herramienta.name, entrada)
            extremo.append((time.perf_counter() - t0) * 1000)
            jsonschema.validate(r.structured_content, esquema)
            assert r.structured_content is not None
            assert r.structured_content["datos"]["codigo_predial"] == args.verdad
    _informe("de punta a punta (con la fuente)", extremo)
    print("structuredContent valida contra outputSchema; verdad de Chía: ok")

    p95 = _percentil(ping, 95)
    print(f"\naceptación F0.3 (p95 del salto < 50 ms): {'ok' if p95 < 50 else 'NO'} ({p95:.1f} ms)")
    return 0 if p95 < 50 else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    parser = argparse.ArgumentParser()
    parser.add_argument("--conector", default="http://127.0.0.1:9400/mcp")
    parser.add_argument("--puerta", default="http://127.0.0.1:8100/mcp")
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--llamadas", type=int, default=5)
    parser.add_argument("--verdad", default="251750000000000050067000000000")
    raise SystemExit(asyncio.run(main(parser.parse_args())))
