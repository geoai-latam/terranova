"""G3 (ADR-0024): el plan de consulta de las copias, el conector `copia` y el almacén en PostGIS.

Las pruebas del plan y del conector no usan red ni base. Las del almacén corren solo con
`TERRANOVA_PG_PRUEBAS=postgresql://…` (en CI, el job de Postgres).
"""

import os
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from terranova.catalogo import cargar
from terranova.conector import ErrorConector
from terranova.copias import (
    AlmacenCopias,
    ConectorCopia,
    ErrorCopia,
    Version,
    duracion,
    plan_de_consulta,
)

CATALOGO = cargar()
SECOP = CATALOGO.fuentes["cce.secop2.contratos_copia"]
URL_PG = os.environ.get("TERRANOVA_PG_PRUEBAS")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# --- plan de consulta ---------------------------------------------------------------------------


def test_la_entrada_va_como_parametro_nunca_en_el_texto() -> None:
    malicioso = "x'); DROP TABLE copia.versiones; --"
    plan = plan_de_consulta(
        SECOP,
        {
            "texto": malicioso,
            "filtros": {"ciudad": malicioso},
            "select": ["id_contrato"],
            "limite": 5,
        },
    )
    assert malicioso not in plan.sql and "DROP" not in plan.sql
    assert plan.parametros == (malicioso, malicioso, 5)  # filtro, texto y límite, en ese orden
    assert "plainto_tsquery('spanish', %s)" in plan.sql and plan.sql_total is not None


def test_solo_columnas_de_la_lista_blanca() -> None:
    for argumentos in (
        {"select": ["documento_proveedor"]},
        {"filtros": {"documento_proveedor": "123"}},
        {"order": ["-documento_proveedor"]},
        {"agregados": {"n": "sum:documento_proveedor"}},
    ):
        with pytest.raises(ErrorCopia, match="lista blanca"):
            plan_de_consulta(SECOP, argumentos)


def test_agregados_de_un_vocabulario_cerrado() -> None:
    plan = plan_de_consulta(
        SECOP,
        {
            "select": ["ciudad"],
            "group": ["ciudad"],
            "agregados": {"contratos": "count", "mediana": "median:valor_del_contrato"},
            "order": ["-contratos"],
        },
    )
    assert 'count(*) AS "contratos"' in plan.sql
    assert 'percentile_cont(0.5) WITHIN GROUP (ORDER BY "valor_del_contrato")' in plan.sql
    assert 'ORDER BY "contratos" DESC' in plan.sql and plan.sql_total is None
    with pytest.raises(ErrorCopia, match="agregado desconocido"):
        plan_de_consulta(SECOP, {"agregados": {"x": "pg_sleep:valor_del_contrato"}})
    with pytest.raises(ErrorCopia, match="van en `group`"):
        plan_de_consulta(SECOP, {"select": ["ciudad"], "agregados": {"n": "count"}})


def test_el_limite_tiene_tope() -> None:
    assert plan_de_consulta(SECOP, {"limite": 10_000_000}).limite == 1_000


def test_duracion_iso() -> None:
    assert duracion("P2D") == timedelta(days=2)
    assert duracion("PT6H") == timedelta(hours=6)
    assert duracion("P1Y") == timedelta(days=366)


# --- conector -----------------------------------------------------------------------------------


class AlmacenFalso:
    def __init__(
        self, version: Version | None, filas: list[dict[str, Any]], total: int | None
    ) -> None:
        self.version, self.filas, self.total = version, filas, total

    def vigente(self, tabla: str) -> Version | None:
        return self.version

    def consultar(self, plan: Any) -> tuple[list[dict[str, Any]], int | None]:
        return self.filas, self.total


def _version(edad: timedelta) -> Version:
    return Version(
        SECOP.id,
        "secop_contratos",
        "v1",
        10,
        "sha256:x",
        date(2026, 7, 1),
        datetime.now(UTC) - edad,
        repetidas=3,
    )


@pytest.mark.anyio
async def test_el_conector_dice_que_es_copia_su_fecha_y_si_vino_todo() -> None:
    filas = [{"id_contrato": "CO1.PCCNTR.1", "fecha_de_firma": date(2026, 8, 1)}]
    c = ConectorCopia(CATALOGO, AlmacenFalso(_version(timedelta(hours=3)), filas, 148))  # type: ignore[arg-type]
    sc = await c.llamar("consultar_copia", {"tabla": "secop_contratos", "texto": "farmacia"})
    h = sc["facts"]
    assert h["servido_desde"] == "copia" and h["copia"]["ventana_desde"] == "2026-07-01"
    assert h["copia"]["repetidas_en_la_fuente"] == 3
    assert h["completitud"] == {"vistos": 1, "total": 148, "truncado": True}
    assert sc["artifacts"][0]["rows"][0]["fecha_de_firma"] == "2026-08-01"


@pytest.mark.anyio
async def test_una_copia_vencida_sale_obsoleta() -> None:
    vieja = _version(timedelta(days=5))  # el SLA de SECOP es P2D
    c = ConectorCopia(CATALOGO, AlmacenFalso(vieja, [], 0))  # type: ignore[arg-type]
    sc = await c.llamar("consultar_copia", {"tabla": "secop_contratos", "texto": "farmacia"})
    assert sc["facts"]["servido_desde"] == "obsoleto"


@pytest.mark.anyio
async def test_sin_copia_construida_es_fuente_no_disponible() -> None:
    c = ConectorCopia(CATALOGO, AlmacenFalso(None, [], None))  # type: ignore[arg-type]
    with pytest.raises(ErrorConector) as exc:
        await c.llamar("consultar_copia", {"tabla": "secop_contratos", "texto": "farmacia"})
    assert exc.value.codigo == "fuente_no_disponible"
    with pytest.raises(ErrorConector, match="no hay copia"):
        await c.llamar("consultar_copia", {"tabla": "no_existe"})


# --- almacén en PostGIS -------------------------------------------------------------------------


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_construir_publicar_buscar_y_podar() -> None:
    assert URL_PG
    import psycopg

    with psycopg.connect(URL_PG, autocommit=True) as c:  # base de pruebas: se parte de cero
        c.execute("DROP SCHEMA IF EXISTS copia CASCADE")
    almacen = AlmacenCopias(URL_PG)

    def fila(i: int, objeto: str) -> dict[str, Any]:
        return {
            "id_contrato": f"CO1.PCCNTR.{i}",
            "nombre_entidad": "E",
            "nit_entidad": "1",
            "ciudad": "Chía",
            "objeto_del_contrato": objeto,
            "valor_del_contrato": str(i * 10),
            "fecha_de_firma": f"2026-08-{i:02d}T00:00:00.000",
        }

    paginas = [
        [fila(1, "Auxiliar de farmacia"), fila(2, "Vías terciarias")],
        [fila(2, "repetida"), fila(3, "Alimentación de escolares")],
    ]
    v1 = almacen.construir(SECOP, iter(paginas), date(2026, 8, 1))
    assert (v1.filas, v1.repetidas) == (3, 1)
    assert almacen.vigente("secop_contratos") == v1

    # todas las palabras, sin importar mayúsculas ni la tilde de «vías» (stemmer de español)
    plan = plan_de_consulta(SECOP, {"texto": "VIAS terciarias", "select": ["id_contrato"]})
    filas, total = almacen.consultar(plan)
    assert [f["id_contrato"] for f in filas] == ["CO1.PCCNTR.2"] and total == 1

    v2 = almacen.construir(SECOP, iter([[fila(9, "otra")]]), None)
    assert almacen.vigente("secop_contratos") == v2 and v2.huella != v1.huella
    assert almacen.consultar(plan) == ([], 0)  # la vista ya apunta a la versión nueva
    almacen.construir(SECOP, iter([[fila(8, "y otra")]]), None)
    assert almacen.podar("secop_contratos") == [v1.version]  # quedan la vigente y la anterior
