"""Pruebas doradas (F2.1): cada herramienta del catálogo contra la respuesta real grabada de
su conector (`scripts/grabar_doradas.py`). Sin red: si cambia el mapeo, el contrato o el catálogo,
falla aquí; si cambia la fuente, falla al regrabar (spec 04, §11.3)."""

import json
from pathlib import Path
from typing import Any

import pytest

from terranova.canario import comprobar
from terranova.catalogo import cargar
from terranova.contrato import Sobre, fuera_de_lista_blanca
from terranova.ejecutor import Ejecutor

DORADAS = Path(__file__).parent / "doradas"
CATALOGO = cargar()


class ConectorGrabado:
    """Responde lo grabado para esa misma llamada; una llamada distinta es un error de la prueba."""

    def __init__(self, nombre: str, llamadas: list[dict[str, Any]]) -> None:
        self.grabadas = [ll for ll in llamadas if ll["conector"] == nombre]

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.grabadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise AssertionError(f"llamada no grabada: {herramienta} {argumentos}")


def _ejecutor(llamadas: list[dict[str, Any]]) -> Ejecutor:
    nombres = {ll["conector"] for ll in llamadas}
    return Ejecutor(CATALOGO, {n: ConectorGrabado(n, llamadas) for n in nombres})


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_cada_herramienta_tiene_su_dorada() -> None:
    assert {p.stem for p in DORADAS.glob("*.json")} == set(CATALOGO.herramientas)


@pytest.mark.anyio
@pytest.mark.parametrize("herramienta", sorted(CATALOGO.herramientas))
async def test_dorada(herramienta: str) -> None:
    h = CATALOGO.herramientas[herramienta]
    fuente = CATALOGO.fuentes[h.fuente]
    grabado = json.loads((DORADAS / f"{herramienta}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(herramienta, h.canario.entrada)

    Sobre.model_validate(sobre.model_dump(mode="json"))  # reglas 1-9, ida y vuelta por JSON
    assert comprobar(h, sobre) == [], "la verdad medida del canario no coincide"
    permitidos = fuente.nombres_rt | set(h.derivados) | {"elementos"}
    assert fuera_de_lista_blanca(sobre, permitidos) == set(), "regla 10: campo fuera de la lista"
    for elemento in sobre.datos.get("elementos", []):
        assert set(elemento) <= permitidos
    assert {p.fuente_id for p in sobre.procedencia} >= {fuente.id}
    for p in sobre.procedencia:
        if p.fuente_id == fuente.id:
            assert p.licencia.spdx == (fuente.licencia.spdx or "LicenseRef-por-verificar")
            assert p.atribucion == fuente.atribucion
    assert sobre.creditos == h.creditos
