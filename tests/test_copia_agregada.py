"""Copias de microdatos de personas, guardadas ya agregadas (origen `socrata_agregado`).

El Saber 11 trae una fila por estudiante y repite algunos. La copia baja un periodo a la vez,
cuenta a cada estudiante una vez y guarda solo grupos; las herramientas sacan promedios como
cociente de sumas y nunca un grupo de menos de 10 (ADR-0014). La prueba del almacén corre solo con
`TERRANOVA_PG_PRUEBAS=postgresql://…`.
"""

import os
from typing import Any

import pytest
from pydantic import ValidationError

from terranova.catalogo import Copia, Preagregado, cargar
from terranova.copias import (
    AlmacenCopias,
    ErrorCopia,
    agregar_tanda,
    descargar_socrata_agregado,
    plan_de_consulta,
)

CATALOGO = cargar()
ICFES = CATALOGO.fuentes["icfes.saber11"]
assert ICFES.copia is not None and ICFES.copia.preagregado is not None
PRE = ICFES.copia.preagregado
URL_PG = os.environ.get("TERRANOVA_PG_PRUEBAS")


def _estudiante(
    unico: str,
    *,
    periodo: str = "20224",
    sede: str = "125175000493",
    estrato: str | None = "Estrato 1",
    nombre: str = "I.E. DIVERSIFICADO",
    glob: str | None = "250",
    mat: str | None = "50",
    lec: str | None = "60",
) -> dict[str, Any]:
    return {
        "periodo": periodo,
        "estu_consecutivo": unico,
        "cole_cod_mcpio_ubicacion": sede[1:6],
        "cole_cod_dane_sede": sede,
        "fami_estratovivienda": estrato,
        "cole_nombre_sede": nombre,
        "punt_global": glob,
        "punt_matematicas": mat,
        "punt_lectura_critica": lec,
    }


def test_cada_estudiante_cuenta_una_vez_y_sin_su_seudonimo() -> None:
    filas = [
        _estudiante("SB1", glob="200"),
        _estudiante("SB1", glob="200"),  # la fuente lo repite
        _estudiante("SB2", glob="300", nombre="INSTITUCION EDUCATIVA DIVERSIFICADO"),
        _estudiante("SB3", glob=None, lec=""),  # sin puntaje global (los periodos de 2010)
        _estudiante("", glob="499"),  # sin seudónimo no se sabe si se repite: no cuenta
    ]
    (grupo,) = agregar_tanda(iter(filas), PRE)
    assert grupo["estudiantes"] == 3
    assert (grupo["suma_punt_global"], grupo["n_punt_global"]) == (500.0, 2)
    assert (grupo["suma_punt_lectura_critica"], grupo["n_punt_lectura_critica"]) == (120.0, 2)
    assert grupo["cole_nombre_sede"] == "INSTITUCION EDUCATIVA DIVERSIFICADO"  # el mayor
    assert "estu_consecutivo" not in grupo
    assert set(grupo) == set(PRE.columnas_copia)


def test_un_grupo_sin_datos_de_una_medida_la_deja_vacia_no_en_cero() -> None:
    (grupo,) = agregar_tanda(iter([_estudiante("SB1", glob=None)]), PRE)
    assert (grupo["suma_punt_global"], grupo["n_punt_global"]) == (None, 0)


def test_los_grupos_se_separan_por_sede_y_estrato_y_el_vacio_es_vacio() -> None:
    filas = [
        _estudiante("SB1"),
        _estudiante("SB2", estrato="Estrato 5"),
        _estudiante("SB3", estrato=""),
        _estudiante("SB4", sede="125175000001"),
    ]
    grupos = agregar_tanda(iter(filas), PRE)
    claves = {(g["cole_cod_dane_sede"], g["fami_estratovivienda"]) for g in grupos}
    assert claves == {
        ("125175000493", "Estrato 1"),
        ("125175000493", "Estrato 5"),
        ("125175000493", None),
        ("125175000001", "Estrato 1"),
    }


class _Respuesta:
    def __init__(self, datos: list[dict[str, Any]]) -> None:
        self.datos = datos

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, Any]]:
        return self.datos


class SocrataFalso:
    """Responde la lista de periodos y luego las páginas de cada uno, en orden de `:id`."""

    def __init__(self, por_periodo: dict[str, list[dict[str, Any]]], pagina: int) -> None:
        self.por_periodo = por_periodo
        self.pagina = pagina
        self.pedidos: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, Any]) -> _Respuesta:
        self.pedidos.append(params)
        if "$group" in params:
            return _Respuesta([{"periodo": p} for p in reversed(list(self.por_periodo))])
        periodo = params["$where"].split("'")[1]
        inicio = params["$offset"]
        return _Respuesta(self.por_periodo[periodo][inicio : inicio + self.pagina])


def test_descargar_baja_periodo_por_periodo_pagina_y_numera_los_grupos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import terranova.copias as copias

    monkeypatch.setattr(copias, "PAGINA", 2)
    por_periodo = {
        "20101": [_estudiante(f"A{i}", periodo="20101") for i in range(3)],
        "20224": [
            _estudiante("B1"),
            _estudiante("B1"),  # repetido, partido entre dos páginas
            _estudiante("B2", estrato="Estrato 2"),
        ],
    }
    http = SocrataFalso(por_periodo, pagina=2)
    paginas = list(descargar_socrata_agregado(ICFES, None, cliente=http))
    assert [[g["periodo"] for g in p] for p in paginas] == [["20101"], ["20224", "20224"]]
    assert [g["estudiantes"] for p in paginas for g in p] == [3, 1, 1]
    assert [g["_fila"] for p in paginas for g in p] == [1, 2, 3]
    pedidos = [p for p in http.pedidos if "$where" in p]
    assert all(p["$order"] == ":id" and "estu_consecutivo" in p["$select"] for p in pedidos)
    # Socrata responde 400 a un `$select` con una columna repetida (periodo es partición y grupo)
    columnas = pedidos[0]["$select"].split(", ")
    assert len(columnas) == len(set(columnas)) and "periodo" in columnas
    assert [p["$offset"] for p in pedidos] == [0, 2, 0, 2]


def test_una_tanda_vacia_no_publica_la_copia() -> None:
    http = SocrataFalso({"20101": [_estudiante("A1", periodo="20101")], "20102": []}, pagina=10)
    with pytest.raises(ErrorCopia, match="20102 llegó sin filas"):
        list(descargar_socrata_agregado(ICFES, None, cliente=http))


def test_cociente_y_minimo_en_el_plan() -> None:
    plan = plan_de_consulta(
        ICFES,
        {
            "filtros": {"cole_cod_mcpio_ubicacion": "25175"},
            "select": ["periodo"],
            "group": ["periodo"],
            "agregados": {
                "estudiantes": "sum:estudiantes",
                "promedio_global": "cociente:suma_punt_global/n_punt_global",
            },
            "minimo": {"sum:estudiantes": 10},
            "order": ["periodo"],
        },
    )
    assert 'sum("suma_punt_global")::float / nullif(sum("n_punt_global"), 0)' in plan.sql
    assert 'GROUP BY "periodo" HAVING sum("estudiantes") >= %s ORDER BY' in plan.sql
    assert plan.parametros == ("25175", 10, 1000)
    with pytest.raises(ErrorCopia, match="«cociente:suma/conteo»"):
        plan_de_consulta(ICFES, {"agregados": {"p": "cociente:suma_punt_global"}})
    with pytest.raises(ErrorCopia, match="lista blanca"):
        plan_de_consulta(ICFES, {"agregados": {"p": "cociente:estu_consecutivo/n_punt_global"}})
    with pytest.raises(ErrorCopia, match="`minimo` va con `group`"):
        plan_de_consulta(ICFES, {"agregados": {"n": "count"}, "minimo": {"count": 10}})


def test_preagregado_va_con_su_origen_y_la_clave_fila() -> None:
    pre = Preagregado(particion="periodo", unico="id", grupo=["periodo", "municipio"])
    with pytest.raises(ValidationError, match="`preagregado` va con el origen"):
        Copia(origen="socrata_agregado", conjunto="abcd-1234", tabla="t", clave="_fila")
    with pytest.raises(ValidationError, match="`preagregado` va con el origen"):
        Copia(origen="socrata", conjunto="abcd-1234", tabla="t", clave="id", preagregado=pre)
    with pytest.raises(ValidationError, match="lleva `clave: _fila`"):
        Copia(
            origen="socrata_agregado", conjunto="abcd-1234", tabla="t", clave="id", preagregado=pre
        )


def test_una_fuente_copiada_va_por_el_conector_copia() -> None:
    """El Saber 11 pasó a copia y seguía con `conector: datos-abiertos-mcp`: la consulta iba al
    conector en vivo, que no tiene `consultar_copia`."""
    from terranova.catalogo import Fuente

    datos = ICFES.model_dump(by_alias=True, exclude_none=True)
    with pytest.raises(ValidationError, match="lleva `conector: copia`"):
        Fuente.model_validate({**datos, "conector": "datos-abiertos-mcp"})


def test_las_herramientas_del_saber_nunca_sacan_grupos_chicos() -> None:
    """ADR-0014: toda herramienta sobre la copia agrega y exige 10 estudiantes por grupo."""
    sobre = [h for h in CATALOGO.herramientas.values() if h.fuente == ICFES.id]
    assert len(sobre) == 4
    for h in sobre:
        argumentos = h.consulta.argumentos
        assert argumentos["agregados"] and argumentos["group"], h.id
        assert argumentos["minimo"] == {"sum:estudiantes": 10}, h.id


@pytest.mark.skipif(not URL_PG, reason="sin TERRANOVA_PG_PRUEBAS")
def test_promedio_y_minimo_en_postgis() -> None:
    assert URL_PG
    psycopg = pytest.importorskip("psycopg")
    with psycopg.connect(URL_PG, autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS copia CASCADE")
    almacen = AlmacenCopias(URL_PG)
    filas = [_estudiante(f"S{i}", glob=str(200 + i)) for i in range(12)]
    filas += [_estudiante(f"T{i}", estrato="Estrato 6", glob="400") for i in range(3)]
    grupos = agregar_tanda(iter(filas), PRE)
    for i, g in enumerate(grupos, start=1):
        g["_fila"] = i
    almacen.construir(ICFES, iter([grupos]), None)

    def consultar(group: str) -> list[dict[str, Any]]:
        argumentos = {
            "filtros": {"cole_cod_mcpio_ubicacion": "25175"},
            "select": [group],
            "group": [group],
            "agregados": {
                "estudiantes": "sum:estudiantes",
                "promedio": "cociente:suma_punt_global/n_punt_global",
            },
            "minimo": {"sum:estudiantes": 10},
            "order": [group],
        }
        return almacen.consultar(plan_de_consulta(ICFES, argumentos))[0]

    # por periodo, los 15 juntos; el promedio pesa por estudiante, no por grupo
    (todo,) = consultar("periodo")
    assert todo["estudiantes"] == 15
    assert todo["promedio"] == pytest.approx((sum(range(200, 212)) + 3 * 400) / 15)
    # por estrato, el de 3 estudiantes no sale
    assert [f["fami_estratovivienda"] for f in consultar("fami_estratovivienda")] == ["Estrato 1"]


def test_el_plan_de_secop2_cuenta_cada_item_una_vez() -> None:
    """El PAA de SECOP II repite un ítem por cada categoría UNSPSC, con el mismo valor: sumar filas
    inflaba el plan 2025 de Pitalito de $54 008 millones a $91 410 millones. La copia cuenta el
    ítem una vez, con su valor una vez."""
    paa = CATALOGO.fuentes["cce.secop2.paa_entidades_copia"]
    assert paa.copia is not None and paa.copia.preagregado is not None
    pre = paa.copia.preagregado

    def item(id_: str, valor: str, codigo: str = "702330010") -> dict[str, Any]:
        return {
            "annio": "2025",
            "id": id_,
            "nit_entidad": "891180077",
            "codigo_entidad": codigo,
            "version_del_paa": "40",
            "valor_total_esperado": valor,
            "nombre_entidad": "MUNICIPIO DE PITALITO",
        }

    filas = [item("1", "100"), item("1", "100"), item("1", "100"), item("2", "50")]
    filas.append(item("3", "7", codigo="724816145"))
    grupos = {g["codigo_entidad"]: g for g in agregar_tanda(iter(filas), pre)}
    assert grupos["702330010"]["items"] == 2
    assert grupos["702330010"]["suma_valor_total_esperado"] == 150.0
    assert grupos["724816145"]["items"] == 1
    assert "id" not in grupos["702330010"]


def test_con_tandas_escritas_no_se_agrupa_la_fuente(monkeypatch: pytest.MonkeyPatch) -> None:
    """El PAA de SECOP II no responde en 180 s al agrupar 19,6 M filas por año: la ficha escribe
    los años y la copia los baja sin preguntar."""
    import terranova.copias as copias

    monkeypatch.setattr(copias, "PAGINA", 2)
    assert ICFES.copia is not None and ICFES.copia.preagregado is not None
    pre = ICFES.copia.preagregado.model_copy(update={"tandas": ["20224"]})
    fuente = ICFES.model_copy(update={"copia": ICFES.copia.model_copy(update={"preagregado": pre})})
    por_periodo = {"20224": [_estudiante("B1"), _estudiante("B2")], "20101": [_estudiante("A")]}
    http = SocrataFalso(por_periodo, pagina=2)
    paginas = list(descargar_socrata_agregado(fuente, None, cliente=http))
    assert not any("$group" in p for p in http.pedidos)
    assert [g["periodo"] for p in paginas for g in p] == ["20224"]


def test_lo_agregado_se_baja_entero_antes_de_escribir() -> None:
    """Con el COPY abierto mientras se bajaban los años del PAA (horas), la conexión a Postgres
    se perdía: la descarga agregada termina antes de rendir la primera página."""
    from terranova.cli import _primero_todo

    bajadas: list[int] = []

    def descargar(fuente: Any, desde: Any) -> Any:
        for i in range(3):
            bajadas.append(i)
            yield [{"i": i}]

    paginas = _primero_todo(descargar)(ICFES, None)
    assert bajadas == [0, 1, 2]  # ya bajó todo, antes de pedir la primera página
    assert [p[0]["i"] for p in paginas] == [0, 1, 2]
