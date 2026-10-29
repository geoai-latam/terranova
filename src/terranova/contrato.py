"""Contrato de respuesta `rt/1` (docs/specs/01-contrato-rt1.md).

Las reglas 1 a 9 de la spec (§6.2) se validan aquí mismo, así que un sobre que no las cumple no
se puede construir. La 10 (lista blanca) depende del catálogo: `fuera_de_lista_blanca`.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
import unicodedata
from datetime import UTC, datetime
from typing import Annotated, Any, Final, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

CONTRATO: Final = "rt/1"
MAX_TEXTO = 4000  # caracteres por campo de texto de la fuente (regla 9)

#: Parámetro común de las herramientas que pueden devolver geometría (ADR-0032).
GEOMETRIA = "geometria"
ESQUEMA_GEOMETRIA: Final[dict[str, Any]] = {
    "type": "boolean",
    "default": False,
    "description": "true: el polígono o la línea completa de cada elemento en geo_result (puede "
    "pesar cientos de KB). Sin él, cada uno sale como su envolvente (bbox); los puntos salen "
    "completos.",
}
AVISO_GEOMETRIA = (
    "Geometría resumida: cada polígono o línea va como su envolvente (bbox), con sus atributos en "
    "`datos` (`properties.elemento` es su posición). Pida `geometria: true` para la forma completa."
)
CRS_PERMITIDOS = ("EPSG:4326", "EPSG:9377")

Estado = Literal["encontrado", "no_encontrado", "fuera_de_cobertura", "parcial"]
ServidoDesde = Literal["fuente", "copia", "curado", "cache", "obsoleto"]
UsoComercial = Literal["si", "no", "por_verificar"]
CodigoError = Literal[
    "parametro_invalido",
    "zona_demasiado_grande",
    "no_autenticado",
    "sin_permiso",
    "licencia_no_habilitada",
    "no_existe",
    "saldo_agotado",
    "limite_tasa",
    "fuente_no_disponible",
    "fuente_respuesta_invalida",
    "fuente_lenta",
    "error_interno",
]
# §6.3: código → HTTP. Ningún error descuenta cuota.
HTTP_DE: dict[str, int] = {
    "parametro_invalido": 400,
    "zona_demasiado_grande": 400,
    "no_autenticado": 401,
    "sin_permiso": 403,
    "licencia_no_habilitada": 403,
    "no_existe": 404,
    "saldo_agotado": 402,  # ADR-0029: hay un plan que pagar; 429 queda para la tasa
    "limite_tasa": 429,
    "fuente_no_disponible": 502,
    "fuente_respuesta_invalida": 502,
    "fuente_lenta": 504,
    "error_interno": 500,
}

Huella = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
_BIDI = {"\u061c", "\u200e", "\u200f", *(chr(c) for c in range(0x202A, 0x202F))}
_BIDI |= {chr(c) for c in range(0x2066, 0x206A)}


class _Modelo(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Licencia(_Modelo):
    spdx: str = Field(description="Identificador SPDX o LicenseRef-…")
    url: str | None = None
    uso_comercial: UsoComercial


class Completitud(_Modelo):
    vistos: int = Field(ge=0)
    total: int | None = Field(ge=0, description="null si la fuente no dice cuántos hay")
    truncado: bool
    motivo: str | None = None

    @model_validator(mode="after")
    def _regla_4(self) -> Self:
        if self.total is None:
            return self
        if self.vistos > self.total:
            raise ValueError("regla 4: vistos > total")
        if self.truncado != (self.vistos < self.total):
            raise ValueError("regla 4: truncado debe ser (vistos < total)")
        return self


class Cache(_Modelo):
    acierto: bool
    edad_s: int = Field(ge=0)


class Procedencia(_Modelo):
    fuente_id: str = Field(pattern=r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")
    entidad: str
    acto: str | None = None
    url: str
    licencia: Licencia
    atribucion: str
    servido_desde: ServidoDesde
    consultado_en: AwareDatetime
    version_dataset: str | None = None
    consulta: dict[str, Any]
    completitud: Completitud
    cache: Cache
    transformaciones: list[str]
    conector: str
    huella: Huella = Field(description="sha256 de lo que aportó esta fuente a `datos`")


class ErrorParte(_Modelo):
    """Error de una fuente dentro de un sobre `parcial` (regla 5)."""

    codigo: CodigoError
    fuente_id: str
    detalle: str
    reintentar_en_s: int | None = Field(default=None, ge=0)


class ZonaUsada(_Modelo):
    tipo: Literal["punto", "bbox", "poligono", "divipola", "codigo"]
    valor: Any
    crs: Literal["EPSG:4326", "EPSG:9377"] | None = None
    # Regla 11: con un código DIVIPOLA, el lugar con su nombre. Un agente que supuso el código
    # (05380 por Granada) ve que el dato es de La Estrella, no de Granada (F6, GEO Copilot).
    nombre: str | None = None


class Artefacto(BaseModel):
    """Un artefacto de `GeoResult` v1. Se valida lo que el contrato exige; el resto pasa igual."""

    model_config = ConfigDict(extra="allow", frozen=True)

    kind: str
    name: str | None = None
    crs: str | None = None
    data: Any = None


class GeoResult(_Modelo):
    geo_result: Literal["1"] = "1"
    artifacts: list[Artefacto]
    facts: dict[str, Any] = Field(default_factory=dict)
    style_hint: dict[str, Any] | None = None


class Sobre(_Modelo):
    contrato: Literal["rt/1"] = "rt/1"
    solicitud_id: str = Field(pattern=r"^req_[0-9A-Za-z]{10,40}$")
    herramienta: str = Field(pattern=r"^[a-z][a-z0-9_]*@[1-9][0-9]*$")
    estado: Estado
    entrada: dict[str, Any]
    zona_usada: ZonaUsada | None
    datos: dict[str, Any]
    huella: Huella = Field(description="sha256 del JSON canónico de `datos` (regla 7)")
    geo_result: GeoResult | None
    procedencia: list[Procedencia] = Field(min_length=1)
    avisos: list[str]
    errores: list[ErrorParte]
    creditos: int = Field(ge=0)

    @model_validator(mode="after")
    def _reglas(self) -> Self:
        # 2: fuera de cobertura no descuenta
        if self.estado == "fuera_de_cobertura" and self.creditos != 0:
            raise ValueError("regla 2: fuera_de_cobertura no descuenta créditos")
        # 3: toda fuente con error también está en procedencia
        ids = {p.fuente_id for p in self.procedencia}
        if faltan := {e.fuente_id for e in self.errores} - ids:
            raise ValueError(f"regla 3: fuentes con error sin procedencia: {sorted(faltan)}")
        # 4: total desconocido ⇒ aviso
        if any(p.completitud.total is None for p in self.procedencia) and not self.avisos:
            raise ValueError("regla 4: total desconocido sin aviso")
        # 5: parcial ⇔ hay errores (un fallo total es un error, no un sobre)
        if (self.estado == "parcial") != bool(self.errores):
            raise ValueError("regla 5: parcial exige errores y solo parcial los lleva")
        # 6: obsoleto ⇒ aviso
        if any(p.servido_desde == "obsoleto" for p in self.procedencia) and not self.avisos:
            raise ValueError("regla 6: servido_desde obsoleto sin aviso")
        # 7: huella de datos
        if self.huella != huella(self.datos):
            raise ValueError("regla 7: huella no corresponde a datos")
        # 8: geometría en EPSG:4326 (lon, lat); 9377 solo si se pidió
        if self.geo_result is not None:
            pedido = self.entrada.get("crs_salida", "EPSG:4326")
            for art in self.geo_result.artifacts:
                if art.kind in ("feature_collection", "feature_ref") and art.crs != pedido:
                    raise ValueError(f"regla 8: artefacto en {art.crs}, se esperaba {pedido}")
                if art.kind == "feature_collection" and pedido == "EPSG:4326":
                    _coordenadas_lon_lat(art.data)
        # 9: texto de la fuente limpio y acotado, en datos y en las propiedades de la capa
        _texto_limpio(self.datos, "datos")
        if self.geo_result is not None:
            for art in self.geo_result.artifacts:
                for rasgo in (
                    (art.data or {}).get("features", []) if isinstance(art.data, dict) else []
                ):
                    _texto_limpio(rasgo.get("properties") or {}, "geo_result.properties")
        return self


class Problema(_Modelo):
    """Error total (RFC 9457): REST `application/problem+json`; MCP `isError` con este objeto."""

    type: str = "about:blank"
    title: str
    status: int
    code: CodigoError
    detail: str | None = None
    param: str | None = None
    fuente_id: str | None = None
    reintentar_en_s: int | None = Field(default=None, ge=0)
    solicitud_id: str = Field(pattern=r"^req_[0-9A-Za-z]{10,40}$")

    @model_validator(mode="after")
    def _http_del_codigo(self) -> Self:
        if self.status != HTTP_DE[self.code]:
            raise ValueError(f"{self.code} es HTTP {HTTP_DE[self.code]}, no {self.status}")
        if self.code == "parametro_invalido" and not self.param:
            raise ValueError("parametro_invalido debe nombrar el parámetro")
        return self


def huella(datos: dict[str, Any]) -> str:
    """sha256 del JSON canónico (claves ordenadas, sin espacios, UTF-8)."""
    canonico = json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonico.encode()).hexdigest()


def _rango(desde: int, hasta: int) -> str:
    return chr(desde) if desde == hasta else f"{chr(desde)}-{chr(hasta)}"


# La misma regla que `texto_es_limpio`, como patrón publicable en el OpenAPI (JSON Schema y el motor
# de pydantic): control salvo salto de línea y tabulador, y marcas bidi. Con caracteres literales,
# no escapes, para que los dos motores lo lean igual. Schemathesis manda texto con control y
# espera que el esquema lo diga.
PATRON_TEXTO_LIMPIO = (
    "^[^"
    + _rango(0x00, 0x08)
    + _rango(0x0B, 0x1F)
    + _rango(0x7F, 0x9F)
    + "".join(sorted(_BIDI))
    + "]*$"
)


def texto_es_limpio(texto: str) -> bool:
    """Sin caracteres de control (salvo salto de línea y tabulador) ni marcas bidi."""
    for c in texto:
        if c in _BIDI:
            return False
        if unicodedata.category(c) == "Cc" and c not in "\n\t":
            return False
    return True


def fuera_de_lista_blanca(sobre: Sobre, campos: set[str]) -> set[str]:
    """Regla 10: campos de `datos` o de las propiedades de la capa que el catálogo no declara."""
    extra = set(sobre.datos) - campos
    if sobre.geo_result is not None:
        for art in sobre.geo_result.artifacts:
            if isinstance(art.data, dict):
                for rasgo in art.data.get("features", []):
                    extra |= set(rasgo.get("properties") or {}) - campos
    return extra


def _texto_limpio(valor: Any, ruta: str) -> None:
    if isinstance(valor, str):
        if len(valor) > MAX_TEXTO:
            raise ValueError(f"regla 9: {ruta} supera {MAX_TEXTO} caracteres")
        if not texto_es_limpio(valor):
            raise ValueError(f"regla 9: {ruta} trae caracteres de control o bidi")
    elif isinstance(valor, dict):
        for k, v in valor.items():
            _texto_limpio(k, f"{ruta}.<clave>")
            _texto_limpio(v, f"{ruta}.{k}")
    elif isinstance(valor, list):
        for i, v in enumerate(valor):
            _texto_limpio(v, f"{ruta}[{i}]")


def _coordenadas_lon_lat(fc: Any) -> None:
    def recorrer(c: Any) -> None:
        if isinstance(c, list) and len(c) >= 2 and all(isinstance(x, int | float) for x in c[:2]):
            lon, lat = c[0], c[1]
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError(f"regla 8: coordenada fuera de lon/lat: {c[:2]}")
        elif isinstance(c, list):
            for x in c:
                recorrer(x)

    if not isinstance(fc, dict):
        return
    for rasgo in fc.get("features", []):
        geometria = rasgo.get("geometry") or {}
        recorrer(geometria.get("coordinates"))


def resumir_geometria(sobre: Sobre) -> Sobre:
    """Cada polígono o línea de `geo_result` como su envolvente, con `geometry: null` y `bbox`
    (RFC 7946 §5); los puntos quedan. Un polígono pesa de 20 a 300 KB y los clientes MCP no se lo
    pasan al modelo: Claude Code lo manda a un archivo y el agente no ve los datos (ADR-0032).
    Las propiedades repiten un elemento de `datos`: van como su posición (`elemento`), que con
    169 áreas protegidas era otro 60 % del sobre. `datos` y la huella no cambian."""
    if sobre.geo_result is None:
        return sobre
    elementos = sobre.datos.get("elementos")
    lista = elementos if isinstance(elementos, list) else [sobre.datos]
    artefactos, resumido = [], False
    for art in sobre.geo_result.artifacts:
        datos = art.data
        if art.kind == "feature_collection" and isinstance(datos, dict):
            rasgos = []
            for rasgo in datos.get("features", []):
                g = rasgo.get("geometry")
                if isinstance(g, dict) and g.get("type") not in ("Point", "MultiPoint"):
                    caja = _envolvente(g.get("coordinates"))
                    rasgo = {**rasgo, "geometry": None} | ({"bbox": caja} if caja else {})
                    posicion = next(
                        (i for i, e in enumerate(lista) if e == rasgo.get("properties")), None
                    )
                    if posicion is not None:
                        rasgo["properties"] = {"elemento": posicion}
                    resumido = True
                rasgos.append(rasgo)
            datos = {**datos, "features": rasgos}
        artefactos.append(art.model_copy(update={"data": datos}))
    if not resumido:
        return sobre
    geo = sobre.geo_result.model_copy(update={"artifacts": artefactos})
    return sobre.model_copy(update={"geo_result": geo, "avisos": [*sobre.avisos, AVISO_GEOMETRIA]})


def _envolvente(coordenadas: Any) -> list[float] | None:
    xs: list[float] = []
    ys: list[float] = []

    def recorrer(c: Any) -> None:
        if isinstance(c, list) and len(c) >= 2 and all(isinstance(x, int | float) for x in c[:2]):
            xs.append(float(c[0]))
            ys.append(float(c[1]))
        elif isinstance(c, list):
            for x in c:
                recorrer(x)

    recorrer(coordenadas)
    return [min(xs), min(ys), max(xs), max(ys)] if xs else None


def nueva_solicitud_id() -> str:
    """`req_` + 26 caracteres ordenables por tiempo (ms en base 32 Crockford + aleatorio)."""
    alfabeto = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    n = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    return "req_" + "".join(alfabeto[(n >> (5 * i)) & 31] for i in reversed(range(26)))


def ahora() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)
