"""E2E-01 y E2E-02 (spec 04, §11.5) contra una puerta desplegada.

E2E-01: con una llave creada por CLI, `igac_predio_en_punto` por REST → 200, `rt/1` válido, la
verdad de Chía, la licencia del ítem y 10 créditos descontados en `/v1/uso`.
E2E-02: la misma llamada por MCP da la misma huella.

Uso: `uv run scripts/e2e.py --base http://127.0.0.1:8180 --llave rt_live_…`
"""

import argparse
import asyncio
import sys
from typing import Any

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from terranova.contrato import Sobre

CHIA = {"lon": -74.0262, "lat": 4.8619}
VERDAD = "251750000000000050067000000000"


def _ok(condicion: bool, texto: str, fallas: list[str]) -> None:
    print(("  ✓ " if condicion else "  ✗ ") + texto)
    if not condicion:
        fallas.append(texto)


async def main(base: str, llave: str) -> int:
    fallas: list[str] = []
    cab = {"Authorization": f"Bearer {llave}"}
    async with httpx.AsyncClient(base_url=base, timeout=120) as http:
        print("E2E-01 · REST")
        antes: dict[str, Any] = (await http.get("/v1/uso", headers=cab)).json()
        r = await http.post("/v1/co/territorio/igac_predio_en_punto", json=CHIA, headers=cab)
        _ok(r.status_code == 200, f"200 ({r.status_code})", fallas)
        sobre = Sobre.model_validate(r.json()) if r.status_code == 200 else None
        _ok(sobre is not None, "sobre rt/1 válido", fallas)
        if sobre is not None:
            _ok(sobre.datos.get("codigo_predial") == VERDAD, f"verdad de Chía {VERDAD}", fallas)
            _ok(
                sobre.procedencia[0].licencia.spdx == "CC-BY-SA-4.0",
                "licencia del ítem CC-BY-SA-4.0",
                fallas,
            )
            # 10 si vino de la fuente; 0 si vino de la caché compartida (ADR-0010)
            desde = sobre.procedencia[0].servido_desde
            esperado = 10 if desde == "fuente" else 0
            _ok(sobre.creditos == esperado, f"{esperado} créditos (servido desde {desde})", fallas)
        cobrado = sobre.creditos if sobre is not None else -1
        despues: dict[str, Any] = (await http.get("/v1/uso", headers=cab)).json()
        _ok(
            despues.get("usados", 0) - antes.get("usados", 0) == cobrado,
            f"/v1/uso descontó lo cobrado ({antes.get('usados')} → {despues.get('usados')})",
            fallas,
        )
        sin = await http.post("/v1/co/territorio/igac_predio_en_punto", json=CHIA)
        _ok(sin.status_code == 401, "sin llave: 401", fallas)

    print("E2E-02 · MCP")
    transporte = StreamableHttpTransport(f"{base}/mcp", headers=cab)
    async with Client(transporte) as mcp:
        m = await mcp.call_tool("igac_predio_en_punto", CHIA)
        sc = m.structured_content or {}
        _ok(
            sobre is not None and sc.get("huella") == sobre.huella,
            "misma huella que por REST",
            fallas,
        )
    print("verde" if not fallas else f"{len(fallas)} fallas")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://127.0.0.1:8180")
    p.add_argument("--llave", required=True)
    a = p.parse_args()
    sys.exit(asyncio.run(main(a.base.rstrip("/"), a.llave)))
