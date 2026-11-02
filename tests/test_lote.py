"""`ficha_lote`: junta las capas de un polígono y no disfraza un «no se pudo» de «no hay»."""

from typing import Any

import pytest

from terranova import lote as l
from terranova.catalogo import cargar
from terranova.contrato import Sobre, ahora
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.ficha import _procedencia_vacia

CATALOGO = cargar()
LOTE = {
    "poligono": {
        "type": "Polygon",
        "coordinates": [[[-74.0, 4.0], [-73.9, 4.0], [-73.9, 4.1], [-74.0, 4.0]]],
    }
}
RUNAP = "pnn_areas_protegidas_en_poligono"
URT = "urt_microzona_en_poligono"


def _sobre(estado: str, creditos: int = 5) -> Sobre:
    return Sobre.model_construct(
        estado=estado,
        datos={"total": 1},
        procedencia=[_procedencia_vacia(Falso(), "pnn.runap", ahora(), {})],  # type: ignore[arg-type]
        errores=[],
        avisos=[],
        creditos=creditos,
        geo_result=None,
    )


class Falso:
    catalogo = CATALOGO

    def __init__(self, **respuestas: Any) -> None:
        self.respuestas = respuestas
        self.llamadas: list[tuple[str, dict[str, Any]]] = []

    async def ejecutar(self, herramienta: str, entrada: dict[str, Any], **_: Any) -> Sobre:
        self.llamadas.append((herramienta, entrada))
        r = self.respuestas.get(herramienta)
        if isinstance(r, ErrorEjecucion):
            raise r
        return r if isinstance(r, Sobre) else _sobre("no_encontrado", 0)


def test_las_partes_existen_y_cruzan_por_poligono() -> None:
    for parte in l.PARTES:
        h = CATALOGO.herramientas[parte.herramienta]
        assert set(h.entrada) == {"poligono"} and CATALOGO.fuentes[h.fuente].copia is not None


@pytest.mark.anyio
async def test_una_capa_hallada_es_encontrado_y_consulta_todas() -> None:
    falso = Falso(**{RUNAP: _sobre("encontrado")})
    s = await l.ficha(falso, LOTE)  # type: ignore[arg-type]
    assert s.estado == "encontrado" and s.creditos == 5
    assert {h for h, _ in falso.llamadas} == l.HERRAMIENTAS
    assert s.datos["areas_protegidas"]["estado"] == "encontrado"
    assert s.zona_usada is not None and s.zona_usada.tipo == "poligono"


@pytest.mark.anyio
async def test_sin_nada_en_ninguna_capa_es_no_encontrado_y_dice_lo_que_no_cruza() -> None:
    s = await l.ficha(Falso(), LOTE)  # type: ignore[arg-type]
    assert s.estado == "no_encontrado" and l.AVISO_FUERA in s.avisos


@pytest.mark.anyio
async def test_una_parte_caida_no_es_no_hay() -> None:
    caida = ErrorEjecucion("fuente_no_disponible", "se cayó")
    s = await l.ficha(Falso(**{URT: caida}), LOTE)  # type: ignore[arg-type]
    assert s.estado == "parcial"
    assert [e.fuente_id for e in s.errores] == ["urt.microzonas"]
    assert "microzonas_restitucion" not in s.datos


@pytest.mark.anyio
async def test_todas_caidas_es_error() -> None:
    caida = ErrorEjecucion("fuente_no_disponible", "se cayó")
    with pytest.raises(ErrorEjecucion):
        await l.ficha(Falso(**dict.fromkeys(l.HERRAMIENTAS, caida)), LOTE)  # type: ignore[arg-type]


@pytest.mark.anyio
async def test_sin_scope_no_se_consulta_y_se_avisa() -> None:
    falso = Falso()
    s = await l.ficha(falso, LOTE, puede=lambda f: f != "ambiente")  # type: ignore[arg-type]
    assert RUNAP not in {h for h, _ in falso.llamadas}
    assert any("areas_protegidas" in a for a in s.avisos)


@pytest.mark.anyio
async def test_el_cobro_no_pasa_del_tope() -> None:
    falso = Falso(**{h: _sobre("encontrado", 20) for h in l.HERRAMIENTAS})
    assert (await l.ficha(falso, LOTE)).creditos == l.TOPE_CREDITOS  # type: ignore[arg-type]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "entrada",
    [{}, {**LOTE, "lon": 1}, {"poligono": {"type": "Point", "coordinates": [1, 2]}}],
)
async def test_entrada_invalida(entrada: dict[str, Any]) -> None:
    with pytest.raises(ErrorEntrada):
        await l.ficha(Falso(), entrada)  # type: ignore[arg-type]
