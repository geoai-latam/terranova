"""Ejecutor genérico (F2.1): ficha del catálogo → conector → lista blanca → sobre `rt/1`.

Todo lo que es propio de una fuente sale del catálogo (ADR-0006, ADR-0007, ADR-0012): qué
herramienta del conector se llama y con qué argumentos, qué campos salen y con qué nombre, qué se
calcula (derivados) y qué índice de cobertura decide entre «no encontrado» y «fuera de cobertura».
Aquí solo vive la mecánica común.
"""

from __future__ import annotations

import asyncio
import functools
import html
import itertools
import json
import math
import re
import time
import unicodedata
from collections import Counter
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Literal

from terranova import metricas
from terranova.cache import RETENCION_S, Almacen
from terranova.cache import clave as clave_cache
from terranova.cache import huella as huella_cache
from terranova.catalogo import (
    AVISO_DATO_PUBLICO,
    MARCADOR,
    MARCADOR_PREVIA,
    PATRONES_ENTRADA,
    SUFIJO_SIGNIFICADO,
    TIPOS_NIT,
    Campo,
    Catalogo,
    Derivado,
    Fuente,
    Herramienta,
    cargar_cobertura,
    entero_de_json,
    motivo_no_vendible,
    normalizar_nit,
    rango_entero,
    vendible,
)
from terranova.conector import Conector, ErrorConector
from terranova.contrato import (
    MAX_TEXTO,
    Cache,
    Completitud,
    ErrorParte,
    Estado,
    GeoResult,
    Licencia,
    Procedencia,
    ServidoDesde,
    Sobre,
    ZonaUsada,
    ahora,
    huella,
    nueva_solicitud_id,
    texto_es_limpio,
)
from terranova.errores import ErrorEjecucion, ErrorEntrada
from terranova.proteccion import Proteccion

MAX_TEXTO_LIBRE = 200
# ADR-0035: un lote o una finca, no un departamento
MAX_VERTICES_POLIGONO = 500
MAX_LADO_POLIGONO_GRADOS = 1.0
# ADR-0032: `geometria: true` da la forma guardada si la lista es corta. Una zona puede traer
# cientos de polígonos completos, decenas de MB: esas siguen simplificadas y lo avisan.
MAX_ELEMENTOS_GEOMETRIA_FIEL = 20

# ADR-0040: las consultas que pueden seguir en la fuente desde una fila (`desde`) y el argumento
# que en cada una pone el tope. Una página que pasa del tope de la ficha va a la fuente con estos.
TOPE_PAGINABLE: dict[str, str] = {
    "consultar_copia": "limite",
    "datos_consultar": "max_filas",
    "arcgis_query_features": "max_features",
}


# P0.7: el aviso con que se dice que los conteos por grupo son de la lista entera; la página lo
# reconoce para no decir que esos cuentan solo la primera consulta
CONTEOS_COMPLETOS = "Estos resúmenes cuentan la lista completa de la fuente, no solo una consulta: "
_SIN_DATO = object()  # un agregado completo que no se pudo pedir: queda el de la ventana


def ventana_de(h: Herramienta) -> int | None:
    """Cuántas filas trae la consulta de la ficha si se puede seguir en la fuente (ADR-0040); None
    si la herramienta no pagina en la fuente (varias capas, consulta previa, agregados, un tope que
    sale de la entrada o una consulta que no admite `desde`). El complemento corre aparte y no
    cuenta en el total: no estorba."""
    nombre = TOPE_PAGINABLE.get(h.consulta.tool)
    if nombre is None or len(h.consulta.capas) > 1 or h.consulta.previa:
        return None
    if h.consulta.argumentos.get("agregados") or h.consulta.argumentos.get("group"):
        return None
    tope = h.consulta.argumentos.get(nombre)
    return tope if isinstance(tope, int) and not isinstance(tope, bool) else None


METROS_POR_GRADO = 111_320
Plan = Literal["evaluacion", "normal"]


# --- entrada ---------------------------------------------------------------------------------


def validar_entrada(h: Herramienta, entrada: dict[str, Any]) -> dict[str, Any]:
    """Comprueba cada parámetro contra su tipo del catálogo y devuelve los valores normalizados."""
    if faltan := set(h.entrada) - set(entrada):
        raise ErrorEntrada(sorted(faltan)[0], "falta")
    if sobran := set(entrada) - set(h.entrada):
        raise ErrorEntrada(sorted(sobran)[0], "no es un parámetro de esta herramienta")
    return {nombre: _valor(nombre, tipo, entrada[nombre]) for nombre, tipo in h.entrada.items()}


def _valor(nombre: str, tipo: str, v: Any) -> Any:
    if tipo == "int":
        v = entero_de_json(v)
        if isinstance(v, bool) or not isinstance(v, int):
            raise ErrorEntrada(nombre, "debe ser un número entero (int)")
        minimo, maximo = rango_entero(nombre)
        if not minimo <= v <= maximo:
            raise ErrorEntrada(nombre, f"fuera de rango ({minimo} a {maximo})")
        return v
    if tipo == "float":
        if isinstance(v, bool) or not isinstance(v, int | float) or not math.isfinite(v):
            raise ErrorEntrada(nombre, "debe ser un número (float)")
        if (nombre == "lon" and not -180 <= v <= 180) or (nombre == "lat" and not -90 <= v <= 90):
            raise ErrorEntrada(nombre, "fuera de rango (EPSG:4326)")
        return float(v)
    if tipo == "bool":
        if not isinstance(v, bool):
            raise ErrorEntrada(nombre, "debe ser true o false")
        return v
    if tipo == "bbox":
        if not (isinstance(v, list) and len(v) == 4 and all(_numero(x) for x in v)):
            raise ErrorEntrada(nombre, "debe ser [lon_min, lat_min, lon_max, lat_max]")
        x0, y0, x1, y1 = (float(x) for x in v)
        if not (-180 <= x0 < x1 <= 180 and -90 <= y0 < y1 <= 90):
            raise ErrorEntrada(nombre, "rectángulo inválido en EPSG:4326 (lon, lat; min < max)")
        return [x0, y0, x1, y1]
    if tipo == "poligono":
        return _poligono(nombre, v)
    if tipo == "geojson":
        if not isinstance(v, dict) or "type" not in v:
            raise ErrorEntrada(nombre, "debe ser un objeto GeoJSON")
        return v
    if tipo in TIPOS_NIT and isinstance(v, int) and not isinstance(v, bool):
        v = str(v)  # un NIT escrito como número (899999172) es el mismo NIT
    if not isinstance(v, str):
        raise ErrorEntrada(nombre, "debe ser texto")
    if tipo in TIPOS_NIT:
        v = v.strip()
        if not re.fullmatch(PATRONES_ENTRADA[tipo], v):
            raise ErrorEntrada(nombre, "NIT de 9 dígitos que empieza por 8 o 9 (ej. 899999172)")
        try:
            return normalizar_nit(v)
        except ValueError as e:
            raise ErrorEntrada(nombre, str(e)) from None
    if tipo == "sentencia_relatoria":
        v = v.strip().upper()
    if tipo in PATRONES_ENTRADA:
        if not re.fullmatch(PATRONES_ENTRADA[tipo], v):
            raise ErrorEntrada(nombre, f"no tiene el formato de {tipo}")
        if tipo == "sentencia_relatoria" and v.startswith("SU-"):
            # la relatoría guarda las de unificación como SU214-16.htm; SU-214-16.htm es una página
            # vacía con estado 200 (medido el 2026-11-03)
            return "SU" + v[3:]
        if tipo == "fecha":
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ErrorEntrada(nombre, "no es una fecha real (AAAA-MM-DD)") from None
        if tipo == "divipola" and not v.isdigit():
            codigo = municipio_por_nombre(nombre, v, _municipios())
            # defensa en profundidad: lo que va sin comillas a la plantilla es siempre un código
            if not re.fullmatch(r"[0-9]{5}", str(codigo)):
                raise ErrorEntrada(nombre, "no se pudo convertir a código DIVIPOLA")
            return codigo
        return v
    if len(v) > MAX_TEXTO_LIBRE or not texto_es_limpio(v):
        raise ErrorEntrada(nombre, f"texto de hasta {MAX_TEXTO_LIBRE} caracteres, sin control")
    return v


def _poligono(nombre: str, v: Any) -> dict[str, Any]:
    """Un GeoJSON `Polygon` en EPSG:4326 dentro de los topes de la ADR-0035, solo con lo suyo."""
    if not isinstance(v, dict) or v.get("type") != "Polygon":
        raise ErrorEntrada(nombre, 'debe ser un GeoJSON {"type": "Polygon", "coordinates": [...]}')
    anillos = v.get("coordinates")
    if not isinstance(anillos, list) or not anillos:
        raise ErrorEntrada(nombre, "le faltan las coordenadas")
    vertices = 0
    limpios: list[list[list[float]]] = []
    for anillo in anillos:
        if not isinstance(anillo, list) or len(anillo) < 4:
            raise ErrorEntrada(nombre, "cada anillo lleva al menos 4 vértices")
        if not all(
            isinstance(p, list) and len(p) == 2 and all(_numero(c) for c in p) for p in anillo
        ):
            raise ErrorEntrada(nombre, "cada vértice es [lon, lat]")
        puntos = [[float(p[0]), float(p[1])] for p in anillo]
        if puntos[0] != puntos[-1]:
            raise ErrorEntrada(nombre, "cada anillo termina en su primer vértice")
        if not all(-180 <= x <= 180 and -90 <= y <= 90 for x, y in puntos):
            raise ErrorEntrada(nombre, "fuera de rango (EPSG:4326)")
        vertices += len(puntos)
        limpios.append(puntos)
    if vertices > MAX_VERTICES_POLIGONO:
        raise ErrorEntrada(
            nombre,
            f"tiene {vertices} vértices; el tope es {MAX_VERTICES_POLIGONO}: simplifíquelo",
            "zona_demasiado_grande",
        )
    lons, lats = [x for x, _ in limpios[0]], [y for _, y in limpios[0]]
    if max(max(lons) - min(lons), max(lats) - min(lats)) > MAX_LADO_POLIGONO_GRADOS:
        raise ErrorEntrada(
            nombre,
            f"pasa de {MAX_LADO_POLIGONO_GRADOS:g} grado de lado: divídalo en partes",
            "zona_demasiado_grande",
        )
    # ADR-0035 lo reparaba en la base (ST_MakeValid) y uno degenerado salía «no encontrado»: un
    # polígono sin área o que se cruza no es una pregunta, es un error de quien lo dibujó
    for i, anillo in enumerate(limpios):
        que = "el borde" if i == 0 else f"el hueco {i}"
        if len({(x, y) for x, y in anillo}) < 3:
            raise ErrorEntrada(nombre, f"{que} tiene menos de 3 vértices distintos")
        # el cruce va antes: un moño simétrico también suma área cero
        if cruce := _autocruce(anillo):
            raise ErrorEntrada(
                nombre,
                f"{que} se cruza consigo mismo (los lados {cruce[0] + 1} y {cruce[1] + 1}): "
                "dibújelo sin que los lados se crucen",
            )
        if abs(_area_anillo(anillo)) < MIN_AREA_GRADOS2:
            raise ErrorEntrada(nombre, f"{que} no tiene área: sus vértices están alineados")
    return {"type": "Polygon", "coordinates": limpios}


# un metro cuadrado en el ecuador es ~8e-11 grados²: menos que esto es una línea, no un lote
MIN_AREA_GRADOS2 = 1e-12


def _area_anillo(anillo: list[list[float]]) -> float:
    """Área con signo (fórmula del cordón), en grados²: basta para saber si hay área."""
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in itertools.pairwise(anillo)) / 2


def _autocruce(anillo: list[list[float]]) -> tuple[int, int] | None:
    """El primer par de lados no vecinos que se tocan, o None. Hasta 500 vértices: ~125 000
    pares, unos 100 ms."""
    # un vértice repetido seguido es un lado de largo cero, no un cruce
    sin_repetidos = [p for k, p in enumerate(anillo) if k == 0 or p != anillo[k - 1]]
    lados = list(itertools.pairwise(sin_repetidos))
    n = len(lados)
    for i in range(n):
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:  # el primero y el último comparten el vértice de cierre
                continue
            if _se_tocan(*lados[i], *lados[j]):
                return i, j
    return None


def _se_tocan(a: list[float], b: list[float], c: list[float], d: list[float]) -> bool:
    def orientacion(p: list[float], q: list[float], r: list[float]) -> float:
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def en_lado(p: list[float], q: list[float], r: list[float]) -> bool:
        return min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and min(p[1], q[1]) <= r[1] <= max(
            p[1], q[1]
        )

    o1, o2, o3, o4 = (
        orientacion(a, b, c),
        orientacion(a, b, d),
        orientacion(c, d, a),
        orientacion(c, d, b),
    )
    if (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0) and o1 and o2 and o3 and o4:
        return True
    return (
        (o1 == 0 and en_lado(a, b, c))
        or (o2 == 0 and en_lado(a, b, d))
        or (o3 == 0 and en_lado(c, d, a))
        or (o4 == 0 and en_lado(c, d, b))
    )


def _numero(x: Any) -> bool:
    return isinstance(x, int | float) and not isinstance(x, bool) and math.isfinite(x)


_TILDES = str.maketrans(dict.fromkeys("ÁÉÍÓÚÜáéíóúü", "_"))
_VOCALES = str.maketrans(dict.fromkeys("AEIOUaeiouÁÉÍÓÚÜáéíóúü", "_"))


def _marcador(m: re.Match[str], valores: dict[str, Any]) -> Any:
    valor = valores[m.group(1)]
    if m.group(0).endswith(":sin_tildes}"):
        return str(valor).translate(_TILDES)
    if m.group(0).endswith(":vocales}"):
        # solo en palabras de 5 letras o más: en una corta el comodín casa con casi todo
        # («SURA» como S_R_ casaba con «usar el», porque `_` también es un espacio)
        return re.sub(r"\w{5,}", lambda p: p.group(0).translate(_VOCALES), str(valor))
    if m.group(0).endswith(":ascii}"):
        return unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode()
    return valor


def renderizar(plantilla: Any, valores: dict[str, Any]) -> Any:
    """Reemplaza `{marcador}`: si el texto es solo el marcador, el valor conserva su tipo.
    `{marcador:sin_tildes}` cambia cada vocal con tilde por `_`, el comodín de LIKE;
    `{marcador:vocales}` cambia toda vocal, con tilde o sin ella, por `_` en las palabras de 5
    letras o más: «BOGOTA» encuentra «BOGOTÁ» (la tilde está en el dato, no en lo que se
    escribe); `{marcador:ascii}` quita tildes y eñes («daño» → «dano»)."""
    if isinstance(plantilla, str):
        entero = MARCADOR.fullmatch(plantilla)
        if entero:
            return _marcador(entero, valores)
        return MARCADOR.sub(lambda m: str(_marcador(m, valores)), plantilla)
    if isinstance(plantilla, list):
        return [renderizar(v, valores) for v in plantilla]
    if isinstance(plantilla, dict):
        return {k: renderizar(v, valores) for k, v in plantilla.items()}
    return plantilla


# --- salida ----------------------------------------------------------------------------------

_BIDI_Y_CONTROL = re.compile(
    "[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]|[\x00-\x08\x0b-\x1f\x7f-\x9f]"
)


# La «í» en UTF-8 es C3 AD. Si la fuente pierde el C3, queda U+FFFD seguido de un guion suave
# (U+00AD): SECOP escribe «Medell\ufffd\u00adn» en 223 466 ubicaciones (medido el 2026-11-03 en
# gra4-pcp2). Ese par no es texto en ningún caso: se lee como la «í» que era.
_I_PARTIDA = "\ufffd\u00ad"


def sanear(texto: str) -> str:
    """Texto de la fuente sin control ni bidi y con el largo máximo de `rt/1` (regla 9)."""
    # el retorno de carro (0x0D) tampoco cabe en `rt/1`: «\r\n» queda en «\n» (el IGAC escribe
    # «Aeropuerto Alberto Jaramillo Sánchez\r\n» en la cartografía 1:100 000)
    texto = texto.replace("\r\n", "\n").replace(_I_PARTIDA, "í")
    limpio = _BIDI_Y_CONTROL.sub("", unicodedata.normalize("NFC", texto))
    return limpio if len(limpio) <= MAX_TEXTO else limpio[: MAX_TEXTO - 1] + "…"


_AÑO = re.compile(r"^(\d{4})")
_HTTP_DE_FUENTE = re.compile(r"el servicio respondió HTTP (\d{3})")
AUSENTE = "documento_ausente"  # hecho interno: la fuente respondió que ese documento no existe
_MILES = re.compile(r"\d{1,3}(,\d{3})+")
_DECIMALES = re.compile(r"\.0+$")


def convertir(valor: Any, tipo: str) -> Any:
    """Al tipo del catálogo. Lo que no se puede convertir sale como `None`, nunca inventado."""
    if valor is None:
        return None
    try:
        if tipo == "int":
            texto = str(valor).strip()
            return int(float(texto.replace(",", "") if _MILES.fullmatch(texto) else valor))
        if tipo == "float":
            return float(valor)
        if tipo == "bool":
            return (
                valor
                if isinstance(valor, bool)
                else str(valor).strip().lower() in ("true", "1", "si", "sí")
            )
        if tipo == "date":
            return _fecha(valor)[:10]
        if tipo == "datetime":
            return _fecha(valor)
    except (TypeError, ValueError):
        return None
    if isinstance(valor, dict) and "url" in valor:  # Socrata da las URL como {url: …}
        valor = valor["url"]
    texto = sanear(valor if isinstance(valor, str) else str(valor))
    return texto if texto.strip() else None


def _fecha(valor: Any) -> str:
    if isinstance(valor, int | float) and not isinstance(valor, bool):  # epoch ms de ArcGIS
        return datetime.fromtimestamp(valor / 1000, UTC).isoformat()
    if re.fullmatch(r"\d{8}", texto := str(valor)):  # AAAAMMDD del SDMX del BanRep
        return f"{texto[:4]}-{texto[4:6]}-{texto[6:]}"
    return sanear(str(valor))


@dataclass
class Respuesta:
    """Lo que devolvió una llamada al conector, ya separado en filas y hechos."""

    capa: str | None
    argumentos: dict[str, Any]
    filas: list[dict[str, Any]]
    geometrias: list[Any]
    hechos: dict[str, Any]
    crs: str | None = None


def separar(
    h: Herramienta, capa: str | None, argumentos: dict[str, Any], sc: dict[str, Any]
) -> Respuesta:
    hechos = (
        sc.get("facts") if isinstance(sc.get("facts"), dict) else ({} if "geo_result" in sc else sc)
    )
    filas: list[dict[str, Any]] = []
    geometrias: list[Any] = []
    crs = None
    for art in sc.get("artifacts") or []:
        if art.get("kind") == "feature_collection":
            for rasgo in (art.get("data") or {}).get("features") or []:
                filas.append(rasgo.get("properties") or {})
                geometrias.append(rasgo.get("geometry"))
            crs = art.get("crs")
            break
        if art.get("kind") == "table":
            filas = list(art.get("rows") or [])
            break
    if not filas and h.consulta.filas_en:
        actual: Any = sc
        for parte in h.consulta.filas_en.split("."):
            actual = actual.get(parte) if isinstance(actual, dict) else None
        filas = [f for f in actual or [] if isinstance(f, dict)]
    if len(geometrias) != len(filas):
        geometrias = [None] * len(filas)
    return Respuesta(capa, argumentos, filas, geometrias, hechos or {}, crs)


def mapear_fila(
    h: Herramienta, fuente: Fuente, fila: dict[str, Any], capa: str | None
) -> dict[str, Any]:
    """La fila con SOLO la lista blanca (regla 10), renombrada y con los derivados por elemento."""
    out: dict[str, Any] = {}
    for clave, campo in fuente.campos.items():
        if campo.origen != "fila":
            continue
        presente = next((c for c in (clave, *campo.alias) if c in fila), None)
        if presente is not None:
            valor = fila[presente]
            if campo.reparar_codificacion and isinstance(valor, str):
                valor = reparar_codificacion(valor)
            if campo.coma_decimal and isinstance(valor, str):
                valor = valor.replace(",", ".")
            if campo.orden_fecha and isinstance(valor, str):
                valor = fecha_en_orden(valor, campo.orden_fecha)
            if campo.moneda and isinstance(valor, str):
                valor = re.sub(r"[$\s]", "", valor)  # «-$0.00», «$ 2.31»
            if campo.vacios and valor is not None and str(valor).strip() in campo.vacios:
                valor = None  # relleno de la fuente («0», «Pendiente»), no un dato
            out[campo.nombre] = _validar(campo, convertir(valor, campo.tipo))
            if campo.decimales is not None and isinstance(out[campo.nombre], float):
                out[campo.nombre] = round(out[campo.nombre], campo.decimales)
            if campo.codigos is not None or campo.codigos_por_capa is not None:
                # un código solo no dice nada: el significado va al lado, no en la ficha técnica
                significado = campo.significado(out[campo.nombre], capa)
                out[f"{campo.nombre}{SUFIJO_SIGNIFICADO}"] = significado
    for nombre, d in h.derivados.items():
        if not d.por_elemento:
            continue
        if d.de == "capa":
            out[nombre] = (d.valores or {}).get(str(capa))
        elif d.de == "prefijo":
            base = out.get(d.campo or "")
            out[nombre] = str(base)[: d.n] if base else None
        elif d.de == "columna":
            crudo = fila.get(d.campo or "")
            if d.patron is not None and crudo is not None:
                hallado = re.search(d.patron, str(crudo))
                crudo = hallado.group(1) if hallado else None
            if d.html and crudo is not None:
                crudo = texto_de_html(str(crudo))
            if d.valores is not None and crudo is not None:
                # la misma cosa escrita de varias formas («Faja Paralela», «Faja paralela»)
                crudo = d.valores.get(str(crudo), crudo)
            if d.orden_fecha and isinstance(crudo, str):
                crudo = fecha_en_orden(crudo, d.orden_fecha)
            out[nombre] = convertir(crudo, d.tipo)
        elif d.de == "codigo":
            base = out.get(d.campo or "")
            out[nombre] = (d.valores or {}).get(str(base)) if base is not None else None
        elif d.de == "fijo":
            out[nombre] = convertir(d.valor, d.tipo)
        if nombre in out:  # otros (p. ej. las diferencias entre filas) se calculan después
            out[nombre] = redondear(out[nombre], d.decimales)
    return out


def texto_de_html(texto: str) -> str | None:
    """Un pedazo de HTML como texto: sin etiquetas, con las entidades leídas y los espacios de
    más quitados. Vacío, None."""
    limpio = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", texto)).split())
    return limpio or None


def redondear(valor: Any, decimales: int | None) -> Any:
    """Un número con los decimales que tienen sentido; lo demás pasa igual."""
    if decimales is None or not isinstance(valor, float):
        return valor
    return round(valor, decimales)


def aviso_de_anio_incompleto(fuente: Fuente, valores: dict[str, Any]) -> str | None:
    """Un año en que a la fuente le falta parte de lo que promete: el total parece completo y no."""
    hasta, anio = fuente.cobertura.incompleta_hasta, str(valores.get("anio"))
    if hasta and anio.isdigit() and int(anio) <= hasta:
        return fuente.cobertura.aviso_incompleta or "Este año está incompleto en la fuente."
    return None


def avisos_de_la_ficha(h: Herramienta, fuente: Fuente, sobre: Sobre) -> list[str]:
    """Lo que la ficha sabe y la fuente no dice (patrón A de la revisión de valor): un vacío que no
    es «no hay» (garantías de SECOP: menos del 0,5 % de los contratos) y lo que hay que saber al
    leer ciertos datos (un solo proponente). Un aviso de vacío de la herramienta reemplaza el de
    la fuente."""
    if sobre.estado == "no_encontrado":
        propios = [a.texto.strip() for a in h.avisos if a.cuando == "vacio"]
        de_la_fuente = (fuente.cobertura.aviso_vacio or "").strip()  # el `>` de YAML deja un salto
        return propios or ([de_la_fuente] if de_la_fuente else [])
    if sobre.estado == "fuera_de_cobertura":
        return [a.texto.strip() for a in h.avisos if a.cuando == "fuera"]
    if sobre.estado not in ("encontrado", "parcial"):
        return []
    # si el complemento falló, la falta de sus hechos es «no se pudo», no «no hay»: un aviso que
    # mira uno de ellos no sale (el predio de Chía no está «sin registro» porque el registro cayó)
    sin_complemento: set[str] = set()
    if (comp := h.consulta.complemento) is not None and any(
        av.startswith(f"No se pudo saber {comp.que_dice}") for av in sobre.avisos
    ):
        sin_complemento = {x.nombre for x in comp.hechos.values()}
    return [
        a.texto.strip()
        for a in h.avisos
        if a.cuando == "encontrado"
        and (a.si is None or (a.si.campo not in sin_complemento and a.si.cumple(sobre.datos)))
    ]


def reparar_codificacion(texto: str) -> str:
    """Deshace el UTF-8 leído como Latin-1: «BOGOTÃ, D.C.» → «BOGOTÁ, D.C.», «MEDELLÃN» →
    «MEDELLÍN», «SAN JOSÃ‰ DE CÃšCUTA» → «SAN JOSÉ DE CÚCUTA» (Supersolidaria, medido el
    2026-11-05). Si no es eso, el texto queda como vino."""
    if "Ã" not in texto and "Â" not in texto:
        return texto
    try:
        # cada letra como su byte de Windows-1252 («‰» es 0x89, de la É de «JOSÃ‰») o, si no está
        # en esa tabla, de Latin-1 («» es 0x8D, de la Í de «MEDELLÃN»)
        crudo = b"".join(_byte_original(c) for c in texto)
        return crudo.decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def _byte_original(letra: str) -> bytes:
    try:
        return letra.encode("cp1252")
    except UnicodeEncodeError:
        return letra.encode("latin-1")


def unico_por(
    elementos: list[dict[str, Any]], campo: str, mayor: str | None
) -> list[dict[str, Any]]:
    """Una fila por valor de `campo`: la de mayor `mayor` (la primera que llegó si empatan), en el
    lugar de la primera que llegó. La Supersolidaria daba 14 NIT repetidos en 50 filas para
    «COOPERATIVA», porque su grupo se partía con cada cambio de un atributo (2026-11-05)."""
    elegidos: dict[str, dict[str, Any]] = {}
    for e in elementos:
        clave = json.dumps(e.get(campo), default=str)
        actual = elegidos.get(clave)
        if actual is None or (
            mayor is not None and str(e.get(mayor) or "") > str(actual.get(mayor) or "")
        ):
            elegidos[clave] = e
    orden = list(dict.fromkeys(json.dumps(e.get(campo), default=str) for e in elementos))
    return [elegidos[c] for c in orden]


def juntar_filas(elementos: list[dict[str, Any]], campo: str) -> list[dict[str, Any]]:
    """Las filas iguales en todo menos `campo` salen como una, con `campo` como lista de sus
    valores distintos, en el orden en que llegaron. El INVIMA repite cada presentación por vía de
    administración: Buscapina daba 28 filas para 14 presentaciones (2026-11-03)."""
    grupos: dict[str, dict[str, Any]] = {}
    for e in elementos:
        clave = json.dumps({k: v for k, v in e.items() if k != campo}, sort_keys=True, default=str)
        fila = grupos.setdefault(clave, {**e, campo: []})
        if (valor := e.get(campo)) is not None and valor not in fila[campo]:
            fila[campo].append(valor)
    return list(grupos.values())


def es_relleno(h: Herramienta, elementos: list[Any], hechos: dict[str, Any]) -> bool:
    """La fuente contestó, pero sin el documento: una portada de 32 caracteres no es la sentencia,
    y un título sin resultados no es un resultado."""
    minimo = h.consulta.minimo_caracteres
    if minimo and int(hechos.get("caracteres") or 0) < minimo:
        return True
    return h.consulta.solo_elementos and not elementos


def _validar(campo: Campo, valor: Any) -> Any:
    if valor is None:
        return None
    if campo.ancho:
        return _DECIMALES.sub("", str(valor)).zfill(campo.ancho)
    if campo.maximo_valido is not None and valor > campo.maximo_valido:
        return None
    if campo.anios_validos and re.match(r"\d{4}-", str(valor)):
        desde, hasta = campo.anios_validos
        if not desde <= int(str(valor)[:4]) <= hasta:
            return None  # relleno de la fuente (3000, 1900), no una fecha
    return valor


def fecha_en_orden(texto: str, orden: str) -> str:
    """«06/15/2016» (mda), «15/06/2016» (dma) o «2016.06.15» (amd) a ISO. Lo que no tiene esa
    forma pasa igual: el mismo conjunto puede traer fechas ISO en otras filas. Si detrás de la
    fecha viene más texto («18/12/1997 Fecha de modificación: 26/09/2024»), cuenta la primera."""
    if orden == "amd":  # «2012.07.07» (los puentes del INVÍAS)
        iso = re.match(r"\s*(\d{4})[./](\d{1,2})[./](\d{1,2})(?!\d)", texto)
        return f"{iso[1]}-{int(iso[2]):02d}-{int(iso[3]):02d}" if iso else texto
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)", texto)
    if not m:
        return texto
    a, b, anio = m.groups()
    mes, dia = (a, b) if orden == "mda" else (b, a)
    return f"{anio}-{int(mes):02d}-{int(dia):02d}"


def derivar_secuencia(h: Herramienta, elementos: list[dict[str, Any]]) -> None:
    """Los derivados que miran al elemento anterior (en el orden de la consulta), en su lugar.
    Con `solo_si`, el que no cumple queda vacío y no es «el anterior» de nadie."""
    for nombre, d in h.derivados.items():
        if d.de != "diferencia_anterior":
            continue
        anterior: float | None = None
        for e in elementos:
            if d.solo_si and not d.solo_si.cumple(e):
                e[nombre] = None
                continue
            actual = e.get(d.campo or "")
            numero = float(actual) if actual is not None and _numero(actual) else None
            e[nombre] = (
                convertir(round(numero - anterior, 6), d.tipo)
                if numero is not None and anterior is not None
                else None
            )
            if numero is not None:
                anterior = numero


def derivar_resultado(
    d: Derivado,
    elementos: list[dict[str, Any]],
    total: int | None,
    total_filas: int | None = None,
) -> Any:
    """`total_filas`: cuántas filas hay en la fuente, si se sabe y una fila es un elemento (sin
    `juntar`). Un `conteo` sin condición da ese total y no lo que vino: con páginas que siguen en
    la fuente (ADR-0040), la red vial decía «500 registros» de 659."""
    if d.solo_si:
        elementos = [e for e in elementos if d.solo_si.cumple(e)]
    valores = [e.get(d.campo or "") for e in elementos]
    numeros = [float(v) for v in valores if v is not None and _numero(v)]
    if d.de == "conteo":
        if not d.solo_si and total_filas is not None and total_filas > len(elementos):
            return total_filas
        return len(elementos)
    if d.de == "conteo_por":
        # sin espacios de más: el IGAC escribe «CARRERA 11 » y «CALLE  3» en unos tramos y
        # «CARRERA 11» y «CALLE 3» en otros, y son la misma vía
        cuenta = Counter(" ".join(str(v).split()) for v in valores if v is not None)
        if d.vacio is not None and (sin := sum(v is None for v in valores)):
            cuenta[d.vacio] = sin
        return dict(cuenta.most_common())
    if d.de == "suma_por":
        sumas: dict[str, float] = {}
        for e in elementos:
            clave, valor = e.get(d.campo or ""), e.get(d.sumar or "")
            if clave is not None and valor is not None and _numero(valor):
                sumas[str(clave)] = sumas.get(str(clave), 0.0) + float(valor)
        cifras = 6 if d.decimales is None else d.decimales
        # con `tipo: int`, un conteo sale entero (21, no 21.0)
        return {
            k: round(v) if d.tipo == "int" else round(v, cifras)
            for k, v in sorted(sumas.items(), key=lambda kv: -kv[1])
        }
    if d.de == "suma":
        return convertir(round(sum(numeros), 6), d.tipo) if numeros else None
    if d.de == "maximo":
        return convertir(max(numeros), d.tipo) if numeros else None
    if d.de == "primero":
        return convertir(valores[0], d.tipo) if valores else None
    if d.de == "ultimo":
        return convertir(valores[-1], d.tipo) if valores else None
    if d.de == "distintos":
        return len({" ".join(str(v).split()) for v in valores if v is not None})
    if d.de == "completitud_total":
        return total
    raise ValueError(d.de)


def completitud_de(r: Respuesta, por_construccion: bool) -> Completitud:
    c = r.hechos.get("completitud")
    if isinstance(c, dict) and isinstance(c.get("vistos"), int):
        total = c.get("total") if isinstance(c.get("total"), int) else None
        return Completitud(
            vistos=c["vistos"],
            total=total,
            truncado=bool(c.get("truncado")) if total is None else c["vistos"] < total,
        )
    vistos = len(r.filas)
    total = r.hechos.get("total_en_servicio")
    if por_construccion:
        return Completitud(vistos=vistos, total=vistos, truncado=False)
    if isinstance(total, int) and total >= vistos:
        return Completitud(vistos=vistos, total=total, truncado=vistos < total)
    return Completitud(vistos=vistos, total=None, truncado=False)


def licencia_de(fuente: Fuente) -> Licencia:
    spdx = fuente.licencia.spdx
    if spdx is None:
        # ADR-0019 (enmienda): una fuente ámbar sin SPDX sirve como dato público reutilizable.
        spdx = (
            "LicenseRef-terminos-no-verificados"
            if fuente.clasificacion_licencia == "ambar"
            else "LicenseRef-por-verificar"
        )
    return Licencia(spdx=spdx, url=fuente.licencia.url, uso_comercial=fuente.uso_comercial)


# --- cobertura -------------------------------------------------------------------------------

Cobertura = Callable[["Ejecutor", Herramienta, dict[str, Any], datetime], Awaitable["Veredicto"]]


@dataclass
class Veredicto:
    fuera: bool
    aviso: str | None = None
    procedencia: list[Procedencia] = field(default_factory=list)


async def cobertura_catastral(
    ej: Ejecutor, h: Herramienta, entrada: dict[str, Any], consultado_en: datetime
) -> Veredicto:
    """¿El municipio está en la base catastral pública del IGAC? (F1.5, medido por sectores)."""
    municipios: dict[str, Any] = ej.indice("cobertura_catastral")["municipios"]
    procedencia: list[Procedencia] = []
    divipola = next(
        (str(v)[:5] for k, v in entrada.items() if h.entrada[k] == "codigo_predial"), None
    )
    if divipola is None and "lon" in entrada and "lat" in entrada:
        argumentos = {
            "url": CAPA_GESTORES,
            "bbox": [entrada["lon"], entrada["lat"], entrada["lon"], entrada["lat"]],
            "out_fields": ["divipola"],
            "max_features": 1,
        }
        gestores = ej.catalogo.fuentes["igac.gestores_catastrales"]
        # solo explica un vacío que la capa ya dio: si tarda o cae, el vacío sigue en pie
        try:
            sc = await asyncio.wait_for(
                ej.llamar("arcgis-mcp", "arcgis_query_features", argumentos, fuente_id=gestores.id),
                TOPE_COBERTURA_S,
            )
        except TimeoutError:
            if ej.proteccion is not None:
                ej.proteccion.registrar_caida(gestores.id)
            return Veredicto(False, AVISO_SIN_VERIFICAR)
        except ErrorEjecucion:
            return Veredicto(False, AVISO_SIN_VERIFICAR)
        rasgos = ((sc.get("artifacts") or [{}])[0].get("data") or {}).get("features") or []
        divipola = str(rasgos[0]["properties"].get("divipola") or "") if rasgos else None
        procedencia.append(
            Procedencia(
                # la fuente REAL del catálogo (no un id fantasma): su licencia es la que declara su
                # ficha (CC-BY-SA-4.0 verificada), no un `por-verificar` fijado a mano
                fuente_id=gestores.id,
                entidad=gestores.entidad,
                url=CAPA_GESTORES,
                licencia=licencia_de(gestores),
                atribucion=gestores.atribucion,
                servido_desde="fuente",
                consultado_en=consultado_en,
                consulta=argumentos,
                completitud=Completitud(vistos=len(rasgos), total=len(rasgos), truncado=False),
                cache=Cache(acierto=False, edad_s=0),
                transformaciones=[],
                conector="arcgis-mcp",
                huella=huella({}),
            )
        )
    m = municipios.get(divipola or "")
    if m is None:
        return Veredicto(False, None, procedencia)
    if m["rural"] or m["urbano"]:
        return Veredicto(False, None, procedencia)
    nombre = m["municipio"] or divipola
    if m["gestor"] == "IGAC":
        aviso = (
            f"{nombre} ({divipola}) figura con gestor IGAC, pero la base pública no trae sus datos."
        )
    else:
        gestor = m["gestor"]
        aviso = f"{nombre} ({divipola}) lo gestiona {gestor}; la base del IGAC no lo cubre."
    return Veredicto(True, aviso, procedencia)


# de Malpelo y San Andrés a Puerto Carreño e Inírida, y del Amazonas a Serranilla
RECTANGULO_COLOMBIA = (-82.0, -4.3, -66.8, 16.2)
TOPE_COBERTURA_S = 5.0
AVISO_SIN_VERIFICAR = (
    "La capa no trae nada en este punto, pero no se pudo comprobar si el IGAC cubre el municipio. "
    "Si lo atiende otro gestor catastral, esta base no lo tiene: pruebe predio_en_punto."
)
CAPA_GESTORES = (
    "https://mapas.igac.gov.co/server/rest/services/catastro/Gestores_Catastrales/MapServer/1"
)
COBERTURAS: dict[str, Cobertura] = {"cobertura_catastral": cobertura_catastral}


# --- ejecutor --------------------------------------------------------------------------------


Frescura = Literal["normal", "estricta"]
CODIGOS_DE_CAIDA = frozenset({"fuente_no_disponible", "fuente_lenta"})


async def _reunir_capas(
    llamadas: Sequence[Awaitable[Respuesta]],
) -> tuple[list[Respuesta], list[BaseException]]:
    """Lanza todas las capas a la vez y separa las que respondieron de las que fallaron: una capa
    caída no tumba a las demás (una fuente de varias capas sale `parcial`, no en error entero). La
    cancelación sí se propaga: no es un fallo de la fuente."""
    resultados = await asyncio.gather(*llamadas, return_exceptions=True)
    ok: list[Respuesta] = []
    fallos: list[BaseException] = []
    for r in resultados:
        if isinstance(r, asyncio.CancelledError):
            raise r
        if isinstance(r, BaseException):
            fallos.append(r)
        else:
            ok.append(r)
    return ok, fallos


class Ejecutor:
    def __init__(
        self,
        catalogo: Catalogo,
        conectores: dict[str, Conector],
        almacen: Almacen | None = None,
        reloj: Callable[[], float] = time.time,
        proteccion: Proteccion | None = None,
    ) -> None:
        self.catalogo = catalogo
        self.conectores = conectores
        self.almacen = almacen
        self.proteccion = proteccion
        self.reloj = reloj
        self._indices: dict[str, dict[str, Any]] = {}

    def _anio_fuera(self, fuente: Fuente, valores: dict[str, Any]) -> str | None:
        """Un año pedido fuera de los que cubre la fuente (spec 08: mínimo y máximo cosechados de
        su columna de tiempo). Solo se usa si la consulta volvió vacía: un año publicado después de
        la cosecha trae datos y no pasa por aquí. Sin esto, «¿homicidios en Chía en 2030?» volvía
        `no_encontrado` y un agente lo dio como «0 homicidios» (GEO Copilot, fiabilidad)."""
        anio = valores.get("anio")
        desde_anio = fuente.cobertura.desde_anio
        hasta_anio = fuente.cobertura.hasta_anio
        if str(anio).isdigit() and (
            (desde_anio and int(str(anio)) < desde_anio)
            or (hasta_anio and int(str(anio)) > hasta_anio)
        ):
            if desde_anio and hasta_anio:
                return f"Esta fuente cubre de {desde_anio} a {hasta_anio}: {anio} no está."
            if desde_anio and int(str(anio)) < desde_anio:
                return f"Esta fuente cubre desde {desde_anio}: {anio} no está."
            return f"Esta fuente cubre hasta {hasta_anio}: {anio} no está."
        columna = fuente.cobertura.columna_tiempo
        metadatos = self.catalogo.metadatos.get(fuente.id)
        campo = metadatos.campos.get(columna) if metadatos and columna else None
        if not isinstance(anio, int) or not campo or not campo.minimo or not campo.maximo:
            return None if hasta_anio else self._anio_futuro(anio)
        desde, hasta = (
            int(m[1]) if (m := _AÑO.match(v)) else None for v in (campo.minimo, campo.maximo)
        )
        if desde is None or hasta is None:
            return self._anio_futuro(anio)
        if desde <= anio <= hasta:
            return None
        return (
            f"La fuente cubre de {desde} a {hasta}: {anio} está fuera de su cobertura (no es que "
            "haya cero casos)."
        )

    def _anio_futuro(self, anio: Any) -> str | None:
        """«¿Inflación en 2027?» volvía `no_encontrado` a secas: un año que aún no llega no es un
        año sin datos (revisión de valor, 2026-11-04). Solo cuando no hay cobertura cosechada, que
        dice más."""
        if str(anio).isdigit() and int(str(anio)) > datetime.fromtimestamp(self.reloj(), UTC).year:
            return f"{anio} todavía no ha llegado: la fuente no tiene datos de un año futuro."
        return None

    def indice(self, nombre: str) -> dict[str, Any]:
        if nombre not in self._indices:
            self._indices[nombre] = cargar_cobertura(nombre)
        return self._indices[nombre]

    async def llamar(
        self,
        conector: str,
        tool: str,
        argumentos: dict[str, Any],
        *,
        fuente_id: str | None = None,
        ausente: Sequence[int] = (),
    ) -> dict[str, Any]:
        c = self.conectores.get(conector)
        if c is None:
            raise ErrorEjecucion(
                "fuente_no_disponible", f"el conector {conector} no está configurado"
            )

        async def una() -> dict[str, Any]:
            inicio = time.monotonic()
            try:
                return await c.llamar(tool, argumentos)
            except ErrorConector as exc:
                # La fuente respondió que eso no existe: ni es una caída ni cuenta para el corte.
                if (m := _HTTP_DE_FUENTE.search(str(exc))) and int(m[1]) in ausente:
                    # cero de cero: la fuente sí dijo cuántos hay (ninguno), no es un silencio
                    completitud = {"vistos": 0, "total": 0, "truncado": False}
                    return {"facts": {"completitud": completitud, AUSENTE: int(m[1])}}
                raise ErrorEjecucion(exc.codigo, str(exc), exc.reintentar_en_s) from exc
            finally:
                metricas.FUENTE_LATENCIA.labels(fuente_id or conector).observe(
                    time.monotonic() - inicio
                )

        if self.proteccion is None:
            return await una()
        return await self.proteccion.llamar(fuente_id or conector, una)

    async def ejecutar(
        self,
        herramienta: str,
        entrada: dict[str, Any],
        *,
        plan: Plan = "normal",
        frescura: Frescura = "normal",
        geometria_completa: bool = False,
        desde: int = 0,
        tope: int | None = None,
    ) -> Sobre:
        """`desde` y `tope` (ADR-0040): una página que sigue en la fuente desde la fila `desde`, de
        `tope` filas. Solo para herramientas con `ventana_de`; los pone la puerta, no la entrada."""
        h = self.catalogo.herramientas.get(herramienta)
        if h is None:
            raise ErrorEjecucion("no_existe", f"no hay herramienta {herramienta}")
        fuente = self.catalogo.fuentes[h.fuente]
        # ADR-0007 (enmienda del 2026-11-01): una llave de producción solo usa lo vendible
        # (publicada y con uso comercial); lo demás responde solo a llaves de evaluación
        if plan != "evaluacion" and not vendible(fuente):
            raise ErrorEjecucion(
                "licencia_no_habilitada",
                f"{fuente.id}: {motivo_no_vendible(fuente)}; solo responde a llaves de evaluación",
            )
        valores = validar_entrada(h, entrada)

        # ADR-0008: caché por frescura de la fuente; con la fuente caída, la copia vieja sale como
        # «obsoleto» y lo dice. `frescura=estricta` nunca usa caché.
        simplificada = h.consulta.argumentos.get("geometria") == "simplificada"
        fiel = geometria_completa and simplificada and _lista_corta(h)
        aviso = AVISO_SIMPLIFICADA if geometria_completa and simplificada and not fiel else None
        if desde or tope is not None:
            if ventana_de(h) is None:
                raise ErrorEjecucion("error_interno", f"{h.id} no pagina en la fuente")
            fiel = False  # una página larga no lleva la forma completa
            aviso = None
        pagina_fuente = {"_desde": desde, "_tope": tope} if desde or tope is not None else {}
        k = clave_cache(
            h.id,
            h.version,
            valores | ({"_geometria": "completa"} if fiel else {}) | pagina_fuente,
        )
        guardado = None
        vigente = huella_cache(h.model_dump_json(), fuente.model_dump_json())
        if self.almacen is not None and frescura == "normal":
            guardado = await self.almacen.leer(k)
            if (
                guardado
                and guardado.get("huella") == vigente
                and self.reloj() - guardado["guardado_en"] <= fuente.frescura.ttl_cache_s
            ):
                metricas.CACHE_ACIERTOS.inc()
                return self._servir(self._desde_cache(guardado, "cache"), h, valores, aviso)
        try:
            sobre = await self._desde_fuente(h, fuente, valores, fiel, desde, tope)
        except ErrorEjecucion as exc:
            if guardado and exc.codigo in CODIGOS_DE_CAIDA:
                obsoleto = self._desde_cache(guardado, "obsoleto", exc.codigo)
                return self._servir(obsoleto, h, valores, aviso)
            raise
        if self.almacen is not None and sobre.estado != "parcial":
            await self.almacen.guardar(
                k,
                {
                    "guardado_en": self.reloj(),
                    "huella": vigente,
                    "sobre": sobre.model_dump(mode="json"),
                },
                RETENCION_S,
            )
        return self._servir(sobre, h, valores, aviso)

    def _servir(
        self, sobre: Sobre, h: Herramienta, valores: dict[str, Any], aviso: str | None = None
    ) -> Sobre:
        """Los avisos que salen del catálogo y no de la fuente: se agregan al servir (de la fuente
        o de la caché) y no se guardan en la caché. Los homónimos del municipio, y si los datos
        no son recientes: ICFES Saber 11 no cambia desde 2023 y la respuesta solo decía la fecha
        de la consulta, de hoy («nunca un dato viejo disfrazado de actual»)."""
        from terranova.ficha_tecnica import atraso

        fuente = self.catalogo.fuentes[h.fuente]
        avisos = [
            *avisos_de_la_ficha(h, fuente, sobre),
            *((a,) if (a := _aviso_de_homonimos(h, valores)) else ()),
            *((a,) if (a := _aviso_de_escala(fuente)) else ()),
            *((aviso,) if aviso else ()),
            *(
                f"Datos no recientes: {a}."
                for a in atraso(fuente, self.catalogo.metadatos.get(fuente.id), ahora().date())
            ),
        ]
        nuevos = [a for a in avisos if a not in sobre.avisos]
        return sobre.model_copy(update={"avisos": [*sobre.avisos, *nuevos]}) if nuevos else sobre

    def _desde_cache(
        self, guardado: dict[str, Any], modo: Literal["cache", "obsoleto"], causa: str | None = None
    ) -> Sobre:
        crudo = guardado["sobre"]
        edad = max(0, int(self.reloj() - guardado["guardado_en"]))
        for p in crudo["procedencia"]:
            p["servido_desde"] = modo  # `consultado_en` queda el original (regla 6)
            p["cache"] = {"acierto": True, "edad_s": edad}
        avisos = list(crudo["avisos"])
        if modo == "obsoleto":
            fecha = crudo["procedencia"][0]["consultado_en"]
            avisos.append(
                f"La fuente no respondió ({causa}): este dato es del {fecha}, no es actual."
            )
        # ADR-0010: lo que sale de caché no descuenta
        return Sobre.model_validate(
            {**crudo, "solicitud_id": nueva_solicitud_id(), "avisos": avisos, "creditos": 0}
        )

    async def _desde_fuente(
        self,
        h: Herramienta,
        fuente: Fuente,
        valores: dict[str, Any],
        fiel: bool = False,
        desde: int = 0,
        tope: int | None = None,
    ) -> Sobre:
        consultado_en = ahora()
        previas: list[Procedencia] = []
        if h.consulta.previa is not None:
            valores, procedencia_previa = await self._previa(h, valores, consultado_en)
            previas.append(procedencia_previa)

        complemento = (
            asyncio.ensure_future(self._complemento(h, valores, consultado_en))
            if h.consulta.complemento is not None
            else None
        )
        capas: list[str | None] = [str(c) for c in h.consulta.capas] or [None]
        llamadas = []
        for capa in capas:
            argumentos = renderizar(
                h.consulta.argumentos,
                # `capa` sola sirve cuando cada capa es un conjunto (un id de Socrata), no una url
                {
                    **valores,
                    "url_fuente": fuente.url,
                    "url_capa": f"{fuente.url}/{capa}",
                    "capa": capa or "",
                },
            )
            if fiel:
                argumentos["geometria"] = "completa"
            if desde or tope is not None:
                argumentos["desde"] = desde
                if tope is not None:
                    argumentos[TOPE_PAGINABLE[h.consulta.tool]] = tope
            llamadas.append(self._una(h, fuente.conector, capa, argumentos))
        respuestas, fallos = await _reunir_capas(llamadas)
        if not respuestas:
            if complemento is not None:
                complemento.cancel()
            raise fallos[0]  # todas las capas fallaron: se falla igual (no hay `parcial` de una)
        capas_incompletas = len(fallos)  # unas capas sí respondieron y otras no: será `parcial`
        hechos_de_dato = [k for k, c in fuente.campos.items() if c.origen == "hecho"]
        reintentos = 0
        while reintentos < fuente.comportamiento.reintentos_si_vacio and all(
            not r.filas and not any(k in r.hechos for k in hechos_de_dato) for r in respuestas
        ):
            reintentos += 1
            nuevas, _ = await _reunir_capas(
                [self._una(h, fuente.conector, r.capa, r.argumentos) for r in respuestas]
            )
            if len(nuevas) < len(respuestas):
                break  # un reintento que pierde capas no borra lo que ya se tenía
            respuestas = nuevas

        elementos: list[dict[str, Any]] = []
        rasgos: list[dict[str, Any]] = []
        procedencia: list[Procedencia] = list(previas)
        hechos: dict[str, Any] = {}
        crs = "EPSG:4326"
        for r in respuestas:
            mapeadas = [mapear_fila(h, fuente, f, r.capa) for f in r.filas]
            elementos += mapeadas
            for fila, geom in zip(mapeadas, r.geometrias, strict=True):
                if geom is not None:
                    rasgos.append({"type": "Feature", "geometry": a_2d(geom), "properties": fila})
            crs = r.crs or crs
            for clave, campo in fuente.campos.items():
                if campo.origen == "hecho" and clave in r.hechos:
                    hechos[campo.nombre] = convertir(r.hechos[clave], campo.tipo)
            procedencia.append(self._procedencia(h, fuente, r, consultado_en, mapeadas))

        filas_recibidas = len(elementos)
        if h.consulta.juntar:
            elementos = juntar_filas(elementos, h.consulta.juntar)
        if h.consulta.unico_por:
            elementos = unico_por(elementos, h.consulta.unico_por, h.consulta.unico_mayor)
        total = None
        principales = procedencia[len(previas) :]  # la previa no cuenta en el total
        if len(principales) == 1:
            total = principales[0].completitud.total
        elif all(p.completitud.total is not None for p in principales):
            total = sum(p.completitud.total or 0 for p in principales)
        # honestidad: la fuente dijo que hay `total` y no entregó ninguno (una página que llegó
        # vacía, un corte): eso es «no se pudo», nunca «no encontrado». Con SINCHI, el conector
        # contó 1 polígono y su página vino vacía; el sobre decía «no encontrado» (2026-10-28).
        # (con `desde`, una página que pasa del total llega vacía y es correcta: ADR-0040)
        if not elementos and not capas_incompletas and total and total > desde:
            raise ErrorEjecucion(
                "fuente_respuesta_invalida",
                f"la fuente dice que hay {total} y no entregó ninguno: no se pudo leer la "
                "respuesta",
            )
        hechos_complemento: dict[str, Any] = {}
        aviso_complemento: str | None = None
        if complemento is not None:
            try:
                hechos_complemento, procedencia_complemento = await complemento
                procedencia.append(procedencia_complemento)  # después del total: no cuenta
            except Exception as fallo:  # noqa: BLE001 — la principal respondió: se sigue sin esto
                assert h.consulta.complemento is not None
                aviso_complemento = (
                    f"No se pudo saber {h.consulta.complemento.que_dice}: la consulta "
                    f"complementaria falló ({type(fallo).__name__})."
                )
        derivar_secuencia(h, elementos)
        agregados = {
            nombre: redondear(
                derivar_resultado(
                    d,
                    elementos,
                    total,
                    None if h.consulta.juntar or h.consulta.unico_por else total,
                ),
                d.decimales,
            )
            for nombre, d in h.derivados.items()
            if not d.por_elemento and not d.al_final
        }
        avisos_conteo: list[str] = []
        if total is not None and total != filas_recibidas and len(respuestas) == 1:
            # P0.7: la lista sigue en la fuente; los conteos por grupo se piden enteros
            completos = await self._conteos_completos(h, fuente, respuestas[0])
            agregados.update(completos)
            if completos:
                avisos_conteo = [CONTEOS_COMPLETOS + ", ".join(sorted(completos)) + "."]

        if es_relleno(h, elementos, hechos):
            elementos, hechos = [], {}
        hay_algo = bool(elementos) or bool(hechos)
        if hay_algo:
            hechos = {**hechos, **hechos_complemento}
        if h.consulta.forma == "uno":
            datos = {
                **(elementos[0] if elementos else {}),
                **hechos,
                **(agregados if hay_algo else {}),
            }
        else:
            datos = {**hechos, **(agregados if hay_algo else {})}
            if any(c.origen == "fila" for c in fuente.campos.values()):
                datos["elementos"] = elementos
        if hay_algo:
            for nombre, d in h.derivados.items():
                if d.al_final:
                    a, b = datos.get(d.campo or ""), datos.get(d.igual_a or "")
                    datos[nombre] = None if a is None or b is None else str(a) == str(b)
        datos = {k: v for k, v in datos.items() if v is not None} if hay_algo else {}

        avisos: list[str] = [aviso_complemento] if aviso_complemento and hay_algo else []
        avisos += avisos_conteo if hay_algo else []
        estado: Estado = "encontrado" if hay_algo else "no_encontrado"
        # honestidad: una fila cuyos campos de lista blanca mapean todos a None deja `datos` vacío
        # (forma «uno»); «encontrado» con datos vacío es indistinguible de un bug → «no encontrado»
        if h.consulta.forma == "uno" and not datos:
            estado = "no_encontrado"
        if not hay_algo and reintentos:
            avisos.append(
                f"Esta fuente a veces responde vacío sin error: se consultó {reintentos + 1} veces "
                "y en todas vino vacía."
            )
        if h.consulta.forma == "uno" and len(elementos) > 1:
            avisos.append(
                f"Hay {len(elementos)} resultados; se muestra el primero (todos van en la capa)."
            )
        if hay_algo and (incompleta := aviso_de_anio_incompleto(fuente, valores)):
            avisos.append(incompleta)
        lejos = not hay_algo and fuente.cobertura.pais == "CO" and fuera_de(h, valores)
        regional = fuente.cobertura.rectangulo
        if lejos:
            estado = "fuera_de_cobertura"
            avisos.append("Ese lugar queda fuera de Colombia y esta fuente solo cubre Colombia.")
        elif not hay_algo and regional and fuera_de(h, valores, regional):
            estado = "fuera_de_cobertura"
            avisos.append(f"Ese lugar queda fuera del área que cubre {fuente.entidad}.")
        elif not hay_algo and fuente.cobertura.indice in COBERTURAS:
            veredicto = await COBERTURAS[fuente.cobertura.indice](self, h, valores, consultado_en)
            procedencia += veredicto.procedencia
            if veredicto.aviso:
                avisos.append(veredicto.aviso)
            if veredicto.fuera:
                estado = "fuera_de_cobertura"
        if (
            not hay_algo
            and estado == "no_encontrado"
            and (fuera := self._anio_fuera(fuente, valores))
        ):
            estado = "fuera_de_cobertura"
            avisos.append(fuera)
        if not hay_algo and estado == "no_encontrado" and (raro := _codigo_desconocido(h, valores)):
            avisos.append(raro)
        errores: list[ErrorParte] = []
        if capas_incompletas and estado != "fuera_de_cobertura":
            # honestidad: con unas capas caídas no se puede afirmar «encontrado» ni «no encontrado»
            estado = "parcial"
            avisos.append(
                f"{capas_incompletas} de {len(capas)} capas de la fuente no respondieron: "
                "el resultado puede estar incompleto."
            )
            # regla 5: un sobre `parcial` lleva el error de cada capa que cayó (de la misma fuente)
            for exc in fallos:
                errores.append(
                    ErrorParte(
                        codigo=getattr(exc, "codigo", "fuente_no_disponible"),
                        fuente_id=fuente.id,
                        detalle=str(exc)[:500],
                        reintentar_en_s=getattr(exc, "reintentar_en_s", None),
                    )
                )
        if any(p.completitud.total is None for p in procedencia):
            avisos.append("La fuente no dijo cuántos elementos hay: no se sabe si vino todo.")
        if any(AUSENTE in r.hechos for r in respuestas):
            # «015» en vez de «0015» en la CREG: antes salía «la fuente no dijo cuántos hay»
            avisos.append(
                "La fuente respondió que ese documento no existe: revise cómo se escribe su "
                "nombre (la descripción de la herramienta da la forma y ejemplos). No es una caída."
            )
        # la lista llegó al tope de la consulta: decirlo en el sobre, no solo en la procedencia.
        # Con un tope de 200, Chapinero trajo una parte de 948 tratamientos y nada lo decía
        # (GEO Copilot, 2026-11-03).
        # (el inicio de un texto largo es un solo elemento cuyo total son caracteres: lo dice
        # `caracteres`, no este aviso)
        if (
            filas_recibidas > 1
            and total is not None
            and filas_recibidas < total
            and any(p.completitud.truncado for p in principales)
            and filas_recibidas != _tope_pedido(h, valores)
        ):
            avisos.append(
                f"Vinieron {filas_recibidas} de {total}: la consulta trae como máximo "
                f"{filas_recibidas}, y la lista y lo que `datos` suma o cuenta van solo sobre "
                "esos. "
                "Acote la búsqueda (zona, periodo o filtro) para tenerlo todo."
            )
        if fuente.modo == "copia":
            avisos += [_aviso_de_copia(r.hechos) for r in respuestas[:1]]
        if fuente.uso_comercial == "no":
            avisos.append(
                f"Solo uso no comercial ({fuente.licencia.spdx}): este dato no se puede usar con "
                "fines comerciales."
            )
        if fuente.clasificacion_licencia == "ambar":
            avisos.append(AVISO_DATO_PUBLICO)

        geo = None
        if rasgos:
            geo = GeoResult.model_validate(
                {
                    "geo_result": "1",
                    "artifacts": [
                        {
                            "kind": "feature_collection",
                            "name": fuente.titulo,
                            "crs": crs,
                            "data": {"type": "FeatureCollection", "features": rasgos},
                        }
                    ],
                    "facts": {},
                }
            )
        return Sobre(
            solicitud_id=nueva_solicitud_id(),
            herramienta=f"{h.id}@{h.version}",
            estado=estado,
            entrada=valores,
            zona_usada=_zona(h, valores, _municipios()),
            datos=datos,
            huella=huella(datos),
            geo_result=geo,
            procedencia=procedencia,
            avisos=avisos,
            errores=errores,
            creditos=0 if estado == "fuera_de_cobertura" else h.creditos,
        )

    async def _previa(
        self, h: Herramienta, valores: dict[str, Any], consultado_en: datetime
    ) -> tuple[dict[str, Any], Procedencia]:
        """La consulta previa: sus valores de `columna` que cumplen el patrón van a `{previa}`.
        Sin ninguno, `{previa}` es `''` (o «0» con `formato: coma`): la consulta principal no
        encuentra nada, y lo dice."""
        previa = h.consulta.previa
        assert previa is not None
        fuente = self.catalogo.fuentes[previa.fuente]
        argumentos = renderizar(previa.argumentos, {**valores, "url_fuente": fuente.url})
        sc = await self.llamar(fuente.conector, previa.tool, argumentos, fuente_id=fuente.id)
        r = separar(h, None, argumentos, sc)
        patron = re.compile(PATRONES_ENTRADA[previa.patron])
        hallados = sorted(
            {
                str(f[previa.columna])
                for f in r.filas
                if f.get(previa.columna) is not None and patron.fullmatch(str(f[previa.columna]))
            }
        )
        if previa.formato == "coma":
            # sin ninguno, «0»: un id que no existe (WordPress da 0 resultados con descriptor=0;
            # vacío, en cambio, quita el filtro y devolvería todo)
            lista = ",".join(hallados) or "0"
        else:
            lista = ", ".join(f"'{v}'" for v in hallados) or "''"
        vistos = [{previa.columna: v} for v in hallados]
        procedencia = self._procedencia(h, fuente, r, consultado_en, vistos)
        return {**valores, MARCADOR_PREVIA: lista}, procedencia

    async def _complemento(
        self, h: Herramienta, valores: dict[str, Any], consultado_en: datetime
    ) -> tuple[dict[str, Any], Procedencia]:
        """La consulta complementaria: su primera fila, con los nombres y tipos de `hechos`."""
        comp = h.consulta.complemento
        assert comp is not None
        fuente = self.catalogo.fuentes[comp.fuente]
        argumentos = renderizar(comp.argumentos, {**valores, "url_fuente": fuente.url})
        sc = await self.llamar(fuente.conector, comp.tool, argumentos, fuente_id=fuente.id)
        r = separar(h, None, argumentos, sc)
        fila = r.filas[0] if r.filas else {}
        hechos = {
            hecho.nombre: convertir(fila.get(columna), hecho.tipo)
            for columna, hecho in comp.hechos.items()
        }
        hechos = {k: v for k, v in hechos.items() if v is not None}
        for columna, hecho in comp.hechos.items():
            campo = fuente.campos.get(columna)
            if campo is not None and campo.codigos is not None and hecho.nombre in hechos:
                significado = campo.significado(hechos[hecho.nombre], None)
                if significado is not None:
                    hechos[f"{hecho.nombre}{SUFIJO_SIGNIFICADO}"] = significado
        procedencia = self._procedencia(h, fuente, r, consultado_en, [hechos] if hechos else [])
        return hechos, procedencia

    async def _conteos_completos(
        self, h: Herramienta, fuente: Fuente, r: Respuesta
    ) -> dict[str, dict[str, int]]:
        """P0.7: los `conteo_por` sobre la lista entera, cuando no cupo en una consulta. Solo en
        copias (un `group by` por derivado, con los mismos filtros) y solo si el `campo` es una
        columna de la fuente o su significado; los grupos se traducen con `mapear_fila`, como
        cada fila. Con 1 000 grupos o más, o si la consulta falla, queda el conteo de la ventana."""
        if h.consulta.tool != "consultar_copia":
            return {}
        quitar = {"select", "order", "limite", "desde", "geometria", "group", "agregados"}
        base = {k: v for k, v in r.argumentos.items() if k not in quitar}
        salida: dict[str, dict[str, int]] = {}
        for nombre, d in h.derivados.items():
            if d.solo_si is not None or d.por_elemento:
                continue
            if d.de in ("suma", "maximo"):
                total_col = await self._agregado_completo(h, fuente, r, base, d)
                if total_col is not _SIN_DATO:
                    salida[nombre] = total_col
                continue
            if d.de != "conteo_por":
                continue
            columna = next(
                (
                    k
                    for k, c in fuente.campos.items()
                    if c.origen == "fila"
                    and (
                        c.nombre == d.campo
                        or (c.codigos is not None and f"{c.nombre}{SUFIJO_SIGNIFICADO}" == d.campo)
                    )
                ),
                None,
            )
            if columna is None:
                continue
            argumentos = {
                **base,
                "select": [columna],
                "group": [columna],
                "agregados": {"n": "count"},
                "geometria": "ninguna",
                "limite": 1000,
            }
            try:
                grupos = await self._una(h, fuente.conector, r.capa, argumentos)
            except Exception:  # noqa: BLE001 — queda el conteo de la ventana, que el aviso explica
                continue
            if len(grupos.filas) >= 1000:
                continue
            cuenta: Counter[str] = Counter()
            for g in grupos.filas:
                valor = mapear_fila(h, fuente, {columna: g.get(columna)}, r.capa).get(d.campo or "")
                if valor is None:
                    if d.vacio is None:
                        continue
                    clave = d.vacio
                else:
                    clave = " ".join(str(valor).split())
                cuenta[clave] += int(g.get("n") or 0)
            salida[nombre] = dict(cuenta.most_common())
        return salida

    async def _agregado_completo(
        self, h: Herramienta, fuente: Fuente, r: Respuesta, base: dict[str, Any], d: Derivado
    ) -> Any:
        """`suma` o `maximo` de una columna numérica sobre la lista entera. Solo si la columna sale
        tal cual (sin `vacios`, coma decimal ni moneda que la fila corrija al mapearla)."""
        campo = next(
            (
                (k, c)
                for k, c in fuente.campos.items()
                if c.origen == "fila" and c.nombre == d.campo
            ),
            None,
        )
        if campo is None or campo[1].vacios or campo[1].coma_decimal or campo[1].moneda:
            return _SIN_DATO
        funcion = "sum" if d.de == "suma" else "max"
        argumentos = {
            **base,
            "agregados": {"v": f"{funcion}:{campo[0]}"},
            "geometria": "ninguna",
            "limite": 1,
        }
        try:
            resultado = await self._una(h, fuente.conector, r.capa, argumentos)
        except Exception:  # noqa: BLE001 — queda el de la ventana (p. ej. una columna de texto)
            return _SIN_DATO
        if len(resultado.filas) != 1 or not _numero(resultado.filas[0].get("v")):
            return _SIN_DATO
        valor = convertir(round(float(resultado.filas[0]["v"]), 6), d.tipo)
        return redondear(valor, d.decimales)

    async def _una(
        self, h: Herramienta, conector: str, capa: str | None, argumentos: dict[str, Any]
    ) -> Respuesta:
        sc = await self.llamar(
            conector,
            h.consulta.tool,
            argumentos,
            fuente_id=h.fuente,
            ausente=h.consulta.documento_ausente,
        )
        return separar(h, capa, argumentos, sc)

    def _procedencia(
        self,
        h: Herramienta,
        fuente: Fuente,
        r: Respuesta,
        consultado_en: datetime,
        mapeadas: list[dict[str, Any]],
    ) -> Procedencia:
        servido_desde: ServidoDesde = "fuente"
        if fuente.modo == "copia":  # ADR-0024: la fecha es la de la copia, no la de la pregunta
            servido_desde = "obsoleto" if r.hechos.get("servido_desde") == "obsoleto" else "copia"
            consultado_en = _fecha_de_copia(r.hechos)
        return Procedencia(
            fuente_id=fuente.id,
            entidad=fuente.entidad,
            acto=fuente.acto,
            url=str(r.argumentos.get("url") or fuente.url),
            licencia=licencia_de(fuente),
            atribucion=fuente.atribucion,
            servido_desde=servido_desde,
            consultado_en=consultado_en,
            consulta={**r.argumentos, **({"capa": r.capa} if r.capa else {})},
            completitud=completitud_de(r, h.consulta.completo_por_construccion),
            cache=Cache(acierto=False, edad_s=0),
            transformaciones=[e] if (e := _aviso_de_escala(fuente)) else [],
            conector=fuente.conector,
            huella=huella({"elementos": mapeadas}),
        )


AVISO_SIMPLIFICADA = (
    "Geometría simplificada a unos 55 m: la lista es larga para las formas completas. Pida cada "
    "elemento en un punto suyo para ver su forma completa."
)


def _lista_corta(h: Herramienta) -> bool:
    argumentos = h.consulta.argumentos
    return (argumentos.get("limite") or argumentos.get("max_features") or 0) <= (
        MAX_ELEMENTOS_GEOMETRIA_FIEL
    )


def _aviso_de_escala(fuente: Fuente) -> str | None:
    """Lo simplificado al copiar no se recupera: el cruce y el área son tan finos como la copia."""
    tolerancia = fuente.copia.tolerancia if fuente.copia else None
    if not tolerancia:
        return None
    metros = max(1, round(tolerancia * METROS_POR_GRADO))
    return f"La copia simplificó la geometría a unos {metros} m: bordes y áreas llegan hasta ahí."


def _fecha_de_copia(hechos: dict[str, Any]) -> datetime:
    """Sin la fecha de la copia no se sabe qué tan vieja es: no se responde como si fuera actual."""
    try:
        return datetime.fromisoformat(str(hechos["consultado_en"]))
    except (KeyError, ValueError) as exc:
        raise ErrorEjecucion("fuente_respuesta_invalida", "la copia no dijo de cuándo es") from exc


def _aviso_de_copia(hechos: dict[str, Any]) -> str:
    """ADR-0024: de cuándo es la copia y qué ventana cubre; vencida, se dice."""
    copia = hechos.get("copia") or {}
    fecha = str(hechos.get("consultado_en", ""))[:10]
    desde = f", con lo firmado desde {copia['ventana_desde']}" if copia.get("ventana_desde") else ""
    vencida = (
        " Está vencida: puede faltar lo más reciente."
        if hechos.get("servido_desde") == "obsoleto"
        else ""
    )
    return f"Sale de la copia de Terrnova del {fecha}{desde}, no de la fuente en vivo.{vencida}"


def a_2d(geometria: Any) -> Any:
    """La geometría solo con lon y lat (regla 8 de rt/1). USGS manda la profundidad como tercera
    coordenada y GEO Copilot no pudo pintar los sismos («Geometry has Z dimension»); la
    profundidad ya va en las propiedades."""
    if not isinstance(geometria, dict):
        return geometria
    if geometria.get("type") == "GeometryCollection":
        return {**geometria, "geometries": [a_2d(g) for g in geometria.get("geometries") or []]}

    def recortar(c: Any) -> Any:
        if isinstance(c, list) and c and isinstance(c[0], int | float):
            return c[:2]
        return [recortar(x) for x in c] if isinstance(c, list) else c

    if "coordinates" not in geometria:
        return geometria
    return {**geometria, "coordinates": recortar(geometria["coordinates"])}


@functools.cache
def _municipios() -> dict[str, Any]:
    """Nombre de cada municipio para `zona_usada` (regla 11), leído una vez por proceso: el índice
    pesa 0,3 s y el ejecutor se crea en cada solicitud (Schemathesis se colgaba)."""
    municipios: dict[str, Any] = cargar_cobertura("cobertura_catastral")["municipios"]
    return municipios


def _plano(texto: str) -> str:
    sin = unicodedata.normalize("NFD", texto.casefold())
    return " ".join("".join(c for c in sin if unicodedata.category(c) != "Mn").split())


def _clave(texto: str) -> str:
    """Solo letras y espacios: «BOGOTA, D.C.» → «bogota d c»."""
    return " ".join(re.sub(r"[^a-zñ ]", " ", _plano(texto)).split())


_VACIAS = frozenset({"y", "de", "del", "la", "el", "los", "las"})


def municipio_por_nombre(param: str, texto: str, municipios: dict[str, Any]) -> str:
    """El código DIVIPOLA de un municipio dicho por su nombre («Chía», «San Andrés, Santander»).

    Un agente que ponía el código de memoria mandó 08001 (Barranquilla) por «San Andrés» (GEO
    Copilot, plan de fiabilidad F4): con el nombre, la puerta resuelve con el índice y, si hay
    varios, no elige: el error los lista con su código."""
    nombre, _, depto = texto.partition(",")
    # «Bogotá D.C.» y «Bogotá, D.C.»: «D.C.» es Distrito Capital, no un departamento aparte
    q = re.sub(r"( d ?c| distrito capital)$", "", _clave(nombre))
    qd = set(re.sub(r"^(d ?c|distrito capital)$", "", _clave(depto)).split()) - _VACIAS
    todos = [(c, m) for c, m in sorted(municipios.items()) if m.get("municipio")]
    exactos = [(c, m) for c, m in todos if _clave(m["municipio"]) == q]
    parecidos = [(c, m) for c, m in todos if _clave(m["municipio"]).startswith(q + " ")]
    # «Tumaco» es SAN ANDRES DE TUMACO: el nombre como palabras dentro del oficial, de último
    contienen = [(c, m) for c, m in todos if f" {q} " in f" {_clave(m['municipio'])} "]
    candidatos = exactos or parecidos or contienen
    if qd:
        # «San Andrés y Providencia» está en «ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y …»
        candidatos = [
            (c, m) for c, m in candidatos if qd <= set(_clave(m.get("departamento") or "").split())
        ]
    if len(candidatos) == 1:
        return candidatos[0][0]
    if not candidatos:
        raise ErrorEntrada(
            param,
            f"no hay un municipio llamado «{texto.strip()}» en el DIVIPOLA; búscalo con "
            "dane_divipola_buscar o usa su código",
        )
    vistos = {c for c, _ in candidatos}
    lista = [*candidatos, *((c, m) for c, m in exactos + parecidos if c not in vistos)]
    opciones = "; ".join(
        f"{c} {m['municipio']} ({m.get('departamento') or '?'})" for c, m in lista[:8]
    ) + (f"; y {len(lista) - 8} más" if len(lista) > 8 else "")
    raise ErrorEntrada(
        param,
        f"«{texto.strip()}» es ambiguo: {len(lista)} municipios se llaman así: {opciones}. Usa el "
        "código o «nombre, departamento»",
    )


def _tope_pedido(h: Herramienta, v: dict[str, Any]) -> int | None:
    """Cuántas filas pidió quien pregunta, si el tope de la consulta sale de su entrada («los
    últimos 6 trimestres»). Con 6 pedidos y 6 recibidos, «vinieron 6 de 82, acote la búsqueda»
    contradecía la pregunta (revisión de valor, 2026-11-04)."""
    plantilla = h.consulta.argumentos.get("limite")
    marcador = MARCADOR.fullmatch(plantilla) if isinstance(plantilla, str) else None
    pedido = v.get(marcador.group(1)) if marcador else None
    return pedido if isinstance(pedido, int) else None


def _codigo_desconocido(h: Herramienta, v: dict[str, Any]) -> str | None:
    """Un código DIVIPOLA que no figura en la lista de municipios y volvió vacío: puede estar mal
    escrito. No se rechaza (la lista no trae los municipios más nuevos, como 27493), pero se dice:
    «99999» volvía `no_encontrado` como un municipio real sin datos (revisión de valor,
    2026-11-04)."""
    municipios = _municipios()
    for nombre, tipo in h.entrada.items():
        codigo = v.get(nombre)
        if tipo == "divipola" and isinstance(codigo, str) and codigo not in municipios:
            return (
                f"{codigo} no figura en la lista de municipios de Terrnova: puede estar mal "
                "escrito o ser un municipio creado hace poco (como 27493, Nuevo Belén de Bajirá, "
                "de 2022). Compruébelo con dane_divipola_buscar antes de leer el vacío como «sin "
                "datos»."
            )
    return None


def homonimos(codigo: str, municipios: dict[str, Any], *, tope: int = 6) -> list[str]:
    """Los otros municipios que se llaman igual que `codigo` o empiezan por su nombre («SAN
    ANDRES»: el de Santander, SAN ANDRES DE SOTAVENTO…), como «código NOMBRE (DEPTO)»."""
    nombre = (municipios.get(codigo) or {}).get("municipio")
    if not nombre:
        return []
    base = _plano(nombre)
    otros = []
    for cod, m in sorted(municipios.items()):
        otro = _plano(m.get("municipio") or "")
        if cod != codigo and (otro == base or otro.startswith(base + " ")):
            otros.append(f"{cod} {m['municipio']} ({m.get('departamento') or '?'})")
    return otros[:tope] + ([f"y {len(otros) - tope} más"] if len(otros) > tope else [])


def _aviso_de_homonimos(h: Herramienta, v: dict[str, Any]) -> str | None:
    """Con un municipio por código, el hecho de que hay otros con ese nombre. Un agente que puso de
    memoria 88001 para «San Andrés» respondía «no hay masacres» sin decir que hay cinco San Andrés
    (GEO Copilot, plan de fiabilidad F4): con el aviso, decide si pregunta o dice cuál tomó."""
    municipios = _municipios()
    for nombre, tipo in h.entrada.items():
        if tipo != "divipola" or not isinstance(v.get(nombre), str):
            continue
        if otros := homonimos(v[nombre], municipios):
            lugar = municipios[v[nombre]]
            depto = lugar.get("departamento") or "?"
            return (
                f"Se consultó {v[nombre]} = {lugar['municipio']} ({depto}). "
                f"Otros municipios con ese nombre: {'; '.join(otros)}. Si la pregunta era por "
                "otro, no se consultó."
            )
    return None


def fuera_de(
    h: Herramienta,
    v: dict[str, Any],
    rectangulo: tuple[float, float, float, float] = RECTANGULO_COLOMBIA,
) -> bool:
    """Si la zona pedida queda entera fuera del rectángulo. Solo por rectángulo: Quito o Panamá caen
    dentro del de Colombia y siguen siendo «no encontrado»."""
    oeste, sur, este, norte = rectangulo
    if "lon" in v and "lat" in v:
        return not (oeste <= float(v["lon"]) <= este and sur <= float(v["lat"]) <= norte)
    for nombre, tipo in h.entrada.items():
        if tipo == "bbox":
            x0, y0, x1, y1 = v[nombre]
            return bool(x1 < oeste or x0 > este or y1 < sur or y0 > norte)
        if tipo == "poligono":
            vertices = v[nombre]["coordinates"][0]
            return all(
                not (oeste <= lon <= este and sur <= lat <= norte) for lon, lat, *_ in vertices
            )
    return False


def _zona(
    h: Herramienta, v: dict[str, Any], municipios: dict[str, Any] | None = None
) -> ZonaUsada | None:
    if "lon" in v and "lat" in v:
        return ZonaUsada(tipo="punto", valor=[v["lon"], v["lat"]], crs="EPSG:4326")
    for nombre, tipo in h.entrada.items():
        if tipo == "bbox":
            return ZonaUsada(tipo="bbox", valor=v[nombre], crs="EPSG:4326")
        if tipo == "poligono":
            return ZonaUsada(tipo="poligono", valor=v[nombre], crs="EPSG:4326")
        if tipo == "divipola":
            lugar = (municipios or {}).get(v[nombre]) or {}
            nombre_lugar = ", ".join(
                x for x in (lugar.get("municipio"), lugar.get("departamento")) if x
            )
            return ZonaUsada(tipo="divipola", valor=v[nombre], nombre=nombre_lugar or None)
        if tipo == "codigo_predial":
            return ZonaUsada(tipo="codigo", valor=v[nombre])
    return None
