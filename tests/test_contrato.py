"""Las reglas de `rt/1` (spec 01, §6.2) como propiedades: todo sobre válido las cumple y cada
violación se rechaza al construirlo."""

import json
from pathlib import Path
from typing import Annotated, Any

import jsonschema
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from terranova.contrato import (
    HTTP_DE,
    MAX_TEXTO,
    Problema,
    Sobre,
    fuera_de_lista_blanca,
    huella,
    nueva_solicitud_id,
    texto_es_limpio,
)

ESQUEMA = json.loads(Path("esquemas/rt1.sobre.schema.json").read_text(encoding="utf-8"))

texto_limpio = st.text(
    alphabet=st.characters(blacklist_categories=("Cc", "Cs"), blacklist_characters="\u061c"),
    max_size=40,
).filter(texto_es_limpio)
valor_dato = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(-(10**9), 10**9),
    texto_limpio,
    st.floats(allow_nan=False, allow_infinity=False),
)
datos_st = st.dictionaries(
    st.from_regex(r"[a-z][a-z0-9_]{0,15}", fullmatch=True), valor_dato, max_size=6
)


@st.composite
def completitud(draw: st.DrawFn) -> dict[str, Any]:
    total = draw(st.one_of(st.none(), st.integers(0, 10_000)))
    vistos = draw(st.integers(0, 10_000 if total is None else total))
    return {"vistos": vistos, "total": total, "truncado": total is not None and vistos < total}


@st.composite
def procedencia(draw: st.DrawFn, fuente_id: str) -> dict[str, Any]:
    return {
        "fuente_id": fuente_id,
        "entidad": draw(texto_limpio),
        "url": "https://ejemplo.gov.co/servicio",
        "licencia": {
            "spdx": "CC-BY-SA-4.0",
            "uso_comercial": draw(st.sampled_from(["si", "no", "por_verificar"])),
        },
        "atribucion": "Fuente: entidad",
        "servido_desde": draw(st.sampled_from(["fuente", "copia", "curado", "cache", "obsoleto"])),
        "consultado_en": "2026-10-21T16:20:00Z",
        "consulta": {},
        "completitud": draw(completitud()),
        "cache": {"acierto": False, "edad_s": 0},
        "transformaciones": [],
        "conector": "arcgis-mcp",
        "huella": huella({}),
    }


@st.composite
def sobres(draw: st.DrawFn) -> dict[str, Any]:
    """Sobres válidos: se construyen respetando las reglas para probar que las cumplen."""
    ids = draw(
        st.lists(
            st.sampled_from(["igac.terreno", "pnn.runap", "dane.mgn", "upra.precios"]),
            min_size=1,
            max_size=4,
            unique=True,
        )
    )
    procs = [draw(procedencia(i)) for i in ids]
    estado = draw(st.sampled_from(["encontrado", "no_encontrado", "fuera_de_cobertura", "parcial"]))
    errores = []
    if estado == "parcial":
        errores = [{"codigo": "fuente_no_disponible", "fuente_id": ids[0], "detalle": "caída"}]
    datos = draw(datos_st)
    lon, lat = draw(st.floats(-180, 180)), draw(st.floats(-90, 90))
    geo = draw(st.booleans())
    necesita_aviso = any(
        p["completitud"]["total"] is None or p["servido_desde"] == "obsoleto" for p in procs
    )
    return {
        "solicitud_id": nueva_solicitud_id(),
        "herramienta": "igac_predio_en_punto@1",
        "estado": estado,
        "entrada": {"lon": lon, "lat": lat},
        "zona_usada": {"tipo": "punto", "valor": [lon, lat], "crs": "EPSG:4326"},
        "datos": datos,
        "huella": huella(datos),
        "geo_result": {
            "geo_result": "1",
            "facts": {},
            "artifacts": [
                {
                    "kind": "feature_collection",
                    "name": "capa",
                    "crs": "EPSG:4326",
                    "data": {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                                "properties": datos,
                            }
                        ],
                    },
                }
            ],
        }
        if geo
        else None,
        "procedencia": procs,
        "avisos": ["aviso"] if necesita_aviso or draw(st.booleans()) else [],
        "errores": errores,
        "creditos": 0 if estado == "fuera_de_cobertura" else draw(st.sampled_from([1, 10])),
    }


def _rompe(sobre: dict[str, Any], regla: str) -> None:
    with pytest.raises(ValidationError, match=regla):
        Sobre.model_validate(sobre)


# --- todo sobre válido cumple el contrato y su esquema ---------------------------------------


@given(sobres())
def test_sobre_valido_cumple_y_viaja_en_json(s: dict[str, Any]) -> None:
    sobre = Sobre.model_validate(s)
    salida = sobre.model_dump(mode="json")
    jsonschema.validate(salida, ESQUEMA)
    assert Sobre.model_validate_json(sobre.model_dump_json()) == sobre


# --- regla 1: estado cerrado ----------------------------------------------------------------


@given(
    sobres(),
    st.text(min_size=1).filter(
        lambda e: e not in {"encontrado", "no_encontrado", "fuera_de_cobertura", "parcial"}
    ),
)
def test_regla_1_estado_desconocido(s: dict[str, Any], estado: str) -> None:
    _rompe({**s, "estado": estado}, "estado")


# --- regla 2: fuera de cobertura no descuenta ------------------------------------------------


@given(sobres(), st.integers(1, 100))
def test_regla_2_fuera_de_cobertura_no_descuenta(s: dict[str, Any], creditos: int) -> None:
    _rompe({**s, "estado": "fuera_de_cobertura", "errores": [], "creditos": creditos}, "regla 2")


# --- regla 3: toda fuente con error está en procedencia ----------------------------------------


@given(sobres())
def test_regla_3_error_de_fuente_sin_procedencia(s: dict[str, Any]) -> None:
    error = {"codigo": "fuente_lenta", "fuente_id": "otra.fuente", "detalle": "x"}
    _rompe({**s, "estado": "parcial", "errores": [error]}, "regla 3")


def test_regla_3_sin_procedencia() -> None:
    s = Sobre.model_validate(_minimo()).model_dump(mode="json")
    _rompe({**s, "procedencia": []}, "procedencia")


# --- regla 4: completitud coherente ---------------------------------------------------------


@given(sobres(), st.integers(1, 50))
def test_regla_4_vistos_mayor_que_total(s: dict[str, Any], exceso: int) -> None:
    p = s["procedencia"][0]
    total = p["completitud"]["total"] or 0
    p["completitud"] = {"vistos": total + exceso, "total": total, "truncado": False}
    _rompe(s, "regla 4")


@given(sobres())
def test_regla_4_truncado_mentiroso(s: dict[str, Any]) -> None:
    p = s["procedencia"][0]
    c = p["completitud"]
    if c["total"] is None:
        c["total"] = c["vistos"]
    c["truncado"] = not (c["vistos"] < c["total"])
    _rompe(s, "regla 4")


@given(sobres())
def test_regla_4_total_desconocido_sin_aviso(s: dict[str, Any]) -> None:
    s["procedencia"][0]["completitud"] = {"vistos": 3, "total": None, "truncado": False}
    _rompe({**s, "avisos": []}, "regla 4")


# --- regla 5: parcial ⇔ errores -------------------------------------------------------------


@given(sobres())
def test_regla_5_parcial_sin_errores(s: dict[str, Any]) -> None:
    _rompe({**s, "estado": "parcial", "errores": [], "creditos": 1}, "regla 5")


@given(sobres())
def test_regla_5_errores_fuera_de_parcial(s: dict[str, Any]) -> None:
    error = {
        "codigo": "fuente_lenta",
        "fuente_id": s["procedencia"][0]["fuente_id"],
        "detalle": "x",
    }
    _rompe({**s, "estado": "encontrado", "errores": [error], "creditos": 10}, "regla 5")


# --- regla 6: obsoleto avisa ----------------------------------------------------------------


@given(sobres())
def test_regla_6_obsoleto_sin_aviso(s: dict[str, Any]) -> None:
    for p in s["procedencia"]:
        if p["completitud"]["total"] is None:
            p["completitud"] = {"vistos": 0, "total": 0, "truncado": False}
    s["procedencia"][0]["servido_desde"] = "obsoleto"
    _rompe({**s, "avisos": []}, "regla 6")


@given(
    sobres(),
    st.text(min_size=1).filter(
        lambda e: e not in {"fuente", "copia", "curado", "cache", "obsoleto"}
    ),
)
def test_regla_6_servido_desde_cerrado(s: dict[str, Any], valor: str) -> None:
    s["procedencia"][0]["servido_desde"] = valor
    _rompe(s, "servido_desde")


# --- regla 7: huella --------------------------------------------------------------------------


@given(sobres(), datos_st)
def test_regla_7_huella_de_otros_datos(s: dict[str, Any], otros: dict[str, Any]) -> None:
    if huella(otros) == s["huella"]:
        return
    _rompe({**s, "huella": huella(otros)}, "regla 7")


def test_regla_7_huella_es_estable_e_independiente_del_orden() -> None:
    assert huella({"a": 1, "b": "ñ"}) == huella({"b": "ñ", "a": 1})


# --- regla 8: geometría en lon/lat EPSG:4326 -------------------------------------------------


@given(sobres())
def test_regla_8_crs_no_declarado(s: dict[str, Any]) -> None:
    if s["geo_result"] is None:
        return
    s["geo_result"]["artifacts"][0]["crs"] = "EPSG:3116"
    _rompe(s, "regla 8")


@given(sobres(), st.floats(90.001, 1e7))
def test_regla_8_lat_lon_invertidas_o_proyectadas(s: dict[str, Any], fuera: float) -> None:
    if s["geo_result"] is None:
        return
    s["geo_result"]["artifacts"][0]["data"]["features"][0]["geometry"]["coordinates"] = [
        fuera,
        fuera,
    ]
    _rompe(s, "regla 8")


def test_regla_8_9377_solo_si_se_pide() -> None:
    s = _minimo(geo_crs="EPSG:9377")
    _rompe(s, "regla 8")
    s["entrada"]["crs_salida"] = "EPSG:9377"
    s["geo_result"]["artifacts"][0]["data"]["features"][0]["geometry"]["coordinates"] = [
        4_880_000.0,
        2_070_000.0,
    ]
    Sobre.model_validate(s)


# --- regla 9: texto de la fuente limpio y acotado -------------------------------------------


@pytest.mark.parametrize("sucio", ["a\u202eb", "a\u0000b", "x\u2066y", "\u001b[31mrojo"])
def test_regla_9_control_y_bidi(sucio: str) -> None:
    _rompe(_minimo(datos={"nombre": sucio}), "regla 9")
    s = _minimo(geo_crs="EPSG:4326")
    s["geo_result"]["artifacts"][0]["data"]["features"][0]["properties"] = {"nombre": sucio}
    _rompe(s, "regla 9")


def test_regla_9_largo_maximo() -> None:
    _rompe(_minimo(datos={"nombre": "a" * (MAX_TEXTO + 1)}), "regla 9")
    Sobre.model_validate(_minimo(datos={"nombre": "a" * MAX_TEXTO, "nota": "línea\ncon\ttab"}))


# --- regla 10: lista blanca (depende del catálogo) -------------------------------------------


@given(sobres())
def test_regla_10_lista_blanca(s: dict[str, Any]) -> None:
    sobre = Sobre.model_validate(s)
    assert fuera_de_lista_blanca(sobre, set(s["datos"])) == set()
    if s["datos"]:
        quitado = sorted(s["datos"])[0]
        assert quitado in fuera_de_lista_blanca(sobre, set(s["datos"]) - {quitado})


# --- errores (problem+json) -------------------------------------------------------------------


@pytest.mark.parametrize("codigo", sorted(HTTP_DE))
def test_problema_lleva_el_http_de_su_codigo(codigo: str) -> None:
    base = {"title": codigo, "code": codigo, "solicitud_id": nueva_solicitud_id(), "param": "lon"}
    Problema.model_validate({**base, "status": HTTP_DE[codigo]})
    with pytest.raises(ValidationError):
        Problema.model_validate({**base, "status": 418})


def test_parametro_invalido_nombra_el_parametro() -> None:
    with pytest.raises(ValidationError, match="parámetro"):
        Problema(
            title="x", status=400, code="parametro_invalido", solicitud_id=nueva_solicitud_id()
        )


def test_saldo_agotado_es_429_y_no_402() -> None:
    assert HTTP_DE["saldo_agotado"] == 429


def test_solicitud_id_ordenable_y_unico() -> None:
    ids = [nueva_solicitud_id() for _ in range(200)]
    assert len(set(ids)) == 200 and all(len(i) == 30 for i in ids)


def _minimo(datos: dict[str, Any] | None = None, geo_crs: str | None = None) -> dict[str, Any]:
    datos = {"codigo": "1"} if datos is None else datos
    return {
        "solicitud_id": nueva_solicitud_id(),
        "herramienta": "igac_predio_en_punto@1",
        "estado": "encontrado",
        "entrada": {"lon": -74.0, "lat": 4.8},
        "zona_usada": None,
        "datos": datos,
        "huella": huella(datos),
        "geo_result": {
            "geo_result": "1",
            "artifacts": [
                {
                    "kind": "feature_collection",
                    "crs": geo_crs,
                    "data": {
                        "type": "FeatureCollection",
                        "features": [
                            {
                                "type": "Feature",
                                "geometry": {"type": "Point", "coordinates": [-74.0, 4.8]},
                                "properties": {},
                            }
                        ],
                    },
                }
            ],
        }
        if geo_crs
        else None,
        "procedencia": [
            {
                "fuente_id": "igac.terreno",
                "entidad": "IGAC",
                "url": "https://x",
                "atribucion": "IGAC",
                "licencia": {"spdx": "CC-BY-SA-4.0", "uso_comercial": "si"},
                "servido_desde": "fuente",
                "consultado_en": "2026-10-21T00:00:00Z",
                "consulta": {},
                "transformaciones": [],
                "conector": "c",
                "completitud": {"vistos": 1, "total": 1, "truncado": False},
                "cache": {"acierto": False, "edad_s": 0},
                "huella": huella(datos),
            }
        ],
        "avisos": [],
        "errores": [],
        "creditos": 10,
    }


def test_el_patron_publicado_es_la_misma_regla_que_texto_es_limpio() -> None:
    """Schemathesis manda texto con control: el OpenAPI debe decir lo mismo que la puerta valida."""
    import re

    from pydantic import Field, TypeAdapter

    from terranova.contrato import PATRON_TEXTO_LIMPIO, texto_es_limpio

    validador = TypeAdapter(Annotated[str, Field(pattern=PATRON_TEXTO_LIMPIO)])
    for texto in ("ARTÍCULO 1o", "a\nb\tc", "x\x07y", "x‮y", "x\x85y", "\U000bcbb5", "؜", ""):
        try:
            validador.validate_python(texto)
            pydantic_acepta = True
        except ValueError:
            pydantic_acepta = False
        assert (
            texto_es_limpio(texto)
            == bool(re.fullmatch(PATRON_TEXTO_LIMPIO, texto))
            == pydantic_acepta
        )
