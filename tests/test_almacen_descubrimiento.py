"""Almacén del catálogo en PostGIS + pgvector (G6, ADR-0028).

La prueba del literal no usa base. La del almacén corre solo con `TERRANOVA_PG_PRUEBAS=postgresql://…`
apuntando a un Postgres **con la extensión pgvector** (en CI, el job `descubrimiento`).
"""

import os
from typing import Any

import pytest

from terranova.almacen_descubrimiento import (
    ESQUEMA,
    AlmacenDescubrimiento,
    ConectorCatalogo,
    _vector_literal,
)
from terranova.conector import ErrorConector
from terranova.descubrimiento import DatasetDescubrible

URL_PG = os.environ.get("TERRANOVA_PG_PRUEBAS")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_vector_literal() -> None:
    assert _vector_literal((0.1, 0.2, 0.3)) == "[0.1,0.2,0.3]"
    assert _vector_literal(()) == "[]"


def _ds(
    id_: str, titulo: str, *, licencia: str | None = "CC BY", protocolo: str = "icde"
) -> DatasetDescubrible:
    return DatasetDescubrible(
        id_socrata=id_,
        titulo=titulo,
        descripcion="",
        entidad="IGAC",
        categoria="Dato temático",
        columnas=("hidrografia",),
        licencia=licencia,
        actualizado_en="2026-10-01T00:00:00Z",
        vistas=0,
        descargas=0,
        url=f"https://mapas.igac.gov.co/server/rest/services/{id_}",
        protocolo=protocolo,
    )


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_reemplazar_y_buscar_vectorial() -> None:
    assert URL_PG
    psycopg = pytest.importorskip("psycopg")

    with psycopg.connect(URL_PG, autocommit=True) as c:  # base de pruebas: se parte de cero
        c.execute(f"DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE")

    almacen = AlmacenDescubrimiento(URL_PG, dim=3)
    agua = _ds("agua", "Cuerpos de agua")
    bosque = _ds("bosque", "Cobertura de bosque")
    vectores = {"agua": (1.0, 0.0, 0.0), "bosque": (0.0, 1.0, 0.0)}
    n = almacen.reemplazar("icde", [agua, bosque], vectores)
    assert n == 2

    # una consulta alineada con «agua» trae agua primero y filtra bosque (ortogonal) por el piso
    hallados = almacen.buscar((1.0, 0.0, 0.0), piso=0.5)
    assert [d.id_socrata for d in hallados] == ["agua"]
    assert hallados[0].protocolo == "icde"  # se conserva el protocolo (lo usa el agente)


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_reemplazar_es_por_catalogo() -> None:
    assert URL_PG
    psycopg = pytest.importorskip("psycopg")

    with psycopg.connect(URL_PG, autocommit=True) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE")

    almacen = AlmacenDescubrimiento(URL_PG, dim=3)
    almacen.reemplazar("icde", [_ds("a", "agua icde")], {"a": (1.0, 0.0, 0.0)})
    almacen.reemplazar(
        "socrata", [_ds("b", "agua socrata", protocolo="socrata")], {"b": (1.0, 0.0, 0.0)}
    )
    # refrescar icde no borra socrata
    almacen.reemplazar("icde", [_ds("a2", "agua icde nueva")], {"a2": (1.0, 0.0, 0.0)})
    hallados = almacen.buscar((1.0, 0.0, 0.0), piso=0.5, limite=10)
    ids = {d.id_socrata for d in hallados}
    assert ids == {"a2", "b"}  # icde quedó con a2 (no a), socrata intacto


# --- conector interno catalogo_dcat (sin DB ni modelo) ------------------------------------------
class _AlmacenFalso:
    def __init__(self, resultado: list[DatasetDescubrible]) -> None:
        self._resultado = resultado
        self.visto: dict[str, Any] = {}

    def buscar(
        self, vector: tuple[float, ...], *, limite: int = 20, **_: Any
    ) -> list[DatasetDescubrible]:
        self.visto = {"vector": vector, "limite": limite}
        return self._resultado


class _EmbedderFalso:
    def consulta(self, texto: str) -> tuple[float, ...]:
        return (1.0, 0.0, 0.0)

    def documentos(self, textos: list[str]) -> list[tuple[float, ...]]:
        return [(1.0, 0.0, 0.0) for _ in textos]


@pytest.mark.anyio
async def test_conector_catalogo_busca_y_surte_procedencia() -> None:
    agua = _ds("agua", "Cuerpos de agua")
    almacen = _AlmacenFalso([agua])
    con = ConectorCatalogo(almacen, _EmbedderFalso())  # type: ignore[arg-type]
    r = await con.llamar("buscar_catalogo", {"consulta": "dónde hay agua", "limite": 5})
    fila = r["artifacts"][0]["rows"][0]
    assert fila["id"] == "agua" and fila["licencia"] == "CC BY" and fila["protocolo"] == "icde"
    assert "url" in fila and fila["url"].endswith("/agua")
    assert almacen.visto["limite"] == 5  # el límite llega al almacén
    assert r["facts"]["completitud"]["vistos"] == 1


@pytest.mark.anyio
async def test_conector_catalogo_herramienta_desconocida() -> None:
    con = ConectorCatalogo(_AlmacenFalso([]), _EmbedderFalso())  # type: ignore[arg-type]
    with pytest.raises(ErrorConector) as exc:
        await con.llamar("otra", {"consulta": "x"})
    assert exc.value.codigo == "error_interno"


@pytest.mark.anyio
async def test_conector_catalogo_sin_embebedor_es_fuente_no_disponible() -> None:
    con = ConectorCatalogo(_AlmacenFalso([]), None)  # type: ignore[arg-type]
    with pytest.raises(ErrorConector) as exc:
        await con.llamar("buscar_catalogo", {"consulta": "x"})
    assert exc.value.codigo == "fuente_no_disponible"
