"""Ejecutor genérico (F2.1): ficha del catálogo → conector → lista blanca → sobre `rt/1`.

Todo lo que es propio de una fuente sale del catálogo (ADR-0006, ADR-0007, ADR-0012): qué
herramienta del conector se llama y con qué argumentos, qué campos salen y con qué nombre, qué se
calcula (derivados) y qué índice de cobertura decide entre «no encontrado» y «fuera de cobertura».
Aquí solo vive la mecánica común.
"""

from __future__ import annotations

import asyncio
import functools
import math
import re
import time
import unicodedata
from collections import Counter
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

from terranova import metricas
from terranova.cache import RETENCION_S, Almacen
from terranova.cache import clave as clave_cache
from terranova.catalogo import (
    AVISO_DATO_PUBLICO,
    MARCADOR,
    MARCADOR_PREVIA,
    PATRONES_ENTRADA,
    SUFIJO_SIGNIFICADO,
    Campo,
    Catalogo,
    Derivado,
    Fuente,
    Herramienta,
    cargar_cobertura,
    entero_de_json,
    motivo_no_vendible,
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
    if not isinstance(v, str):
        raise ErrorEntrada(nombre, "debe ser texto")
    if tipo in PATRONES_ENTRADA:
        if not re.fullmatch(PATRONES_ENTRADA[tipo], v):
            raise ErrorEntrada(nombre, f"no tiene el formato de {tipo}")
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
        raise ErrorEntrada(nombre, f"tiene {vertices} vértices; el tope es {MAX_VERTICES_POLIGONO}")
    lons, lats = [x for x, _ in limpios[0]], [y for _, y in limpios[0]]
    if max(max(lons) - min(lons), max(lats) - min(lats)) > MAX_LADO_POLIGONO_GRADOS:
        raise ErrorEntrada(nombre, f"pasa de {MAX_LADO_POLIGONO_GRADOS:g} grado de lado")
    return {"type": "Polygon", "coordinates": limpios}


def _numero(x: Any) -> bool:
    return isinstance(x, int | float) and not isinstance(x, bool) and math.isfinite(x)


_TILDES = str.maketrans(dict.fromkeys("ÁÉÍÓÚÜáéíóúü", "_"))


def _marcador(m: re.Match[str], valores: dict[str, Any]) -> Any:
    valor = valores[m.group(1)]
    return str(valor).translate(_TILDES) if m.group(0).endswith(":sin_tildes}") else valor


def renderizar(plantilla: Any, valores: dict[str, Any]) -> Any:
    """Reemplaza `{marcador}`: si el texto es solo el marcador, el valor conserva su tipo.
    `{marcador:sin_tildes}` cambia cada vocal con tilde por `_`, el comodín de LIKE."""
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
    "[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]|[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]"
)


def sanear(texto: str) -> str:
    """Texto de la fuente sin control ni bidi y con el largo máximo de `rt/1` (regla 9)."""
    limpio = _BIDI_Y_CONTROL.sub("", unicodedata.normalize("NFC", texto))
    return limpio if len(limpio) <= MAX_TEXTO else limpio[: MAX_TEXTO - 1] + "…"


_AÑO = re.compile(r"^(\d{4})")
_HTTP_DE_FUENTE = re.compile(r"el servicio respondió HTTP (\d{3})")
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
        from datetime import UTC

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
    return [
        a.texto.strip()
        for a in h.avisos
        if a.cuando == "encontrado" and (a.si is None or a.si.cumple(sobre.datos))
    ]


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
    """«06/15/2016» (mda) o «15/06/2016» (dma) a ISO. Lo que no tiene esa forma pasa igual: el
    mismo conjunto puede traer fechas ISO en otras filas. Si detrás de la fecha viene más texto
    («18/12/1997 Fecha de modificación: 26/09/2024»), cuenta la primera."""
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


def derivar_resultado(d: Derivado, elementos: list[dict[str, Any]], total: int | None) -> Any:
    if d.solo_si:
        elementos = [e for e in elementos if d.solo_si.cumple(e)]
    valores = [e.get(d.campo or "") for e in elementos]
    numeros = [float(v) for v in valores if v is not None and _numero(v)]
    if d.de == "conteo":
        return len(elementos)
    if d.de == "conteo_por":
        return dict(Counter(str(v) for v in valores if v is not None).most_common())
    if d.de == "suma":
        return convertir(round(sum(numeros), 6), d.tipo) if numeros else None
    if d.de == "maximo":
        return convertir(max(numeros), d.tipo) if numeros else None
    if d.de == "primero":
        return convertir(valores[0], d.tipo) if valores else None
    if d.de == "ultimo":
        return convertir(valores[-1], d.tipo) if valores else None
    if d.de == "distintos":
        return len({str(v) for v in valores if v is not None})
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
        if desde_anio and str(anio).isdigit() and int(str(anio)) < desde_anio:
            return f"Esta fuente cubre desde {desde_anio}: {anio} no está."
        columna = fuente.cobertura.columna_tiempo
        metadatos = self.catalogo.metadatos.get(fuente.id)
        campo = metadatos.campos.get(columna) if metadatos and columna else None
        if not isinstance(anio, int) or not campo or not campo.minimo or not campo.maximo:
            return None
        desde, hasta = (
            int(m[1]) if (m := _AÑO.match(v)) else None for v in (campo.minimo, campo.maximo)
        )
        if desde is None or hasta is None or desde <= anio <= hasta:
            return None
        return (
            f"La fuente cubre de {desde} a {hasta}: {anio} está fuera de su cobertura (no es que "
            "haya cero casos)."
        )

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
                    return {}
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
    ) -> Sobre:
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
        k = clave_cache(h.id, h.version, valores | ({"_geometria": "completa"} if fiel else {}))
        guardado = None
        if self.almacen is not None and frescura == "normal":
            guardado = await self.almacen.leer(k)
            if guardado and self.reloj() - guardado["guardado_en"] <= fuente.frescura.ttl_cache_s:
                metricas.CACHE_ACIERTOS.inc()
                return self._servir(self._desde_cache(guardado, "cache"), h, valores, aviso)
        try:
            sobre = await self._desde_fuente(h, fuente, valores, fiel)
        except ErrorEjecucion as exc:
            if guardado and exc.codigo in CODIGOS_DE_CAIDA:
                obsoleto = self._desde_cache(guardado, "obsoleto", exc.codigo)
                return self._servir(obsoleto, h, valores, aviso)
            raise
        if self.almacen is not None and sobre.estado != "parcial":
            await self.almacen.guardar(
                k,
                {"guardado_en": self.reloj(), "sobre": sobre.model_dump(mode="json")},
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
        self, h: Herramienta, fuente: Fuente, valores: dict[str, Any], fiel: bool = False
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
                {**valores, "url_fuente": fuente.url, "url_capa": f"{fuente.url}/{capa}"},
            )
            if fiel:
                argumentos["geometria"] = "completa"
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

        total = None
        principales = procedencia[len(previas) :]  # la previa no cuenta en el total
        if len(principales) == 1:
            total = principales[0].completitud.total
        elif all(p.completitud.total is not None for p in principales):
            total = sum(p.completitud.total or 0 for p in principales)
        # honestidad: la fuente dijo que hay `total` y no entregó ninguno (una página que llegó
        # vacía, un corte): eso es «no se pudo», nunca «no encontrado». Con SINCHI, el conector
        # contó 1 polígono y su página vino vacía; el sobre decía «no encontrado» (2026-10-28).
        if not elementos and not capas_incompletas and total and total > 0:
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
            nombre: redondear(derivar_resultado(d, elementos, total), d.decimales)
            for nombre, d in h.derivados.items()
            if not d.por_elemento
        }

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
        datos = {k: v for k, v in datos.items() if v is not None} if hay_algo else {}

        avisos: list[str] = [aviso_complemento] if aviso_complemento and hay_algo else []
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
        Sin ninguno, `{previa}` es `''`: la consulta principal no encuentra nada, y lo dice."""
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
        procedencia = self._procedencia(h, fuente, r, consultado_en, [hechos] if hechos else [])
        return hechos, procedencia

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
