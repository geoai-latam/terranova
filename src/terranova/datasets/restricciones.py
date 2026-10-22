"""Dataset curado de restricciones v0 (F4.1, ADR-0008 «curado»).

descarga → normalización → validación (pandera) → unión → GeoParquet (+ PostGIS) → huella → versión.

Fuentes v0, todas con licencia verificada CC BY-SA 4.0 (catalogo/licencias/m1.yaml), así que el
dataset también es CC BY-SA 4.0 (ADR-0019):
- RUNAP (Parques Nacionales Naturales): descarga masiva publicada.
- ANT: resguardos indígenas formalizados y zonas de reserva campesina constituidas.
Fuera de v0: reservas de la Ley 2.ª (licencia por verificar) y lo que no pase la compuerta.

La huella es del CONTENIDO (filas ordenadas, atributos y geometría normalizada en WKB), no de los
bytes del archivo: dos corridas sobre la misma fuente dan la misma huella aunque cambie el escritor.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pandera.pandas as pa
import shapely

CRS = "EPSG:4326"
EPOCA = datetime(1970, 1, 1, tzinfo=UTC)
PRECISION = 1e-7  # ≈ 1 cm: estabiliza la geometría para la huella
TIPOS = ("area_protegida", "resguardo_indigena", "zona_reserva_campesina")
COLUMNAS = ["id", "tipo", "nombre", "categoria", "acto", "fecha", "fuente_id", "url", "geometry"]

RUNAP_URL = "https://storage.googleapis.com/pnn_geodatabase/runap/latest.zip"


@dataclass(frozen=True)
class CapaAnt:
    url: str
    fuente_id: str
    oid: str  # campo de orden estable para paginar
    id: str
    nombre: str
    acto: tuple[str, ...]  # se unen con espacio (tipo y número)
    fecha: str
    categoria: str | None = None


ANT: dict[str, CapaAnt] = {
    "resguardo_indigena": CapaAnt(
        url="https://utility.arcgis.com/usrsvcs/servers/8944116ccfd34a7189c4bc44b8e19186/rest/services/"
        "DatosAbiertos/Resguardo_Indigena_Formalizado/FeatureServer/0",
        fuente_id="ant.resguardos_indigenas",
        oid="OBJECTID",
        id="ID",
        nombre="NOMBRE",
        acto=("ULTIMO_TIPO_ACTO_ADMIN", "ULTIMO_NUMERO_ACTO_ADMIN"),
        fecha="ULTIMA_FECHA_ACTO_ADMIN",
        categoria="PUEBLO",
    ),
    "zona_reserva_campesina": CapaAnt(
        url="https://utility.arcgis.com/usrsvcs/servers/0eca5beb8afe43708622fdd7646cd577/rest/services/"
        "DatosAbiertos/Zonas_de_Reserva_Campesina_Constituida/FeatureServer/0",
        fuente_id="ant.zonas_reserva_campesina",
        oid="OBJECTID_1",
        id="ID_ZRC_C",
        nombre="NOMBRE_ZON",
        acto=("ACTO_ADMIN",),
        fecha="FECHA_CONSTITUCION",
    ),
}


@dataclass
class Origen:
    fuente_id: str
    url: str
    version: str  # Last-Modified de la descarga o fecha de la consulta
    filas: int
    licencia: str = "CC-BY-SA-4.0"


@dataclass
class Manifiesto:
    dataset: str
    version: str
    huella: str
    filas: int
    por_tipo: dict[str, int]
    licencia: str
    generado: str
    origenes: list[Origen] = field(default_factory=list)
    excluidas: list[str] = field(default_factory=list)


ESQUEMA = pa.DataFrameSchema(
    {
        "id": pa.Column(str, unique=True, nullable=False),
        "tipo": pa.Column(str, pa.Check.isin(TIPOS)),
        "nombre": pa.Column(str, pa.Check.str_length(1, 300), nullable=False),
        "categoria": pa.Column(str, nullable=True),
        "acto": pa.Column(str, nullable=True),
        "fecha": pa.Column(str, nullable=True),
        "fuente_id": pa.Column(str, nullable=False),
        "url": pa.Column(str, nullable=True),
    },
    checks=[
        pa.Check(lambda d: d.geometry.notna().all(), error="sin geometría"),
        pa.Check(lambda d: d.geometry.is_valid.all(), error="geometría inválida"),
        pa.Check(
            lambda d: d.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all(),
            error="solo polígonos",
        ),
        pa.Check(lambda d: str(d.crs) == CRS, error=f"CRS distinto de {CRS}"),
        pa.Check(
            lambda d: (lambda b: b[0] >= -180 and b[2] <= 180 and b[1] >= -90 and b[3] <= 90)(
                d.total_bounds
            ),
            error="fuera de lon/lat",
        ),
    ],
    strict=False,  # las columnas ya se eligieron (COLUMNAS); la geometría se revisa en los checks
)


def _texto(v: Any) -> str | None:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    t = str(v).strip()
    return t or None


def normalizar_runap(g: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """RUNAP → esquema común. Fuera `nit` y `organizacion`: en reservas de la sociedad civil pueden
    identificar a una persona (ADR-0014)."""
    return gpd.GeoDataFrame(
        {
            "id": "runap:" + g["ap_id"].astype(str),
            "tipo": "area_protegida",
            "nombre": g["ap_nombre"].map(_texto),
            "categoria": g["ap_categor"].map(_texto),
            "acto": None,
            "fecha": g["fecha_insc"].map(_texto),
            "fuente_id": "pnn.runap",
            "url": g["url"].map(_texto),
        },
        geometry=g.geometry.to_crs(CRS),
        crs=CRS,
    )


def normalizar_ant(g: gpd.GeoDataFrame, tipo: str, capa: CapaAnt) -> gpd.GeoDataFrame:
    def col(nombre: str | None) -> pd.Series:
        if nombre and nombre in g.columns:
            return g[nombre].map(_texto)
        return pd.Series([None] * len(g), index=g.index, dtype=object)

    acto = pd.concat([col(c) for c in capa.acto], axis=1).apply(
        lambda f: " ".join(x for x in f if isinstance(x, str) and x) or None, axis=1
    )
    return gpd.GeoDataFrame(
        {
            "id": f"{capa.fuente_id}:" + col(capa.id).fillna(col(capa.oid)).astype(str),
            "tipo": tipo,
            "nombre": col(capa.nombre),
            "categoria": col(capa.categoria),
            "acto": acto,
            "fecha": col(capa.fecha).map(_fecha),
            "fuente_id": capa.fuente_id,
            "url": None,
        },
        geometry=g.geometry.to_crs(CRS),
        crs=CRS,
    )


def _fecha(v: str | None) -> str | None:
    """Epoch en ms (ArcGIS) a fecha ISO; un texto se deja como viene."""
    if v and v.lstrip("-").isdigit() and len(v) >= 10:
        # 1970 + timedelta: fromtimestamp no acepta fechas anteriores a 1970 en Windows
        return (EPOCA + timedelta(milliseconds=int(v))).date().isoformat()
    return v


def estabilizar(g: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Geometrías válidas, con precisión fija y normalizadas; filas en orden estable."""
    geom = shapely.make_valid(g.geometry.values)
    geom = shapely.normalize(shapely.set_precision(geom, PRECISION))
    g = g.set_geometry(gpd.GeoSeries(geom, index=g.index, crs=g.crs))
    g = g[g.geometry.notna() & ~g.geometry.is_empty]
    # make_valid puede dejar colecciones: se conservan solo las partes de área
    g = g.set_geometry(g.geometry.map(_solo_area))
    g = g[g.geometry.notna()]
    return g.sort_values(["tipo", "id"]).reset_index(drop=True)


def _solo_area(geom: Any) -> Any:
    if geom is None or geom.geom_type in ("Polygon", "MultiPolygon"):
        return geom
    partes = [p for p in getattr(geom, "geoms", []) if p.geom_type in ("Polygon", "MultiPolygon")]
    if not partes:
        return None
    return shapely.normalize(shapely.union_all(partes))


def huella(g: gpd.GeoDataFrame) -> str:
    """sha256 del contenido: por fila, sus atributos (JSON canónico) y su geometría (WKB)."""
    h = hashlib.sha256()
    ordenado = g.sort_values(["tipo", "id"])
    for fila, wkb in zip(
        ordenado.drop(columns="geometry").to_dict("records"),
        shapely.to_wkb(ordenado.geometry.values, hex=True),
        strict=True,
    ):
        limpio = {k: (None if pd.isna(v) else v) for k, v in fila.items()}
        h.update(json.dumps(limpio, ensure_ascii=False, sort_keys=True).encode())
        h.update(b"|")
        h.update(str(wkb).encode())
        h.update(b"\n")
    return "sha256:" + h.hexdigest()


def validar(g: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(ESQUEMA.validate(g), geometry="geometry", crs=g.crs)


# --- descarga -----------------------------------------------------------------------------------


def descargar_runap(directorio: Path) -> tuple[Path, str]:
    """La descarga masiva de RUNAP, guardada por su fecha de publicación (no se repite)."""
    with urllib.request.urlopen(urllib.request.Request(RUNAP_URL, method="HEAD"), timeout=60) as r:
        modificado = r.headers.get("Last-Modified", "")
    version = datetime.strptime(modificado, "%a, %d %b %Y %H:%M:%S GMT").date().isoformat()
    ruta = directorio / "runap" / f"runap_{version}.zip"
    if not ruta.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(RUNAP_URL, ruta)
    return ruta, version


PAGINA_ANT = 200  # con 1000 polígonos por página el proxy de utility.arcgis.com responde 500


def _con_reintentos(url: str, intentos: int = 3) -> dict[str, Any]:
    """Una consulta de la descarga, con dos reintentos ante un 5xx (pocas consultas, con espera)."""
    for intento in range(1, intentos + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                datos: dict[str, Any] = json.load(r)
                return datos
        except urllib.error.HTTPError as exc:
            if exc.code < 500 or intento == intentos:
                raise
            time.sleep(5 * intento)
    raise AssertionError("inalcanzable")


def consultar_ant(capa: CapaAnt, directorio: Path) -> tuple[Path, str]:
    """Todas las filas de una capa ArcGIS, por páginas, en GeoJSON (una corrida por día)."""
    version = datetime.now(UTC).date().isoformat()
    ruta = directorio / "ant" / f"{capa.fuente_id}_{version}.geojson"
    if ruta.exists():
        return ruta, version
    rasgos: list[dict[str, Any]] = []
    while True:
        q = urllib.parse.urlencode(
            {
                "where": "1=1",
                "outFields": "*",
                "outSR": "4326",
                "geometryPrecision": "7",
                "orderByFields": capa.oid,
                "resultOffset": len(rasgos),
                "resultRecordCount": PAGINA_ANT,
                "f": "geojson",
            }
        )
        pagina = _con_reintentos(f"{capa.url}/query?{q}")
        nuevos = pagina.get("features") or []
        rasgos += nuevos
        if len(nuevos) < PAGINA_ANT:
            break
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps({"type": "FeatureCollection", "features": rasgos}, ensure_ascii=False),
        encoding="utf-8",
    )
    return ruta, version


# --- construcción -------------------------------------------------------------------------------


def construir(fuentes: Path, salida: Path) -> Manifiesto:
    ruta_runap, v_runap = descargar_runap(fuentes)
    partes = [normalizar_runap(gpd.read_file(f"zip://{ruta_runap.as_posix()}!runap.shp"))]
    origenes = [Origen("pnn.runap", RUNAP_URL, v_runap, len(partes[0]))]
    for tipo, capa in ANT.items():
        ruta, version = consultar_ant(capa, fuentes)
        parte = normalizar_ant(gpd.read_file(ruta), tipo, capa)
        partes.append(parte)
        origenes.append(Origen(capa.fuente_id, capa.url, version, len(parte)))
    return publicar(partes, origenes, salida)


def publicar(partes: list[gpd.GeoDataFrame], origenes: list[Origen], salida: Path) -> Manifiesto:
    unido = gpd.GeoDataFrame(pd.concat(partes, ignore_index=True), geometry="geometry", crs=CRS)
    unido = validar(estabilizar(unido[COLUMNAS]))
    hu = huella(unido)
    version = f"v0-{max(o.version for o in origenes)}-{hu[7:15]}"
    salida.mkdir(parents=True, exist_ok=True)
    unido.to_parquet(salida / f"restricciones_{version}.parquet", index=False)
    manifiesto = Manifiesto(
        dataset="restricciones",
        version=version,
        huella=hu,
        filas=len(unido),
        por_tipo={t: int((unido["tipo"] == t).sum()) for t in TIPOS},
        licencia="CC-BY-SA-4.0",
        generado=datetime.now(UTC).replace(microsecond=0).isoformat(),
        origenes=origenes,
        excluidas=["reservas Ley 2.ª (Minambiente): licencia por verificar"],
    )
    (salida / f"restricciones_{version}.json").write_text(
        json.dumps(asdict(manifiesto), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifiesto


# --- PostGIS ------------------------------------------------------------------------------------


def cargar_postgis(parquet: Path, url: str, manifiesto: Manifiesto) -> str:
    """Carga una versión en `curado.restricciones_<version>` (GiST, huella en el comentario) y
    deja la vista `curado.restricciones` apuntando a ella. Cargar otra vez la misma versión no hace
    nada. Devuelve el nombre de la tabla."""
    psycopg: Any = importlib.import_module("psycopg")
    sql: Any = importlib.import_module("psycopg.sql")
    g = gpd.read_parquet(parquet)
    if huella(g) != manifiesto.huella:
        raise ValueError("el GeoParquet no corresponde a la huella del manifiesto")
    tabla = "restricciones_" + manifiesto.version.replace("-", "_").replace(".", "_")
    destino = sql.Identifier("curado", tabla)
    with psycopg.connect(url, autocommit=False) as c, c.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        cur.execute("CREATE SCHEMA IF NOT EXISTS curado")
        cur.execute("SELECT obj_description(to_regclass(%s), 'pg_class')", (f"curado.{tabla}",))
        fila = cur.fetchone()
        if fila and fila[0] == manifiesto.huella:
            return tabla
        cur.execute(sql.SQL("DROP TABLE IF EXISTS {}").format(destino))
        cur.execute(
            sql.SQL(
                """CREATE TABLE {} (
                id text PRIMARY KEY, tipo text NOT NULL, nombre text NOT NULL, categoria text,
                acto text, fecha text, fuente_id text NOT NULL, url text,
                geom geometry(Geometry, 4326) NOT NULL)"""
            ).format(destino)
        )
        filas = [
            (*(None if pd.isna(v) else v for v in fila[:-1]), shapely.to_wkb(fila[-1]))
            for fila in g[COLUMNAS].itertuples(index=False, name=None)
        ]
        cur.executemany(
            sql.SQL(
                "INSERT INTO {} VALUES (%s,%s,%s,%s,%s,%s,%s,%s, "
                "ST_SetSRID(ST_GeomFromWKB(%s), 4326))"
            ).format(destino),
            filas,
        )
        cur.execute(sql.SQL("CREATE INDEX ON {} USING gist (geom)").format(destino))
        # DDL no acepta parámetros: la huella va como literal escapado
        cur.execute(
            sql.SQL("COMMENT ON TABLE {} IS {}").format(destino, sql.Literal(manifiesto.huella))
        )
        cur.execute(
            sql.SQL("CREATE OR REPLACE VIEW curado.restricciones AS SELECT * FROM {}").format(
                destino
            )
        )
        c.commit()
    return tabla
