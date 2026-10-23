"""Spec 08: la cosecha interpreta bien lo que publican Socrata y ArcGIS, sin red."""

from datetime import date

import pytest

from terranova.catalogo import Metadatos, cargar
from terranova.cosecha import de_arcgis, de_socrata, diferencias

CATALOGO = cargar()
HOY = date(2026, 10, 22)


def _columna(nombre: str, tipo: str = "text", **contenido: object) -> dict[str, object]:
    return {
        "fieldName": nombre,
        "name": nombre.upper(),
        "dataTypeName": tipo,
        "description": f"<p>{nombre}</p>",
        "cachedContents": contenido,
    }


def _vista(*columnas: dict[str, object]) -> dict[str, object]:
    return {
        "id": "jbjy-vk9h",
        "name": "SECOP II - Contratos Electrónicos",
        "description": "Contratos a corte de 30 de junio de 2026.",
        "publicationDate": 1_500_000_000,
        "rowsUpdatedAt": 1_692_831_127,
        "category": "Gastos Gubernamentales",
        "tags": ["secop"],
        "metadata": {
            "custom_fields": {
                "Información de Datos": {
                    "Frecuencia de Actualización": "Diaria",
                    "Cobertura Geográfica": "Nacional",
                    "Idioma": "Español",
                }
            }
        },
        "columns": list(columnas),
    }


def test_socrata_trae_fechas_frecuencia_y_diccionario() -> None:
    fuente = CATALOGO.fuentes["cce.secop2.contratos"]
    m = de_socrata(
        fuente,
        _vista(
            _columna(
                "estado_contrato",
                count="9",
                non_null="9",
                null="0",
                smallest="Activo",
                largest="terminado",
                top=[{"item": "Activo", "count": "9"}],
            )
        ),
        HOY,
    )
    assert m.datos_actualizados == date(2023, 8, 23) and m.frecuencia_declarada == "Diaria"
    assert m.corte == "30 de junio de 2026" and m.filas == 9
    campo = m.campos["estado_contrato"]
    assert campo.descripcion == "estado_contrato" and campo.comparacion == "texto"
    assert campo.valores == {"Activo": 9}


def test_socrata_no_guarda_valores_de_columnas_de_personas() -> None:
    """El mínimo de `documento_proveedor` es una cédula: el repo es público (ADR-0014)."""
    fuente = CATALOGO.fuentes["cce.secop2.contratos"]
    m = de_socrata(
        fuente,
        _vista(
            _columna(
                "documento_proveedor",
                count="3",
                non_null="3",
                null="0",
                smallest="1012345678",
                largest="98765432",
                top=[{"item": "1012345678", "count": "3"}],
            )
        ),
        HOY,
    )
    campo = m.campos["documento_proveedor"]
    assert campo.minimo is None and campo.maximo is None and campo.valores is None


def test_socrata_solo_guarda_frecuentes_de_una_categoria() -> None:
    """Si los 20 más frecuentes no cubren el 95 %, no describen la columna: no se guardan."""
    fuente = CATALOGO.fuentes["cce.secop2.contratos"]
    m = de_socrata(
        fuente,
        _vista(
            _columna(
                "estado_contrato",
                count="100",
                non_null="100",
                top=[{"item": "Activo", "count": "40"}],
            )
        ),
        HOY,
    )
    assert m.campos["estado_contrato"].valores is None


def test_socrata_ignora_columnas_fuera_de_la_lista_blanca() -> None:
    fuente = CATALOGO.fuentes["cce.secop2.contratos"]
    m = de_socrata(fuente, _vista(_columna("correo_supervisor", count="1")), HOY)
    assert m.campos == {}


def _capa(**extra: object) -> dict[str, object]:
    return {
        "name": "R_TERRENO",
        "geometryType": "esriGeometryPolygon",
        "extent": {
            "xmin": -8_240_000.0,
            "ymin": 540_000.0,
            "xmax": -8_230_000.0,
            "ymax": 545_000.0,
            "spatialReference": {"wkid": 102100, "latestWkid": 3857},
        },
        # 1899-12-30, la «fecha cero» de Excel y Access (así salen vigencias vacías del IGAC); en
        # Windows `fromtimestamp` no la convierte
        "editingInfo": {"dataLastEditDate": -2_209_161_600_000},
        "fields": [
            {"name": "CODIGO", "type": "esriFieldTypeString", "alias": "Código"},
            {
                "name": "CODIGO_ANTERIOR",
                "type": "esriFieldTypeString",
                "alias": "Anterior",
                "domain": {"codedValues": [{"code": "1", "name": "uno"}]},
            },
            {"name": "SHAPE", "type": "esriFieldTypeGeometry"},
        ],
        **extra,
    }


def test_arcgis_trae_geometria_crs_extension_capas_y_dominios() -> None:
    fuente = CATALOGO.fuentes["igac.catastro.terreno"]
    servicio = {
        "serviceDescription": "Información catastral pública a corte de 30 de junio de 2026"
    }
    m = de_arcgis(fuente, servicio, {14: _capa()}, {14: 10}, {}, None, HOY)
    assert m.geografia is not None and m.geografia.geometria == "poligono"
    assert m.geografia.crs == "EPSG:3857" and m.geografia.capas == {14: "R_TERRENO"}
    oeste, sur, este, norte = m.geografia.extension or []
    assert -74.1 < oeste < este < -73.9 and 4.8 < sur < norte < 4.95  # Chía, en EPSG:4326
    assert m.corte == "30 de junio de 2026" and m.filas == 10
    assert m.datos_actualizados == date(1899, 12, 30)
    assert m.campos["CODIGO_ANTERIOR"].codigos == {"1": "uno"}
    assert set(m.campos) == {"CODIGO", "CODIGO_ANTERIOR"}


def test_arcgis_con_geometrias_distintas_no_es_una_fuente() -> None:
    fuente = CATALOGO.fuentes["igac.catastro.terreno"]
    capas = {14: _capa(), 7: _capa(geometryType="esriGeometryPoint")}
    with pytest.raises(ValueError, match="geometrías distintas"):
        de_arcgis(fuente, {}, capas, {}, {}, None, HOY)


def test_la_deriva_dice_que_cambio() -> None:
    antes = CATALOGO.metadatos["icfes.saber11"]
    campos = dict(antes.campos)
    quitado = campos.pop("punt_global")
    tipo = campos["periodo"].model_copy(update={"tipo_fuente": "number"})
    ahora = antes.model_copy(update={"campos": {**campos, "periodo": tipo}, "corte": "otro"})
    cambios = diferencias(antes, ahora)
    assert any("punt_global" in c for c in cambios) and quitado.tipo_fuente
    assert any("periodo cambió de tipo" in c for c in cambios)
    assert any(c.startswith("corte:") for c in cambios)
    assert diferencias(antes, antes) == []


def test_un_metadato_valida_su_esquema() -> None:
    with pytest.raises(ValueError):
        Metadatos.model_validate(
            {
                "fuente": "x.y",
                "metodo": "cosechado",
                "cosechado": "2026-10-22",
                "origen": "http://inseguro",
            }
        )


def test_socrata_no_guarda_extremos_de_texto_libre() -> None:
    """Medido en el PAA de SECOP I: el máximo de `ppto_total` era el teléfono de alguien."""
    fuente = CATALOGO.fuentes["cce.secop2.contratos"]
    m = de_socrata(
        fuente,
        _vista(
            _columna(
                "estado_contrato",
                count="2",
                non_null="2",
                null="0",
                smallest="Activo",
                largest="ANA PEREZ ALCALDESA TELEFONO 3110000000",
            )
        ),
        HOY,
    )
    assert m.campos["estado_contrato"].minimo == "Activo"
    assert m.campos["estado_contrato"].maximo is None
