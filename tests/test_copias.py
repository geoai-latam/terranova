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
    MapaComex,
    Version,
    agregar_comex_csv,
    anio_mes_dane,
    duracion,
    ewkt,
    filas_de_acumulador,
    fusionar_mes,
    num_europeo,
    plan_de_consulta,
)

CATALOGO = cargar()
SECOP = CATALOGO.fuentes["cce.secop2.contratos_copia"]
URL_PG = os.environ.get("TERRANOVA_PG_PRUEBAS")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


# --- plan de consulta ---------------------------------------------------------------------------


def test_contiene_todas_las_palabras_sin_tildes_ni_comodines() -> None:
    plan = plan_de_consulta(
        SECOP,
        {
            "contiene": {"nombre_entidad": "Alcaldía  CHÍA 100%_"},
            "select": ["nombre_entidad", "nit_entidad"],
            "group": ["nombre_entidad", "nit_entidad"],
            "agregados": {"contratos": "count"},
        },
    )
    assert plan.sql.count("LIKE %s") == 3 and "translate(lower(" in plan.sql
    # lo que escribe el usuario va como parámetro y sus comodines no comodinean
    assert plan.parametros[:3] == ("%alcaldia%", "%chia%", r"%100\%\_%")
    with pytest.raises(ErrorCopia, match="vacío"):
        plan_de_consulta(SECOP, {"contiene": {"nombre_entidad": "   "}})
    with pytest.raises(ErrorCopia, match="lista blanca"):
        plan_de_consulta(SECOP, {"contiene": {"columna_rara": "x"}})


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
    psycopg = pytest.importorskip("psycopg")
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


@pytest.mark.anyio
async def test_una_copia_que_no_dice_su_fecha_no_se_sirve_como_actual() -> None:
    from terranova.ejecutor import Ejecutor
    from terranova.errores import ErrorEjecucion

    class SinFecha:
        async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
            return {"artifacts": [{"kind": "table", "rows": [{"id_contrato": "x"}]}], "facts": {}}

    ej = Ejecutor(CATALOGO, {"copia": SinFecha()})
    with pytest.raises(ErrorEjecucion) as exc:
        await ej.ejecutar("secop_contratos_buscar", {"texto": "farmacia"}, plan="evaluacion")
    assert exc.value.codigo == "fuente_respuesta_invalida"


# --- ingesta de los microdatos de comercio exterior del DANE (origen zip_dane) ------------------

_MAPA_IMPO = MapaComex(
    subpartida_csv="NABAN",
    pais_csv="PAISGEN",
    pais_col="pais_origen",
    medidas={"valor_cif_pesos": "VACIP", "valor_fob_usd": "VAFODO"},
)
_MAPA_EXPO = MapaComex(
    subpartida_csv="POSAR",
    pais_csv="PAIS",
    pais_col="pais_destino",
    medidas={"valor_fob_usd": "FOBDOL", "valor_fob_pesos": "FOBPES"},
)
_HEADER = "FECH;NABAN;PAISGEN; VACIP ; VACID ; VAFODO ; PNK ; CANU "
# dos líneas del mismo mes/subpartida/país: se suman dentro de un archivo
_CSV_NOV = (
    _HEADER + "\r\n"
    "2511;8517130000;156; 1.000,50 ; 100,25 ; 90,00 ; 10,00 ; 5,00 \r\n"
    "2511;8517130000;156; 2.000,00 ; 200,00 ; 180,00 ; 20,00 ; 10,00 \r\n"
    "2511;8703239090;276; 500.000,00 ; 1.234,56 ; -   ; 7,00 ; 1,00 \r\n"
)
_CSV_OCT = _HEADER + "\r\n2510;8517130000;156; 9,00 ; 9,00 ; 9,00 ; 9,00 ; 9,00 \r\n"
# expo: columnas distintas (POSAR, PAIS, FOBDOL, FOBPES)
_CSV_EXPO = "FECH;POSAR;PAIS; FOBDOL ; FOBPES \r\n2503;0901110000;842; 1.000,00 ; 4.000.000,00 \r\n"


def test_num_europeo() -> None:
    assert num_europeo("285.792,00") == 285792.0
    assert num_europeo(" 1.234,56 ") == 1234.56
    assert num_europeo("54000,00") == 54000.0
    assert num_europeo("-   ") == 0.0
    assert num_europeo("") == 0.0
    assert num_europeo("0") == 0.0


def test_anio_mes_dane() -> None:
    assert anio_mes_dane("2511") == (2025, 11)
    assert anio_mes_dane("2601") == (2026, 1)
    with pytest.raises(ValueError, match="FECH"):
        anio_mes_dane("25")


def test_agregar_comex_csv_suma_por_subpartida_y_pais() -> None:
    acc: dict[Any, Any] = {}
    n = agregar_comex_csv(_CSV_NOV, acc, _MAPA_IMPO)
    assert n == 3
    tel = acc[(2025, 11, "8517130000", "156")]
    assert tel["valor_cif_pesos"] == 3000.5  # 1000,50 + 2000,00
    assert tel["valor_fob_usd"] == 270.0
    assert tel["lineas"] == 2.0
    carro = acc[(2025, 11, "8703239090", "276")]
    assert carro["valor_fob_usd"] == 0.0  # «-   » es cero
    assert carro["lineas"] == 1.0


def test_agregar_comex_csv_mapa_expo() -> None:
    # el mismo motor sirve exportaciones con otras columnas (POSAR/PAIS/FOBDOL/FOBPES)
    acc: dict[Any, Any] = {}
    agregar_comex_csv(_CSV_EXPO, acc, _MAPA_EXPO)
    café = acc[(2025, 3, "0901110000", "842")]
    assert café["valor_fob_usd"] == 1000.0
    assert café["valor_fob_pesos"] == 4000000.0


def test_agregar_comex_csv_exige_columnas() -> None:
    with pytest.raises(ValueError, match="faltan columnas"):
        agregar_comex_csv("FECH;NABAN\r\n2511;8517130000\r\n", {}, _MAPA_IMPO)


def test_fusionar_mes_deduplica_el_mes_repetido() -> None:
    acc: dict[Any, Any] = {}
    fusionar_mes(_CSV_NOV, acc, _MAPA_IMPO)
    fusionar_mes(_CSV_NOV, acc, _MAPA_IMPO)  # el mismo mes otra vez: reemplaza, NO duplica
    assert acc[(2025, 11, "8517130000", "156")]["valor_cif_pesos"] == 3000.5


def test_fusionar_mes_conserva_otros_meses() -> None:
    acc: dict[Any, Any] = {}
    fusionar_mes(_CSV_NOV, acc, _MAPA_IMPO)
    fusionar_mes(_CSV_OCT, acc, _MAPA_IMPO)  # otro mes: se conserva
    fusionar_mes(_CSV_NOV, acc, _MAPA_IMPO)  # noviembre otra vez: reemplaza nov, octubre intacto
    assert (2025, 10, "8517130000", "156") in acc
    assert acc[(2025, 10, "8517130000", "156")]["valor_fob_usd"] == 9.0
    assert acc[(2025, 11, "8517130000", "156")]["valor_cif_pesos"] == 3000.5


def test_filas_de_acumulador_da_la_lista_blanca() -> None:
    acc: dict[Any, Any] = {}
    agregar_comex_csv(_CSV_NOV, acc, _MAPA_IMPO)
    filas = {f["clave"]: f for f in filas_de_acumulador(acc, _MAPA_IMPO)}
    tel = filas["202511-8517130000-156"]
    assert tel["anio"] == "2025"  # str, como la columna de la ficha
    assert tel["mes"] == 11
    assert tel["subpartida"] == "8517130000"
    assert tel["pais_origen"] == "156"
    assert tel["valor_cif_pesos"] == 3000.5
    assert tel["lineas"] == 2  # int


# --- copias espaciales de capas ArcGIS (origen arcgis) ------------------------------------------

RUNAP = CATALOGO.fuentes["pnn.runap"]
UPRA = CATALOGO.fuentes["upra.rango_precios_nacional"]
_CUADRO = [[[-74.0, 4.0], [-73.0, 4.0], [-73.0, 5.0], [-74.0, 5.0], [-74.0, 4.0]]]
# un «moño»: el anillo se cruza a sí mismo, inválido (la copia lo repara al cargar)
_MONO = [[[-75.0, 6.0], [-74.0, 7.0], [-74.0, 6.0], [-75.0, 7.0], [-75.0, 6.0]]]


def test_plan_espacial_por_punto_y_por_zona() -> None:
    plan = plan_de_consulta(
        RUNAP, {"punto": ["-73.75", "4.55"], "select": ["ap_nombre"], "geometria": "simplificada"}
    )
    assert "ST_Intersects(_geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))" in plan.sql
    assert plan.parametros[:2] == (-73.75, 4.55) and plan.geometria
    assert "ST_SimplifyPreserveTopology(_geom, 0.0005)" in plan.sql
    zona = plan_de_consulta(RUNAP, {"bbox": [-74.5, 4.0, -73.5, 5.0]})
    assert "ST_MakeEnvelope(%s, %s, %s, %s, 4326)" in zona.sql and not zona.geometria
    assert '"_geom"' not in zona.sql and "*" not in zona.sql  # sin select: la lista blanca
    assert zona.sql_total is not None and zona.parametros_total == (-74.5, 4.0, -73.5, 5.0)


def test_plan_espacial_rechaza_lo_que_no_es() -> None:
    for argumentos, error in (
        ({"punto": ["x", "4"]}, "2 números"),
        ({"punto": [1.0, float("nan")]}, "2 números"),
        ({"bbox": [-73.0, 4.0, -74.0, 5.0]}, "oeste, sur, este, norte"),
        ({"punto": [1, 2], "bbox": [0, 0, 1, 1]}, "no van juntos"),
        ({"geometria": "toda"}, "geometría desconocida"),
        ({"agregados": {"n": "count"}, "geometria": "completa"}, "no sale geometría"),
    ):
        with pytest.raises(ErrorCopia, match=error):
            plan_de_consulta(RUNAP, argumentos)
    with pytest.raises(ErrorCopia, match="no tiene geometría"):
        plan_de_consulta(SECOP, {"punto": [-74, 4]})


def test_ewkt_de_geojson() -> None:
    assert ewkt({"type": "Point", "coordinates": [-74.5, 4.25, 30.0]}) == (
        "SRID=4326;POINT(-74.5 4.25)"  # solo lon y lat
    )
    assert ewkt({"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}) == (
        "SRID=4326;POLYGON((0.0 0.0,1.0 0.0,1.0 1.0,0.0 0.0))"
    )
    multi = ewkt({"type": "MultiPolygon", "coordinates": [_CUADRO, _CUADRO]})
    assert multi.startswith("SRID=4326;MULTIPOLYGON(((-74.0 4.0,") and multi.count("((") == 2
    with pytest.raises(ErrorCopia, match="no sabe guardar"):
        ewkt({"type": "GeometryCollection", "geometries": []})


def test_fecha_de_arcgis_en_epoch_ms() -> None:
    from terranova.copias import _convertir

    assert _convertir(1309410000000, "date") == "2011-06-30"  # 2011-06-30T05:00Z
    assert _convertir("2011-06-30T00:00:00.000", "date") == "2011-06-30"


class _Respuesta:
    def __init__(self, datos: dict[str, Any]) -> None:
        self.datos = datos

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.datos


class ArcgisFalso:
    """Una capa de `n` rasgos (claves 1, 4, 7…: con huecos) que pagina como un MapServer por
    `where clave > x`; anota cada petición. `desordenada` ignora el `where` (repite la página)."""

    def __init__(self, n: int, conteo: dict[str, Any], *, desordenada: bool = False) -> None:
        self.n, self.conteo, self.desordenada = n, conteo, desordenada
        self.pedidos: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, params: dict[str, Any]) -> _Respuesta:
        self.pedidos.append((url, params))
        if params.get("returnCountOnly"):
            return _Respuesta(self.conteo)
        donde = params["where"]
        desde = (
            -1 if donde.endswith("IS NOT NULL") or self.desordenada else int(donde.split(">")[1])
        )
        claves = [c for c in (3 * i + 1 for i in range(self.n)) if c > desde]
        rasgos = [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": _CUADRO},
                "properties": {"objectid": c, "ap_nombre": f"Área {c}", "fecha_inscrita": 0},
            }
            for c in claves[: params["resultRecordCount"]]
        ]
        return _Respuesta({"type": "FeatureCollection", "features": rasgos})


def test_descargar_arcgis_pagina_por_la_clave_hasta_vaciar() -> None:
    from terranova.copias import descargar_arcgis

    http = ArcgisFalso(60, {"count": 60})
    paginas = list(descargar_arcgis(RUNAP, cliente=http, pausa_s=0))
    assert [len(p) for p in paginas] == [25, 25, 10]  # `por_pagina` de la ficha: 25
    url, params = http.pedidos[1]
    assert url == f"{RUNAP.url}/0/query" and params["orderByFields"] == "objectid"
    assert params["outSR"] == "4326" and "maxAllowableOffset" not in params  # RUNAP: completa
    assert set(params["outFields"].split(",")) == set(RUNAP.campos)
    assert paginas[0][0]["_geom"]["type"] == "Polygon" and paginas[0][0]["ap_nombre"] == "Área 1"
    # por la clave, no por desplazamiento: la segunda página arranca tras la última clave vista
    # sin paréntesis ni `1=1`: el geoportal del DANE rechaza los dos con un 500
    assert params["where"] == "objectid IS NOT NULL"
    assert http.pedidos[2][1]["where"] == "objectid > 73"
    assert "resultOffset" not in http.pedidos[2][1]
    vistas = [f["objectid"] for p in paginas for f in p]
    assert len(set(vistas)) == 60  # ni repetidas ni perdidas pese a los huecos


def test_descargar_arcgis_simplifica_si_la_ficha_lo_declara() -> None:
    from terranova.copias import descargar_arcgis

    assert UPRA.copia is not None
    http = ArcgisFalso(0, {"count": 0})
    assert list(descargar_arcgis(UPRA, cliente=http, pausa_s=0)) == []
    assert http.pedidos[1][1]["maxAllowableOffset"] == str(UPRA.copia.tolerancia)


def test_descargar_arcgis_no_publica_una_copia_a_medias() -> None:
    from terranova.copias import descargar_arcgis

    with pytest.raises(ErrorCopia, match="dice 61 elementos y llegaron 60"):
        list(descargar_arcgis(RUNAP, cliente=ArcgisFalso(60, {"count": 61}), pausa_s=0))
    # una capa que no respeta `clave > x` repetiría páginas sin fin: se corta con error
    with pytest.raises(ErrorCopia, match="no pagina por objectid"):
        list(descargar_arcgis(RUNAP, cliente=ArcgisFalso(60, {}, desordenada=True), pausa_s=0))
    # si el servicio no sabe contar, se copia igual (sin esa verificación)
    sin_conteo = ArcgisFalso(3, {"error": {"code": 500}})
    assert sum(len(p) for p in descargar_arcgis(RUNAP, cliente=sin_conteo, pausa_s=0)) == 3


@pytest.mark.anyio
async def test_el_conector_da_la_geometria_como_coleccion_de_rasgos() -> None:
    punto = '{"type": "Point", "coordinates": [-73.8, 4.7]}'
    filas = [{"ap_nombre": "Chingaza", "_geojson": punto}]
    version = Version(RUNAP.id, "runap", "v1", 1936, "sha256:x", None, datetime.now(UTC))
    c = ConectorCopia(CATALOGO, AlmacenFalso(version, filas, 1))  # type: ignore[arg-type]
    sc = await c.llamar(
        "consultar_copia", {"tabla": "runap", "punto": [-73.75, 4.55], "geometria": "simplificada"}
    )
    art = sc["artifacts"][0]
    assert art["kind"] == "feature_collection" and art["crs"] == "EPSG:4326"
    rasgo = art["data"]["features"][0]
    assert rasgo["properties"] == {"ap_nombre": "Chingaza"}
    assert rasgo["geometry"]["coordinates"] == [-73.8, 4.7]


def test_solo_vencidas_rehace_la_que_va_por_la_mitad_del_sla() -> None:
    from terranova.copias import toca_actualizar

    ahora = datetime(2026, 10, 27, tzinfo=UTC)

    def de_hace(dias: int) -> Version:
        return Version(RUNAP.id, "runap", "v", 1, "h", None, ahora - timedelta(days=dias))

    assert toca_actualizar(RUNAP, None, ahora)  # sin copia: se hace
    assert not toca_actualizar(RUNAP, de_hace(10), ahora)  # SLA P1M ≈ 31 días: la mitad, 15,5
    assert toca_actualizar(RUNAP, de_hace(16), ahora)


def test_la_capa_va_con_el_origen_arcgis() -> None:
    from pydantic import ValidationError

    from terranova.catalogo import Copia

    with pytest.raises(ValidationError, match="`capa` va con el origen `arcgis`"):
        Copia(origen="arcgis", tabla="t", clave="objectid")
    with pytest.raises(ValidationError, match="`tolerancia` solo aplica"):
        Copia(origen="socrata", conjunto="abcd-1234", tabla="t", clave="id", tolerancia=0.0001)


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_copia_espacial_en_postgis() -> None:
    assert URL_PG
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(URL_PG, autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS copia CASCADE")
    almacen = AlmacenCopias(URL_PG)

    def area(i: int, anillos: Any) -> dict[str, Any]:
        return {
            "objectid": i,
            "ap_nombre": f"Área {i}",
            "fecha_inscrita": 1309410000000,
            "_geom": {"type": "Polygon", "coordinates": anillos},
        }

    v = almacen.construir(RUNAP, iter([[area(1, _CUADRO), area(2, _MONO)]]), None)
    assert v.filas == 2

    def consultar(argumentos: dict[str, Any]) -> tuple[list[dict[str, Any]], int | None]:
        return almacen.consultar(plan_de_consulta(RUNAP, argumentos))

    filas, total = consultar({"punto": [-73.5, 4.5], "select": ["ap_nombre", "fecha_inscrita"]})
    assert filas == [{"ap_nombre": "Área 1", "fecha_inscrita": date(2011, 6, 30)}] and total == 1
    assert consultar({"punto": [-80.0, 0.0]}) == ([], 0)
    # el moño se reparó al cargar: el cruce no falla y lo encuentra
    filas, total = consultar({"bbox": [-76.0, 3.0, -72.0, 8.0], "order": ["objectid"]})
    assert [f["objectid"] for f in filas] == [1, 2] and total == 2
    filas, _ = consultar({"punto": [-73.5, 4.5], "geometria": "completa", "select": ["objectid"]})
    assert '"Polygon"' in filas[0]["_geojson"]

    def rota() -> Any:
        yield [area(3, _CUADRO)]
        raise ErrorCopia("la capa se cortó")

    with pytest.raises(ErrorCopia):
        almacen.construir(RUNAP, rota(), None)
    with psycopg.connect(URL_PG, autocommit=True) as c:
        tablas = c.execute(
            "SELECT count(*) FROM pg_tables WHERE schemaname = 'copia' AND tablename LIKE 'runap_%'"
        ).fetchone()
    assert tablas == (1,)  # la que falló no quedó huérfana; la vigente sigue
    assert almacen.vigente("runap") == v


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_la_reparacion_va_por_tandas_y_deja_los_poligonos_enormes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """ST_MakeValid de un polígono enorme pide ~1 GB: ese queda como viene, con aviso."""
    import terranova.copias as copias

    assert URL_PG
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(URL_PG, autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS copia CASCADE")
    almacen = AlmacenCopias(URL_PG)
    monkeypatch.setattr(copias, "REPARAR_POR_TANDA", 2)  # claves 1, 4, 7: tres tandas
    monkeypatch.setattr(copias, "REPARAR_HASTA_VERTICES", 4)  # el moño tiene 5: «enorme»

    def area(i: int, anillos: Any) -> dict[str, Any]:
        return {
            "objectid": i,
            "ap_nombre": f"Área {i}",
            "_geom": {"type": "Polygon", "coordinates": anillos},
        }

    chico = [[[-75.0, 6.0], [-74.0, 7.0], [-74.0, 6.0], [-75.0, 6.0]]]  # triángulo válido (4)
    almacen.construir(RUNAP, iter([[area(1, chico), area(4, _MONO), area(7, chico)]]), None)
    assert (
        "1 polígonos inválidos de más de 4 vértices quedan como vienen" in capsys.readouterr().err
    )
    with psycopg.connect(URL_PG) as c:
        validos = c.execute(
            "SELECT objectid, ST_IsValid(_geom) FROM copia.runap ORDER BY objectid"
        ).fetchall()
    assert validos == [(1, True), (4, False), (7, True)]
    # el cruce por punto responde igual sobre el moño sin reparar
    filas, total = almacen.consultar(plan_de_consulta(RUNAP, {"punto": [-74.9, 6.5]}))
    assert total == 1 and filas[0]["objectid"] == 4


# --- origen conector: la tabla entera que da la tool del conector (xlsx del DANE) ---------------

GEIH = CATALOGO.fuentes["dane.geih_nacional"]


class ConectorFalso:
    """Un conector MCP que da una tabla y anota cómo lo llamaron."""

    def __init__(self, filas: list[dict[str, Any]], total: int | None = None) -> None:
        self.filas, self.total = filas, len(filas) if total is None else total
        self.llamadas: list[tuple[str, dict[str, Any]]] = []

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        self.llamadas.append((herramienta, argumentos))
        vistos = len(self.filas)
        return {
            "artifacts": [
                {
                    "kind": "table",
                    "columns": list(self.filas[0]) if self.filas else [],
                    "rows": self.filas,
                }
            ],
            "facts": {
                "completitud": {
                    "vistos": vistos,
                    "total": self.total,
                    "truncado": vistos < self.total,
                }
            },
        }


def test_descargar_conector_copia_la_tabla_entera_y_numera_las_filas() -> None:
    from terranova.copias import descargar_conector

    filas = [
        {"Concepto": "TD", "columna": "2026", "subcolumna": "Ene", "valor": 11.6, "otra": "x"},
        {"Concepto": "TD", "columna": "2026", "subcolumna": "Feb", "valor": 10.3, "otra": "y"},
    ]
    conector = ConectorFalso(filas)
    paginas = list(descargar_conector(GEIH, conector=conector))
    assert paginas == [
        [
            {"Concepto": "TD", "columna": "2026", "subcolumna": "Ene", "valor": 11.6, "_fila": 1},
            {"Concepto": "TD", "columna": "2026", "subcolumna": "Feb", "valor": 10.3, "_fila": 2},
        ]
    ]  # solo la lista blanca; `otra` no entra
    tool, argumentos = conector.llamadas[0]
    assert tool == "web_tabla" and argumentos["pagina"] == GEIH.url  # {url_fuente} resuelto
    assert argumentos["hoja"] == "Total nacional" and "filtros" not in argumentos
    assert argumentos["max_filas"] >= 50_000  # la tabla entera, no el tope de una consulta


def test_descargar_conector_no_publica_una_tabla_cortada_o_vacia() -> None:
    from terranova.copias import descargar_conector

    fila = {"Concepto": "TD", "columna": "2026", "subcolumna": "Ene", "valor": 11.6}
    with pytest.raises(ErrorCopia, match="cortó la tabla"):
        list(descargar_conector(GEIH, conector=ConectorFalso([fila], total=2)))
    with pytest.raises(ErrorCopia, match="tabla vacía"):
        list(descargar_conector(GEIH, conector=ConectorFalso([])))


def test_el_origen_conector_pide_conector_y_tool_y_no_lleva_filtros() -> None:
    from pydantic import ValidationError

    from terranova.catalogo import Copia

    with pytest.raises(ValidationError, match="`conector` y `tool` van con el origen"):
        Copia(origen="conector", tabla="t", clave="_fila")
    with pytest.raises(ValidationError, match="`conector` y `tool` van con el origen"):
        Copia(origen="socrata", conjunto="abcd-1234", tabla="t", clave="id", tool="web_tabla")
    with pytest.raises(ValidationError, match="los filtros van en la herramienta"):
        Copia(
            origen="conector",
            conector="web-mcp",
            tool="web_tabla",
            tabla="t",
            clave="_fila",
            argumentos={"filtros": {"ID": "05001"}},
        )
    with pytest.raises(ValidationError, match="`argumentos` solo aplica"):
        Copia(origen="socrata", conjunto="abcd-1234", tabla="t", clave="id", argumentos={"x": 1})


def test_el_filtro_toma_el_tipo_de_la_columna() -> None:
    """La GEIH guarda el año como texto («2001»); la herramienta lo recibe como número."""
    plan = plan_de_consulta(GEIH, {"filtros": {"columna": 2001}, "order": ["_fila"]})
    assert plan.parametros[:1] == ("2001",)


def test_derivado_codigo_da_el_significado_del_codigo() -> None:
    """El censo copia el código del departamento; el nombre oficial sale de la ficha."""
    from terranova.catalogo import Derivado
    from terranova.ejecutor import mapear_fila

    h = CATALOGO.herramientas["dane_poblacion_municipio"]
    deptos = {"11": "BOGOTÁ, D.C.", "25": "CUNDINAMARCA"}
    con = h.model_copy(
        update={
            "derivados": {
                "departamento_nombre": Derivado(
                    de="codigo", campo="municipio_divipola", valores=deptos
                )
            }
        }
    )
    fuente = CATALOGO.fuentes[h.fuente]
    clave = next(k for k, c in fuente.campos.items() if c.nombre == "municipio_divipola")
    assert mapear_fila(con, fuente, {clave: "11"}, None)["departamento_nombre"] == "BOGOTÁ, D.C."
    assert mapear_fila(con, fuente, {clave: "99"}, None)["departamento_nombre"] is None
    assert mapear_fila(con, fuente, {}, None)["departamento_nombre"] is None


def test_copia_arcgis_sin_geometria_no_pide_ni_guarda_geometria() -> None:
    from pydantic import ValidationError

    from terranova.catalogo import Copia
    from terranova.copias import descargar_arcgis

    assert RUNAP.copia is not None
    sin = RUNAP.model_copy(update={"copia": RUNAP.copia.model_copy(update={"geometria": False})})
    assert sin.copia is not None and not sin.copia.espacial
    http = ArcgisFalso(3, {"count": 3})
    paginas = list(descargar_arcgis(sin, cliente=http, pausa_s=0))
    assert http.pedidos[1][1]["returnGeometry"] == "false"
    assert "_geom" not in paginas[0][0] and paginas[0][0]["ap_nombre"] == "Área 1"
    with pytest.raises(ErrorCopia, match="no tiene geometría"):  # sin geometría no hay cruce
        plan_de_consulta(sin, {"punto": [-74.0, 4.6]})
    with pytest.raises(ValidationError, match="solo aplica a una capa ArcGIS"):
        Copia(origen="socrata", conjunto="abcd-1234", tabla="t", clave="id", geometria=False)


class ArcgisConRasgoRoto:
    """Una capa de 10 rasgos (claves 1..10) donde la geometría del 7 rompe la consulta: cualquier
    página que lo incluya CON geometría llega vacía, sin error (SINIC, objectid 1420608)."""

    ROTO = 7

    def __init__(self, rechaza: bool = False) -> None:
        self.pedidos: list[dict[str, Any]] = []
        self.rechaza = rechaza  # SDP: la consulta falla con 400 en vez de llegar vacía

    def get(self, url: str, params: dict[str, Any]) -> _Respuesta:
        self.pedidos.append(params)
        if params.get("returnCountOnly"):
            return _Respuesta({"count": 10})
        donde = params["where"]
        if ">=" in donde:
            desde, hasta = int(donde.split(">=")[1].split()[0]), int(donde.split("<=")[1])
            claves = list(range(desde, hasta + 1))
        else:
            desde = int(donde.split(">")[1]) if ">" in donde else 0
            claves = [c for c in range(1, 11) if c > desde][: params.get("resultRecordCount", 10)]
        con_geometria = params.get("returnGeometry") != "false"
        if con_geometria and self.ROTO in claves:
            if self.rechaza:
                return _Respuesta({"error": {"code": 400, "message": "Failed to execute query."}})
            return _Respuesta({"type": "FeatureCollection", "features": []})
        rasgos = [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": _CUADRO} if con_geometria else None,
                "properties": {"objectid": c, "ap_nombre": f"Área {c}", "fecha_inscrita": 0},
            }
            for c in claves
        ]
        return _Respuesta({"type": "FeatureCollection", "features": rasgos})


@pytest.mark.parametrize("rechaza", [False, True], ids=["vacia", "rechazada"])
def test_un_rasgo_sin_geometria_no_tumba_la_copia(
    rechaza: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    from terranova.copias import descargar_arcgis

    http = ArcgisConRasgoRoto(rechaza)
    paginas = list(descargar_arcgis(RUNAP, cliente=http, pausa_s=0))
    filas = [f for p in paginas for f in p]
    assert [f["objectid"] for f in filas] == list(range(1, 11))  # ninguno se pierde
    assert [f["objectid"] for f in filas if f["_geom"] is None] == [7]  # solo el roto
    assert "1 elementos sin geometría" in capsys.readouterr().err


def test_el_filtro_solo_va_con_una_capa_arcgis() -> None:
    from pydantic import ValidationError

    from terranova.catalogo import Copia

    with pytest.raises(ValidationError, match="`filtro` solo aplica a una capa ArcGIS"):
        Copia(origen="socrata", conjunto="abcd-1234", tabla="t", clave="id", filtro="a = 1")
    with pytest.raises(ValidationError):  # nada de comillas dobles ni punto y coma
        Copia(origen="arcgis", capa=0, tabla="t", clave="id", filtro='a = "x"; drop')


# --- un GeoJSON publicado como archivo (origen geojson) -------------------------------------------


class GeojsonFalso:
    """Un CKAN que sirve GeoJSON exportados de escritorio: sin OBJECTID, en la cartesiana de
    Bogotá."""

    def __init__(self, archivos: dict[str, list[dict[str, Any]]]) -> None:
        self.archivos = archivos
        self.pedidos: list[str] = []

    def get(self, url: str) -> _Respuesta:
        self.pedidos.append(url)
        return _Respuesta({"type": "FeatureCollection", "features": self.archivos[url]})


_CARMAGBOG = (
    "+proj=tmerc +lat_0=4.680486111 +lon_0=-74.14659167 +k=1 +x_0=92334.879 +y_0=109320.965 "
    "+a=6380687 +rf=298.257222101 +units=m +no_defs"
)


def _amenazas() -> Any:
    from terranova.catalogo import Campo, Copia

    return RUNAP.model_copy(
        update={
            "id": "sdp.prueba_geojson",
            "copia": Copia(
                origen="geojson",
                descargas=["https://ckan/urbano.geojson", "https://ckan/rural.geojson"],
                proyeccion=_CARMAGBOG,
                tabla="prueba_geojson",
                clave="_fila",
            ),
            "campos": {
                "_fila": Campo(nombre="id_elemento", tipo="int", desc="orden del rasgo"),
                "CATEGORIZA": Campo(nombre="categoria", tipo="str", desc="categoría"),
            },
        }
    )


def _cuadro_bogota(x: float, y: float, categoria: str) -> dict[str, Any]:
    anillo = [[x, y], [x + 100, y], [x + 100, y + 100], [x, y + 100], [x, y]]
    return {
        "type": "Feature",
        "properties": {"CATEGORIZA": categoria, "OTRA": "no va"},
        "geometry": {"type": "Polygon", "coordinates": [anillo]},
    }


def test_geojson_numera_los_rasgos_sin_clave_entre_archivos() -> None:
    from terranova.copias import descargar_geojson

    http = GeojsonFalso(
        {
            "https://ckan/urbano.geojson": [_cuadro_bogota(92300, 109300, "1")] * 3,
            "https://ckan/rural.geojson": [_cuadro_bogota(80000, 90000, "3")],
        }
    )
    filas = [f for p in descargar_geojson(_amenazas(), cliente=http) for f in p]
    assert [f["_fila"] for f in filas] == [1, 2, 3, 4]
    assert [f["CATEGORIZA"] for f in filas] == ["1", "1", "1", "3"]
    assert "OTRA" not in filas[0]  # solo la lista blanca
    assert filas[0]["_geom"]["coordinates"][0][0] == [92300, 109300]  # tal cual: reproyecta PostGIS


def test_geojson_vacio_no_se_publica() -> None:
    from terranova.copias import descargar_geojson

    http = GeojsonFalso({"https://ckan/urbano.geojson": [], "https://ckan/rural.geojson": []})
    with pytest.raises(ErrorCopia, match="sin rasgos"):
        list(descargar_geojson(_amenazas(), cliente=http))


def test_la_proyeccion_solo_va_con_geojson() -> None:
    from pydantic import ValidationError

    from terranova.catalogo import Copia
    from terranova.copias import _geograficas

    with pytest.raises(ValidationError, match="`proyeccion` solo aplica"):
        Copia(origen="arcgis", capa=0, tabla="t", clave="id", proyeccion=_CARMAGBOG)
    with pytest.raises(ValidationError, match="exige `descargas`"):
        Copia(origen="geojson", tabla="t", clave="id")
    with pytest.raises(ValidationError):  # una cadena proj, nada más
        Copia(origen="geojson", descargas=["u"], tabla="t", clave="id", proyeccion="'; drop")
    assert _geograficas(_CARMAGBOG) == "+proj=longlat +a=6380687 +rf=298.257222101 +no_defs"


class CsvFalso:
    """Un servidor de archivos que sirve CSV en bytes (con BOM, como los del IDEAM)."""

    def __init__(self, archivos: dict[str, str]) -> None:
        self.archivos = archivos

    def get(self, url: str) -> Any:
        contenido = self.archivos[url].encode("utf-8-sig")

        class _R:
            content = contenido

            def raise_for_status(self) -> None:
                return None

        return _R()


def _alertas() -> Any:
    from terranova.catalogo import Campo, Copia

    return RUNAP.model_copy(
        update={
            "id": "ideam.prueba_csv",
            "copia": Copia(
                origen="csv",
                descargas=["https://bart/a.csv", "https://bart/b.csv"],
                separador=";",
                ceros={"COD_DANE": 5},
                tabla="prueba_csv",
                clave="_fila",
            ),
            "campos": {
                "COD_DANE": Campo(nombre="municipio_divipola", tipo="str", desc="DIVIPOLA"),
                "TEXTO_AMENAZA": Campo(nombre="nivel", tipo="str", desc="nivel"),
                "FECHA_EJECUCION": Campo(nombre="fecha", tipo="date", desc="fecha"),
                "_fila": Campo(nombre="fila", tipo="int", desc="orden"),
            },
        }
    )


_CSV_A = (
    "OBJECTID;COD_DANE;TEXTO_AMENAZA;FECHA_EJECUCION;OTRA\n"
    "1;05001;ALTA;27/10/2026;no va\n"
    "2;5893;BAJA;02/05/2026;no va\n"
)
_AMBOS = ("https://bart/a.csv", "https://bart/b.csv")


def test_csv_numera_entre_archivos_con_fechas_iso_y_ceros() -> None:
    from terranova.copias import descargar_csv

    http = CsvFalso(dict.fromkeys(_AMBOS, _CSV_A))
    filas = [f for p in descargar_csv(_alertas(), cliente=http) for f in p]
    assert [f["_fila"] for f in filas] == [1, 2, 3, 4]
    assert filas[0] == {
        "COD_DANE": "05001",
        "TEXTO_AMENAZA": "ALTA",
        "FECHA_EJECUCION": "2026-10-27",  # día primero
        "_fila": 1,
    }  # solo la lista blanca: ni OBJECTID ni OTRA
    assert filas[1]["COD_DANE"] == "05893"  # el cero que el archivo perdió


def test_csv_vacio_o_sin_una_columna_no_se_publica() -> None:
    from terranova.copias import descargar_csv

    vacio = CsvFalso(dict.fromkeys(_AMBOS, "COD_DANE;TEXTO_AMENAZA;FECHA_EJECUCION\n"))
    with pytest.raises(ErrorCopia, match="sin filas"):
        list(descargar_csv(_alertas(), cliente=vacio))
    sin_fecha = CsvFalso(dict.fromkeys(_AMBOS, "COD_DANE;TEXTO_AMENAZA\n05001;ALTA\n"))
    with pytest.raises(ErrorCopia, match="faltan columnas"):
        list(descargar_csv(_alertas(), cliente=sin_fecha))


def test_las_reglas_del_origen_csv() -> None:
    from pydantic import ValidationError

    from terranova.catalogo import Copia

    with pytest.raises(ValidationError, match="exige `descargas`"):
        Copia(origen="csv", tabla="t", clave="_fila")
    with pytest.raises(ValidationError, match="solo aplican al origen `csv`"):
        Copia(origen="geojson", descargas=["u"], tabla="t", clave="_fila", separador=";")
    with pytest.raises(ValidationError, match="solo aplican al origen `csv`"):
        Copia(origen="geojson", descargas=["u"], tabla="t", clave="_fila", ceros={"C": 5})


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_geojson_en_la_cartesiana_de_bogota_se_reproyecta() -> None:
    assert URL_PG
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(URL_PG, autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS copia CASCADE")
    almacen = AlmacenCopias(URL_PG)
    fuente = _amenazas()
    # el origen de la cartesiana (92334,879; 109320,965) es lon -74,14659167, lat 4,680486111
    cuadro = _cuadro_bogota(92334.879 - 50, 109320.965 - 50, "2")
    v = almacen.construir(
        fuente, iter([[{"_fila": 1, "CATEGORIZA": "2", "_geom": cuadro["geometry"]}]]), None
    )
    assert v.filas == 1
    filas, total = almacen.consultar(
        plan_de_consulta(fuente, {"punto": [-74.14659167, 4.680486111], "select": ["CATEGORIZA"]})
    )
    assert filas == [{"CATEGORIZA": "2"}] and total == 1
    assert almacen.consultar(plan_de_consulta(fuente, {"punto": [-74.1500, 4.680486111]}))[1] == 0
