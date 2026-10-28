"""Catálogo como código (ADR-0007, spec 02): una ficha YAML por fuente y una por herramienta.

`cargar()` lee `catalogo/` y `validar()` aplica las reglas que cruzan fichas. Un catálogo inválido
rompe el CI (`scripts/check.py`).
"""

from __future__ import annotations

import difflib
import functools
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

RAIZ = Path(__file__).resolve().parents[2] / "catalogo"

#: Nombre de campo que delata la cédula de una persona natural (ADR-0014). Solo las personas
#: naturales tienen «cédula»; las empresas (nit, razón social) se permiten, y un documento genérico
#: que a veces es cédula va con nombre `documento_…` (ADR-0025), no `cedula`.
PATRON_CEDULA = re.compile(r"c[eé]dula")
ID_FUENTE = r"^[a-z0-9_]+(\.[a-z0-9_]+)+$"
ID_HERRAMIENTA = r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$"
DURACION_ISO = r"^P(?:\d+[YMWD])+(?:T(?:\d+[HMS])+)?$|^PT(?:\d+[HMS])+$"

# Créditos por tipo de pregunta (ADR-0010, enmienda del 2026-10-27): el cliente paga por lo que
# pregunta, no por cómo la puerta lo trae; pasar una fuente a copia no cambia su precio.
Cobro = Literal["codigo", "registro", "agregado", "punto", "zona"]
TARIFA: dict[str, int] = {
    "codigo": 1,  # de nombre a código y buscador del catálogo
    "registro": 2,  # un registro o una serie simple (por id, NIT, código)
    "agregado": 5,  # agregados o búsqueda de texto (por municipio, por año)
    "punto": 10,  # espacial en un punto
    "zona": 20,  # espacial en una zona o ráster
}

# Tipos de entrada. Los que tienen patrón los valida la puerta antes de llamar; solo esos y los
# numéricos se pueden meter dentro de un texto de la consulta (un `where`): un `str` libre ahí sería
# inyección SQL/SoQL.
PATRONES_ENTRADA: dict[str, str] = {
    "codigo_predial": r"^[0-9]{30}$",
    # el código, o el nombre del municipio (con «, departamento» si hace falta): la puerta lo
    # convierte en el código antes de la consulta, así que a la fuente siempre llegan 5 dígitos
    "divipola": r"^([0-9]{5}|[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .,-]{0,99})$",
    "id_secop": r"^CO1\.[A-Z]+\.[0-9]+$",
    "constancia_secop": r"^[0-9]{2}-[0-9]{1,2}-[0-9]+$",  # SECOP I: 19-12-10176235
    "contrato_secop": r"^(CO1\.[A-Z]+\.[0-9]+|[0-9]{2}-[0-9]{1,2}-[0-9]+)$",  # SECOP II o I
    "fecha": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
    "sentencia_cc": r"^(C|T|SU)-[0-9]{1,4}/[0-9]{2}$",  # Corte Constitucional: T-760/08
    # en la URL de la relatoría: T-760-08 (sin «/»: nada de rutas)
    "sentencia_relatoria": r"^(C|T|SU)-[0-9]{1,4}-[0-9]{2}$",
    # documento de un gestor normativo (decreto_1165_2019): sin «/» ni «.», nada de rutas
    "documento_normativo": r"^[a-z][a-z0-9_-]{2,60}_[0-9]{4}$",
    # NIT de persona jurídica (empieza por 8 o 9): buscar por cédula queda fuera (ADR-0014)
    "nit_empresa": r"^[89][0-9]{8}$",
    "codigo_dane_sede": r"^[0-9]{12}$",  # sede educativa (DANE): 125175000493
    "matricula_inmobiliaria": r"^[0-9A-Z]{2,4}-[0-9]{1,10}$",  # folio de matrícula: 50N-20849403
    "bpin": r"^[0-9]{13,14}$",  # proyecto del Banco de Proyectos (DNP): 2013157610001
    "nombre": r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .-]{0,79}$",
    # expediente de título minero (ANM): mayúsculas, dígitos y guion; sin comillas ni espacios
    "expediente_minero": r"^[A-Z0-9][A-Z0-9-]{3,19}$",
    # código SIGEP de la entidad (Función Pública): dígitos, con posible cero inicial (0870)
    "codigo_sigep": r"^[0-9]{1,6}$",
    # subpartida arancelaria NANDINA de 10 dígitos (comercio exterior DANE/DIAN): 8517130000
    "subpartida": r"^[0-9]{10}$",
    # año de cuatro dígitos (2000 a 2099)
    "anio": r"^20[0-9]{2}$",
}
# Qué forma lleva cada tipo con patrón, con un ejemplo válido: el agente lo lee en el esquema de la
# herramienta. Sin esto, uno leyó en la ficha técnica «DIVIPOLA seguido de 000» y mandó 25175000.
FORMAS_ENTRADA: dict[str, tuple[str, str]] = {
    "codigo_predial": ("número predial nacional de 30 dígitos", "251750000000000050067000000000"),
    "divipola": (
        "código DIVIPOLA del municipio (5 dígitos, con el cero inicial) o su nombre; si varios se "
        "llaman igual, con el departamento: «San Andrés, Santander»",
        "25175",
    ),
    "id_secop": ("identificador de SECOP II", "CO1.PCCNTR.5141215"),
    "constancia_secop": ("número de constancia de SECOP I", "19-12-10176235"),
    "contrato_secop": ("identificador de SECOP II o constancia de SECOP I", "CO1.PCCNTR.5141215"),
    "fecha": ("fecha AAAA-MM-DD", "2026-10-23"),
    "sentencia_cc": ("sentencia de la Corte Constitucional, tipo-número/año", "T-760/08"),
    "sentencia_relatoria": ("sentencia como la escribe la relatoría, con guiones", "T-760-08"),
    "documento_normativo": ("documento del gestor normativo, tipo_número_año", "decreto_1165_2019"),
    "nit_empresa": ("NIT de la empresa, 9 dígitos sin dígito de verificación", "899999714"),
    "codigo_dane_sede": ("código DANE de la sede educativa, 12 dígitos", "125175000493"),
    "matricula_inmobiliaria": ("folio de matrícula: oficina, guion y número", "50N-20849403"),
    "bpin": ("código BPIN del proyecto, 13 o 14 dígitos", "2013157610001"),
    "nombre": ("nombre o parte de él: letras, espacios, puntos y guiones", "Bancolombia"),
    "expediente_minero": ("código de expediente del título minero (ANM)", "ABQ-101"),
    "codigo_sigep": ("código SIGEP de la entidad (Función Pública)", "6194"),
    "subpartida": ("subpartida arancelaria NANDINA de 10 dígitos", "8517130000"),
    "anio": ("año de cuatro dígitos", "2025"),
}

TipoEntrada = Literal[
    "float",
    "int",
    "str",
    "bool",
    "bbox",
    "geojson",
    "codigo_predial",
    "divipola",
    "id_secop",
    "constancia_secop",
    "contrato_secop",
    "fecha",
    "sentencia_cc",
    "sentencia_relatoria",
    "documento_normativo",
    "nit_empresa",
    "codigo_dane_sede",
    "matricula_inmobiliaria",
    "bpin",
    "nombre",
    "expediente_minero",
    "codigo_sigep",
    "subpartida",
    "anio",
]
SEGUROS_EN_TEXTO = frozenset({"int", "float", *PATRONES_ENTRADA})

Familia = Literal[
    "territorio",
    "contratacion",
    "empresas",
    "normativa",
    "justicia",
    "estadisticas",
    "ambiente",
    "meta",  # G6 (ADR-0026/0028): el buscador del catálogo, `catalogo_buscar`
]
UsoComercial = Literal["si", "no", "por_verificar"]
# ADR-0019 (enmienda 2026-10-26): clasificación de licencia por ítem.
#   verde  → licencia abierta verificada; sirve a todas las llaves.
#   ambar  → dato público reutilizable (Ley 1712/2014) con términos no verificados; sirve con
#            aviso (traslada a la fuente la responsabilidad de exactitud/uso). No cabe persona.
#   rojo   → bloqueado (persona, reserva legal o prohibición de redistribuir); no se publica.
ClasificacionLicencia = Literal["verde", "ambar", "rojo"]
# Aviso que acompaña cada respuesta de una fuente ámbar (modelo Superfinanciera Res.1519/2020).
AVISO_DATO_PUBLICO = (
    "Dato público reutilizable (Ley 1712/2014). La exactitud y vigencia son responsabilidad de la "
    "entidad fuente; verifique los términos para su uso específico. Terranova normaliza y entrega, "
    "no certifica."
)


class _Ficha(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LicenciaFuente(_Ficha):
    spdx: str | None
    url: str | None = None
    verificada: date | None = None
    evidencia: str | None = Field(default=None, description="URL de la evidencia primaria")
    cita: str | None = None

    @model_validator(mode="after")
    def _evidencia(self) -> Self:
        if self.verificada is not None and not (self.evidencia and self.cita):
            raise ValueError("una licencia verificada lleva evidencia (URL) y cita")
        return self


class Permiso(_Ficha):
    fecha: date
    evidencia: str = Field(description="radicado o documento del permiso escrito")


class Campo(_Ficha):
    nombre: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    tipo: Literal["str", "int", "float", "bool", "date", "datetime"]
    origen: Literal["fila", "hecho"] = Field(
        default="fila",
        description="fila: propiedad de cada elemento; hecho: dato del resultado (facts)",
    )
    desc: str
    codigos: dict[str, str] | None = Field(
        default=None, description="significado de cada código, cuando la fuente no lo publica"
    )
    codigos_norma: str | None = Field(
        default=None, description="la norma que define `codigos` (resolución, artículo, URL)"
    )
    coma_decimal: bool = Field(
        default=False,
        description="la fuente escribe el decimal con coma (-74,05): se declara por campo, porque "
        "en general «1,234» es ambiguo",
    )

    @model_validator(mode="after")
    def _codigos_con_norma(self) -> Self:
        if (self.codigos is None) != (self.codigos_norma is None):
            raise ValueError("spec 08: los códigos escritos a mano van con la norma que los define")
        return self


class Frescura(_Ficha):
    ttl_cache_s: int = Field(ge=0)
    sla_actualizacion: str = Field(pattern=DURACION_ISO)


class Cobertura(_Ficha):
    pais: str = Field(pattern=r"^([A-Z]{2}|GLOBAL)$")
    excluye: list[str] = Field(default_factory=list)
    indice: str | None = None
    columna_tiempo: str | None = Field(
        default=None,
        description="columna de la lista blanca que fecha cada fila: su mínimo y máximo cosechados "
        "son los años que cubre la fuente (spec 08)",
    )
    periodo: str | None = Field(
        default=None, description="años que cubre, escritos a mano cuando no hay columna (spec 08)"
    )


class Comportamiento(_Ficha):
    p95_ms_medido: int | None = Field(default=None, ge=0)
    max_por_pagina: int | None = Field(default=None, ge=1)
    orden_coordenadas: Literal["lon_lat", "lat_lon"] = "lon_lat"
    # Medido en la fuente: a veces responde vacío sin error (la ANT por utility.arcgis.com, ~25 %).
    # Antes de decir «no encontrado» se vuelve a preguntar: «no se pudo» no es «no hay».
    reintentos_si_vacio: int = Field(default=0, ge=0, le=3)


IDENTIFICADOR_SQL = r"^[a-z][a-z0-9_]{0,40}$"
OPERACIONES_PERFIL = ("filtrar", "contar", "ordenar", "agrupar")


class ClavePerfil(_Ficha):
    columna: str
    unica: bool = Field(description="filas = valores distintos en la muestra medida")


class Perfil(_Ficha):
    """Lo medido en la fuente antes de diseñar sus herramientas (spec 07)."""

    medido: date
    fila: str = Field(min_length=10, description="qué representa una fila, con un ejemplo medido")
    clave: ClavePerfil | None = None
    operaciones: dict[str, float | None] = Field(
        default_factory=dict, description="segundos por operación; None = no responde en 300 s"
    )
    hallazgos: list[str] = Field(default_factory=list)
    decision: str = Field(min_length=5)

    @model_validator(mode="after")
    def _operaciones_conocidas(self) -> Self:
        if sueltas := set(self.operaciones) - set(OPERACIONES_PERFIL):
            raise ValueError(f"operaciones desconocidas en el perfil: {sorted(sueltas)}")
        return self


class Ventana(_Ficha):
    """Qué parte de la fuente se copia: las filas con `columna` desde `desde` (ADR-0024)."""

    columna: str
    desde: date


class Copia(_Ficha):
    """Cómo se copia una fuente a PostGIS (G3, ADR-0024): solo las columnas de `campos`."""

    origen: Literal["socrata", "zip_dane", "arcgis", "conector"]
    conjunto: str | None = Field(
        default=None,
        pattern=r"^[a-z0-9]{4}-[a-z0-9]{4}$",
        description="id en datos.gov.co (socrata)",
    )
    descargas: list[str] = Field(
        default_factory=list, description="URLs de los ZIP a copiar y pre-agregar (origen zip_dane)"
    )
    # Mapeo del microdato de comercio exterior del DANE (origen zip_dane): se pre-agrega a
    # (año, mes, subpartida, país) sumando las medidas. Las columnas del CSV difieren impo/expo.
    subpartida_csv: str | None = Field(
        default=None, description="columna CSV de la subpartida NANDINA (NABAN impo, POSAR expo)"
    )
    pais_csv: str | None = Field(
        default=None, description="columna CSV del país (PAISGEN impo, PAIS expo)"
    )
    pais_col: str | None = Field(
        default=None,
        description="columna de la lista blanca para el país (pais_origen/pais_destino)",
    )
    medidas: dict[str, str] = Field(
        default_factory=dict,
        description="medidas a sumar: {columna de la lista blanca: columna del CSV}",
    )
    # Capa de un servicio ArcGIS (origen arcgis): se copia con su geometría, en EPSG:4326, a una
    # columna `_geom` con índice espacial; `consultar_copia` la cruza con un punto o un bbox.
    capa: int | None = Field(default=None, ge=0, description="capa del servicio (origen arcgis)")
    geometria: bool = Field(
        default=True,
        description="copiar la geometría (origen arcgis); sin ella, solo los atributos: p. ej. los "
        "totales del censo por municipio, que se consultan por código",
    )
    por_pagina: int = Field(
        default=500, ge=1, le=2000, description="elementos por petición (polígonos pesados: menos)"
    )
    tolerancia: float | None = Field(
        default=None,
        gt=0,
        le=0.001,
        description="simplificación al copiar, en grados (maxAllowableOffset; 0,0001 ≈ 11 m): "
        "solo si la escala de la fuente es más gruesa que eso",
    )
    # Lo que un conector MCP lee de la fuente (origen conector), entero y tal cual lo sirve en vivo:
    # p. ej. una hoja de un xlsx del DANE por `web_tabla`, sin filtros. Así la copia no duplica el
    # lector de la fuente. `{url_fuente}` en los argumentos se cambia por la `url` de la ficha.
    conector: str | None = Field(
        default=None, description="conector MCP que lee la fuente (origen conector)"
    )
    tool: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="tool del conector (origen conector)",
    )
    argumentos: dict[str, Any] = Field(
        default_factory=dict, description="argumentos de la tool, sin filtros (origen conector)"
    )
    tabla: str = Field(pattern=IDENTIFICADOR_SQL, description="nombre de la vista en `copia.`")
    clave: str = Field(
        description="columna única y estable: ordena las páginas y la huella (`_fila`: el orden "
        "de la fila en lo que dio el conector, para tablas sin columna única)"
    )
    ventana: Ventana | None = None
    indices: list[str] = Field(default_factory=list)
    texto: list[str] = Field(
        default_factory=list, description="columnas de la búsqueda de texto completo (español)"
    )

    @model_validator(mode="after")
    def _origen_coherente(self) -> Copia:
        if self.origen == "socrata" and not self.conjunto:
            raise ValueError("ADR-0024: origen `socrata` exige `conjunto` (id datos.gov.co)")
        if (self.origen == "arcgis") != (self.capa is not None):
            raise ValueError("ADR-0024: `capa` va con el origen `arcgis` (y solo con él)")
        if self.tolerancia is not None and not (self.origen == "arcgis" and self.geometria):
            raise ValueError("ADR-0024: `tolerancia` solo aplica a una capa ArcGIS con geometría")
        if not self.geometria and self.origen != "arcgis":
            raise ValueError("ADR-0024: `geometria: false` solo aplica a una capa ArcGIS")
        lee_conector = (self.conector is not None, self.tool is not None)
        if lee_conector != ((self.origen == "conector"),) * 2:
            raise ValueError(
                "ADR-0024: `conector` y `tool` van con el origen `conector` (y solo con él)"
            )
        if self.argumentos and self.origen != "conector":
            raise ValueError("ADR-0024: `argumentos` solo aplica al origen `conector`")
        if "filtros" in self.argumentos:
            raise ValueError(
                "ADR-0024: la copia es la fuente entera; los filtros van en la herramienta"
            )
        if self.origen == "zip_dane":
            if not self.descargas:
                raise ValueError("ADR-0024: origen `zip_dane` exige `descargas` (URLs de los ZIP)")
            faltan = [
                c for c in ("subpartida_csv", "pais_csv", "pais_col") if getattr(self, c) is None
            ]
            if faltan or not self.medidas:
                raise ValueError(
                    "ADR-0024: origen `zip_dane` exige subpartida_csv, pais_csv, pais_col y "
                    f"medidas (faltan: {faltan or ['medidas']})"
                )
        return self

    @property
    def espacial(self) -> bool:
        """Lleva geometría (`_geom`): se puede cruzar con un punto o un bbox."""
        return self.origen == "arcgis" and self.geometria

    @property
    def columnas_usadas(self) -> set[str]:
        ventana = {self.ventana.columna} if self.ventana else set()
        extra = set(self.medidas) | ({self.pais_col} if self.pais_col else set())
        return {self.clave, *ventana, *self.indices, *self.texto, *extra}


Geometria = Literal["punto", "multipunto", "linea", "poligono", "raster"]


class Geografia(_Ficha):
    """Lo geográfico de la fuente, tal como lo declara su servicio (spec 08)."""

    geometria: Geometria
    crs: str | None = Field(default=None, description="EPSG:… del servicio")
    extension: list[float] | None = Field(
        default=None, min_length=4, max_length=4, description="[oeste, sur, este, norte] EPSG:4326"
    )
    capas: dict[int, str] = Field(default_factory=dict, description="capa → nombre en el servicio")
    resolucion_m: float | None = Field(
        default=None,
        gt=0,
        description="tamaño de la celda o del píxel, en metros (raster y mallas)",
    )


class CampoDeLaFuente(_Ficha):
    """Una columna de la lista blanca según la fuente: su tipo, su texto y lo que contiene."""

    tipo_fuente: str
    etiqueta: str | None = None
    descripcion: str | None = None
    nulos: int | None = Field(default=None, ge=0)
    minimo: str | None = None
    maximo: str | None = None
    comparacion: Literal["numero", "texto", "fecha"] | None = Field(
        default=None, description="cómo se ordenan mínimo y máximo: en texto, «99» > «500»"
    )
    valores: dict[str, int] | None = Field(
        default=None, description="valores más frecuentes (solo categorías sin datos de personas)"
    )
    codigos: dict[str, str] | None = Field(default=None, description="dominio de la fuente")


class Metadatos(_Ficha):
    """Ficha técnica (spec 08): lo que la fuente dice de sí misma, cosechado por
    `scripts/cosechar_metadatos.py` en `catalogo/metadatos/<fuente>.yaml`. No se edita a mano;
    lo que la fuente no dice va en la ficha de la fuente (perfil, campos, cobertura)."""

    fuente: str = Field(pattern=ID_FUENTE)
    metodo: Literal["cosechado", "manual"]
    cosechado: date
    origen: str = Field(pattern=r"^https://", description="de dónde salió esta ficha técnica")
    pagina: str | None = Field(default=None, description="página de la fuente para personas")
    titulo: str | None = None
    descripcion: str | None = None
    publicado: date | None = None
    datos_actualizados: date | None = Field(
        default=None, description="última vez que cambiaron los datos, según la fuente"
    )
    frecuencia_declarada: str | None = None
    cobertura_declarada: str | None = None
    corte: str | None = Field(default=None, description="corte de la información, si lo declara")
    idioma: str | None = None
    categoria: str | None = None
    etiquetas: list[str] = Field(default_factory=list)
    filas: int | None = Field(default=None, ge=0)
    geografia: Geografia | None = None
    campos: dict[str, CampoDeLaFuente] = Field(default_factory=dict)


class Fuente(_Ficha):
    id: str = Field(pattern=ID_FUENTE)
    titulo: str
    entidad: str
    competencia: str | None = None
    acto: str | None = None
    licencia: LicenciaFuente
    uso_comercial: UsoComercial
    clase_acceso: Literal["api", "bulk", "html_publico", "interno_con_permiso"]
    permiso: Permiso | None = None
    atribucion: str
    protocolo: Literal[
        "arcgis_rest", "wfs", "wms", "socrata", "ckan", "stac", "api_propia", "archivo", "html"
    ]
    conector: str
    url: str = Field(pattern=r"^https://")
    modo: Literal["en_vivo", "copia", "curado"]
    copia: Copia | None = None
    perfil: Perfil | None = None
    frescura: Frescura
    cobertura: Cobertura
    datos_personales: Literal["ninguno", "filtrados", "presentes"]
    estado: Literal["borrador", "publicada"]
    clasificacion_licencia: ClasificacionLicencia = Field(
        default="verde",
        description="ADR-0019 (enmienda): verde=licencia abierta verificada; ambar=dato público "
        "reutilizable, términos no verificados, sirve con aviso; rojo=bloqueado (persona, reserva "
        "legal o prohibición expresa), no se publica.",
    )
    campos: dict[str, Campo] = Field(
        min_length=1, description="lista blanca: campo de la fuente → rt/1"
    )
    comportamiento: Comportamiento = Field(default_factory=Comportamiento)
    capas_servicio: list[int] = Field(
        default_factory=list,
        description="capas ArcGIS que consulta un conector propio (las de las herramientas ya se "
        "saben): la ficha técnica las cosecha (spec 08)",
    )
    dcat: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _reglas(self) -> Self:
        clf = self.clasificacion_licencia
        if clf == "rojo" and self.estado != "borrador":
            raise ValueError(
                "ADR-0019 (enmienda): una fuente roja (persona, reserva legal o prohibición "
                "expresa de redistribuir) no se publica; déjala en borrador"
            )
        if clf == "ambar":
            # Dato público reutilizable (Ley 1712/2014): sirve sin SPDX verificado, con aviso.
            # Queda exenta de ADR-0007 (licencia verificada), pero NO de la línea roja de personas.
            if self.uso_comercial != "si":
                raise ValueError(
                    "ADR-0019 (enmienda): una fuente ámbar es dato público reutilizable, "
                    "uso_comercial es «si» (el aviso traslada la responsabilidad de uso)"
                )
            if self.datos_personales == "presentes":
                raise ValueError(
                    "ADR-0014: datos personales presentes no caben en ámbar; esa fuente es roja"
                )
        else:  # verde (o rojo en borrador): reglas clásicas de ADR-0019/0007
            if self.licencia.spdx is None and self.uso_comercial != "por_verificar":
                raise ValueError("ADR-0019: sin licencia conocida, la fuente es ámbar o rojo")
            if self.uso_comercial != "por_verificar" and self.licencia.verificada is None:
                raise ValueError("ADR-0007: uso_comercial decidido exige licencia verificada")
        if self.clase_acceso == "interno_con_permiso" and self.permiso is None:
            raise ValueError("ADR-0018: un backend interno exige el permiso escrito")
        if self.estado == "publicada" and self.datos_personales == "presentes":
            raise ValueError("ADR-0014: una fuente con datos personales presentes no se publica")
        cedulas = [c.nombre for c in self.campos.values() if PATRON_CEDULA.search(c.nombre)]
        if cedulas:
            # ADR-0014: una cédula de persona natural no sale como campo de la lista blanca. Si la
            # fuente la trae dentro de un documento (SECOP), va con nombre genérico (`documento_…`,
            # ADR-0025), no `cedula`. El resto (empresas: nit, razón social, nombres) se permite.
            raise ValueError(
                f"ADR-0014: campo de cédula de persona natural en la lista blanca: {cedulas}"
            )
        if self.cobertura.columna_tiempo and self.cobertura.columna_tiempo not in self.campos:
            raise ValueError("spec 08: cobertura.columna_tiempo no está en la lista blanca")
        if (self.modo == "copia") != (self.copia is not None):
            raise ValueError("ADR-0024: `modo: copia` va con su bloque `copia:` (y solo con él)")
        if self.copia is not None and (sueltas := self.copia.columnas_usadas - set(self.campos)):
            raise ValueError(f"ADR-0024: la copia usa columnas no listadas: {sorted(sueltas)}")
        nombres = [c.nombre for c in self.campos.values()]
        if len(nombres) != len(set(nombres)):
            raise ValueError("dos campos de la fuente van al mismo nombre rt/1")
        return self

    @property
    def nombres_rt(self) -> set[str]:
        return {c.nombre for c in self.campos.values()}


MARCADOR = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
MARCADORES_DE_LA_PUERTA = frozenset({"url_capa", "url_fuente"})


class Consulta(_Ficha):
    """Cómo se responde la pregunta con un conector. El ejecutor (F2.1) la sigue tal cual.

    `argumentos` es una plantilla: `{lon}` toma la entrada `lon` y conserva su tipo si el valor es
    solo el marcador; `{url_capa}` es la url de la fuente + `/<capa>` (una llamada por capa) y
    `{url_fuente}`, la url de la fuente.
    """

    operacion: Literal["en_punto", "en_zona", "por_codigo", "buscar", "serie"]
    resultado: Literal["uno", "lista"] | None = Field(
        default=None,
        description="uno: `datos` es el primer elemento; lista: `datos.elementos`. Por defecto, "
        "uno para en_punto/por_codigo y lista para el resto",
    )
    tool: str = Field(pattern=r"^[a-z][a-z0-9_]*$", description="herramienta del conector")
    filas_en: str | None = Field(
        default=None,
        description="ruta (con puntos) de la lista de elementos cuando no vienen como capa ni "
        "tabla, p. ej. `clases` o `facts.municipios`",
    )
    completo_por_construccion: bool = Field(
        default=False,
        description="resumen completo (ráster, serie): no hay «vistos de un total»",
    )
    capas: list[int | str] = Field(default_factory=list)
    argumentos: dict[str, Any]
    campos: list[str] = Field(min_length=1, description="campos de la fuente que se piden")

    @property
    def marcadores(self) -> set[str]:
        return set(MARCADOR.findall(json.dumps(self.argumentos, ensure_ascii=False)))

    @property
    def forma(self) -> Literal["uno", "lista"]:
        if self.resultado is not None:
            return self.resultado
        return "uno" if self.operacion in ("en_punto", "por_codigo") else "lista"


# Vocabulario cerrado de campos que calcula la puerta (ADR-0012: nada de código suelto por fuente).
DE_ELEMENTO = frozenset({"capa", "prefijo", "columna", "codigo"})
DE_RESULTADO = frozenset({"conteo", "suma", "maximo", "primero", "completitud_total"})


class Derivado(_Ficha):
    """Un campo `rt/1` que no viene tal cual de la fuente.

    Por elemento: `capa` (valor según la capa que respondió, `valores`), `prefijo` (los `n`
    primeros caracteres de `campo`, ya en nombre rt/1) y `columna` (una columna cruda del
    resultado, p. ej. un alias de un `select` agregado) y `codigo` (el significado de un código
    de `campo`, ya en nombre rt/1, según `valores`: p. ej. el nombre oficial del departamento
    por su código DIVIPOLA). Del resultado: `conteo`, `suma` y
    `maximo` de `campo`, `primero` (el `campo` del primer elemento) y `completitud_total` (el
    total que dio la fuente).
    """

    de: Literal[
        "capa",
        "prefijo",
        "columna",
        "codigo",
        "conteo",
        "suma",
        "maximo",
        "primero",
        "completitud_total",
    ]
    campo: str | None = None
    n: int | None = Field(default=None, ge=1)
    valores: dict[str, str] | None = None
    tipo: Literal["str", "int", "float", "bool", "date", "datetime"] = "str"

    @model_validator(mode="after")
    def _completo(self) -> Self:
        necesita_campo = {"prefijo", "columna", "codigo", "suma", "maximo", "primero"}
        if self.de in necesita_campo and not self.campo:
            raise ValueError(f"un derivado «{self.de}» necesita `campo`")
        if self.de == "prefijo" and self.n is None:
            raise ValueError("un derivado «prefijo» necesita `n`")
        if self.de == "capa" and not self.valores:
            raise ValueError("un derivado «capa» necesita `valores` (capa → valor)")
        if self.de == "codigo" and not self.valores:
            raise ValueError("un derivado «codigo» necesita `valores` (código → significado)")
        return self

    @property
    def por_elemento(self) -> bool:
        return self.de in DE_ELEMENTO


class Canario(_Ficha):
    """Verdad medida en la fuente. `verdad` es exacta; `minimos` (≥) sirve para lo que solo crece
    (contratos de un municipio); un dato que cambia sin dirección necesita una entrada fija."""

    entrada: dict[str, Any]
    verdad: dict[str, Any] = Field(default_factory=dict)
    minimos: dict[str, float] = Field(default_factory=dict)
    # los que trae la respuesta grabada (`scripts/campos_canario.py`); si uno deja de llegar, la
    # fuente cambió su esquema (F7.3)
    campos: list[str] = Field(default_factory=list)
    latencia_max_ms: int = Field(ge=1)

    @model_validator(mode="after")
    def _algo_que_comprobar(self) -> Self:
        if not self.verdad and not self.minimos:
            raise ValueError("el canario necesita verdad o minimos")
        if comunes := set(self.verdad) & set(self.minimos):
            raise ValueError(f"campos a la vez en verdad y minimos: {sorted(comunes)}")
        return self


class Herramienta(_Ficha):
    id: str = Field(pattern=ID_HERRAMIENTA)
    version: int = Field(ge=1)
    familia: Familia
    fuente: str = Field(pattern=ID_FUENTE)
    pregunta: str
    descripcion: str
    entrada: dict[str, TipoEntrada] = Field(min_length=1)
    consulta: Consulta
    salida: str
    derivados: dict[str, Derivado] = Field(
        default_factory=dict, description="campos rt/1 que calcula la puerta"
    )
    cobro: Cobro
    canario: Canario

    @property
    def creditos(self) -> int:
        return TARIFA[self.cobro]

    @model_validator(mode="after")
    def _propias(self) -> Self:
        if set(self.canario.entrada) != set(self.entrada):
            raise ValueError("la entrada del canario no coincide con la de la herramienta")
        # lo espacial se cobra como espacial y nada más (un ráster en un punto cuenta como zona)
        espacial = {"en_punto": {"punto", "zona"}, "en_zona": {"zona"}}
        permitidos = espacial.get(self.consulta.operacion, {"codigo", "registro", "agregado"})
        if self.cobro not in permitidos:
            raise ValueError(
                f"cobro «{self.cobro}» no corresponde a la operación {self.consulta.operacion}: "
                f"uno de {sorted(permitidos)}"
            )
        return self


_CIERRE = re.compile(r"\(Fuente: (?P<fuente>[^;]+); licencia: (?P<licencia>[^)]+)\.\)\s*$")


class Catalogo(BaseModel):
    fuentes: dict[str, Fuente]
    herramientas: dict[str, Herramienta]
    coberturas: set[str] = Field(default_factory=set, description="índices en catalogo/cobertura/")
    metadatos: dict[str, Metadatos] = Field(
        default_factory=dict, description="ficha técnica por fuente (spec 08), catalogo/metadatos/"
    )


class CatalogoInvalido(Exception):
    def __init__(self, errores: list[str]) -> None:
        super().__init__("\n".join(errores))
        self.errores = errores


def cargar(raiz: Path = RAIZ) -> Catalogo:
    """Lee las fichas y aplica `validar`. Junta todos los errores antes de fallar."""
    errores: list[str] = []
    fuentes: dict[str, Fuente] = {}
    herramientas: dict[str, Herramienta] = {}
    for modelo, carpeta, destino in (
        (Fuente, "fuentes", fuentes),
        (Herramienta, "herramientas", herramientas),
    ):
        for ruta in sorted((raiz / carpeta).glob("*.yaml")):
            nombre = ruta.relative_to(raiz).as_posix()
            try:
                ficha = modelo.model_validate(yaml.safe_load(ruta.read_text(encoding="utf-8")))
            except (ValidationError, yaml.YAMLError) as exc:
                errores.append(f"{nombre}: {exc}")
                continue
            if ruta.stem != ficha.id:
                errores.append(f"{nombre}: el archivo debe llamarse {ficha.id}.yaml")
            if ficha.id in destino:
                errores.append(f"{nombre}: id repetido {ficha.id}")
            destino[ficha.id] = ficha  # type: ignore[assignment]
    coberturas = {ruta.stem for ruta in (raiz / "cobertura").glob("*.yaml")}
    metadatos: dict[str, Metadatos] = {}
    for ruta in sorted((raiz / "metadatos").glob("*.yaml")):
        nombre = ruta.relative_to(raiz).as_posix()
        try:
            m = Metadatos.model_validate(yaml.safe_load(ruta.read_text(encoding="utf-8")))
        except (ValidationError, yaml.YAMLError) as exc:
            errores.append(f"{nombre}: {exc}")
            continue
        if ruta.stem != m.fuente:
            errores.append(f"{nombre}: el archivo debe llamarse {m.fuente}.yaml")
        metadatos[m.fuente] = m
    catalogo = Catalogo(
        fuentes=fuentes, herramientas=herramientas, coberturas=coberturas, metadatos=metadatos
    )
    errores += validar(catalogo)
    if errores:
        raise CatalogoInvalido(errores)
    return catalogo


def validar(catalogo: Catalogo) -> list[str]:
    """Reglas entre fichas (spec 02, §7.3)."""
    errores = []
    for fid, m in catalogo.metadatos.items():
        fuente = catalogo.fuentes.get(fid)
        if fuente is None:
            errores.append(f"metadatos/{fid}.yaml: la fuente {fid} no existe")
        elif sueltos := set(m.campos) - set(fuente.campos):
            errores.append(
                f"metadatos/{fid}.yaml: describe campos fuera de la lista blanca: {sorted(sueltos)}"
            )
    for f in catalogo.fuentes.values():
        if f.cobertura.indice and f.cobertura.indice not in catalogo.coberturas:
            errores.append(
                f"fuentes/{f.id}.yaml: el índice de cobertura {f.cobertura.indice} no existe "
                "en catalogo/cobertura/"
            )
    for h in catalogo.herramientas.values():
        donde = f"herramientas/{h.id}.yaml"
        fuente = catalogo.fuentes.get(h.fuente)
        if fuente is None:
            errores.append(f"{donde}: la fuente {h.fuente} no existe")
            continue
        if sueltos := h.consulta.marcadores - set(h.entrada) - MARCADORES_DE_LA_PUERTA:
            errores.append(f"{donde}: la consulta usa marcadores sin entrada: {sorted(sueltos)}")
        for marcador in sorted(_interpolados(h.consulta.argumentos) & set(h.entrada)):
            if h.entrada[marcador] not in SEGUROS_EN_TEXTO:
                errores.append(
                    f"{donde}: «{marcador}» ({h.entrada[marcador]}) va dentro de un texto de la "
                    "consulta: inyección. Usa un tipo con patrón (codigo_predial, divipola…)"
                )
        if "url_capa" in h.consulta.marcadores and not h.consulta.capas:
            errores.append(f"{donde}: usa {{url_capa}} pero no declara capas")
        if faltan := set(h.consulta.campos) - set(fuente.campos):
            errores.append(f"{donde}: pide campos fuera de la lista blanca: {sorted(faltan)}")
        salen = fuente.nombres_rt | set(h.derivados)
        for nombre, d in h.derivados.items():
            if d.de in (
                "prefijo",
                "codigo",
                "suma",
                "maximo",
                "primero",
            ) and d.campo not in fuente.nombres_rt | set(h.derivados):
                errores.append(f"{donde}: el derivado {nombre} usa «{d.campo}», que no sale")
            if d.de == "capa" and set(map(str, h.consulta.capas)) != set(d.valores or {}):
                errores.append(f"{donde}: el derivado {nombre} debe dar un valor para cada capa")
        if fuera := (set(h.canario.verdad) | set(h.canario.minimos)) - salen:
            errores.append(
                f"{donde}: la verdad del canario usa campos que no salen: {sorted(fuera)}"
            )
        cierre = _CIERRE.search(h.descripcion)
        if cierre is None:
            errores.append(f"{donde}: la descripción debe cerrar con «(Fuente: X; licencia: Y.)»")
        else:
            esperada = _licencia_legible(fuente)
            if cierre["licencia"].strip() != esperada:
                errores.append(
                    f"{donde}: la descripción dice licencia «{cierre['licencia'].strip()}» y la "
                    f"fuente es «{esperada}»"
                )
    return errores


def _interpolados(valor: Any) -> set[str]:
    """Marcadores metidos dentro de un texto más largo (`"CODIGO = '{codigo}'"`), no los que son
    el valor entero (`"{lon}"`, que conserva su tipo)."""
    if isinstance(valor, str):
        return set() if MARCADOR.fullmatch(valor) else set(MARCADOR.findall(valor))
    if isinstance(valor, dict):
        return set().union(*(_interpolados(v) for v in valor.values())) if valor else set()
    if isinstance(valor, list):
        return set().union(*(_interpolados(v) for v in valor)) if valor else set()
    return set()


LICENCIAS_LEGIBLES = {
    "CC0-1.0": "CC0 1.0",
    "LicenseRef-dominio-publico-EEUU": "dominio público de Estados Unidos",
    "LicenseRef-banrep-aviso-legal": "aviso legal del BanRep",
    "LicenseRef-ley23-1982-art41": "Ley 23 de 1982, art. 41",
    "LicenseRef-dane-terminos": "términos de uso del DANE",
    "LicenseRef-dian-terminos": "términos de uso de la DIAN, sin fines de lucro",
}


def _licencia_legible(fuente: Fuente) -> str:
    """La licencia como la lee un agente, con «sin uso comercial» si la fuente no lo permite: con
    «licencia: CC BY 4.0» a secas, un agente contestó que Open-Meteo se podía usar comercialmente
    (su API gratuita es solo no comercial; GEO Copilot, plan de fiabilidad)."""
    spdx = fuente.licencia.spdx
    if spdx is None:
        return (
            "dato público reutilizable"
            if fuente.clasificacion_licencia == "ambar"
            else "por verificar"
        )
    if spdx in LICENCIAS_LEGIBLES:
        legible = LICENCIAS_LEGIBLES[spdx]
    else:
        legible = re.sub(r"^CC-(BY(?:-SA|-NC|-ND)*)-(\d\.\d)$", lambda m: f"CC {m[1]} {m[2]}", spdx)
    return f"{legible}, sin uso comercial" if fuente.uso_comercial == "no" else legible


def ids_parecidos(catalogo: Catalogo, texto: str, n: int = 5) -> list[str]:
    """Ids de fuentes y herramientas que se parecen a `texto`, para un error accionable: un agente
    pidió `fuente_describir("open-meteo")` y, sin pistas, se rindió (GEO Copilot, fiabilidad).
    Primero los que contienen el texto (o lo contiene su título o entidad), luego los parecidos."""
    clave = re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")
    if not clave:
        return []
    candidatos = {
        **{f.id: f"{f.titulo} {f.entidad}" for f in catalogo.fuentes.values()},
        **{h.id: h.pregunta for h in catalogo.herramientas.values()},
    }
    normal = {i: re.sub(r"[^a-z0-9]+", "_", f"{i} {t}".lower()) for i, t in candidatos.items()}
    contienen = sorted(i for i, t in normal.items() if clave in t)
    parecidos = difflib.get_close_matches(clave, list(candidatos), n=n, cutoff=0.6)
    return list(dict.fromkeys([*contienen, *parecidos]))[:n]


@functools.cache
def cargar_cobertura(indice: str, raiz: Path = RAIZ) -> dict[str, Any]:
    """Un índice de cobertura (`catalogo/cobertura/<indice>.yaml`). Memoizado a nivel proceso: el
    YAML (~0,3 s) se parsea una vez, no por petición catastral (se lee solo, no se muta)."""
    datos = yaml.safe_load((raiz / "cobertura" / f"{indice}.yaml").read_text(encoding="utf-8"))
    if not isinstance(datos, dict) or "municipios" not in datos:
        raise CatalogoInvalido([f"cobertura/{indice}.yaml: falta `municipios`"])
    return datos
