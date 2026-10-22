"""Pruebas doradas (F2.1): cada herramienta del catálogo contra la respuesta real grabada de
su conector (`scripts/grabar_doradas.py`). Sin red: si cambia el mapeo, el contrato o el catálogo,
falla aquí; si cambia la fuente, falla al regrabar (spec 04, §11.3)."""

import json
from pathlib import Path
from typing import Any

import pytest

from terranova.canario import campos_presentes, comprobar
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
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(
        herramienta, h.canario.entrada, plan="evaluacion"
    )

    Sobre.model_validate(sobre.model_dump(mode="json"))  # reglas 1-9, ida y vuelta por JSON
    assert comprobar(h, sobre) == [], "la verdad medida del canario no coincide"
    assert sorted(campos_presentes(sobre)) == h.canario.campos, "corre scripts/campos_canario.py"
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


def _filas_crudas(respuesta: dict[str, Any]) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for art in respuesta.get("artifacts") or []:
        filas += [r for r in art.get("rows") or [] if isinstance(r, dict)]
        filas += [f.get("properties") or {} for f in (art.get("data") or {}).get("features") or []]
    return filas


DE_SOCRATA = sorted(
    h for h, f in CATALOGO.herramientas.items() if CATALOGO.fuentes[f.fuente].protocolo == "socrata"
)


@pytest.mark.parametrize("herramienta", DE_SOCRATA)
def test_la_dorada_de_socrata_solo_guarda_la_lista_blanca(herramienta: str) -> None:
    """El repo es público: la respuesta grabada no puede traer columnas fuera de la lista blanca
    (cédulas, supervisores, contactos). Por eso las fichas de Socrata piden `select`."""
    h = CATALOGO.herramientas[herramienta]
    permitidas = set(CATALOGO.fuentes[h.fuente].campos) | {
        d.campo for d in h.derivados.values() if d.de == "columna" and d.campo
    }
    grabado = json.loads((DORADAS / f"{herramienta}.json").read_text(encoding="utf-8"))
    filas = [fila for ll in grabado["llamadas"] for fila in _filas_crudas(ll["respuesta"])]
    vistas = {k for fila in filas for k in fila}
    assert vistas <= permitidas, f"columnas fuera de la lista blanca: {sorted(vistas - permitidas)}"
