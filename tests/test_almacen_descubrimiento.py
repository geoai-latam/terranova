"""Almacén del catálogo en PostGIS + pgvector (G6, ADR-0028).

La prueba del literal no usa base. La del almacén corre solo con `TERRANOVA_PG_PRUEBAS=postgresql://…`
apuntando a un Postgres **con la extensión pgvector** (en CI, el job `descubrimiento`).
"""

import os

import pytest

from terranova.almacen_descubrimiento import ESQUEMA, AlmacenDescubrimiento, _vector_literal
from terranova.descubrimiento import DatasetDescubrible

URL_PG = os.environ.get("TERRANOVA_PG_PRUEBAS")


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
