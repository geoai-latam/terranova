"""Copias de fuentes abiertas en PostGIS (G3, ADR-0024).

Tres piezas, de la más pura a la que toca la red y la base:

- `plan_de_consulta`: arma el SQL parametrizado de `consultar_copia` con un vocabulario cerrado.
  Los nombres de columna salen del catálogo (la lista blanca) y los valores de la entrada van como
  parámetros, nunca dentro del texto (ADR-0012).
- `descargar_socrata` y `AlmacenCopias`: el job diario. Baja la ventana de la fuente (solo la lista
  blanca, ordenada por la clave), la guarda en una tabla nueva `copia.<tabla>_<version>` y mueve la
  vista `copia.<tabla>` a esa versión de una vez. El manifiesto queda en `copia.versiones`.
- `ConectorCopia`: el conector interno `copia` que usa la puerta. Responde como un conector MCP,
  con `servido_desde` y `consultado_en` de la copia, y `obsoleto` si pasó su SLA (ADR-0008).
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from terranova.catalogo import Catalogo, Copia, Fuente

ESQUEMA = "copia"
PAGINA = 50_000
MAX_LIMITE = 1_000
AGREGADOS = {"count", "sum", "avg", "median", "min", "max", "cociente"}
_ALIAS = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_TIPO_SQL = {
    "str": "text",
    "int": "bigint",
    "float": "double precision",
    "bool": "boolean",
    "date": "date",
    "datetime": "timestamptz",
}


class ErrorCopia(ValueError):
    """La consulta pide algo fuera del vocabulario o de la lista blanca: error de la ficha."""


# --- plan de consulta (sin red ni base) ------------------------------------------------------


@dataclass(frozen=True)
class Plan:
    sql: str
    parametros: tuple[Any, ...]
    sql_total: str | None  # cuántas filas cumplen, para la completitud (None con agregados)
    parametros_total: tuple[Any, ...]
    limite: int
    geometria: bool = False  # cada fila trae `_geojson`: sale como feature_collection


# Cómo sale la geometría de una copia espacial: la misma idea que el conector ArcGIS («simplificada»
# ≈ 55 m basta para pintar un parque y evita mandar polígonos de decenas de MB).
_GEOMETRIA = {
    "completa": "ST_AsGeoJSON(_geom, 7)",
    "simplificada": "ST_AsGeoJSON(ST_SimplifyPreserveTopology(_geom, 0.0005), 5)",
}


_POLIGONO = "ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))"
# la columna con el área de cada elemento dentro del polígono (`area_en_poligono`)
AREA_EN_POLIGONO = "_area_ha"


# Sin mayúsculas ni tildes, en la columna y en lo buscado: SECOP escribe «CHIA» y el agente, «Chía».
_TILDES = ("áéíóúüñ", "aeiouun")


def _plano(texto: str) -> str:
    return texto.lower().translate(str.maketrans(*_TILDES))


def _plano_sql(columna: str) -> str:
    """La misma expresión en la consulta de `contiene` y en su índice: si difieren, no se usa."""
    return f"translate(lower({columna}), '{_TILDES[0]}', '{_TILDES[1]}')"


def _coordenadas(valor: Any, n: int, nombre: str) -> list[float]:
    """`n` números finitos (lon, lat…): van como parámetros, nunca dentro del SQL."""
    import math

    try:
        numeros = [float(v) for v in valor]
    except (TypeError, ValueError) as exc:
        raise ErrorCopia(f"`{nombre}` debe ser una lista de {n} números") from exc
    if len(numeros) != n or not all(math.isfinite(v) for v in numeros):
        raise ErrorCopia(f"`{nombre}` debe ser una lista de {n} números")
    return numeros


def _columna(nombre: str, permitidas: set[str]) -> str:
    if nombre not in permitidas:
        raise ErrorCopia(f"«{nombre}» no está en la lista blanca de la copia")
    return f'"{nombre}"'


def _agregado(alias: str, expresion: str, permitidas: set[str]) -> str:
    if not _ALIAS.match(alias):
        raise ErrorCopia(f"alias inválido: «{alias}»")
    return f'{_expresion_agregada(expresion, permitidas)} AS "{alias}"'


def _expresion_agregada(expresion: str, permitidas: set[str]) -> str:
    funcion, _, columna = expresion.partition(":")
    if funcion not in AGREGADOS:
        raise ErrorCopia(f"agregado desconocido: «{funcion}» (se puede {sorted(AGREGADOS)})")
    if funcion == "count" and not columna:
        return "count(*)"
    if funcion == "cociente":
        # promedio de una copia preagregada: suma de las sumas sobre suma de los conteos
        numerador, barra, denominador = columna.partition("/")
        if not barra:
            raise ErrorCopia("`cociente` va como «cociente:suma/conteo»")
        num, den = _columna(numerador, permitidas), _columna(denominador, permitidas)
        return f"sum({num})::float / nullif(sum({den}), 0)"
    col = _columna(columna, permitidas)
    if funcion == "median":
        return f"percentile_cont(0.5) WITHIN GROUP (ORDER BY {col})"
    return f"{funcion}({col})"


def plan_de_consulta(fuente: Fuente, argumentos: dict[str, Any]) -> Plan:
    """El SQL de `consultar_copia`.

    `argumentos` (de la ficha, ya con la entrada puesta): `select` (columnas), `filtros`
    ({columna: valor}, igualdad), `texto` (búsqueda en las columnas `copia.texto`), `agregados`
    ({alias: "count" | "sum:col" | "median:col" | "cociente:suma/conteo" …}), `group`
    (columnas), `minimo` ({agregado: n}: solo los grupos en que llega a n), `order` (columnas; con
    `-` delante, descendente), `limite` y `contiene` ({columna: palabras}: la columna trae todas
    las palabras, sin distinguir mayúsculas ni tildes). En una copia espacial, además: `punto`
    ([lon, lat]), `poligono` (GeoJSON, ADR-0035) o
    `bbox` ([oeste, sur, este, norte]), en EPSG:4326, para los elementos que los tocan,
    `geometria` («completa», «simplificada» o «ninguna», la de por defecto; con `poligono`,
    también «recortada»: solo la parte de cada elemento que cae dentro) y, con `poligono`,
    `area_en_poligono` (la columna `_area_ha`: las hectáreas de cada elemento dentro del polígono;
    se puede ordenar por ella).
    """
    if fuente.copia is None:
        raise ErrorCopia(f"{fuente.id} no tiene copia")
    permitidas = set(fuente.campos)
    vista = f'{ESQUEMA}."{fuente.copia.tabla}"'
    group = [_columna(c, permitidas) for c in argumentos.get("group") or []]
    agregados = [
        _agregado(a, e, permitidas) for a, e in (argumentos.get("agregados") or {}).items()
    ]
    columnas = [_columna(c, permitidas) for c in argumentos.get("select") or []]
    if agregados and (sueltas := set(columnas) - set(group)):
        raise ErrorCopia(f"con agregados, las columnas van en `group`: {sorted(sueltas)}")
    espaciales = [k for k in ("punto", "bbox", "poligono") if argumentos.get(k) is not None]
    geometria = str(argumentos.get("geometria") or "ninguna")
    if (espaciales or geometria != "ninguna") and not fuente.copia.espacial:
        raise ErrorCopia(f"{fuente.id} no tiene geometría en su copia")
    if geometria not in (*_GEOMETRIA, "ninguna", "recortada"):
        raise ErrorCopia(f"geometría desconocida: «{geometria}»")
    if geometria != "ninguna" and agregados:
        raise ErrorCopia("con agregados no sale geometría")
    if not columnas and not agregados and fuente.copia.espacial:
        columnas = [_columna(c, permitidas) for c in fuente.campos]  # `*` traería `_geom` cruda
    if columnas and not agregados and not group and fuente.copia.clave in permitidas:
        # P0.6 (visores): cada elemento sale con su id estable, la clave de la copia, para que quien
        # pinta o une capas distinga dos tramos con los mismos atributos (UPME trae 24 así)
        if (clave_copia := _columna(fuente.copia.clave, permitidas)) not in columnas:
            columnas.append(clave_copia)
    con_geometria = geometria != "ninguna"
    salida: list[str] = []
    parametros_seleccion: list[Any] = []
    if geometria == "recortada":
        # la parte de cada elemento dentro del polígono: en una ronda que cruza un lote, la franja
        # que no se puede construir, no los 40 km del río
        if argumentos.get("poligono") is None:
            raise ErrorCopia("la geometría «recortada» va con `poligono`")
        salida.append(f"ST_AsGeoJSON(ST_Intersection(_geom, {_POLIGONO}), 7) AS _geojson")
        parametros_seleccion.append(json.dumps(argumentos["poligono"]))
    elif con_geometria:
        salida.append(f"{_GEOMETRIA[geometria]} AS _geojson")
    if argumentos.get("area_en_poligono"):
        # cuánto de cada elemento cae dentro del polígono, en hectáreas (geodésicas): lo que
        # pesa cada tratamiento o cada uso en un lote, no solo que lo toca
        if argumentos.get("poligono") is None or agregados:
            raise ErrorCopia("`area_en_poligono` va con `poligono` y sin agregados")
        salida.append(
            f"round((ST_Area(ST_Intersection(_geom, {_POLIGONO})::geography) / 10000)::numeric, 4)"
            f"::float AS {AREA_EN_POLIGONO}"
        )
        parametros_seleccion.append(json.dumps(argumentos["poligono"]))
    seleccion = ", ".join([*(columnas or ([] if agregados else ["*"])), *agregados, *salida])

    condiciones, parametros = [], []
    for columna, valor in (argumentos.get("filtros") or {}).items():
        condiciones.append(f"{_columna(columna, permitidas)} = %s")
        # al tipo de la columna en la ficha: un año que entra como número (2001) contra una columna
        # de texto («2001») haría fallar la consulta (text = integer)
        campo = fuente.campos.get(columna)
        parametros.append(str(valor) if campo and campo.tipo == "str" else valor)
    for columna, buscado in (argumentos.get("contiene") or {}).items():
        expresion = _plano_sql(_columna(columna, permitidas))
        palabras = _plano(str(buscado)).split()
        if not palabras:
            raise ErrorCopia(f"`contiene` de «{columna}» está vacío")
        for palabra in palabras:
            condiciones.append(f"{expresion} LIKE %s")  # la barra invertida escapa por defecto
            seguro = re.sub(r"([\\%_])", r"\\\1", palabra)
            parametros.append(f"%{seguro}%")
    if (texto := argumentos.get("texto")) is not None:
        if not fuente.copia.texto:
            raise ErrorCopia(f"{fuente.id} no tiene columnas de texto en su copia")
        condiciones.append("_texto @@ plainto_tsquery('spanish', %s)")
        parametros.append(str(texto))
    if len(espaciales) > 1:
        raise ErrorCopia("`punto`, `bbox` y `poligono` no van juntos")
    if (punto := argumentos.get("punto")) is not None:
        condiciones.append("ST_Intersects(_geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))")
        parametros += _coordenadas(punto, 2, "punto")
    if (bbox := argumentos.get("bbox")) is not None:
        caja = _coordenadas(bbox, 4, "bbox")
        if caja[0] > caja[2] or caja[1] > caja[3]:
            raise ErrorCopia("`bbox` va como [oeste, sur, este, norte]")
        condiciones.append("ST_Intersects(_geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))")
        parametros += caja
    if (poligono := argumentos.get("poligono")) is not None:
        condiciones.append(f"ST_Intersects(_geom, {_POLIGONO})")
        parametros.append(json.dumps(poligono))
    donde = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""

    orden = []
    for c in argumentos.get("order") or []:
        desc = c.startswith("-")
        nombre = c.lstrip("-")
        if nombre == AREA_EN_POLIGONO and argumentos.get("area_en_poligono"):
            expr = AREA_EN_POLIGONO
        elif agregados and _ALIAS.match(nombre):
            expr = f'"{nombre}"'
        else:
            expr = _columna(nombre, permitidas)
        orden.append(f"{expr} {'DESC' if desc else 'ASC'} NULLS LAST")
    limite = max(1, min(int(argumentos.get("limite") or MAX_LIMITE), MAX_LIMITE))
    # `desde` (ADR-0040): las páginas que pasan del tope de la ficha van a la copia con OFFSET. Para
    # que dos páginas no se crucen, el orden termina siempre en la clave (única en la copia).
    desde = int(argumentos.get("desde") or 0)
    if desde < 0:
        raise ErrorCopia("`desde` va desde 0")
    if not agregados and not group and fuente.copia.clave in permitidas:
        clave = _columna(fuente.copia.clave, permitidas)
        if not any(o.startswith(f"{clave} ") for o in orden):
            orden.append(f"{clave} ASC")

    # `minimo` ({agregado: n}): solo los grupos en que el agregado llega a n, p. ej. 10 personas
    # (ADR-0014: un grupo chico de personas no sale)
    minimos, parametros_minimo = [], []
    for expresion, n in (argumentos.get("minimo") or {}).items():
        if not group:
            raise ErrorCopia("`minimo` va con `group`")
        minimos.append(f"{_expresion_agregada(expresion, permitidas)} >= %s")
        parametros_minimo.append(int(n))

    sql = f"SELECT {seleccion} FROM {vista}{donde}"
    if group:
        sql += f" GROUP BY {', '.join(group)}"
    if minimos:
        sql += f" HAVING {' AND '.join(minimos)}"
    if orden:
        sql += f" ORDER BY {', '.join(orden)}"
    sql += " LIMIT %s"
    if desde:
        sql += " OFFSET %s"
    sql_total = None if agregados else f"SELECT count(*) FROM {vista}{donde}"
    return Plan(
        sql,
        (
            *parametros_seleccion,
            *parametros,
            *parametros_minimo,
            limite,
            *([desde] if desde else []),
        ),
        sql_total,
        tuple(parametros),
        limite,
        con_geometria,
    )


# --- el job: descarga y almacén --------------------------------------------------------------


def _valor_socrata(valor: Any) -> Any:
    if isinstance(valor, dict) and "url" in valor:  # las URL vienen como {url: …}
        return valor["url"]
    return valor


def descargar_socrata(
    fuente: Fuente, desde: date | None = None, *, cliente: Any = None
) -> Iterator[list[dict[str, Any]]]:
    """Páginas de la ventana de la fuente: solo la lista blanca, ordenadas por la clave."""
    import httpx

    assert fuente.copia is not None
    copia = fuente.copia
    columnas = list(fuente.campos)
    params: dict[str, Any] = {"$select": ", ".join(columnas), "$order": f"{copia.clave}"}
    inicio = desde or (copia.ventana.desde if copia.ventana else None)
    if copia.ventana and inicio:
        params["$where"] = f"{copia.ventana.columna} >= '{inicio.isoformat()}'"
    url = f"https://www.datos.gov.co/resource/{copia.conjunto}.json"
    propio = cliente is None
    http = cliente or httpx.Client(timeout=180, headers={"User-Agent": "terranova-copias/1"})
    try:
        desplazamiento = 0
        while True:
            pagina = _pedir(http, url, {**params, "$limit": PAGINA, "$offset": desplazamiento})
            if not pagina:
                return
            yield [{c: _valor_socrata(f.get(c)) for c in columnas} for f in pagina]
            if len(pagina) < PAGINA:
                return
            desplazamiento += len(pagina)
    finally:
        if propio:
            http.close()


# --- microdatos de personas, copiados ya agregados (origen socrata_agregado) ----------------------
#
# El Saber 11 trae una fila por estudiante (7,1 M) y la fuente repite algunos. Agregar en vivo en
# dos etapas (por estudiante y luego por grupo) pasa de 90 s en un municipio grande. La copia baja
# una tanda (periodo) a la vez, cuenta a cada persona una vez dentro de su tanda y guarda solo los
# grupos: personas, y suma y número de datos de cada medida. El seudónimo no se guarda (ADR-0014).


def _numero(valor: Any) -> float | None:
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def agregar_tanda(
    filas: Iterator[dict[str, Any]], pre: Any, vistos: set[int] | None = None
) -> list[dict[str, Any]]:
    """Los grupos de una tanda, sin `_fila`. Una persona (`pre.unico`) cuenta una vez: se toma su
    primera fila (la fuente repite la misma, con los mismos puntajes)."""
    vistos = set() if vistos is None else vistos
    grupos: dict[tuple[Any, ...], dict[str, Any]] = {}
    for fila in filas:
        unico = fila.get(pre.unico)
        if unico in (None, ""):
            continue  # sin seudónimo no se puede saber si es una persona repetida
        huella = hash(str(unico))  # un entero ocupa menos que el texto: la tanda trae ~1 M
        if huella in vistos:
            continue
        vistos.add(huella)
        clave = tuple(fila.get(c) or None for c in pre.grupo)
        grupo = grupos.get(clave)
        if grupo is None:
            grupo = dict(zip(pre.grupo, clave, strict=True))
            grupo[pre.cuenta] = 0
            for m in pre.medidas:
                grupo[f"suma_{m}"], grupo[f"n_{m}"] = 0.0, 0
            if pre.nombre:
                grupo[pre.nombre] = None
            grupos[clave] = grupo
        grupo[pre.cuenta] += 1
        for m in pre.medidas:
            if (valor := _numero(fila.get(m))) is not None:
                grupo[f"suma_{m}"] += valor
                grupo[f"n_{m}"] += 1
        if pre.nombre and (nombre := fila.get(pre.nombre)):
            if grupo[pre.nombre] is None or nombre > grupo[pre.nombre]:
                grupo[pre.nombre] = nombre
    for grupo in grupos.values():
        for m in pre.medidas:
            if not grupo[f"n_{m}"]:
                grupo[f"suma_{m}"] = None  # sin datos: vacío, no 0
    return list(grupos.values())


def descargar_socrata_agregado(
    fuente: Fuente, desde: date | None = None, *, cliente: Any = None
) -> Iterator[list[dict[str, Any]]]:
    """Baja el conjunto tanda por tanda (`particion`), en orden de `:id`, y rinde los grupos de
    cada tanda con `_fila` desde 1. `desde` se ignora: se copia entero. Una tanda sin filas no se
    publica: la copia se cae antes de quedar a medias."""
    import httpx

    assert fuente.copia is not None and fuente.copia.preagregado is not None
    pre = fuente.copia.preagregado
    url = f"https://www.datos.gov.co/resource/{fuente.copia.conjunto}.json"
    propio = cliente is None
    http = cliente or httpx.Client(timeout=180, headers={"User-Agent": "terranova-copias/1"})
    try:
        if pre.tandas:
            valores = list(pre.tandas)
        else:
            tandas = _pedir(
                http, url, {"$select": pre.particion, "$group": pre.particion, "$limit": 1000}
            )
            valores = sorted(str(t[pre.particion]) for t in tandas if t.get(pre.particion))
        if not valores:
            raise ErrorCopia("la fuente no dio ninguna tanda: la copia no se publica")
        numero = 0
        for valor in valores:
            seguro = valor.replace("'", "''")
            params = {
                "$select": ", ".join(pre.columnas_fuente),
                "$where": f"{pre.particion} = '{seguro}'",
                "$order": ":id",
            }

            def filas(params: dict[str, Any] = params) -> Iterator[dict[str, Any]]:
                desplazamiento = 0
                while True:
                    pagina = _pedir(
                        http, url, {**params, "$limit": PAGINA, "$offset": desplazamiento}
                    )
                    yield from pagina
                    if len(pagina) < PAGINA:
                        return
                    desplazamiento += len(pagina)

            grupos = agregar_tanda(filas(), pre)
            if not grupos:
                raise ErrorCopia(f"la tanda {valor} llegó sin filas: la copia no se publica")
            for grupo in grupos:
                numero += 1
                grupo[FILA] = numero
            yield grupos
    finally:
        if propio:
            http.close()


# --- capas ArcGIS con su geometría (origen arcgis) ----------------------------------------------
#
# Para las capas que no se pueden consultar en vivo desde el servidor (RUNAP y UPRA bloquean o no
# aceptan la IP del datacenter) o que tardan demasiado (agrología del IGAC, ~50 s por punto). Se
# baja una petición a la vez, con pausa entre páginas: es un servidor del Estado (ADR-0018).

GEOMETRIA = "_geom"  # la columna de la geometría (EPSG:4326) en la copia y en las filas bajadas
PAUSA_ARCGIS_S = 1.0
# La reparación de geometrías va por tandas de la clave y deja como vienen los polígonos enormes:
# un solo UPDATE sobre los 548 mil polígonos de conflictos de uso llevó el proceso de Postgres a
# ~850 MB y el límite del contenedor lo mató; ST_MakeValid de UN polígono de 498 mil vértices pide
# ~1 GB. El cruce por punto responde igual sobre un polígono inválido (anillos), sin error.
REPARAR_POR_TANDA = 5000
REPARAR_HASTA_VERTICES = 50_000


def ewkt(geometria: dict[str, Any]) -> str:
    """GeoJSON → EWKT en EPSG:4326, solo lon y lat: Postgres lo lee tal cual en un COPY."""

    def punto(p: list[float]) -> str:
        return f"{float(p[0])!r} {float(p[1])!r}"

    def linea(ps: list[list[float]]) -> str:
        return "(" + ",".join(punto(p) for p in ps) + ")"

    def poligono(anillos: list[list[list[float]]]) -> str:
        return "(" + ",".join(linea(a) for a in anillos) + ")"

    tipo = geometria.get("type")
    c: Any = geometria.get("coordinates")
    cuerpos = {
        "Point": lambda: f"POINT({punto(c)})",
        "MultiPoint": lambda: "MULTIPOINT(" + ",".join(f"({punto(p)})" for p in c) + ")",
        "LineString": lambda: f"LINESTRING{linea(c)}",
        "MultiLineString": lambda: "MULTILINESTRING(" + ",".join(linea(x) for x in c) + ")",
        "Polygon": lambda: f"POLYGON{poligono(c)}",
        "MultiPolygon": lambda: "MULTIPOLYGON(" + ",".join(poligono(x) for x in c) + ")",
    }
    if tipo not in cuerpos or not c:
        raise ErrorCopia(f"geometría que la copia no sabe guardar: «{tipo}»")
    return f"SRID=4326;{cuerpos[str(tipo)]()}"


class ConsultaRechazada(ValueError):
    """El servicio ArcGIS rechazó la consulta (`{"error": {"code": 400}}`): no se reintenta."""


def _pedir_arcgis(http: Any, url: str, params: dict[str, Any], intentos: int = 5) -> dict[str, Any]:
    """Una petición al servicio; ArcGIS responde los errores con 200 y `{"error": …}`.

    Espera 30, 60, 90 y 120 s entre intentos: un 500 pasajero del IGAC tumbó una copia de
    conflictos de uso a la página 68 de ~275, y la misma página respondió en 1 s minutos después."""
    import time

    for intento in range(1, intentos + 1):
        try:
            r = http.get(url, params=params)
            r.raise_for_status()
            datos: dict[str, Any] = r.json()
            if "error" in datos:
                error = datos["error"]
                if isinstance(error, dict) and error.get("code") == 400:
                    raise ConsultaRechazada(f"ArcGIS: {error}")
                raise ValueError(f"ArcGIS: {error}")
            return datos
        except ConsultaRechazada:
            raise  # la misma consulta fallará igual: no se espera ni se repite
        except Exception:
            if intento == intentos:
                raise
            time.sleep(30 * intento)  # cortesía con la fuente: no se insiste de inmediato
    return {}


def _rescatar_pagina(
    http: Any, url: str, base: dict[str, Any], donde: str, copia: Any, fuente_id: str
) -> list[dict[str, Any]]:
    """La página sin geometría (¿de verdad terminó la capa?) y, si trae rasgos, sus geometrías por
    tandas de la clave: el que el servicio no sabe dar queda sin geometría, con aviso."""
    import sys

    sin = (
        _pedir_arcgis(
            http,
            url,
            {
                **base,
                "where": donde,
                "resultRecordCount": copia.por_pagina,
                "returnGeometry": "false",
            },
        ).get("features")
        or []
    )
    if not sin:
        return []  # la capa sí terminó
    claves: list[int] = [int((r.get("properties") or {})[copia.clave]) for r in sin]
    geometrias: dict[int, Any] = {}
    rotas: list[int] = []
    pendientes = [claves]
    sin_orden = {k: v for k, v in base.items() if k != "orderByFields"}
    while pendientes:
        lote = pendientes.pop()
        # por rango de la clave, no `IN (…)`: 2 000 claves en la URL dan 414 (SINIC). Las claves de
        # la página son contiguas dentro del filtro, así que el rango trae exactamente esas
        rango = f"{copia.clave} >= {lote[0]} AND {copia.clave} <= {lote[-1]}"
        donde_lote = f"({copia.filtro}) AND {rango}" if copia.filtro else rango
        try:
            rasgos = (
                _pedir_arcgis(http, url, {**sin_orden, "where": donde_lote}).get("features") or []
            )
        except ConsultaRechazada:
            rasgos = []  # algún rasgo del lote no sabe dar su geometría: se parte el lote
        if len(rasgos) == len(lote):
            for r in rasgos:
                geometrias[int((r.get("properties") or {})[copia.clave])] = r.get("geometry")
        elif len(lote) == 1:
            rotas.extend(lote)
        else:
            mitad = len(lote) // 2
            pendientes += [lote[:mitad], lote[mitad:]]
    if rotas:
        print(
            f"aviso {fuente_id}: {len(rotas)} elementos sin geometría (el servicio no la da): "
            f"{copia.clave} {rotas[:10]}",
            file=sys.stderr,
        )
    return [
        {"properties": r.get("properties"), "geometry": geometrias.get(c)}
        for r, c in zip(sin, claves, strict=True)
    ]


def descargar_arcgis(
    fuente: Fuente, desde: date | None = None, *, cliente: Any = None, pausa_s: float | None = None
) -> Iterator[list[dict[str, Any]]]:
    """Páginas de la capa: la lista blanca y, si la ficha la copia, la geometría GeoJSON en
    EPSG:4326 (`_geom`).

    `desde` se ignora (se copia la capa entera). Se pagina por la clave (`clave > última vista`,
    ordenado por ella) hasta una página vacía (no se confía en `exceededTransferLimit`): con
    `resultOffset` el servicio del IGAC tardaba ~50 s por página y así ~2 s, porque no recorre las
    filas ya vistas. Si el servicio sabe contar, al final se compara: una copia a medias no se
    publica."""
    import sys
    import time

    import httpx

    assert fuente.copia is not None
    if fuente.copia.servicios:
        yield from descargar_arcgis_servicios(fuente, desde, cliente=cliente, pausa_s=pausa_s)
        return
    assert fuente.copia.capa is not None
    copia = fuente.copia
    url = f"{fuente.url}/{copia.capa}/query"
    columnas = list(fuente.campos)
    # una parte de la capa, si la ficha lo declara; si no, toda: por la clave, que nunca es nula,
    # y no con `1=1`, que el geoportal del DANE rechaza con un 500 (como cualquier paréntesis)
    filtro = copia.filtro or f"{copia.clave} IS NOT NULL"
    base: dict[str, Any] = {
        "outFields": ",".join(columnas),
        "returnGeometry": "true" if copia.espacial else "false",
        "outSR": "4326",
        "geometryPrecision": "6",  # ~0,1 m
        "orderByFields": copia.clave,
        "f": "geojson",
    }
    if copia.tolerancia:
        base["maxAllowableOffset"] = str(copia.tolerancia)
    pausa = PAUSA_ARCGIS_S if pausa_s is None else pausa_s
    propio = cliente is None
    http = cliente or httpx.Client(timeout=600, headers={"User-Agent": "terranova-copias/1"})
    try:
        try:
            conteo = _pedir_arcgis(
                http, url, {"where": filtro, "returnCountOnly": "true", "f": "json"}, intentos=1
            )
            esperado: int | None = int(conteo["count"])
        except Exception as exc:  # noqa: BLE001 — sin conteo se copia igual, sin esa verificación
            esperado = None
            print(f"aviso {fuente.id}: la capa no dijo cuántos tiene ({exc})", file=sys.stderr)
        vistos = 0
        ultima: int | None = None
        while True:
            time.sleep(pausa)
            siguiente = f"{copia.clave} > {ultima}"
            if ultima is None:
                donde = filtro
            else:
                donde = f"({copia.filtro}) AND {siguiente}" if copia.filtro else siguiente
            try:
                datos = _pedir_arcgis(
                    http, url, {**base, "where": donde, "resultRecordCount": copia.por_pagina}
                )
            except ConsultaRechazada:
                if not copia.espacial:
                    raise
                datos = {}  # la geometría de un rasgo rompe la consulta (SDP: «Failed to execute»)
            rasgos = datos.get("features") or []
            if not rasgos and copia.espacial:
                # una página con geometría puede llegar vacía, o rechazada, aunque haya elementos:
                # un solo rasgo cuya geometría el servicio no sabe dar la tumba entera (SINIC,
                # objectid 1420608; SDP, área de actividad)
                rasgos = _rescatar_pagina(http, url, base, donde, copia, fuente.id)
            if not rasgos:
                break
            pagina = []
            for rasgo in rasgos:
                propiedades = rasgo.get("properties") or {}
                fila = {c: propiedades.get(c) for c in columnas}
                if copia.espacial:
                    fila[GEOMETRIA] = rasgo.get("geometry")
                pagina.append(fila)
            clave = pagina[-1].get(copia.clave)
            if (
                not isinstance(clave, int)
                or isinstance(clave, bool)
                or (ultima is not None and clave <= ultima)
            ):
                raise ErrorCopia(
                    f"la capa no pagina por {copia.clave}: llegó {clave!r} después de {ultima!r}"
                )
            ultima = clave
            vistos += len(rasgos)  # el conteo de la capa incluye las filas excluidas
            if copia.excluir:
                pagina = [f for f in pagina if not _excluida(f, copia.excluir)]
            yield pagina
        if esperado is not None and vistos != esperado:
            raise ErrorCopia(
                f"la capa dice {esperado} elementos y llegaron {vistos}: la copia no se publica"
            )
    finally:
        if propio:
            http.close()


def _excluida(fila: dict[str, Any], excluir: dict[str, list[str]]) -> bool:
    """¿La fila tiene en alguna columna uno de los valores que la ficha deja fuera?"""
    return any(str(fila.get(c)) in valores for c, valores in excluir.items())


POR_SERVICIO = 1_000_000  # la clave de la copia: posición del servicio por esto + el id en su capa


def descargar_arcgis_servicios(
    fuente: Fuente, desde: date | None = None, *, cliente: Any = None, pausa_s: float | None = None
) -> Iterator[list[dict[str, Any]]]:
    """Varias capas ArcGIS en una sola copia (`copia.servicios`), una tras otra.

    Cada capa nombra a su manera las mismas columnas (los POMCA de la CAR: `CAT_ORD`, `CAT_ORD_A`
    o `CATEGORIA`) y tiene su propio campo de id (`OBJECTID`, `OBJECTID_1`, `FID`). Se leen los
    campos de la capa, cada columna de la copia toma el primero de sus nombres (el suyo y sus
    `alias`) que la capa tenga, y la capa se baja con `descargar_arcgis`, con su verificación del
    conteo. La fila lleva el valor del servicio en `columna_servicio` y una clave única en toda la
    copia."""
    import httpx

    assert fuente.copia is not None and fuente.copia.columna_servicio is not None
    copia = fuente.copia
    columna_servicio: str = fuente.copia.columna_servicio
    propias = {copia.clave, columna_servicio}
    propio = cliente is None
    http = cliente or httpx.Client(timeout=600, headers={"User-Agent": "terranova-copias/1"})
    try:
        for posicion, (ruta, valor) in enumerate(copia.servicios.items(), start=1):
            servicio, _, capa = ruta.rpartition("/")
            meta = _pedir_arcgis(http, f"{fuente.url}/{ruta}", {"f": "json"})
            nombres = {str(c.get("name")) for c in meta.get("fields") or []}
            id_capa = str(meta.get("objectIdField") or "OBJECTID")
            origen = {}  # columna de la copia → nombre en esta capa
            for columna, campo in fuente.campos.items():
                if columna in propias:
                    continue
                hallado = next((n for n in (columna, *campo.alias) if n in nombres), None)
                if hallado is None:
                    if columna in copia.opcionales:
                        continue  # esta capa no la trae: la fila la lleva vacía
                    raise ErrorCopia(f"{ruta}: no tiene «{columna}» ni sus alias {campo.alias}")
                origen[columna] = hallado
            campos = {n: fuente.campos[c] for c, n in origen.items()}
            campos[id_capa] = fuente.campos[copia.clave]
            una = fuente.model_copy(
                update={
                    "url": f"{fuente.url}/{servicio}",
                    "campos": campos,
                    "copia": copia.model_copy(
                        update={
                            "capa": int(capa),
                            "clave": id_capa,
                            "servicios": {},
                            "columna_servicio": None,
                        }
                    ),
                }
            )
            for pagina in descargar_arcgis(una, desde, cliente=http, pausa_s=pausa_s):
                filas = []
                for fila in pagina:
                    id_fila = int(fila[id_capa])
                    if not 0 <= id_fila < POR_SERVICIO:
                        raise ErrorCopia(f"{ruta}: el id {id_fila} no cabe en la clave de la copia")
                    nueva: dict[str, Any] = dict.fromkeys(copia.opcionales)
                    nueva.update({c: fila.get(n) for c, n in origen.items()})
                    nueva[copia.clave] = posicion * POR_SERVICIO + id_fila
                    nueva[columna_servicio] = valor
                    if copia.espacial:
                        nueva[GEOMETRIA] = fila.get(GEOMETRIA)
                    filas.append(nueva)
                yield filas
    finally:
        if propio:
            http.close()


# --- lo que un conector MCP lee de la fuente (origen conector) ------------------------------------
#
# Para fuentes cuyo lector ya vive en un conector (p. ej. las hojas de los xlsx del DANE, que
# `web_tabla` sabe leer con sus encabezados de varias filas y su formato largo): la copia le pide
# al conector la tabla entera, sin filtros, y la guarda tal cual. Así lo copiado es idéntico a lo
# que se servía en vivo y no hay un segundo lector que mantener. `_fila` numera las filas en el
# orden de la fuente, para las tablas que no tienen una columna única.

FILA = "_fila"
MAX_FILAS_CONECTOR = 100_000  # tope que se le pide al conector; si la fuente da más, no se publica


def _conector_para(nombre: str) -> Any:
    """El conector MCP `nombre` con la URL y la llave del entorno (como la puerta)."""
    import json
    import os

    from terranova.conector import CONECTORES_POR_DEFECTO, ConectorMCP

    crudo = os.environ.get("TERRANOVA_CONECTORES")
    urls = json.loads(crudo) if crudo else dict(CONECTORES_POR_DEFECTO)
    if nombre not in urls:
        raise ErrorCopia(f"el conector {nombre} no está en TERRANOVA_CONECTORES")
    llave = os.environ.get(
        "TERRANOVA_LLAVE_" + nombre.upper().replace("-", "_"),
        os.environ.get("TERRANOVA_CONECTOR_LLAVE", ""),
    )
    if not llave:
        raise ErrorCopia(f"falta la llave del conector {nombre} (TERRANOVA_CONECTOR_LLAVE)")
    return ConectorMCP(urls[nombre], llave, timeout_s=600)


def descargar_conector(
    fuente: Fuente, desde: date | None = None, *, conector: Any = None
) -> Iterator[list[dict[str, Any]]]:
    """Una página: la tabla entera que da la tool del conector con los argumentos de la ficha.

    `desde` se ignora (se copia la tabla entera). Si el conector dice que cortó (completitud con
    `truncado` o menos filas que su total), la copia no se publica."""
    import asyncio

    copia = fuente.copia
    assert copia is not None and copia.tool and copia.conector
    tool, nombre_conector = copia.tool, copia.conector
    argumentos = {
        k: v.replace("{url_fuente}", fuente.url) if isinstance(v, str) else v
        for k, v in copia.argumentos.items()
    }
    argumentos.setdefault("max_filas", MAX_FILAS_CONECTOR)
    propio = conector is None
    mcp = conector or _conector_para(nombre_conector)

    async def pedir() -> dict[str, Any]:
        try:
            resultado: dict[str, Any] = await mcp.llamar(tool, argumentos)
            return resultado
        finally:
            if propio:
                await mcp.cerrar()

    respuesta = asyncio.run(pedir())
    tablas = [a for a in respuesta.get("artifacts") or [] if a.get("kind") == "table"]
    if len(tablas) != 1:
        raise ErrorCopia(f"{copia.tool} no dio una tabla (dio {len(tablas)})")
    filas = tablas[0].get("rows") or []
    completitud = (respuesta.get("facts") or {}).get("completitud") or {}
    total = completitud.get("total")
    if completitud.get("truncado") or (total is not None and total != len(filas)):
        raise ErrorCopia(
            f"{copia.tool} cortó la tabla ({len(filas)} de {total}): la copia no se publica"
        )
    if not filas:
        raise ErrorCopia(f"{copia.tool} dio una tabla vacía: la copia no se publica")
    columnas = [c for c in fuente.campos if c != FILA]
    salida = [
        {**{c: fila.get(c) for c in columnas}, FILA: i} for i, fila in enumerate(filas, start=1)
    ]
    if copia.variaciones is not None:
        con_variaciones(
            salida, copia.variaciones.indice, copia.variaciones.anio, copia.variaciones.mes
        )
    yield salida


MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip


def con_variaciones(filas: list[dict[str, Any]], indice: str, anio: str, mes: str) -> None:
    """Suma a cada fila `variacion_mensual`, `variacion_anual` y `variacion_anio_corrido` de un
    índice mensual, en porcentaje con dos decimales (como las publica el DANE). Sin el mes con qué
    comparar (el primero de la serie), la variación queda vacía: no se inventa."""
    valores: dict[tuple[int, int], float] = {}
    for fila in filas:
        clave = _mes_y_anio(fila.get(anio), fila.get(mes))
        if clave is not None and isinstance(fila.get(indice), int | float):
            valores[clave] = float(fila[indice])

    def variacion(actual: float | None, base: tuple[int, int]) -> float | None:
        previo = valores.get(base)
        return None if actual is None or not previo else round((actual / previo - 1) * 100, 2)

    for fila in filas:
        clave = _mes_y_anio(fila.get(anio), fila.get(mes))
        actual = valores.get(clave) if clave else None
        a, m = clave or (0, 0)
        fila["variacion_mensual"] = variacion(actual, (a - 1, 12) if m == 1 else (a, m - 1))
        fila["variacion_anual"] = variacion(actual, (a - 1, m))
        fila["variacion_anio_corrido"] = variacion(actual, (a - 1, 12))


def _mes_y_anio(anio: Any, mes: Any) -> tuple[int, int] | None:
    nombre = str(mes or "").strip().lower()
    try:
        return (int(float(str(anio))), MESES.index(nombre) + 1)
    except ValueError:
        return None


# --- un GeoJSON publicado como archivo (origen geojson) -------------------------------------------


def descargar_geojson(
    fuente: Fuente, desde: date | None = None, *, cliente: Any = None
) -> Iterator[list[dict[str, Any]]]:
    """Baja los GeoJSON declarados y rinde sus rasgos por página: la lista blanca y la geometría,
    en las coordenadas del archivo (si no son lon/lat, `construir` las reproyecta).

    `desde` se ignora (se copia el archivo entero). Si la clave no viene en las propiedades (un
    GeoJSON exportado de un escritorio no trae OBJECTID), es el orden del rasgo en los archivos,
    desde 1: la copia se rehace entera, así que no tiene que coincidir entre versiones."""
    import httpx

    assert fuente.copia is not None
    copia = fuente.copia
    columnas = list(fuente.campos)
    propio = cliente is None
    http = cliente or httpx.Client(
        timeout=600, follow_redirects=True, headers={"User-Agent": "terranova-copias/1"}
    )
    orden = 0
    try:
        for url in copia.descargas:
            r = http.get(url)
            r.raise_for_status()
            rasgos = r.json().get("features") or []
            if not rasgos:
                raise ErrorCopia(f"el GeoJSON {url} llegó sin rasgos: la copia no se publica")
            for inicio in range(0, len(rasgos), 1000):
                pagina = []
                for rasgo in rasgos[inicio : inicio + 1000]:
                    orden += 1
                    propiedades = rasgo.get("properties") or {}
                    fila = {c: propiedades.get(c) for c in columnas}
                    if fila.get(copia.clave) in (None, ""):
                        fila[copia.clave] = orden
                    fila[GEOMETRIA] = rasgo.get("geometry")
                    pagina.append(fila)
                yield pagina
    finally:
        if propio:
            http.close()


# --- un CSV publicado como archivo (origen csv) -----------------------------------------------


def descargar_csv(
    fuente: Fuente, desde: date | None = None, *, cliente: Any = None
) -> Iterator[list[dict[str, Any]]]:
    """Baja los CSV declarados y rinde sus filas por página: solo la lista blanca, con `_fila` en
    el orden de los archivos (desde 1), las fechas día/mes/año en ISO y los ceros de `ceros`.

    `desde` se ignora (se copia el archivo entero). Un CSV sin filas, o al que le falta una columna
    de la lista blanca, no se publica."""
    import csv
    import io

    import httpx

    assert fuente.copia is not None
    copia = fuente.copia
    columnas = [c for c in fuente.campos if c != FILA]
    fechas = [c for c in columnas if fuente.campos[c].tipo == "date"]
    propio = cliente is None
    http = cliente or httpx.Client(
        timeout=600, follow_redirects=True, headers={"User-Agent": "terranova-copias/1"}
    )
    filas: list[dict[str, Any]] = []
    try:
        for url in copia.descargas:
            r = http.get(url)
            r.raise_for_status()
            try:
                texto = r.content.decode("utf-8-sig")
            except UnicodeDecodeError:
                texto = r.content.decode("latin-1")
            lector = csv.DictReader(io.StringIO(texto), delimiter=copia.separador)
            lector.fieldnames = [n.strip() for n in lector.fieldnames or []]
            if faltan := sorted(set(columnas) - set(lector.fieldnames)):
                raise ErrorCopia(f"al CSV {url} le faltan columnas: {faltan}")
            for registro in lector:
                fila = {c: (registro.get(c) or "").strip() for c in columnas}
                for c in fechas:
                    fila[c] = _fecha_dia_mes(fila[c])
                for c, ancho in copia.ceros.items():
                    if fila.get(c):
                        fila[c] = fila[c].zfill(ancho)
                filas.append({**fila, FILA: len(filas) + 1})
    finally:
        if propio:
            http.close()
    if not filas:
        raise ErrorCopia("los CSV llegaron sin filas: la copia no se publica")
    for inicio in range(0, len(filas), PAGINA):
        yield filas[inicio : inicio + PAGINA]


def _fecha_dia_mes(texto: str) -> str:
    """'27/10/2026' -> '2026-10-27' (en Colombia la fecha va día primero); lo demás, tal cual."""
    partes = texto.split("/")
    if len(partes) == 3 and all(p.isdigit() for p in partes) and len(partes[2]) == 4:
        dia, mes, anio = (int(p) for p in partes)
        return f"{anio:04d}-{mes:02d}-{dia:02d}"
    return texto


def _geograficas(proyeccion: str) -> str:
    """Lon/lat sobre el mismo elipsoide de `proyeccion`, sin cambio de datum: la cartesiana de
    Bogotá infla el GRS80 2 550 m para que sus lat/lon sean las de MAGNA-SIRGAS; pasar por WGS84
    con `towgs84=0` las corría ~1,4 m."""
    elipsoide = [t for t in proyeccion.split() if t.split("=")[0] in ("+a", "+b", "+rf", "+ellps")]
    return " ".join(["+proj=longlat", *elipsoide, "+no_defs"])


# --- ingesta de los microdatos de comercio exterior del DANE (ZIP, origen zip_dane) ------------
#
# El DANE publica las estadísticas de importaciones (ANDA, catálogo 856) como ZIP de microdatos: un
# ZIP por entrega, con un ZIP mensual dentro, y en cada mensual un CSV (`;`, números europeos,
# `FECH`=AAMM). El microdato NO trae NIT ni persona (41 columnas agregables). Se **pre-agrega** en
# la ingesta a (año, mes, subpartida NANDINA, país de origen) con los valores sumados, para no
# guardar decenas de millones de líneas: la copia queda compacta y el `copia` agrega al consultar.


@dataclass(frozen=True)
class MapaComex:
    """Qué columnas del CSV del DANE leer (difieren entre impo y expo); de la ficha (`copia`)."""

    subpartida_csv: str  # NABAN (impo) / POSAR (expo)
    pais_csv: str  # PAISGEN (impo) / PAIS (expo)
    pais_col: str  # columna de la lista blanca: pais_origen / pais_destino
    medidas: dict[str, str]  # {columna de la lista blanca: columna del CSV}

    @classmethod
    def de_copia(cls, copia: Copia) -> MapaComex:
        assert copia.subpartida_csv and copia.pais_csv and copia.pais_col
        return cls(copia.subpartida_csv, copia.pais_csv, copia.pais_col, copia.medidas)


def num_europeo(texto: str) -> float:
    """'285.792,00' -> 285792.0 ; '-   ' o '' -> 0.0 (separador de miles `.`, decimal `,`)."""
    t = (texto or "").strip()
    if t in ("", "-"):
        return 0.0
    try:
        return float(t.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def anio_mes_dane(fech: str) -> tuple[int, int]:
    """`FECH` del microdato AAMM -> (año, mes): '2511' -> (2025, 11)."""
    f = fech.strip()
    if len(f) != 4 or not f.isdigit():
        raise ValueError(f"FECH inesperada: «{fech}»")
    return 2000 + int(f[:2]), int(f[2:])


# acumulador: (anio, mes, subpartida, pais) -> {medida: suma, ...} + lineas
_Clave = tuple[int, int, str, str]


def agregar_comex_csv(
    texto_csv: str, acumulador: dict[_Clave, dict[str, float]], mapa: MapaComex
) -> int:
    """Suma un CSV mensual del DANE dentro de `acumulador`. Devuelve las líneas leídas.

    Pura: no toca red ni base. El CSV es `;`, con BOM y números europeos; las columnas (subpartida,
    país, medidas) salen de `mapa`. El encabezado trae espacios (` VAFODO `) que se recortan."""
    import csv
    import io

    lector = csv.reader(io.StringIO(texto_csv), delimiter=";")
    cols = [c.strip() for c in next(lector, [])]
    idx = {c: i for i, c in enumerate(cols)}
    faltan = {"FECH", mapa.subpartida_csv, mapa.pais_csv, *mapa.medidas.values()} - set(idx)
    if faltan:
        raise ValueError(f"al CSV del DANE le faltan columnas: {sorted(faltan)}")
    i_fech, i_sub, i_pais = idx["FECH"], idx[mapa.subpartida_csv], idx[mapa.pais_csv]
    i_med = {m: idx[c] for m, c in mapa.medidas.items()}
    tope = max(i_fech, i_sub, i_pais, *i_med.values())
    n = 0
    for fila in lector:
        if len(fila) <= tope:
            continue
        anio, mes = anio_mes_dane(fila[i_fech])
        clave: _Clave = (anio, mes, fila[i_sub].strip(), fila[i_pais].strip())
        reg = acumulador.setdefault(clave, dict.fromkeys(mapa.medidas, 0.0) | {"lineas": 0.0})
        for m, col in i_med.items():
            reg[m] += num_europeo(fila[col])
        reg["lineas"] += 1
        n += 1
    return n


def fusionar_mes(
    texto_csv: str, acumulador: dict[_Clave, dict[str, float]], mapa: MapaComex
) -> None:
    """Suma un CSV mensual al acumulador con dedup por (año, mes): gana el último archivo.

    Las entregas del DANE se solapan (p. ej. octubre sale en dos ZIP): sumar sin deduplicar dobla
    ese mes. Cada CSV reemplaza los meses que trae (se procesan en orden de `descargas`; el ZIP más
    reciente pisa al anterior). Pura: no toca red ni base."""
    temp: dict[_Clave, dict[str, float]] = {}
    agregar_comex_csv(texto_csv, temp, mapa)
    meses = {(anio, mes) for (anio, mes, _, _) in temp}
    for clave in [k for k in acumulador if (k[0], k[1]) in meses]:
        del acumulador[clave]
    acumulador.update(temp)


def filas_de_acumulador(
    acumulador: dict[_Clave, dict[str, float]], mapa: MapaComex
) -> Iterator[dict[str, Any]]:
    """Las filas de la copia (lista blanca) desde el acumulador, con clave sintética única."""
    for (anio, mes, sub, pais), reg in acumulador.items():
        yield {
            "clave": f"{anio}{mes:02d}-{sub}-{pais}",
            "anio": str(anio),
            "mes": mes,
            "subpartida": sub,
            mapa.pais_col: pais,
            **{m: round(reg[m], 2) for m in mapa.medidas},
            "lineas": int(reg["lineas"]),
        }


def descargar_zip_dane(
    fuente: Fuente, desde: date | None = None, *, cliente: Any = None
) -> Iterator[list[dict[str, Any]]]:
    """Baja los ZIP del DANE, pre-agrega sus CSV mensuales y rinde las filas de la copia por página.

    `desde` se ignora (se copia la ventana completa de los ZIP declarados). Cada ZIP trae ZIP
    mensuales, y cada mensual un CSV."""
    import io
    import os
    import tempfile
    import zipfile

    import httpx

    assert fuente.copia is not None
    mapa = MapaComex.de_copia(fuente.copia)
    acumulador: dict[_Clave, dict[str, float]] = {}
    propio = cliente is None
    http = cliente or httpx.Client(
        timeout=600, follow_redirects=True, headers={"User-Agent": "terranova-copias/1"}
    )
    try:
        for url in fuente.copia.descargas:
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                with http.stream("GET", url) as r:
                    r.raise_for_status()
                    for trozo in r.iter_bytes(1 << 20):
                        tmp.write(trozo)
                ruta = tmp.name
            try:
                # el ZIP se cierra antes de borrarlo: en Windows no se puede unlink si sigue abierto
                with zipfile.ZipFile(ruta) as externo:
                    for miembro in externo.namelist():
                        low = miembro.lower()
                        if low.endswith(".zip"):  # ZIP mensual anidado
                            with zipfile.ZipFile(io.BytesIO(externo.read(miembro))) as interno:
                                csvs = [n for n in interno.namelist() if n.lower().endswith(".csv")]
                                if not csvs:
                                    continue
                                texto = interno.read(csvs[0]).decode("utf-8-sig", "replace")
                        elif low.endswith(".csv"):  # CSV directo bajo una carpeta del mes
                            texto = externo.read(miembro).decode("utf-8-sig", "replace")
                        else:
                            continue
                        fusionar_mes(texto, acumulador, mapa)
            finally:
                os.unlink(ruta)
    finally:
        if propio:
            http.close()

    pagina: list[dict[str, Any]] = []
    for fila in filas_de_acumulador(acumulador, mapa):
        pagina.append(fila)
        if len(pagina) >= PAGINA:
            yield pagina
            pagina = []
    if pagina:
        yield pagina


def _pedir(http: Any, url: str, params: dict[str, Any], intentos: int = 3) -> list[dict[str, Any]]:
    import time

    for intento in range(1, intentos + 1):
        try:
            r = http.get(url, params=params)
            r.raise_for_status()
            datos: list[dict[str, Any]] = r.json()
            return datos
        except Exception:
            if intento == intentos:
                raise
            time.sleep(30 * intento)  # cortesía con la fuente: no se insiste de inmediato
    return []


def _tipo_de_valor(campo: Any) -> str:
    """Una fecha en texto con orden propio («7/11/2000», día/mes) se guarda tal cual: Postgres la
    leería mes/día, y lo que trae detrás («Fecha de modificación: …») lo usa un derivado. La pasa
    a ISO el ejecutor al responder, igual que en vivo."""
    return "str" if campo.orden_fecha else campo.tipo


def _tipo_en_copia(campo: Any) -> str:
    return _TIPO_SQL[_tipo_de_valor(campo)]


def _convertir(valor: Any, tipo: str) -> Any:
    if valor in (None, ""):
        return None
    try:
        if tipo == "int":
            return int(float(valor))
        if tipo == "float":
            return float(valor)
        if tipo == "bool":
            return str(valor).strip().lower() in ("true", "1", "si", "sí")
        if tipo in ("date", "datetime") and isinstance(valor, int | float):  # epoch ms de ArcGIS
            momento = datetime.fromtimestamp(valor / 1000, UTC).isoformat()
            return momento[:10] if tipo == "date" else momento
        if tipo in ("date", "datetime"):
            texto = str(valor)
            return texto[:10] if tipo == "date" else texto
    except (TypeError, ValueError):
        return None
    return str(valor)


@dataclass(frozen=True)
class Version:
    fuente_id: str
    tabla: str
    version: str
    filas: int
    huella: str
    ventana_desde: date | None
    actualizada_en: datetime
    repetidas: int = 0  # filas con una clave ya vista: la fuente no garantiza claves únicas


class AlmacenCopias:
    """Versiones de las copias en PostGIS: tabla nueva por corrida, vista vigente y manifiesto."""

    def __init__(self, url: str, timeout_ms: int | None = None) -> None:
        self._url = url
        self._timeout_ms = timeout_ms
        self._conexion: Any = None

    @property
    def _c(self) -> Any:
        """La conexión, abierta al primer uso: la puerta arranca aunque la base no esté."""
        c = self._conexion
        if c is None or c.closed or c.broken:
            # Se reconecta sola: un reinicio de Postgres ya no deja las copias caídas hasta
            # reiniciar la puerta. Con `timeout_ms`, ninguna consulta pasa de ese tope.
            import importlib

            psycopg: Any = importlib.import_module("psycopg")  # extra opcional `postgres`
            opciones = (
                {"options": f"-c statement_timeout={self._timeout_ms}"} if self._timeout_ms else {}
            )
            self._conexion = psycopg.connect(self._url, autocommit=True, **opciones)
        return self._conexion

    def rota(self) -> bool:
        """La conexión se cayó (la siguiente consulta reconecta)."""
        c = self._conexion
        return c is not None and bool(c.closed or c.broken)

    def _asegurar_esquema(self) -> None:
        self._c.execute(f"CREATE SCHEMA IF NOT EXISTS {ESQUEMA}")
        self._c.execute(
            f"""CREATE TABLE IF NOT EXISTS {ESQUEMA}.versiones (
                fuente_id text NOT NULL, tabla text NOT NULL, version text NOT NULL,
                filas bigint NOT NULL, huella text NOT NULL, ventana_desde date,
                actualizada_en timestamptz NOT NULL, vigente boolean NOT NULL DEFAULT false,
                repetidas bigint NOT NULL DEFAULT 0, PRIMARY KEY (tabla, version))"""
        )

    def construir(
        self, fuente: Fuente, paginas: Iterator[list[dict[str, Any]]], desde: date | None
    ) -> Version:
        """Carga las páginas en una tabla nueva y, si todo salió bien, la vuelve la vigente."""
        assert fuente.copia is not None
        self._asegurar_esquema()
        copia = fuente.copia
        ahora = datetime.now(UTC)
        version = ahora.strftime("%Y%m%d%H%M%S%f")  # dos corridas en el mismo segundo no chocan
        fisica = f'{ESQUEMA}."{copia.tabla}_{version}"'
        tipos = {c: _tipo_en_copia(campo) for c, campo in fuente.campos.items()}
        definicion = ", ".join(f'"{c}" {t}' for c, t in tipos.items())
        texto = " || ' ' || ".join(f"coalesce(\"{c}\", '')" for c in copia.texto)
        generada = (
            f", _texto tsvector GENERATED ALWAYS AS (to_tsvector('spanish', {texto})) STORED"
            if copia.texto
            else ""
        )
        if copia.espacial:
            self._c.execute("CREATE EXTENSION IF NOT EXISTS postgis")
            definicion += f', "{GEOMETRIA}" geometry(Geometry, 4326)'
        self._c.execute(f"CREATE TABLE {fisica} ({definicion}{generada})")
        resumen = hashlib.sha256()
        filas = repetidas = 0
        anterior: Any = object()
        columnas = list(tipos)
        lista = ", ".join(f'"{c}"' for c in [*columnas, *([GEOMETRIA] if copia.espacial else [])])
        try:
            with self._c.cursor() as cur, cur.copy(f"COPY {fisica} ({lista}) FROM STDIN") as cp:
                for pagina in paginas:
                    for fila in pagina:
                        if fila.get(copia.clave) == anterior:  # ordenadas: la repetida es contigua
                            repetidas += 1
                            continue
                        anterior = fila.get(copia.clave)
                        valores = [
                            _convertir(fila.get(c), _tipo_de_valor(fuente.campos[c]))
                            for c in columnas
                        ]
                        if copia.espacial:
                            geometria = fila.get(GEOMETRIA)
                            valores.append(ewkt(geometria) if geometria else None)
                        cp.write_row(valores)
                        resumen.update(json.dumps(valores, default=str).encode())
                        filas += 1
            if filas == 0:
                # una fuente que responde vacío sin error (el proxy de la ANT, ~25 % de las veces)
                # dejaría la copia vacía y cada consulta diría «no hay»: se queda la anterior
                raise ErrorCopia("la fuente llegó sin filas: la copia no se publica")
            self._c.execute(f'ALTER TABLE {fisica} ADD PRIMARY KEY ("{copia.clave}")')
            for col in copia.indices:
                if col == copia.orden_fisico:
                    # antes de los demás índices: CLUSTER reescribe la tabla y los rehace todos
                    indice = f'"{copia.tabla}_{version}_orden"'
                    self._c.execute(f'CREATE INDEX {indice} ON {fisica} ("{col}")')
                    self._c.execute(f"CLUSTER {fisica} USING {indice}")
                else:
                    self._c.execute(f'CREATE INDEX ON {fisica} ("{col}")')
            if copia.texto:
                self._c.execute(f"CREATE INDEX ON {fisica} USING gin (_texto)")
            if copia.indices_contiene:
                # `contiene` busca '%palabra%': un btree no sirve; los trigramas sí. Sin el índice,
                # buscar una entidad en SECOP recorría 3,6 millones de filas (14 s, al tope).
                self._c.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
                for col in copia.indices_contiene:
                    expresion = _plano_sql(f'"{col}"')
                    self._c.execute(
                        f"CREATE INDEX ON {fisica} USING gin ({expresion} gin_trgm_ops)"
                    )
                self._c.execute(f"ANALYZE {fisica}")
            if copia.espacial and copia.proyeccion:
                # llegaron en las coordenadas del archivo, rotuladas 4326: se pasan a lon/lat
                self._c.execute(
                    f'UPDATE {fisica} SET "{GEOMETRIA}" = ST_SetSRID(ST_Transform('
                    f'ST_SetSRID("{GEOMETRIA}", 0), %s::text, %s::text), 4326)',
                    (copia.proyeccion, _geograficas(copia.proyeccion)),
                )
            if copia.espacial:
                self._reparar_geometrias(fuente, fisica)
                self._c.execute(f'CREATE INDEX ON {fisica} USING gist ("{GEOMETRIA}")')
                self._c.execute(f"ANALYZE {fisica}")
        except BaseException:
            with contextlib.suppress(Exception):  # con la conexión caída, manda el error original
                self._c.execute(f"DROP TABLE IF EXISTS {fisica}")  # una copia a medias no queda
            raise
        v = Version(
            fuente.id,
            copia.tabla,
            version,
            filas,
            f"sha256:{resumen.hexdigest()}",
            desde,
            ahora,
            repetidas,
        )
        self._publicar(v, fisica)
        return v

    def _reparar_geometrias(self, fuente: Fuente, fisica: str) -> None:
        """Un polígono inválido (autointersecciones, a veces por la simplificación) puede hacer
        fallar un cruce por zona: se repara al copiar, no al consultar, por tandas de la clave."""
        import sys

        assert fuente.copia is not None
        clave, g = f'"{fuente.copia.clave}"', f'"{GEOMETRIA}"'
        fila = self._c.execute(f"SELECT min({clave}), max({clave}) FROM {fisica}").fetchone()
        if fila is None or fila[0] is None:
            return
        for inicio in range(int(fila[0]), int(fila[1]) + 1, REPARAR_POR_TANDA):
            self._c.execute(
                f"UPDATE {fisica} SET {g} = ST_MakeValid({g}) WHERE {clave} >= %s AND {clave} < %s"
                f" AND ST_NPoints({g}) <= %s AND NOT ST_IsValid({g})",
                (inicio, inicio + REPARAR_POR_TANDA, REPARAR_HASTA_VERTICES),
            )
        quedan = self._c.execute(
            f"SELECT count(*) FROM {fisica} WHERE ST_NPoints({g}) > %s AND NOT ST_IsValid({g})",
            (REPARAR_HASTA_VERTICES,),
        ).fetchone()
        if quedan and quedan[0]:
            print(
                f"aviso {fuente.id}: {quedan[0]} polígonos inválidos de más de "
                f"{REPARAR_HASTA_VERTICES} vértices quedan como vienen de la fuente",
                file=sys.stderr,
            )

    def _publicar(self, v: Version, fisica: str) -> None:
        """La vista pasa a la versión nueva y el manifiesto la marca vigente, en una transacción."""
        with self._c.transaction():
            # DROP y CREATE, no CREATE OR REPLACE: este no deja cambiar las columnas de la vista
            # (una copia que suma columnas, como las variaciones del IPC). En la misma transacción,
            # quien consulta no ve el hueco.
            self._c.execute(f'DROP VIEW IF EXISTS {ESQUEMA}."{v.tabla}"')
            self._c.execute(f'CREATE VIEW {ESQUEMA}."{v.tabla}" AS SELECT * FROM {fisica}')
            self._c.execute(
                f"UPDATE {ESQUEMA}.versiones SET vigente = false WHERE tabla = %s", (v.tabla,)
            )
            self._c.execute(
                f"""INSERT INTO {ESQUEMA}.versiones (fuente_id, tabla, version, filas, huella,
                    ventana_desde, actualizada_en, repetidas, vigente)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)""",
                (
                    v.fuente_id,
                    v.tabla,
                    v.version,
                    v.filas,
                    v.huella,
                    v.ventana_desde,
                    v.actualizada_en,
                    v.repetidas,
                ),
            )

    def podar(self, tabla: str, conservar: int = 2) -> list[str]:
        """Borra las versiones viejas (se conservan la vigente y la anterior, para volver atrás)."""
        filas = self._c.execute(
            f"SELECT version FROM {ESQUEMA}.versiones WHERE tabla = %s ORDER BY version DESC",
            (tabla,),
        ).fetchall()
        borradas = []
        for (version,) in filas[conservar:]:
            self._c.execute(f'DROP TABLE IF EXISTS {ESQUEMA}."{tabla}_{version}"')
            self._c.execute(
                f"DELETE FROM {ESQUEMA}.versiones WHERE tabla = %s AND version = %s",
                (tabla, version),
            )
            borradas.append(version)
        return borradas

    def vigente(self, tabla: str) -> Version | None:
        existe = self._c.execute(f"SELECT to_regclass('{ESQUEMA}.versiones')").fetchone()
        if not existe or existe[0] is None:
            return None
        fila = self._c.execute(
            f"""SELECT fuente_id, tabla, version, filas, huella, ventana_desde, actualizada_en,
                repetidas FROM {ESQUEMA}.versiones WHERE tabla = %s AND vigente""",
            (tabla,),
        ).fetchone()
        return Version(*fila) if fila else None

    def consultar(self, plan: Plan) -> tuple[list[dict[str, Any]], int | None]:
        cur = self._c.execute(plan.sql, plan.parametros)
        nombres = [d.name for d in cur.description or []]
        filas = [dict(zip(nombres, f, strict=True)) for f in cur.fetchall()]
        total = None
        if plan.sql_total is not None:
            conteo = self._c.execute(plan.sql_total, plan.parametros_total).fetchone()
            total = int(conteo[0]) if conteo else None
        return filas, total


# --- el conector `copia` -----------------------------------------------------------------------


def _completitud(vistos: int, total: int | None, limite: int) -> dict[str, Any]:
    """Cuántas vinieron de cuántas cumplen. Con agregados no hay total aparte: si los grupos
    llegaron al límite, puede haber más."""
    if total is not None:
        return {"vistos": vistos, "total": total, "truncado": vistos < total}
    cortado = vistos >= limite
    return {"vistos": vistos, "total": None if cortado else vistos, "truncado": cortado}


def duracion(iso: str) -> timedelta:
    """Una duración ISO 8601 sencilla (P1D, PT6H, P1M ≈ 31 días, P1Y ≈ 366 días)."""
    m = re.fullmatch(
        r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?", iso
    )
    if not m:
        raise ValueError(f"duración no soportada: {iso}")
    y, mes, sem, d, h, minutos = (int(x or 0) for x in m.groups())
    return timedelta(days=366 * y + 31 * mes + 7 * sem + d, hours=h, minutes=minutos)


def toca_actualizar(fuente: Fuente, version: Version | None, ahora: datetime) -> bool:
    """Con `--solo-vencidas`: se rehace la copia que no existe o que ya va por la mitad de su SLA.

    Así un refresco diario no vuelve a bajar cada día una capa que la fuente cambia una vez al año
    (cortesía con la fuente) y la copia nunca llega a vencerse si el refresco corre."""
    if version is None:
        return True
    return ahora - version.actualizada_en >= duracion(fuente.frescura.sla_actualizacion) / 2


def _a_json(valor: Any) -> Any:
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    return valor


class ConectorCopia:
    """El conector interno `copia` (ADR-0024): misma interfaz que los conectores MCP."""

    def __init__(self, catalogo: Catalogo, almacen: AlmacenCopias) -> None:
        self._por_tabla = {f.copia.tabla: f for f in catalogo.fuentes.values() if f.copia}
        self._almacen = almacen

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        from terranova.conector import ErrorConector

        if herramienta != "consultar_copia":
            raise ErrorConector(f"el conector copia no tiene «{herramienta}»", "error_interno")
        fuente = self._por_tabla.get(str(argumentos.get("tabla")))
        if fuente is None:
            raise ErrorConector(f"no hay copia «{argumentos.get('tabla')}»", "error_interno")
        try:
            plan = plan_de_consulta(fuente, argumentos)
        except ErrorCopia as exc:
            raise ErrorConector(str(exc), "error_interno") from exc
        try:
            version, (filas, total) = await asyncio.to_thread(self._leer, fuente, plan)
        except Exception as exc:  # la base de las copias caída es una fuente caída
            raise ErrorConector(f"copia: {type(exc).__name__}", "fuente_no_disponible") from exc
        if version is None:
            raise ErrorConector(
                f"la copia de {fuente.id} no está construida", "fuente_no_disponible"
            )
        vencida = datetime.now(UTC) - version.actualizada_en > duracion(
            fuente.frescura.sla_actualizacion
        )
        hechos = {
            "servido_desde": "obsoleto" if vencida else "copia",
            "consultado_en": version.actualizada_en.isoformat(),
            "copia": {
                "version": version.version,
                "huella": version.huella,
                "filas": version.filas,
                "repetidas_en_la_fuente": version.repetidas,
                "ventana_desde": _a_json(version.ventana_desde),
            },
            "completitud": _completitud(len(filas), total, plan.limite),
        }
        filas_json = [{k: _a_json(v) for k, v in f.items()} for f in filas]
        if plan.geometria:
            rasgos = []
            for f in filas_json:
                geojson = f.pop("_geojson", None)
                rasgos.append(
                    {
                        "type": "Feature",
                        "geometry": json.loads(geojson) if geojson else None,
                        "properties": f,
                    }
                )
            coleccion = {"type": "FeatureCollection", "features": rasgos}
            artefacto = {"kind": "feature_collection", "crs": "EPSG:4326", "data": coleccion}
            return {"artifacts": [artefacto], "facts": hechos}
        columnas = sorted({k for f in filas_json for k in f})
        return {
            "artifacts": [{"kind": "table", "columns": columnas, "rows": filas_json}],
            "facts": hechos,
        }

    def _leer(
        self, fuente: Fuente, plan: Plan
    ) -> tuple[Version | None, tuple[list[dict[str, Any]], int | None]]:
        assert fuente.copia is not None
        try:
            return self._leer_una_vez(fuente, plan)
        except Exception:
            if not self._almacen.rota():
                raise
            return self._leer_una_vez(
                fuente, plan
            )  # la conexión se cayó: un reintento, ya reconectada

    def _leer_una_vez(
        self, fuente: Fuente, plan: Plan
    ) -> tuple[Version | None, tuple[list[dict[str, Any]], int | None]]:
        assert fuente.copia is not None
        version = self._almacen.vigente(fuente.copia.tabla)
        if version is None:
            return None, ([], None)
        return version, self._almacen.consultar(plan)


def conector_desde_entorno(catalogo: Catalogo) -> ConectorCopia | None:
    """El conector `copia` si hay base (`TERRANOVA_COPIAS_URL` o, si no, la del curado)."""
    import os

    url = os.environ.get("TERRANOVA_COPIAS_URL") or os.environ.get("TERRANOVA_CURADO_URL")
    tope = int(os.environ.get("TERRANOVA_COPIAS_TIMEOUT_MS", "15000"))
    return ConectorCopia(catalogo, AlmacenCopias(url, timeout_ms=tope)) if url else None
