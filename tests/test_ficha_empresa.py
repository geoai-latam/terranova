"""Ficha de una empresa por NIT (auditoría integral C22): partes del catálogo en paralelo."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from terranova import ficha_empresa as f
from terranova import puerta
from terranova.catalogo import cargar
from terranova.contrato import Sobre
from terranova.ejecutor import Ejecutor, Plan
from terranova.errores import ErrorEjecucion, ErrorEntrada

DORADAS = Path(__file__).parent / "doradas"
CATALOGO = cargar()
NIT = "899999068"


class Grabado:
    def __init__(self, nombre: str, llamadas: list[dict[str, Any]]) -> None:
        self.grabadas = [ll for ll in llamadas if ll["conector"] == nombre]

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.grabadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                return json.loads(json.dumps(ll["respuesta"]))  # type: ignore[no-any-return]
        raise AssertionError(f"no grabada: {herramienta} {argumentos}")


def _dorado(herramienta: str) -> Sobre:
    llamadas = json.loads((DORADAS / f"{herramienta}.json").read_text(encoding="utf-8"))["llamadas"]
    ej = Ejecutor(CATALOGO, {n["conector"]: Grabado(n["conector"], llamadas) for n in llamadas})
    entrada = CATALOGO.herramientas[herramienta].canario.entrada
    return asyncio.run(ej.ejecutar(herramienta, entrada, plan="evaluacion"))


SOBRES: dict[str, Sobre] = {}


@pytest.fixture(scope="module")
def sobres() -> dict[str, Sobre]:
    if not SOBRES:
        for h in f.HERRAMIENTAS:
            SOBRES[h] = _dorado(h)
    return SOBRES


class EjecutorFalso(Ejecutor):
    def __init__(self, sobres: dict[str, Sobre], caidas: dict[str, ErrorEjecucion] | None = None):
        super().__init__(CATALOGO, {})
        self.sobres, self.caidas = sobres, caidas or {}
        self.llamadas: dict[str, dict[str, Any]] = {}

    async def ejecutar(
        self, herramienta: str, entrada: dict[str, Any], *, plan: Plan = "normal", **_: Any
    ) -> Sobre:
        self.llamadas[herramienta] = entrada
        if herramienta in self.caidas:
            raise self.caidas[herramienta]
        return self.sobres[herramienta]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_ficha_completa(sobres: dict[str, Sobre]) -> None:
    ej = EjecutorFalso(sobres)
    s = Sobre.model_validate((await f.ficha(ej, {"nit": NIT})).model_dump(mode="json"))
    assert s.estado == "encontrado" and s.herramienta == "ficha_empresa@1" and not s.errores
    assert set(s.datos) == {p.nombre for p in f.PARTES}
    assert all(e == {"nit": NIT} for e in ej.llamadas.values())  # todas por el mismo NIT
    assert s.creditos <= f.TOPE_CREDITOS
    fuentes = {p.fuente_id for p in s.procedencia}
    assert {"confecamaras.rues", "supersociedades.niif_situacion_financiera"} <= fuentes
    assert "dian.usuarios_aduaneros" not in fuentes  # sin uso comercial: no es parte
    assert s.zona_usada is not None and s.zona_usada.valor == NIT


@pytest.mark.anyio
async def test_una_parte_caida_sale_parcial(sobres: dict[str, Sobre]) -> None:
    caida = ErrorEjecucion("fuente_lenta", "RUES lento")
    ej = EjecutorFalso(sobres, caidas={"rues_empresa_por_nit": caida})
    s = Sobre.model_validate((await f.ficha(ej, {"nit": NIT})).model_dump(mode="json"))
    assert s.estado == "parcial" and "registro_mercantil" not in s.datos
    (e,) = s.errores
    assert e.codigo == "fuente_lenta" and e.fuente_id == "confecamaras.rues"


@pytest.mark.anyio
@pytest.mark.parametrize("entrada", [{"nit": "1020304050"}, {"nit": 899999068}, {"x": "1"}])
async def test_solo_nit_de_empresa(sobres: dict[str, Sobre], entrada: dict[str, Any]) -> None:
    """ADR-0014: una cédula (empieza por 1-7) o un número suelto no pasan."""
    with pytest.raises(ErrorEntrada):
        await f.ficha(EjecutorFalso(sobres), entrada)


def test_la_ficha_esta_en_mcp_y_en_su_perfil() -> None:
    nombres = {t.name for t in asyncio.run(puerta.crear_servidor("empresas").list_tools())}
    assert f.HERRAMIENTA in nombres
    todo = {t.name for t in asyncio.run(puerta.puerta.list_tools())}
    assert {f.HERRAMIENTA, "ficha_lugar"} <= todo
