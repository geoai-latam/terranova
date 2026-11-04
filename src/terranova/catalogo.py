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
PATRON_NIT = r"^[89][0-9]{2}\.?[0-9]{3}\.?[0-9]{3}(-?[0-9])?$"
TIPOS_NIT = frozenset({"nit_empresa", "nit_entidad"})
# DIAN: pesos del dígito de verificación, del último dígito del NIT hacia el primero
_PESOS_DV = (3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71)


def digito_verificacion(nit: str) -> int:
    """El dígito de verificación de la DIAN (módulo 11) de un NIT sin él."""
    resto = sum(int(d) * p for d, p in zip(reversed(nit), _PESOS_DV, strict=False)) % 11
    return resto if resto < 2 else 11 - resto


def normalizar_nit(texto: str) -> str:
    """El NIT en 9 dígitos. Quita puntos y, si trae el dígito de verificación (con guion o pegado
    como décimo dígito), lo comprueba: un dígito que no cuadra es un error, no un NIT distinto.
    Espera un texto que ya cumple `PATRON_NIT`."""
    limpio = texto.replace(".", "")
    base, _, dv = limpio.partition("-")
    if not dv and len(base) == 10:
        base, dv = base[:9], base[9]
    if dv and int(dv) != digito_verificacion(base):
        raise ValueError(
            f"el dígito de verificación no cuadra: el de {base} es {digito_verificacion(base)}"
        )
    return base


PATRONES_ENTRADA: dict[str, str] = {
    "codigo_predial": r"^[0-9]{30}$",
    # el código, o el nombre del municipio (con «, departamento» si hace falta): la puerta lo
    # convierte en el código antes de la consulta, así que a la fuente siempre llegan 5 dígitos
    "divipola": r"^([0-9]{5}|[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .,-]{0,99})$",
    "id_secop": r"^CO1\.[A-Z]+\.[0-9]+$",
    "constancia_secop": r"^[0-9]{2}-[0-9]{1,2}-[0-9]+$",  # SECOP I: 19-12-10176235
    "contrato_secop": r"^(CO1\.[A-Z]+\.[0-9]+|[0-9]{2}-[0-9]{1,2}-[0-9]+)$",  # SECOP II o I
    "fecha": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
    # Corte Constitucional: T-760/08; en 1993-1995, algunas con letra (C-155A/93)
    "sentencia_cc": r"^(C|T|SU)-[0-9]{1,4}[A-Z]?/[0-9]{2}$",
    # en la URL de la relatoría: T-760-08 (sin «/»: nada de rutas). Las de unificación van sin el
    # primer guion (SU214-16); la puerta acepta las dos formas y deja la de la relatoría
    "sentencia_relatoria": r"^(C-|T-|SU-?)[0-9]{1,4}[A-Z]?-[0-9]{2}$",
    # documento de un gestor normativo (decreto_1165_2019): sin «/» ni «.», nada de rutas. El año va
    # casi siempre, pero no en todos: el Estatuto Tributario es `estatuto_tributario` en la DIAN
    "documento_normativo": r"^[a-z][a-z0-9_-]{2,60}$",
    # NIT de persona jurídica (empieza por 8 o 9): buscar por cédula queda fuera (ADR-0014). Se
    # acepta como lo escribe la gente (899.999.172-8, 8999991728) y `normalizar_nit` lo deja en 9
    # dígitos, con el dígito de verificación comprobado.
    "nit_empresa": PATRON_NIT,
    # el NIT de una entidad pública (alcaldía, ministerio): la misma forma
    "nit_entidad": PATRON_NIT,
    "codigo_dane_sede": r"^[0-9]{12}$",  # sede educativa (DANE): 125175000493
    "matricula_inmobiliaria": r"^[0-9A-Z]{2,4}-[0-9]{1,10}$",  # folio de matrícula: 50N-20849403
    "bpin": r"^[0-9]{13,14}$",  # proyecto del Banco de Proyectos (DNP): 2013157610001
    # 3 caracteres o más: «A» sería un `like '%A%'` (y su count) sobre millones de filas del Estado
    "nombre": r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .-]{2,79}$",
    # expediente de título minero (ANM): mayúsculas, dígitos y guion; sin comillas ni espacios
    "expediente_minero": r"^[A-Z0-9][A-Z0-9-]{3,19}$",
    # código SIGEP de la entidad (Función Pública): dígitos, con posible cero inicial (0870)
    "codigo_sigep": r"^[0-9]{1,6}$",
    # subpartida arancelaria NANDINA de 10 dígitos (comercio exterior DANE/DIAN): 8517130000
    "subpartida": r"^[0-9]{10}$",
    # año de cuatro dígitos (2000 a 2099)
    "anio": r"^20[0-9]{2}$",
    # estación de la red del IDEAM: 10 dígitos con ceros a la izquierda (0028025502)
    "codigo_estacion_ideam": r"^[0-9]{10}$",
    # campo de hidrocarburos (ANH): como `nombre`, pero con dígitos (BALLENA 2, LLANOS-58-4)
    "campo_hidrocarburos": r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 .-]{0,79}$",
    # aeropuerto en la Aerocivil: sigla IATA de 3 caracteres (BOG); los aeródromos sin IATA llevan
    # una sigla propia de la Aerocivil con dígitos (1GH)
    "codigo_iata": r"^[A-Z0-9]{3}$",
    # indicador de lugar OACI del aeródromo (SKBO); algunos aeródromos menores tienen 3 caracteres
    "codigo_oaci": r"^[A-Z0-9]{3,4}$",
    # identificador numérico de un registro de la fuente (un descriptor de la relatoría: 12021);
    # lo usa la consulta previa para validar lo que devuelve la fuente
    "id_numerico": r"^[0-9]{1,9}$",
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
    "sentencia_relatoria": ("sentencia con guiones en vez de barra", "T-760-08"),
    "documento_normativo": (
        "documento del gestor normativo, tipo_número_año (o su nombre, como estatuto_tributario)",
        "decreto_1165_2019",
    ),
    "nit_empresa": (
        "NIT de la empresa: 9 dígitos, con o sin puntos y dígito de verificación",
        "899999714",
    ),
    "nit_entidad": (
        "NIT de la entidad pública: 9 dígitos, con o sin puntos y dígito de verificación",
        "899999172",
    ),
    "codigo_dane_sede": ("código DANE de la sede educativa, 12 dígitos", "125175000493"),
    "matricula_inmobiliaria": ("folio de matrícula: oficina, guion y número", "50N-20849403"),
    "bpin": ("código BPIN del proyecto, 13 o 14 dígitos", "2013157610001"),
    "nombre": ("nombre o parte de él: letras, espacios, puntos y guiones", "Bancolombia"),
    "expediente_minero": ("código de expediente del título minero (ANM)", "ABQ-101"),
    "codigo_sigep": ("código SIGEP de la entidad (Función Pública)", "6194"),
    "subpartida": ("subpartida arancelaria NANDINA de 10 dígitos", "8517130000"),
    "anio": ("año de cuatro dígitos", "2025"),
    "codigo_estacion_ideam": (
        "código de la estación del IDEAM, 10 dígitos con ceros a la izquierda",
        "0028025502",
    ),
    "campo_hidrocarburos": ("nombre del campo de hidrocarburos (ANH)", "Rubiales"),
    "codigo_iata": ("sigla IATA del aeropuerto, 3 caracteres en mayúscula", "BOG"),
    "codigo_oaci": ("indicador OACI del aeródromo, 4 caracteres en mayúscula", "SKBO"),
    "id_numerico": ("identificador numérico", "12021"),
}

# Un `int` llega a una plantilla SoQL o a una URL: un número desmedido no le sirve a nadie y le
# cuesta una consulta a la fuente. El año 2030 sí pasa: la respuesta dice que está fuera de
# cobertura.
MAX_ENTERO = 10**15


def rango_entero(nombre: str) -> tuple[int, int]:
    return (1900, 2100) if nombre == "anio" else (0, MAX_ENTERO)


def entero_de_json(valor: Any) -> Any:
    """`5.0` es un entero en JSON Schema: se recibe como 5, por MCP y por REST (ADR-0004)."""
    return int(valor) if isinstance(valor, float) and valor.is_integer() else valor


SUFIJO_SIGNIFICADO = "_significado"
TipoEntrada = Literal[
    "float",
    "int",
    "str",
    "bool",
    "bbox",
    "poligono",
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
    "nit_entidad",
    "codigo_dane_sede",
    "matricula_inmobiliaria",
    "bpin",
    "nombre",
    "expediente_minero",
    "codigo_sigep",
    "subpartida",
    "anio",
    "codigo_estacion_ideam",
    "campo_hidrocarburos",
    "codigo_iata",
    "codigo_oaci",
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
    "entidad fuente; verifique los términos para su uso específico. Terrnova normaliza y entrega, "
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
    codigos_por_capa: dict[str, dict[str, str]] | None = Field(
        default=None,
        description="como `codigos`, cuando cada capa da otro significado al mismo código",
    )
    codigos_norma: str | None = Field(
        default=None, description="la norma que define `codigos` (resolución, artículo, URL)"
    )
    ancho: int | None = Field(
        default=None,
        ge=2,
        description="rellena con ceros: un código que la fuente guarda como número (5001 → 05001)",
    )
    maximo_valido: float | None = Field(
        default=None,
        description="por encima de esto la fuente trae un dato dañado: sale vacío, no inventado",
    )
    coma_decimal: bool = Field(
        default=False,
        description="la fuente escribe el decimal con coma (-74,05): se declara por campo, porque "
        "en general «1,234» es ambiguo",
    )
    orden_fecha: Literal["mda", "dma", "amd"] | None = Field(
        default=None,
        description="la fuente escribe la fecha en texto, mes/día/año (mda), día/mes/año (dma) o "
        "año.mes.día (amd): "
        "sale en ISO. Se declara por campo, porque «05/11/2017» es ambiguo",
    )
    anios_validos: tuple[int, int] | None = Field(
        default=None,
        description="años posibles para esta fecha: fuera de ellos es relleno de la fuente (el "
        "INVIMA pone 1000, 1900, 3000 o 9999 en el vencimiento) y sale vacía, no como fecha",
    )
    moneda: bool = Field(
        default=False,
        description="la fuente escribe la cifra como texto con signo de pesos ($84.95, «$ 2.31», "
        "-$0.00): sale como número",
    )
    decimales: int | None = Field(
        default=None,
        ge=0,
        le=6,
        description="redondea un número con más decimales de los que tiene sentido (el anexo de la "
        "GEIH trae la tasa de desempleo con 15: 10.859452814202058); el DANE la publica con uno",
    )
    vacios: tuple[str, ...] = Field(
        default=(),
        description="textos que la fuente pone en lugar de un dato que no tiene (la SFC escribe "
        "NIT «0» y página web «Pendiente»): salen vacíos, no como dato",
    )
    alias: list[str] = Field(
        default_factory=list,
        description="otros nombres del mismo campo en capas de servicios distintos (los POMCA de "
        "la CAR llaman CAT_ORD, CAT_ORD_A o CATEGORIA a la categoría): vale el primero que traiga "
        "la fila",
    )

    @model_validator(mode="after")
    def _codigos_con_norma(self) -> Self:
        if self.codigos is not None and self.codigos_por_capa is not None:
            raise ValueError("spec 08: `codigos` o `codigos_por_capa`, no los dos")
        tiene_codigos = self.codigos is not None or self.codigos_por_capa is not None
        if tiene_codigos != (self.codigos_norma is not None):
            raise ValueError("spec 08: los códigos escritos a mano van con la norma que los define")
        if (self.orden_fecha or self.anios_validos) and self.tipo not in ("date", "datetime"):
            raise ValueError("`orden_fecha` y `anios_validos` son de campos de fecha")
        if self.anios_validos and self.anios_validos[0] > self.anios_validos[1]:
            raise ValueError("`anios_validos` va de menor a mayor")
        if self.moneda and self.tipo not in ("int", "float"):
            raise ValueError("`moneda` es de campos numéricos")
        return self

    def significado(self, valor: Any, capa: str | None) -> str | None:
        """Qué quiere decir un código; None si la tabla no lo define."""
        tabla = self.codigos
        if tabla is None:
            tabla = (self.codigos_por_capa or {}).get(capa or "", {})
        return tabla.get(str(valor))


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
    desde_anio: int | None = Field(
        default=None, description="primer año que cubre, cuando la columna no se cosecha"
    )
    hasta_anio: int | None = Field(
        default=None,
        description="último año que cubre, cuando la columna no se cosecha: una proyección llega "
        "a un año futuro fijo (2042) y no se puede decir «aún no llega» de lo que pasa de ahí",
    )
    incompleta_hasta: int | None = Field(
        default=None, description="último año en que a la fuente le falta parte de lo que promete"
    )
    aviso_incompleta: str | None = Field(
        default=None, description="qué le falta en esos años: se dice con la respuesta"
    )
    rectangulo: tuple[float, float, float, float] | None = Field(
        default=None,
        description="[oeste, sur, este, norte] de una fuente regional: fuera de él, un vacío es "
        "fuera_de_cobertura",
    )
    periodo: str | None = Field(
        default=None, description="años que cubre, escritos a mano cuando no hay columna (spec 08)"
    )
    aviso_vacio: str | None = Field(
        default=None,
        description="por qué un «no encontrado» de esta fuente no quiere decir «no hay»: lo que la "
        "fuente no cubre, medido. Sale con cada respuesta vacía",
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


class VariacionesIndice(_Ficha):
    """Un índice mensual (el IPC del DANE) con un año por columna: al copiar, cada fila suma su
    variación mensual, anual y en lo corrido del año, en porcentaje y con dos decimales, como las
    publica el DANE. Se calculan con el índice porque el anexo no las trae juntas, y una consulta
    de un año no ve el anterior."""

    indice: str = Field(description="columna del índice")
    anio: str = Field(description="columna del año")
    mes: str = Field(description="columna del mes, con su nombre en español (Enero … Diciembre)")


class Preagregado(_Ficha):
    """Un conjunto de datos.gov.co de personas que se copia ya agregado (origen `socrata_agregado`):
    p. ej. el Saber 11, una fila por estudiante. La copia guarda solo grupos, con cuántas personas
    tiene cada uno y la suma de sus medidas; nunca el identificador ni una fila de persona
    (ADR-0014). Las herramientas sacan promedios como cociente de sumas y exigen un mínimo de
    personas por grupo."""

    particion: str = Field(
        description="columna con que se baja la fuente por tandas (el periodo): la cuenta de "
        "personas únicas se hace dentro de cada una"
    )
    unico: str = Field(
        description="columna que identifica a la persona en la fuente (seudónimo): la fuente "
        "repite filas y cada persona cuenta una vez por tanda; no se copia"
    )
    grupo: list[str] = Field(min_length=1, description="columnas de la fuente que forman el grupo")
    medidas: list[str] = Field(
        default_factory=list,
        description="columnas numéricas: la copia guarda `suma_<m>` y `n_<m>` (con dato)",
    )
    nombre: str | None = Field(
        default=None,
        description="columna de texto que se guarda con el mayor valor del grupo (el nombre de la "
        "sede, que cambia de escritura entre años)",
    )
    cuenta: str = Field(
        default="personas", pattern=IDENTIFICADOR_SQL, description="columna con las personas"
    )

    @property
    def columnas_fuente(self) -> list[str]:
        """Lo que se pide a la fuente, cada columna una vez (Socrata rechaza un `$select` con una
        repetida, y la partición suele ir también en el grupo)."""
        nombre = [self.nombre] if self.nombre else []
        columnas = [self.particion, self.unico, *self.grupo, *self.medidas, *nombre]
        return list(dict.fromkeys(columnas))

    @property
    def columnas_copia(self) -> list[str]:
        """Lo que guarda la copia, además de `_fila`."""
        sumas = [f"{p}_{m}" for m in self.medidas for p in ("suma", "n")]
        nombre = [self.nombre] if self.nombre else []
        grupo = [c for c in self.grupo if c != self.particion]
        return [self.particion, *grupo, *nombre, self.cuenta, *sumas]


class Copia(_Ficha):
    """Cómo se copia una fuente a PostGIS (G3, ADR-0024): solo las columnas de `campos`."""

    origen: Literal[
        "socrata", "socrata_agregado", "zip_dane", "arcgis", "conector", "geojson", "csv"
    ]
    conjunto: str | None = Field(
        default=None,
        pattern=r"^[a-z0-9]{4}-[a-z0-9]{4}$",
        description="id en datos.gov.co (socrata)",
    )
    descargas: list[str] = Field(
        default_factory=list,
        description="URLs de los ZIP a copiar y pre-agregar (origen zip_dane), de los GeoJSON "
        "(origen geojson) o de los CSV (origen csv) publicados a copiar tal cual",
    )
    # CSV publicado como archivo (origen csv), p. ej. las alertas diarias del IDEAM, que no tienen
    # API: se copian la lista blanca de columnas y las fechas día/mes/año pasan a ISO.
    separador: str = Field(
        default=",", min_length=1, max_length=1, description="separador del CSV (origen csv)"
    )
    ceros: dict[str, int] = Field(
        default_factory=dict,
        description="columnas a rellenar con ceros a la izquierda hasta ese ancho (origen csv): "
        "el IDEAM a veces publica el DIVIPOLA 05893 como 5893",
    )
    # GeoJSON publicado como archivo (origen geojson), p. ej. en un CKAN cuando el servicio ArcGIS
    # de la entidad no está en pie. Si sus coordenadas no son EPSG:4326, `proyeccion` dice cuáles
    # son y PostGIS las pasa a lon/lat al copiar.
    proyeccion: str | None = Field(
        default=None,
        pattern=r"^\+proj=[a-z0-9_]+( \+[a-z0-9_]+(=[A-Za-z0-9_.,-]+)?)*$",
        description="cadena proj de las coordenadas del GeoJSON (origen geojson); se reproyecta a "
        "lon/lat sobre el mismo elipsoide, sin cambio de datum",
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
    # Varias capas en una sola copia (origen arcgis), p. ej. la zonificación de los POMCA de la CAR:
    # un servicio por cuenca, cada uno con sus nombres de campo (los `alias` de la ficha) y su campo
    # de id. La clave de la copia se arma: posición del servicio por 1 000 000 + el id en su capa.
    servicios: dict[str, str] = Field(
        default_factory=dict,
        description="capas a juntar (origen arcgis): {«<servicio>/FeatureServer/<capa>», relativa "
        "a la url: valor de `columna_servicio` en sus filas}",
    )
    columna_servicio: str | None = Field(
        default=None,
        description="columna que dice de qué servicio salió cada fila (con `servicios`)",
    )
    filtro: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z0-9_ ,'()=<>.-]+$",
        description="`where` de la capa (origen arcgis): copia solo una parte, p. ej. los "
        "municipios que el catastro del IGAC no cubre",
    )
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
    variaciones: VariacionesIndice | None = Field(
        default=None,
        description="calcula al copiar las variaciones de un índice mensual (origen conector)",
    )
    tabla: str = Field(pattern=IDENTIFICADOR_SQL, description="nombre de la vista en `copia.`")
    clave: str = Field(
        description="columna única y estable: ordena las páginas y la huella (`_fila`: el orden "
        "de la fila en lo que dio el conector, para tablas sin columna única)"
    )
    ventana: Ventana | None = None
    indices: list[str] = Field(default_factory=list)
    indices_contiene: list[str] = Field(
        default_factory=list,
        description="columnas que se buscan con `contiene`: llevan un índice de trigramas sobre el "
        "texto sin mayúsculas ni tildes (sin él, cada búsqueda recorre la tabla entera)",
    )
    texto: list[str] = Field(
        default_factory=list, description="columnas de la búsqueda de texto completo (español)"
    )
    orden_fisico: str | None = Field(
        default=None,
        description="columna de `indices` por la que se ordenan las filas en el disco (CLUSTER): "
        "las de un mismo valor quedan juntas y se leen en pocas páginas aunque la copia no esté "
        "en caché (SECOP por NIT: los 50 142 contratos de Medellín tardaban 16 s en frío)",
    )

    preagregado: Preagregado | None = Field(
        default=None, description="cómo se agrega al copiar (origen socrata_agregado)"
    )

    @model_validator(mode="after")
    def _origen_coherente(self) -> Copia:
        if self.origen in ("socrata", "socrata_agregado") and not self.conjunto:
            raise ValueError(f"ADR-0024: origen `{self.origen}` exige `conjunto` (id datos.gov.co)")
        if (self.origen == "socrata_agregado") != (self.preagregado is not None):
            raise ValueError("ADR-0024: `preagregado` va con el origen `socrata_agregado`")
        if self.preagregado is not None and self.clave != "_fila":
            raise ValueError("ADR-0024: una copia preagregada lleva `clave: _fila`")
        if self.ventana is not None and self.preagregado is not None:
            raise ValueError("ADR-0024: una copia preagregada se baja entera, sin `ventana`")
        if self.orden_fisico is not None and self.orden_fisico not in self.indices:
            raise ValueError("`orden_fisico` va sobre una columna de `indices`")
        if (self.origen == "arcgis") != ((self.capa is not None) != bool(self.servicios)):
            raise ValueError(
                "ADR-0024: el origen `arcgis` lleva `capa` o `servicios` (uno), y solo él"
            )
        if bool(self.servicios) != (self.columna_servicio is not None):
            raise ValueError("ADR-0024: `servicios` y `columna_servicio` van juntos")
        if self.tolerancia is not None and not (self.origen == "arcgis" and self.geometria):
            raise ValueError("ADR-0024: `tolerancia` solo aplica a una capa ArcGIS con geometría")
        if self.filtro is not None and self.origen != "arcgis":
            raise ValueError("ADR-0024: `filtro` solo aplica a una capa ArcGIS")
        if not self.geometria and self.origen != "arcgis":
            raise ValueError("ADR-0024: `geometria: false` solo aplica a una capa ArcGIS")
        if self.origen == "geojson" and not self.descargas:
            raise ValueError("ADR-0024: origen `geojson` exige `descargas` (URLs de los GeoJSON)")
        if self.proyeccion is not None and self.origen != "geojson":
            raise ValueError("ADR-0024: `proyeccion` solo aplica al origen `geojson`")
        if self.origen == "csv" and not self.descargas:
            raise ValueError("ADR-0024: origen `csv` exige `descargas` (URLs de los CSV)")
        if (self.separador != "," or self.ceros) and self.origen != "csv":
            raise ValueError("ADR-0024: `separador` y `ceros` solo aplican al origen `csv`")
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
        return self.origen in ("arcgis", "geojson") and self.geometria

    @property
    def columnas_usadas(self) -> set[str]:
        ventana = {self.ventana.columna} if self.ventana else set()
        extra = set(self.medidas) | ({self.pais_col} if self.pais_col else set())
        if self.preagregado is not None:
            extra |= set(self.preagregado.columnas_copia)
        if self.columna_servicio is not None:
            extra.add(self.columna_servicio)
        return {self.clave, *ventana, *self.indices, *self.indices_contiene, *self.texto, *extra}


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
    excepcion_uso_comercial: str | None = Field(
        default=None,
        description="por qué se publica una fuente con uso_comercial «no» (decisión con fecha); "
        "sin ella, no se publica",
    )

    @model_validator(mode="after")
    def _reglas(self) -> Self:
        clf = self.clasificacion_licencia
        if self.estado == "publicada" and self.uso_comercial == "no":
            if not self.excepcion_uso_comercial:
                raise ValueError(
                    "ADR-0019: una fuente sin uso comercial no se publica salvo una "
                    "excepcion_uso_comercial escrita con su decisión (y aun así solo responde a "
                    "llaves de evaluación, ADR-0007)"
                )
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
        if self.modo == "copia" and self.conector != "copia":
            # la herramienta iría al conector en vivo con `consultar_copia`, que no lo tiene
            raise ValueError("ADR-0024: una fuente con `modo: copia` lleva `conector: copia`")
        if self.copia is not None and (sueltas := self.copia.columnas_usadas - set(self.campos)):
            raise ValueError(f"ADR-0024: la copia usa columnas no listadas: {sorted(sueltas)}")
        nombres = [c.nombre for c in self.campos.values()]
        if len(nombres) != len(set(nombres)):
            raise ValueError("dos campos de la fuente van al mismo nombre rt/1")
        alias = [a for c in self.campos.values() for a in c.alias]
        if len(alias) != len(set(alias)) or set(alias) & set(self.campos):
            raise ValueError("un alias repite un campo de la fuente u otro alias")
        if alias and self.copia is not None and not self.copia.servicios:
            # con `servicios`, los alias dicen cómo llama cada capa a la columna de la copia
            raise ValueError("ADR-0024: los alias son de capas en vivo; la copia trae una tabla")
        return self

    @property
    def nombres_rt(self) -> set[str]:
        return {c.nombre for c in self.campos.values()} | {
            f"{c.nombre}{SUFIJO_SIGNIFICADO}"
            for c in self.campos.values()
            if c.codigos is not None or c.codigos_por_capa is not None
        }


# `{nombre}`, `{nombre:sin_tildes}` o `{nombre:ascii}`. Con `sin_tildes`, cada vocal con tilde va
# como `_`, el comodín de una letra de LIKE, y «acetaminofén» encuentra «ACETAMINOFEN» (patrón H).
# Con `ascii`, sin tildes ni eñes («daño» → «dano»): la búsqueda de la relatoría de Colombia
# Compra devuelve todo si el texto trae una letra fuera de ASCII (medido el 2026-11-03).
MARCADOR = re.compile(r"\{([a-z_][a-z0-9_]*)(?::(?:sin_tildes|ascii))?\}")
MARCADORES_DE_LA_PUERTA = frozenset({"url_capa", "url_fuente", "capa"})
MARCADOR_PREVIA = "previa"


class SoloSi(_Ficha):
    """Qué elementos cuentan para un derivado: los que tienen `campo` (nombre rt/1) en `valores`.
    Una modificación cancelada de SECOP sigue en la lista, pero no suma ni es «la anterior»."""

    campo: str
    valores: list[str] = Field(min_length=1)

    def cumple(self, elemento: dict[str, Any]) -> bool:
        return str(elemento.get(self.campo)) in self.valores


class AvisoFicha(_Ficha):
    """Un aviso que sale del catálogo, no de la fuente. `cuando: vacio` sale con «no encontrado»
    (y reemplaza el `aviso_vacio` de la fuente: la herramienta sabe a cuál remitir);
    `cuando: encontrado` sale con datos, y con `si` solo cuando el campo de arriba de `datos`
    tiene uno de esos valores (un solo proponente: no hubo competencia); `cuando: fuera` sale con
    «fuera de cobertura» (dónde está lo que no cubre: la serie vieja en otra herramienta)."""

    texto: str = Field(min_length=10)
    cuando: Literal["vacio", "encontrado", "fuera"] = "vacio"
    si: SoloSi | None = None

    @model_validator(mode="after")
    def _si_con_datos(self) -> Self:
        if self.si is not None and self.cuando != "encontrado":
            raise ValueError("un aviso con `si` mira los datos: va con `cuando: encontrado`")
        return self


class Previa(_Ficha):
    """Una consulta antes de la principal que traduce la entrada: el contrato de SECOP II trae el
    proceso de compra (CO1.BDOS…), y los proponentes cuelgan de sus fases (CO1.REQ…). Los valores
    de `columna` que devuelve van a `{previa}` como lista SoQL entre comillas (o separados por coma,
    con `formato: coma`), solo si cumplen el patrón `patron` (un tipo de PATRONES_ENTRADA): lo que
    viene de la fuente no entra crudo."""

    fuente: str
    tool: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    argumentos: dict[str, Any]
    columna: str
    patron: str
    formato: Literal["soql", "coma"] = Field(
        default="soql",
        description="soql: lista entre comillas para un `in (…)`; coma: ids separados por coma "
        "para un parámetro de URL (`?descriptor=12021,24562`), y sin ninguno, «0»",
    )


class HechoComplemento(_Ficha):
    nombre: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    tipo: Literal["str", "int", "float", "date"]
    desc: str


class Complemento(_Ficha):
    """Una consulta además de la principal, cuya primera fila sale como hechos del resultado: hasta
    qué mes llega la fuente en el año pedido (la Policía publica 2026 hasta julio, y un municipio
    sin casos en julio no lo dice). Corre a la vez que la principal y no cuenta en su total. Si
    falla, la respuesta lo avisa y sigue sin esos hechos. Un hecho de una columna con `codigos` en
    su fuente sale con su `_significado` al lado, como en una fila."""

    fuente: str
    tool: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    argumentos: dict[str, Any]
    hechos: dict[str, HechoComplemento] = Field(
        min_length=1, description="columna de la respuesta → hecho que sale en el resultado"
    )
    que_dice: str = Field(
        min_length=5, description="lo que dan los hechos, para el aviso si la consulta falla"
    )


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
    documento_ausente: list[int] = Field(
        default_factory=list,
        description="códigos HTTP con que la fuente dice que ese documento no existe: es «no "
        "encontrado», no una caída",
    )
    minimo_caracteres: int | None = Field(
        default=None,
        description="una página más corta que esto es relleno de la fuente, no el documento",
    )
    solo_elementos: bool = Field(
        default=False, description="sin elementos no hay respuesta, aunque venga el título"
    )
    completo_por_construccion: bool = Field(
        default=False,
        description="resumen completo (ráster, serie): no hay «vistos de un total»",
    )
    capas: list[int | str] = Field(default_factory=list)
    argumentos: dict[str, Any]
    campos: list[str] = Field(min_length=1, description="campos de la fuente que se piden")
    previa: Previa | None = None
    complemento: Complemento | None = None
    juntar: str | None = Field(
        default=None,
        description="campo rt/1 que se junta en una lista: las filas iguales en todo lo demás "
        "salen como una (una presentación del INVIMA repetida por cada vía de administración)",
    )

    @property
    def marcadores(self) -> set[str]:
        previa = self.previa.argumentos if self.previa else {}
        complemento = self.complemento.argumentos if self.complemento else {}
        return set(
            MARCADOR.findall(json.dumps([self.argumentos, previa, complemento], ensure_ascii=False))
        )

    @property
    def forma(self) -> Literal["uno", "lista"]:
        if self.resultado is not None:
            return self.resultado
        return "uno" if self.operacion in ("en_punto", "por_codigo") else "lista"


# Vocabulario cerrado de campos que calcula la puerta (ADR-0012: nada de código suelto por fuente).
DE_ELEMENTO = frozenset({"capa", "prefijo", "columna", "codigo", "fijo"})
# por elemento, pero mirando al anterior de la lista: se calcula con todos los elementos en mano
DE_SECUENCIA = frozenset({"diferencia_anterior"})
# al final, con los agregados y los hechos del complemento ya en `datos`: compara dos de ellos
DE_FINAL = frozenset({"igual"})
DE_RESULTADO = frozenset(
    {
        "conteo",
        "conteo_por",
        "suma",
        "suma_por",
        "maximo",
        "primero",
        "ultimo",
        "distintos",
        "completitud_total",
    }
)


class Derivado(_Ficha):
    """Un campo `rt/1` que no viene tal cual de la fuente.

    Por elemento: `capa` (valor según la capa que respondió, `valores`), `prefijo` (los `n`
    primeros caracteres de `campo`, ya en nombre rt/1) y `columna` (una columna cruda del
    resultado, p. ej. un alias de un `select` agregado; con `patron`, solo el grupo 1 de esa
    expresión regular; con `valores`, lo hallado escrito de varias formas pasa a una sola, y con
    `orden_fecha`, la fecha en texto pasa a ISO) y `codigo` (el
    significado de un código de `campo`, ya en nombre rt/1, según `valores`: p. ej. el nombre
    oficial del departamento por su código DIVIPOLA) y `fijo` (un `valor` que vale para toda la
    fuente: el año 2018 de una medida censal que no lo trae en la tabla). En secuencia:
    `diferencia_anterior` (el `campo` menos el del elemento anterior en el orden de la consulta;
    el primero queda vacío). Del resultado: `conteo`, `suma` y `maximo` de `campo`, `primero` y
    `ultimo` (el `campo` del primer o del último elemento), `conteo_por` (cuántos elementos hay
    con cada valor de `campo`, el más frecuente primero: áreas protegidas por categoría),
    `suma_por` (la suma de `sumar` en cada valor de `campo`, la mayor primero: hectáreas por
    tratamiento),
    `distintos` (cuántos valores distintos de `campo` hay: los meses con datos de un año) y
    `completitud_total` (el total que dio la fuente). `solo_si` deja contar solo algunos
    elementos. Al final: `igual` (si `campo` vale lo mismo que `igual_a`, ya con los agregados y
    los hechos del complemento: la última alerta del municipio es la del último boletín).
    """

    de: Literal[
        "capa",
        "prefijo",
        "columna",
        "codigo",
        "fijo",
        "conteo",
        "conteo_por",
        "suma_por",
        "suma",
        "maximo",
        "primero",
        "ultimo",
        "distintos",
        "diferencia_anterior",
        "completitud_total",
        "igual",
    ]
    campo: str | None = None
    solo_si: SoloSi | None = None
    n: int | None = Field(default=None, ge=1)
    valores: dict[str, str] | None = None
    valor: str | int | float | None = None
    # solo con `suma_por`: el campo rt/1 que se suma en cada grupo de `campo`
    sumar: str | None = None
    # solo con `igual`: el otro campo de `datos` con el que se compara `campo`
    igual_a: str | None = None
    # solo con `columna`: la parte del texto que interesa (el grupo 1 de una expresión regular) y,
    # si es una fecha en texto, en qué orden viene
    patron: str | None = None
    orden_fecha: Literal["mda", "dma", "amd"] | None = None
    # solo con `columna`: el texto viene en HTML; lo que sale va sin etiquetas y con las entidades
    # leídas («Prórroga &#8211; Procedencia» sale con su raya, no con la entidad)
    html: bool = False
    tipo: Literal["str", "int", "float", "bool", "date", "datetime"] = "str"
    # un promedio calculado en la consulta trae 16 decimales (27.2083333333333333 °C)
    decimales: int | None = Field(default=None, ge=0, le=6)

    @model_validator(mode="after")
    def _completo(self) -> Self:
        necesita_campo = {
            "prefijo",
            "columna",
            "codigo",
            "conteo_por",
            "suma_por",
            "suma",
            "maximo",
            "primero",
            "ultimo",
            "distintos",
            "diferencia_anterior",
        }
        if self.de in necesita_campo and not self.campo:
            raise ValueError(f"un derivado «{self.de}» necesita `campo`")
        if self.de == "prefijo" and self.n is None:
            raise ValueError("un derivado «prefijo» necesita `n`")
        if self.de == "capa" and not self.valores:
            raise ValueError("un derivado «capa» necesita `valores` (capa → valor)")
        if self.de == "codigo" and not self.valores:
            raise ValueError("un derivado «codigo» necesita `valores` (código → significado)")
        if (self.patron or self.orden_fecha or self.html) and self.de != "columna":
            raise ValueError("`patron`, `orden_fecha` y `html` van solo en un derivado «columna»")
        if self.patron is not None and re.compile(self.patron).groups != 1:
            raise ValueError("`patron` lleva exactamente un grupo: la parte que se toma")
        if (self.de == "igual") != (self.igual_a is not None) or (
            self.de == "igual" and not self.campo
        ):
            raise ValueError("un derivado «igual» lleva `campo` e `igual_a`, y solo él")
        if (self.de == "suma_por") != (self.sumar is not None):
            raise ValueError("`sumar` va solo, y siempre, en un derivado «suma_por»")
        if (self.de == "fijo") != (self.valor is not None):
            raise ValueError("`valor` va solo, y siempre, en un derivado «fijo»")
        if self.solo_si is not None and self.de in DE_ELEMENTO | {"completitud_total"}:
            raise ValueError(f"un derivado «{self.de}» no usa `solo_si`")
        return self

    @property
    def por_elemento(self) -> bool:
        return self.de in DE_ELEMENTO | DE_SECUENCIA

    @property
    def al_final(self) -> bool:
        return self.de in DE_FINAL


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
    # false: la herramienta sigue en REST y en las compuestas, pero no sale en ningún perfil MCP.
    # Para las que una compuesta ya cubre: el agente confundía las hermanas (predio_en_punto, #15).
    en_mcp: bool = True
    cobro: Cobro
    canario: Canario
    avisos: list[AvisoFicha] = Field(
        default_factory=list,
        description="lo que una persona debe saber al leer la respuesta y que la fuente no dice",
    )

    @property
    def creditos(self) -> int:
        return TARIFA[self.cobro]

    @model_validator(mode="after")
    def _propias(self) -> Self:
        if set(self.canario.entrada) != set(self.entrada):
            raise ValueError("la entrada del canario no coincide con la de la herramienta")
        if self.entrada.get("nit", "nit_empresa") != "nit_empresa":
            # ADR-0014: un NIT que empieza por 1-7 es la cédula de una persona natural; el patrón
            # `nit_empresa` (8 o 9 y 9 dígitos) deja fuera la búsqueda por cédula
            raise ValueError("ADR-0014: el parámetro `nit` va con el tipo `nit_empresa`")
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


def vendible(f: Fuente) -> bool:
    """Lo que ve y usa una llave de producción (`rt_live_`) y lo que se anuncia: una fuente
    publicada y con uso comercial (ADR-0007, enmienda del 2026-11-01). Lo demás (licencia por
    verificar, sin uso comercial, borrador) solo responde a llaves de evaluación (`rt_test_`)."""
    return f.estado == "publicada" and f.uso_comercial == "si"


def motivo_no_vendible(f: Fuente) -> str:
    """Por qué una fuente no responde a una llave de producción (para el error y los avisos)."""
    if f.uso_comercial == "por_verificar":
        return "licencia de la fuente por verificar"
    if f.uso_comercial == "no":
        return "la fuente no permite uso comercial"
    return "fuente en borrador"


def catalogo_vendible(c: Catalogo) -> Catalogo:
    """El catálogo que se anuncia (`/v1/herramientas`, `/llms.txt`, la tarjeta MCP, el sitio) y el
    que lista `/mcp` a una llave de producción: solo las fuentes vendibles y sus herramientas."""
    fuentes = {k: f for k, f in c.fuentes.items() if vendible(f)}
    return c.model_copy(
        update={
            "fuentes": fuentes,
            "herramientas": {k: h for k, h in c.herramientas.items() if h.fuente in fuentes},
            "metadatos": {k: m for k, m in c.metadatos.items() if k in fuentes},
        }
    )


class CatalogoInvalido(Exception):
    def __init__(self, errores: list[str]) -> None:
        super().__init__("\n".join(errores))
        self.errores = errores


class ErrorDeLista(ValueError):
    """Un campo pide una lista de códigos que no está en `catalogo/codigos/`."""


def _lista_de_codigos(lista: str, raiz: Path) -> dict[str, Any]:
    ruta = raiz / "codigos" / f"{lista}.yaml"
    if not re.fullmatch(r"[a-z0-9_]+", lista) or not ruta.is_file():
        raise ErrorDeLista(f"no existe la lista de códigos catalogo/codigos/{lista}.yaml")
    datos: dict[str, Any] = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    return datos


def _con_listas_de_codigos(crudo: Any, raiz: Path) -> None:
    """Cambia `codigos_lista: <nombre>` (en un campo de una fuente) por los `codigos` y la
    `codigos_norma` de `catalogo/codigos/<nombre>.yaml`, y `valores_lista: <nombre>` (en un
    derivado `codigo` de una herramienta) por sus `valores`. Es para las tablas largas y oficiales
    que comparten varias fichas (la CIIU del DANE, ~500 clases, en las dos del RUES; la unidad de
    cada subpartida, ~7 000, en el comercio exterior): una sola copia, con su norma."""
    if not isinstance(crudo, dict):
        return
    for clave, opcion, destino in (
        ("campos", "codigos_lista", "codigos"),
        ("derivados", "valores_lista", "valores"),
    ):
        if not isinstance(crudo.get(clave), dict):
            continue
        for campo in crudo[clave].values():
            if not isinstance(campo, dict) or opcion not in campo:
                continue
            lista = str(campo.pop(opcion))
            if destino in campo:
                raise ErrorDeLista(f"trae `{destino}` y `{opcion}` ({lista}): una sola")
            datos = _lista_de_codigos(lista, raiz)
            campo[destino] = {str(k): str(v) for k, v in datos["codigos"].items()}
            if clave == "campos":
                campo.setdefault("codigos_norma", datos["norma"])


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
                crudo = yaml.safe_load(ruta.read_text(encoding="utf-8"))
                _con_listas_de_codigos(crudo, raiz)
                ficha = modelo.model_validate(crudo)
            except ErrorDeLista as exc:
                errores.append(f"{nombre}: {exc}")
                continue
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
        de_la_puerta = MARCADORES_DE_LA_PUERTA | ({MARCADOR_PREVIA} if h.consulta.previa else set())
        if sueltos := h.consulta.marcadores - set(h.entrada) - de_la_puerta:
            errores.append(f"{donde}: la consulta usa marcadores sin entrada: {sorted(sueltos)}")
        if "capa" in h.consulta.marcadores and not h.consulta.capas:
            errores.append(f"{donde}: la consulta usa {{capa}} sin `capas`")
        if (previa := h.consulta.previa) is not None:
            if previa.fuente not in catalogo.fuentes:
                errores.append(f"{donde}: la consulta previa usa {previa.fuente}, que no existe")
            if previa.patron not in PATRONES_ENTRADA:
                errores.append(
                    f"{donde}: la consulta previa valida con «{previa.patron}», que no tiene patrón"
                )
        if (juntar := h.consulta.juntar) is not None and juntar not in fuente.nombres_rt:
            errores.append(f"{donde}: `juntar` usa «{juntar}», que no sale de la fuente")
        if (complemento := h.consulta.complemento) is not None:
            if complemento.fuente not in catalogo.fuentes:
                errores.append(f"{donde}: el complemento usa {complemento.fuente}, que no existe")
            nombres = [x.nombre for x in complemento.hechos.values()]
            if chocan := set(nombres) & (fuente.nombres_rt | set(h.derivados)):
                errores.append(
                    f"{donde}: el complemento repite nombres que ya salen: {sorted(chocan)}"
                )
        argumentos_todos = {
            **h.consulta.argumentos,
            **({"_previa": h.consulta.previa.argumentos} if h.consulta.previa else {}),
            **(
                {"_complemento": h.consulta.complemento.argumentos}
                if h.consulta.complemento
                else {}
            ),
        }
        for marcador in sorted(_enteros_en_codigo(argumentos_todos) & set(h.entrada)):
            if h.entrada[marcador] not in ("int", "float", "anio", "bool"):
                errores.append(
                    f"{donde}: «{marcador}» ({h.entrada[marcador]}) es el valor entero de una "
                    "clave con código (where, select, url…): inyección. Ponlo entre comillas "
                    "dentro del texto, con un tipo con patrón"
                )
        for marcador in sorted(_interpolados(argumentos_todos) & set(h.entrada)):
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
        if (comp := h.consulta.complemento) is not None:
            salen |= {x.nombre for x in comp.hechos.values()}
            if (cf := catalogo.fuentes.get(comp.fuente)) is not None:
                salen |= {
                    x.nombre + SUFIJO_SIGNIFICADO
                    for col, x in comp.hechos.items()
                    if col in cf.campos and cf.campos[col].codigos is not None
                }
        for nombre, d in h.derivados.items():
            if d.de in (
                "prefijo",
                "codigo",
                "suma",
                "maximo",
                "primero",
                "ultimo",
                "distintos",
                "diferencia_anterior",
            ) and d.campo not in fuente.nombres_rt | set(h.derivados):
                errores.append(f"{donde}: el derivado {nombre} usa «{d.campo}», que no sale")
            if d.de == "igual" and not {d.campo, d.igual_a} <= salen:
                errores.append(f"{donde}: el derivado {nombre} compara campos que no salen")
            if d.de in ("conteo_por", "suma_por") and d.campo not in salen:
                errores.append(f"{donde}: el derivado {nombre} agrupa por «{d.campo}», que no sale")
            if d.sumar is not None and d.sumar not in fuente.nombres_rt | set(h.derivados):
                errores.append(f"{donde}: el derivado {nombre} suma «{d.sumar}», que no sale")
            if d.solo_si and d.solo_si.campo not in fuente.nombres_rt | set(h.derivados):
                errores.append(
                    f"{donde}: el derivado {nombre} filtra por «{d.solo_si.campo}», que no sale"
                )
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


# Claves cuyo valor es código para la fuente (SoQL, una URL, una expresión regular): un marcador
# que es su valor entero entra tal cual, sin comillas (revisión de seguridad C27, 2026-10-31).
CLAVES_CON_CODIGO = frozenset(
    {
        "where",
        "select",
        "order",
        "group",
        "having",
        "previo_select",
        "previo_group",
        "previo_where",
        "url",
        "enlaces_con",
        "enlace_con",
        "pagina",
        "filtro",
        "q",
    }
)


def _enteros_en_codigo(valor: Any, clave: str = "") -> set[str]:
    """Marcadores que son el valor entero de una clave con código (`where: "{x}"`)."""
    if isinstance(valor, str):
        m = MARCADOR.fullmatch(valor)
        return {m.group(1)} if m and clave in CLAVES_CON_CODIGO else set()
    if isinstance(valor, dict):
        return set().union(*(_enteros_en_codigo(v, str(k)) for k, v in valor.items()))
    if isinstance(valor, list):
        return set().union(*(_enteros_en_codigo(v, clave) for v in valor)) if valor else set()
    return set()


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
