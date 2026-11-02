"""`_meta.geo`: el encuadre de un resultado, también después de resumir la geometría."""

from typing import Any

from terranova.contrato import GeoResult, Sobre, resumen_geo, resumir_geometria

CUADRO = {"type": "Polygon", "coordinates": [[[-74, 4], [-73, 4], [-73, 5], [-74, 4]]]}
PUNTO = {"type": "Point", "coordinates": [-72.0, 6.0]}


def _sobre(*geometrias: dict[str, Any]) -> Sobre:
    rasgos = [{"type": "Feature", "geometry": g, "properties": {}} for g in geometrias]
    coleccion = {"type": "FeatureCollection", "features": rasgos}
    geo = GeoResult.model_validate(
        {
            "artifacts": [
                {"kind": "feature_collection", "name": "x", "crs": "EPSG:4326", "data": coleccion}
            ]
        }
    )
    return Sobre.model_construct(geo_result=geo, datos={}, avisos=[])


def test_poligonos_resumidos_conservan_tipo_y_encuadre() -> None:
    assert resumen_geo(resumir_geometria(_sobre(CUADRO))) == {
        "bbox": [-74.0, 4.0, -73.0, 5.0],
        "crs": "EPSG:4326",
        "tipo": "poligono",
        "elementos": 1,
    }


def test_con_la_forma_completa_da_lo_mismo() -> None:
    sobre = _sobre(CUADRO)
    assert resumen_geo(sobre) == resumen_geo(resumir_geometria(sobre))


def test_puntos_y_mezclas() -> None:
    geo = resumen_geo(resumir_geometria(_sobre(PUNTO)))
    assert geo is not None and geo["tipo"] == "punto" and geo["bbox"] == [-72.0, 6.0, -72.0, 6.0]
    mezcla = resumen_geo(resumir_geometria(_sobre(CUADRO, PUNTO)))
    assert mezcla is not None and mezcla["tipo"] == "mixto" and mezcla["elementos"] == 2
    assert mezcla["bbox"] == [-74.0, 4.0, -72.0, 6.0]


def test_sin_geometria_no_hay_meta() -> None:
    assert resumen_geo(Sobre.model_construct(geo_result=None)) is None
    assert resumen_geo(_sobre()) is None
