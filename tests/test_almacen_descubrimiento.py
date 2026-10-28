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
    _rrf,
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


def test_rrf_fusiona_por_posicion() -> None:
    # "b" sale alto en las dos listas → gana; "a" y "c" primeros en una sola
    puntos = _rrf([["a", "b", "c"], ["b", "c", "x"]])
    assert max(puntos, key=lambda i: puntos[i]) == "b"
    assert puntos["a"] < puntos["b"]  # a solo aparece en una lista


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
    assert [d.id_socrata for d, _ in hallados] == ["agua"]
    assert hallados[0][0].protocolo == "icde"  # se conserva el protocolo (lo usa el agente)
    assert hallados[0][1] == 1.0  # parecido (coseno): agua alineado con la consulta
    # contar es el total honesto: solo agua pasa el piso vectorial; con el término «bosque» el FTS
    # suma bosque (son 2 coincidencias en total aunque el top-N vectorial muestre 1)
    assert almacen.contar((1.0, 0.0, 0.0), piso=0.5) == 1
    assert almacen.contar((1.0, 0.0, 0.0), "cobertura de bosque", piso=0.5) == 2


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
    ids = {d.id_socrata for d, _ in hallados}
    assert ids == {"a2", "b"}  # icde quedó con a2 (no a), socrata intacto


# --- conector interno catalogo_dcat (sin DB ni modelo) ------------------------------------------
class _AlmacenFalso:
    def __init__(self, resultado: list[DatasetDescubrible]) -> None:
        self._resultado = resultado
        self.visto: dict[str, Any] = {}

    def buscar(
        self, vector: tuple[float, ...], texto: str | None = None, *, limite: int = 20, **_: Any
    ) -> list[tuple[DatasetDescubrible, float]]:
        self.visto = {"vector": vector, "texto": texto, "limite": limite}
        return [(d, 0.7) for d in self._resultado]

    def contar(self, vector: tuple[float, ...], texto: str | None = None, **_: Any) -> int:
        return len(self._resultado)


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
    assert fila["parecido"] == 0.7  # el parecido se surte por candidato (el cliente juzga)
    assert almacen.visto["limite"] == 5 and almacen.visto["texto"] == "dónde hay agua"
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


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_buscar_hibrido_trae_match_lexico_que_el_vector_no_ranquea() -> None:
    assert URL_PG
    psycopg = pytest.importorskip("psycopg")

    with psycopg.connect(URL_PG, autocommit=True) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE")

    almacen = AlmacenDescubrimiento(URL_PG, dim=3)
    agua = _ds("agua", "Cuerpos de agua")  # alineado con el vector de consulta
    contrato = _ds("contrato", "Contratación pública estatal", protocolo="socrata")  # ortogonal
    almacen.reemplazar(
        "socrata", [agua, contrato], {"agua": (1.0, 0.0, 0.0), "contrato": (0.0, 0.0, 1.0)}
    )
    # vector (1,0,0) alineado con «agua»; texto «contratación pública» (plainto_tsquery exige TODOS
    # los lexemas, ambos en el título de contrato). El vector trae agua; el FTS trae contrato
    # (con su vector bajo el piso). El híbrido debe traer AMBOS.
    hallados = almacen.buscar((1.0, 0.0, 0.0), "contratación pública", piso=0.5, limite=10)
    ids = {d.id_socrata for d, _ in hallados}
    assert "agua" in ids  # por el vector
    assert "contrato" in ids  # por el FTS (ts_rank), aunque su vector está bajo el piso


# --- WS2: honestidad de error en el conector del catálogo ---------------------------------------
def test_codigo_catalogo_distingue_caida_de_bug() -> None:
    from terranova.almacen_descubrimiento import _codigo_catalogo

    class OperationalError(Exception): ...  # como psycopg: la base se cayó

    class DataException(Exception): ...  # como pgvector: dimensión incompatible (bug propio)

    assert _codigo_catalogo(OperationalError()) == "fuente_no_disponible"
    assert _codigo_catalogo(TimeoutError()) == "fuente_no_disponible"
    assert _codigo_catalogo(DataException()) == "error_interno"
    assert _codigo_catalogo(KeyError()) == "error_interno"


class _AlmacenRevienta:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def buscar(self, *a: Any, **k: Any) -> Any:
        raise self._exc

    def contar(self, *a: Any, **k: Any) -> int:
        return 0


@pytest.mark.anyio
async def test_conector_mapea_bug_a_error_interno_no_a_caida() -> None:
    class DataException(Exception): ...

    con = ConectorCatalogo(_AlmacenRevienta(DataException("dim")), _EmbedderFalso())  # type: ignore[arg-type]
    with pytest.raises(ErrorConector) as exc:
        await con.llamar("buscar_catalogo", {"consulta": "agua"})
    assert exc.value.codigo == "error_interno"  # bug propio, no «fuente caída»


@pytest.mark.anyio
async def test_conector_mapea_caida_a_fuente_no_disponible() -> None:
    class OperationalError(Exception): ...

    con = ConectorCatalogo(_AlmacenRevienta(OperationalError("down")), _EmbedderFalso())  # type: ignore[arg-type]
    with pytest.raises(ErrorConector) as exc:
        await con.llamar("buscar_catalogo", {"consulta": "agua"})
    assert exc.value.codigo == "fuente_no_disponible"


# --- WS4: blindaje de G6 -----------------------------------------------------------------------
def test_recorta_parecido_a_0_1() -> None:
    from terranova.almacen_descubrimiento import _recorta

    assert _recorta(-0.3) == 0.0  # coseno ortogonal/negativo → 0
    assert _recorta(1.5) == 1.0
    assert _recorta(0.42) == 0.42


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_huella_de_modelo_no_se_mezcla() -> None:
    assert URL_PG
    psycopg = pytest.importorskip("psycopg")

    with psycopg.connect(URL_PG, autocommit=True) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE")

    alm = AlmacenDescubrimiento(URL_PG, dim=3)
    alm.reemplazar("icde", [_ds("a", "agua")], {"a": (1.0, 0.0, 0.0)}, modelo="modelo-A")
    assert alm.modelo_indexado() == ("modelo-A", 3)
    # el mismo modelo: ok (otro catálogo)
    alm.reemplazar(
        "socrata", [_ds("b", "x", protocolo="socrata")], {"b": (1.0, 0.0, 0.0)}, modelo="modelo-A"
    )
    # otro modelo con la misma dim: se rechaza (no mezclar, ADR-0028)
    with pytest.raises(ValueError, match="no se puede mezclar"):
        alm.reemplazar("icde", [_ds("c", "y")], {"c": (1.0, 0.0, 0.0)}, modelo="modelo-B")


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_cache_de_vectores_por_huella() -> None:
    assert URL_PG
    psycopg = pytest.importorskip("psycopg")

    with psycopg.connect(URL_PG, autocommit=True) as c:
        c.execute(f"DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE")

    alm = AlmacenDescubrimiento(URL_PG, dim=3)
    assert alm.vectores_por_huella(["h1"]) == {}
    alm.guardar_vectores({"h1": (1.0, 0.0, 0.5), "h2": (0.0, 1.0, 0.0)})
    alm.guardar_vectores({"h2": (0.0, 0.0, 1.0)})  # re-guardar la misma huella la pisa
    assert alm.vectores_por_huella(["h1", "h2", "h3"]) == {
        "h1": (1.0, 0.0, 0.5),
        "h2": (0.0, 0.0, 1.0),
    }
