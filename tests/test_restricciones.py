"""F4.1: el dataset de restricciones. Datos sintéticos (sin red); requiere el extra `datasets`."""

import json
from pathlib import Path
from typing import Any

import pytest

gpd = pytest.importorskip("geopandas")
pa_errors = pytest.importorskip("pandera.errors")

from shapely.geometry import Polygon, box  # noqa: E402

from terranova.datasets import restricciones as r  # noqa: E402


def _runap(filas: list[tuple[int, str, object]]) -> Any:
    return gpd.GeoDataFrame(
        {
            "ap_id": [f[0] for f in filas],
            "ap_nombre": [f[1] for f in filas],
            "ap_categor": ["Parque Nacional Natural"] * len(filas),
            "fecha_insc": ["2011-07-13"] * len(filas),
            "url": ["https://runap.parquesnacionales.gov.co/area-protegida/1"] * len(filas),
            "nit": ["900000000"] * len(filas),
            "organizaci": ["Una persona"] * len(filas),
        },
        geometry=[f[2] for f in filas],
        crs="EPSG:4686",
    )


def _ant() -> Any:
    return gpd.GeoDataFrame(
        {
            "OBJECTID": [1, 2],
            "ID": ["R-1", None],
            "NOMBRE": ["Resguardo Uno", "Resguardo Dos"],
            "ULTIMO_TIPO_ACTO_ADMIN": ["Resolución", "Acuerdo"],
            "ULTIMO_NUMERO_ACTO_ADMIN": ["12", None],
            "ULTIMA_FECHA_ACTO_ADMIN": [632361600000, -2208988800000],
            "PUEBLO": ["Nasa", "Wayuu"],
        },
        geometry=[box(-70.6, 0.7, -70.4, 0.9), box(-72.0, 11.0, -71.9, 11.1)],
        crs="EPSG:4326",
    )


def test_normalizar_runap_y_quitar_datos_de_personas() -> None:
    g = r.normalizar_runap(_runap([(6, "Cueva", box(-76.2, 1.5, -76.1, 1.6))]))
    assert list(g.columns) == r.COLUMNAS and str(g.crs) == r.CRS
    assert g.iloc[0]["id"] == "runap:6" and g.iloc[0]["tipo"] == "area_protegida"
    assert "nit" not in g.columns and "organizaci" not in g.columns


def test_normalizar_ant_actos_y_fechas() -> None:
    capa = r.ANT["resguardo_indigena"]
    g = r.normalizar_ant(_ant(), "resguardo_indigena", capa)
    assert list(g["id"]) == ["ant.resguardos_indigenas:R-1", "ant.resguardos_indigenas:2"]
    assert list(g["acto"]) == ["Resolución 12", "Acuerdo"]
    assert list(g["fecha"]) == ["1990-01-15", "1900-01-01"]  # antes de 1970 también
    assert list(g["categoria"]) == ["Nasa", "Wayuu"]


def _unido() -> Any:
    partes = [
        r.normalizar_runap(
            _runap([(6, "A", box(-76.2, 1.5, -76.1, 1.6)), (8, "B", box(-72, 1, -71, 2))])
        ),
        r.normalizar_ant(_ant(), "resguardo_indigena", r.ANT["resguardo_indigena"]),
    ]
    return gpd.GeoDataFrame(__import__("pandas").concat(partes, ignore_index=True), crs=r.CRS)


def test_la_huella_no_depende_del_orden_ni_de_ruido_bajo_la_precision() -> None:
    a = r.estabilizar(_unido()[r.COLUMNAS])
    b = r.estabilizar(_unido()[r.COLUMNAS].iloc[::-1].reset_index(drop=True))
    assert r.huella(a) == r.huella(b)
    ruido = _unido()[r.COLUMNAS]
    ruido = ruido.set_geometry(ruido.geometry.translate(xoff=1e-9))
    assert r.huella(r.estabilizar(ruido)) == r.huella(a)
    cambiado = _unido()[r.COLUMNAS]
    cambiado.loc[0, "nombre"] = "Otro nombre"
    assert r.huella(r.estabilizar(cambiado)) != r.huella(a)


def test_estabilizar_repara_geometrias_invalidas() -> None:
    corbata = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])  # se cruza a sí misma
    g = r.normalizar_runap(_runap([(1, "Corbata", corbata)]))
    assert not g.geometry.is_valid.all()
    assert r.validar(r.estabilizar(g)).geometry.is_valid.all()


@pytest.mark.parametrize(
    "romper",
    [
        lambda g: g.assign(tipo="mina"),
        lambda g: g.assign(nombre=None),
        lambda g: g.assign(id="repetido"),
        lambda g: g.to_crs("EPSG:3116"),
    ],
)
def test_validar_rechaza(romper: object) -> None:
    g = r.estabilizar(_unido()[r.COLUMNAS])
    with pytest.raises(pa_errors.SchemaError):
        r.validar(romper(g))  # type: ignore[operator]


def test_publicar_dos_veces_la_misma_huella(tmp_path: Path) -> None:
    origenes = [r.Origen("pnn.runap", "https://x", "2026-10-09", 2)]
    m1 = r.publicar([_unido()[r.COLUMNAS]], origenes, tmp_path / "a")
    m2 = r.publicar([_unido()[r.COLUMNAS].iloc[::-1]], origenes, tmp_path / "b")
    assert m1.huella == m2.huella and m1.version == m2.version
    leido = gpd.read_parquet(tmp_path / "a" / f"restricciones_{m1.version}.parquet")
    assert r.huella(leido) == m1.huella  # el GeoParquet guarda exactamente lo medido
    manifiesto = json.loads(
        (tmp_path / "a" / f"restricciones_{m1.version}.json").read_text("utf-8")
    )
    assert manifiesto["licencia"] == "CC-BY-SA-4.0" and manifiesto["filas"] == 4


def test_el_contrato_odcs_y_el_codigo_dicen_lo_mismo() -> None:
    import yaml

    ruta = Path(__file__).resolve().parents[1] / "catalogo" / "datasets" / "restricciones.odcs.yaml"
    contrato = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    (tabla,) = contrato["schema"]
    assert [p["name"] for p in tabla["properties"]] == r.COLUMNAS
    tipos = next(p for p in tabla["properties"] if p["name"] == "tipo")["description"]
    assert [t.strip() for t in tipos.split("|")] == list(r.TIPOS)
    assert contrato["license"] == "CC-BY-SA-4.0" and contrato["kind"] == "DataContract"
