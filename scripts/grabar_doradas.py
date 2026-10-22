"""Corre el canario de cada herramienta EN VIVO y graba las respuestas de los conectores.

Las grabaciones quedan en `tests/doradas/<herramienta>.json` y la prueba dorada las reproduce sin
red. Es una llamada por canario: no es carga. La geometría se reduce a su primer punto para que el
archivo sea pequeño (la prueba dorada valida el mapeo, no la forma del polígono).

Necesita los conectores levantados (ver `terranova.conector.conectores_desde_entorno`).
Uso: `TERRANOVA_CONECTOR_LLAVE=… uv run scripts/grabar_doradas.py [herramienta …]`
"""

import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from terranova.canario import comprobar
from terranova.catalogo import cargar
from terranova.conector import Conector, ConectorMCP, conectores_desde_entorno
from terranova.ejecutor import Ejecutor

DESTINO = Path(__file__).resolve().parents[1] / "tests" / "doradas"


def _reducir(geometria: Any) -> Any:
    """Una geometría como su primer vértice (un punto)."""
    coords = geometria.get("coordinates") if isinstance(geometria, dict) else None
    while isinstance(coords, list) and coords and isinstance(coords[0], list):
        coords = coords[0]
    if isinstance(coords, list) and len(coords) >= 2:
        return {"type": "Point", "coordinates": [round(coords[0], 7), round(coords[1], 7)]}
    return geometria


def _ligera(respuesta: dict[str, Any]) -> dict[str, Any]:
    copia: dict[str, Any] = json.loads(json.dumps(respuesta))
    for art in copia.get("artifacts") or []:
        for rasgo in (art.get("data") or {}).get("features") or []:
            rasgo["geometry"] = _reducir(rasgo.get("geometry"))
    return copia


class Grabador:
    def __init__(self, nombre: str, real: Conector) -> None:
        self.nombre = nombre
        self.real = real
        self.llamadas: list[dict[str, Any]] = []

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        respuesta = await self.real.llamar(herramienta, argumentos)
        self.llamadas.append(
            {
                "conector": self.nombre,
                "tool": herramienta,
                "argumentos": argumentos,
                "respuesta": _ligera(respuesta),
            }
        )
        return respuesta


async def main(nombres: list[str]) -> int:
    catalogo = cargar()
    reales = conectores_desde_entorno()
    for c in reales.values():
        if isinstance(c, ConectorMCP):
            await c.abrir()
    DESTINO.mkdir(parents=True, exist_ok=True)
    fallos = 0
    try:
        for h in catalogo.herramientas.values():
            if nombres and h.id not in nombres:
                continue
            grabadores = {n: Grabador(n, c) for n, c in reales.items()}
            ej = Ejecutor(catalogo, dict(grabadores))
            t0 = time.perf_counter()
            try:
                sobre = await ej.ejecutar(h.id, h.canario.entrada, plan="evaluacion")
            except Exception as exc:  # noqa: BLE001 — una herramienta rota no detiene las demás
                fallos += 1
                print(f"✗ {h.id}: {type(exc).__name__}: {exc}")
                continue
            ms = (time.perf_counter() - t0) * 1000
            problemas = comprobar(h, sobre)
            llamadas = [ll for g in grabadores.values() for ll in g.llamadas]
            (DESTINO / f"{h.id}.json").write_text(
                json.dumps(
                    {
                        "herramienta": h.id,
                        "grabado": datetime.now(UTC).replace(microsecond=0).isoformat(),
                        "geometria_reducida": True,
                        "llamadas": llamadas,
                    },
                    ensure_ascii=False,
                    indent=1,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            marca = "✓" if not problemas else "✗"
            fallos += bool(problemas)
            lento = " (LENTO)" if ms > h.canario.latencia_max_ms else ""
            print(f"{marca} {h.id}: {sobre.estado}, {ms:.0f} ms{lento} {'; '.join(problemas)}")
    finally:
        for c in reales.values():
            if isinstance(c, ConectorMCP):
                await c.cerrar()
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    sys.exit(asyncio.run(main(sys.argv[1:])))
