"""Escribe en cada ficha `canario.campos`: los campos que trae su respuesta dorada (F7.3).

Si una fuente renombra o quita un campo, la lista blanca lo deja fuera sin error; el canario lo
nota porque ese campo ya no llega (`esquema_cambiado`). Sin red: reproduce `tests/doradas/`.
Se corre después de `scripts/grabar_doradas.py`; `tests/test_doradas.py` exige que coincidan.

Uso: `uv run scripts/campos_canario.py`
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Any

from terranova.canario import campos_presentes
from terranova.catalogo import cargar
from terranova.ejecutor import Ejecutor

RAIZ = Path(__file__).resolve().parents[1]
DORADAS = RAIZ / "tests" / "doradas"
FICHAS = RAIZ / "catalogo" / "herramientas"


class Grabado:
    def __init__(self, nombre: str, llamadas: list[dict[str, Any]]) -> None:
        self.grabadas = [ll for ll in llamadas if ll["conector"] == nombre]

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.grabadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise LookupError(f"llamada no grabada: {herramienta} {argumentos}")


async def campos(herramienta: str) -> list[str]:
    catalogo = cargar()
    h = catalogo.herramientas[herramienta]
    llamadas = json.loads((DORADAS / f"{herramienta}.json").read_text(encoding="utf-8"))["llamadas"]
    conectores = {n: Grabado(n, llamadas) for n in {ll["conector"] for ll in llamadas}}
    sobre = await Ejecutor(catalogo, conectores).ejecutar(  # type: ignore[arg-type]
        herramienta, h.canario.entrada, plan="evaluacion"
    )
    return sorted(campos_presentes(sobre))


def escribir(ficha: Path, lista: list[str]) -> bool:
    texto = ficha.read_text(encoding="utf-8")
    # solo dentro del bloque `canario:` (la consulta también tiene `campos:`)
    inicio = re.search(r"^canario:\n", texto, flags=re.M)
    if inicio is None:
        raise SystemExit(f"{ficha.name}: no tiene bloque `canario:`")
    fin = re.search(r"^\S", texto[inicio.end() :], flags=re.M)
    corte = inicio.end() + fin.start() if fin else len(texto)
    bloque = texto[inicio.end() : corte]
    linea = f"  campos: [{', '.join(lista)}]\n"
    if re.search(r"^  campos: .*\n", bloque, flags=re.M):
        bloque = re.sub(r"^  campos: .*\n", linea, bloque, count=1, flags=re.M)
    else:
        bloque, n = re.subn(r"^(  latencia_max_ms: )", linea + r"\1", bloque, count=1, flags=re.M)
        if n != 1:
            raise SystemExit(f"{ficha.name}: no encontré `latencia_max_ms` en el canario")
    nuevo = texto[: inicio.end()] + bloque + texto[corte:]
    if nuevo == texto:
        return False
    ficha.write_text(nuevo, encoding="utf-8")
    return True


def main() -> None:
    for herramienta in sorted(cargar().herramientas):
        lista = asyncio.run(campos(herramienta))
        cambio = escribir(FICHAS / f"{herramienta}.yaml", lista)
        print(f"{'✎' if cambio else '='} {herramienta}: {len(lista)} campos")


if __name__ == "__main__":
    main()
