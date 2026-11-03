"""`cnmh_conflicto_municipio`: once modalidades en una, sin repetir avisos ni disfrazar fallos."""

from typing import Any

import pytest

from terranova import conflicto as c
from terranova.catalogo import cargar
from terranova.contrato import Sobre, ZonaUsada, ahora
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.ficha import _procedencia_vacia

CATALOGO = cargar()
GRANADA = {"municipio_divipola": "05313"}
HOMONIMO = "Se consultó 05313 = GRANADA (ANTIOQUIA). Otros municipios con ese nombre: 25312."
EXCLUYENTES = CATALOGO.herramientas["cnmh_masacres_municipio"].avisos[0].texto.strip()


def _sobre(filas: list[tuple[int, int, int]], *avisos: str) -> Sobre:
    return Sobre.model_construct(
        estado="encontrado" if filas else "no_encontrado",
        datos={
            "total_victimas": sum(v for _, v, _ in filas),
            "elementos": [{"anio": a, "victimas": v, "casos": k} for a, v, k in filas],
        },
        zona_usada=ZonaUsada(tipo="codigo", valor="05313"),
        procedencia=[_procedencia_vacia(Falso(), "cnmh.sievcac_masacres", ahora(), {})],  # type: ignore[arg-type]
        errores=[],
        avisos=list(avisos),
        creditos=5,
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
        if isinstance(r, Exception):
            raise r
        if isinstance(r, Sobre):
            return r
        return _sobre([], "El CNMH no registra víctimas de esto en este municipio.", HOMONIMO)


def test_las_partes_son_las_once_herramientas_cnmh_por_municipio() -> None:
    cnmh = {h for h in CATALOGO.herramientas if h.startswith("cnmh_") and h.endswith("_municipio")}
    assert c.HERRAMIENTAS == cnmh and len(cnmh) == 11 and set(c.NOMBRES) == set(c.MODALIDADES)
    for p in c.PARTES:
        h = CATALOGO.herramientas[p.herramienta]
        assert set(h.entrada) == {"municipio_divipola"}
        assert {"total_victimas", "victimas", "casos"} <= set(h.derivados)


@pytest.mark.anyio
async def test_resume_cada_modalidad_y_suma_el_municipio() -> None:
    falso = Falso(
        cnmh_acciones_belicas_municipio=_sobre(
            [(2002, 89, 1), (2005, 10, 3)], EXCLUYENTES, HOMONIMO
        ),
        cnmh_reclutamiento_municipio=_sobre([(0, 7, 7), (2002, 2, 2)], EXCLUYENTES, HOMONIMO),
    )
    s = await c.ficha(falso, GRANADA)  # type: ignore[arg-type]
    assert s.estado == "encontrado" and len(falso.llamadas) == 11
    assert s.datos["total_victimas"] == 108 and s.datos["total_casos"] == 13
    assert s.datos["modalidades_con_victimas"] == 2
    assert s.datos["anios_con_mas_victimas"] == {"2002": 91, "2005": 10}
    ab = s.datos["por_modalidad"]["acciones_belicas"]
    assert next(iter(s.datos["por_modalidad"])) == "acciones_belicas"
    assert (ab["primer_anio"], ab["ultimo_anio"], ab["anio_pico"], ab["victimas_anio_pico"]) == (
        2002,
        2005,
        2002,
        89,
    )
    rec = s.datos["por_modalidad"]["reclutamiento"]
    assert rec["victimas_sin_anio"] == 7 and rec["primer_anio"] == 2002
    # el aviso de las excluyentes, el del homónimo y el de «no registra» salen una sola vez
    assert s.avisos[0] == c.AVISO_SUMA
    assert s.avisos.count(HOMONIMO) == 1
    assert not any(c.EXCLUYENTES in a or "no registra" in a for a in s.avisos)
    sin = next(a for a in s.avisos if a.startswith("Sin víctimas registradas"))
    assert "daño a bienes civiles" in sin and "acciones bélicas" not in sin
    assert len(s.procedencia) == 11 and s.creditos == c.TOPE_CREDITOS


@pytest.mark.anyio
async def test_lo_que_solo_dice_una_parte_va_con_su_nombre() -> None:
    minas = f"{EXCLUYENTES} Otra fuente sobre lo mismo no cuadra con esta."
    falso = Falso(cnmh_minas_municipio=_sobre([(2003, 18, 5)], minas))
    s = await c.ficha(falso, GRANADA)  # type: ignore[arg-type]
    assert "minas: Otra fuente sobre lo mismo no cuadra con esta." in s.avisos


@pytest.mark.anyio
async def test_una_modalidad_que_falla_deja_la_ficha_parcial_y_el_total_es_un_minimo() -> None:
    falso = Falso(
        cnmh_masacres_municipio=ErrorEjecucion("fuente_lenta", "no llegó"),
        cnmh_secuestro_municipio=_sobre([(2000, 20, 20)]),
    )
    s = await c.ficha(falso, GRANADA)  # type: ignore[arg-type]
    assert s.estado == "parcial" and "masacres" not in s.datos["por_modalidad"]
    assert s.datos["total_victimas"] == 20
    assert s.avisos[0].startswith("Faltan modalidades")
    assert [e.codigo for e in s.errores] == ["fuente_lenta"]


@pytest.mark.anyio
async def test_sin_victimas_en_ninguna_es_no_encontrado() -> None:
    s = await c.ficha(Falso(), GRANADA)  # type: ignore[arg-type]
    assert s.estado == "no_encontrado" and s.datos["total_victimas"] == 0
    assert c.AVISO_SUMA not in s.avisos


@pytest.mark.anyio
@pytest.mark.parametrize("entrada", [{}, {"municipio_divipola": 5313}, {"x": "05313"}])
async def test_entrada_mala(entrada: dict[str, Any]) -> None:
    with pytest.raises(ErrorEntrada):
        await c.ficha(Falso(), entrada)  # type: ignore[arg-type]
