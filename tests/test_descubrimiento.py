"""G6 (ADR-0026, spec 09): la ingesta del catálogo DCAT lee bien la Discovery API, sin red."""

import json
from datetime import date

import pytest

from terranova.descubrimiento import (
    DatasetDescubrible,
    a_jsonl,
    de_socrata_catalog,
    metricas,
)

HOY = date(2026, 10, 25)


def _resultado(**over: object) -> dict[str, object]:
    base = {
        "resource": {
            "id": "jbjy-vk9h",
            "name": "SECOP II - Contratos Electrónicos",
            "description": "Contratos del SECOP II.",
            "attribution": "Colombia Compra Eficiente",
            "columns_field_name": ["nombre_entidad", "valor_del_contrato", "ciudad"],
            "data_updated_at": "2026-10-24T05:48:00.000Z",
            "page_views": {"page_views_total": 1234},
            "download_count": 56,
        },
        "classification": {"domain_category": "Gastos Gubernamentales"},
        "metadata": {"domain": "www.datos.gov.co", "license": "Creative Commons Attribution 4.0"},
        "owner": {"display_name": "SECOP"},
    }
    base.update(over)
    return base


def test_de_socrata_catalog_mapea_los_campos():
    d = de_socrata_catalog(_resultado())
    assert d.id_socrata == "jbjy-vk9h"
    assert d.titulo == "SECOP II - Contratos Electrónicos"
    assert d.entidad == "Colombia Compra Eficiente"  # attribution gana al owner
    assert d.categoria == "Gastos Gubernamentales"
    assert d.columnas == ("nombre_entidad", "valor_del_contrato", "ciudad")
    assert d.licencia == "Creative Commons Attribution 4.0"
    assert d.vistas == 1234 and d.descargas == 56
    assert d.url == "https://www.datos.gov.co/resource/jbjy-vk9h.json"
    assert d.protocolo == "socrata"


def test_entidad_cae_al_owner_y_luego_al_dominio():
    sin_attr = _resultado(resource={"id": "aaaa-bbbb"}, owner={"display_name": "DANE"})
    assert de_socrata_catalog(sin_attr).entidad == "DANE"
    solo_dominio = _resultado(
        resource={"id": "cccc-dddd"}, owner={}, metadata={"domain": "www.datos.gov.co"}
    )
    assert de_socrata_catalog(solo_dominio).entidad == "www.datos.gov.co"


def test_resultado_sin_id_se_rechaza():
    with pytest.raises(KeyError):
        de_socrata_catalog(_resultado(resource={"name": "sin id"}))


def test_con_licencia_y_vivo():
    con = de_socrata_catalog(_resultado())
    assert con.con_licencia() is True
    assert con.vivo(HOY) is True  # actualizado ayer

    sin_lic = de_socrata_catalog(_resultado(metadata={"domain": "x", "license": None}))
    assert sin_lic.con_licencia() is False

    viejo = de_socrata_catalog(
        _resultado(resource={"id": "ee-ff", "data_updated_at": "2023-01-01T00:00:00Z"})
    )
    assert viejo.vivo(HOY) is False

    sin_fecha = de_socrata_catalog(_resultado(resource={"id": "gg-hh"}))
    assert sin_fecha.vivo(HOY) is False  # sin fecha no cuenta como vivo


def _ds(entidad: str, licencia: str | None, fecha: str | None) -> DatasetDescubrible:
    return DatasetDescubrible(
        id_socrata="x",
        titulo="t",
        descripcion="",
        entidad=entidad,
        categoria=None,
        columnas=(),
        licencia=licencia,
        actualizado_en=fecha,
        vistas=0,
        descargas=0,
        url="https://www.datos.gov.co/resource/x.json",
    )


def test_metricas_resume_la_compuerta():
    datasets = [
        _ds("IGAC", "CC BY 4.0", "2026-10-01T00:00:00Z"),
        _ds("IGAC", None, "2026-09-01T00:00:00Z"),
        _ds("DANE", "CC BY-SA 4.0", "2020-01-01T00:00:00Z"),  # con licencia pero no vivo
    ]
    m = metricas(datasets, hoy=HOY)
    assert m.total == 3
    assert m.con_licencia == 2
    assert m.vivos == 2  # los dos de 2026
    assert m.entidades == 2
    assert m.top_entidades[0] == ("IGAC", 2)


def test_a_jsonl_una_linea_por_dataset_con_sus_campos():
    datasets = [_ds("IGAC", "CC BY 4.0", "2026-10-01T00:00:00Z")]
    lineas = a_jsonl(datasets).splitlines()
    assert len(lineas) == 1
    fila = json.loads(lineas[0])
    assert fila["entidad"] == "IGAC" and fila["licencia"] == "CC BY 4.0"
    assert fila["url"].endswith("/resource/x.json")
