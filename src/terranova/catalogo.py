"""Catálogo como código (ADR-0007, spec 02): una ficha YAML por fuente y una por herramienta.

`cargar()` lee `catalogo/` y `validar()` aplica las reglas que cruzan fichas. Un catálogo inválido
rompe el CI (`scripts/check.py`).
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

RAIZ = Path(__file__).resolve().parents[2] / "catalogo"
ID_FUENTE = r"^[a-z0-9_]+(\.[a-z0-9_]+)+$"
ID_HERRAMIENTA = r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$"
DURACION_ISO = r"^P(?:\d+[YMWD])+(?:T(?:\d+[HMS])+)?$|^PT(?:\d+[HMS])+$"

# Tipos de entrada. Los que tienen patrón los valida la puerta antes de llamar; solo esos y los
# numéricos se pueden meter dentro de un texto de la consulta (un `where`): un `str` libre ahí sería
# inyección SQL/SoQL.
PATRONES_ENTRADA: dict[str, str] = {
    "codigo_predial": r"^[0-9]{30}$",
    "divipola": r"^[0-9]{5}$",
    "id_secop": r"^CO1\.[A-Z]+\.[0-9]+$",
    "constancia_secop": r"^[0-9]{2}-[0-9]{1,2}-[0-9]+$",  # SECOP I: 19-12-10176235
    "contrato_secop": r"^(CO1\.[A-Z]+\.[0-9]+|[0-9]{2}-[0-9]{1,2}-[0-9]+)$",  # SECOP II o I
    "fecha": r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$",
    "sentencia_cc": r"^(C|T|SU)-[0-9]{1,4}/[0-9]{2}$",  # Corte Constitucional: T-760/08
    "nombre": r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ .-]{0,79}$",
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
    "nombre",
]
SEGUROS_EN_TEXTO = frozenset({"int", "float", *PATRONES_ENTRADA})

Familia = Literal[
    "territorio", "contratacion", "empresas", "normativa", "justicia", "estadisticas", "ambiente"
]
UsoComercial = Literal["si", "no", "por_verificar"]


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

    origen: Literal["socrata"]
    conjunto: str = Field(pattern=r"^[a-z0-9]{4}-[a-z0-9]{4}$", description="id en datos.gov.co")
    tabla: str = Field(pattern=IDENTIFICADOR_SQL, description="nombre de la vista en `copia.`")
    clave: str = Field(description="columna única y estable: ordena las páginas y la huella")
    ventana: Ventana | None = None
    indices: list[str] = Field(default_factory=list)
    texto: list[str] = Field(
        default_factory=list, description="columnas de la búsqueda de texto completo (español)"
    )

    @property
    def columnas_usadas(self) -> set[str]:
        ventana = {self.ventana.columna} if self.ventana else set()
        return {self.clave, *ventana, *self.indices, *self.texto}


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
        "arcgis_rest", "wfs", "wms", "socrata", "ckan", "stac", "api_propia", "archivo"
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
        if self.licencia.spdx is None and self.uso_comercial != "por_verificar":
            raise ValueError("ADR-0019: sin licencia conocida, uso_comercial es por_verificar")
        if self.uso_comercial != "por_verificar" and self.licencia.verificada is None:
            raise ValueError("ADR-0007: uso_comercial decidido exige licencia verificada")
        if self.clase_acceso == "interno_con_permiso" and self.permiso is None:
            raise ValueError("ADR-0018: un backend interno exige el permiso escrito")
        if self.estado == "publicada" and self.datos_personales == "presentes":
            raise ValueError("ADR-0014: una fuente con datos personales presentes no se publica")
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
DE_ELEMENTO = frozenset({"capa", "prefijo", "columna"})
DE_RESULTADO = frozenset({"conteo", "suma", "maximo", "primero", "completitud_total"})


class Derivado(_Ficha):
    """Un campo `rt/1` que no viene tal cual de la fuente.

    Por elemento: `capa` (valor según la capa que respondió, `valores`), `prefijo` (los `n`
    primeros caracteres de `campo`, ya en nombre rt/1) y `columna` (una columna cruda del
    resultado, p. ej. un alias de un `select` agregado). Del resultado: `conteo`, `suma` y
    `maximo` de `campo`, `primero` (el `campo` del primer elemento) y `completitud_total` (el
    total que dio la fuente).
    """

    de: Literal[
        "capa", "prefijo", "columna", "conteo", "suma", "maximo", "primero", "completitud_total"
    ]
    campo: str | None = None
    n: int | None = Field(default=None, ge=1)
    valores: dict[str, str] | None = None
    tipo: Literal["str", "int", "float", "bool", "date", "datetime"] = "str"

    @model_validator(mode="after")
    def _completo(self) -> Self:
        necesita_campo = {"prefijo", "columna", "suma", "maximo", "primero"}
        if self.de in necesita_campo and not self.campo:
            raise ValueError(f"un derivado «{self.de}» necesita `campo`")
        if self.de == "prefijo" and self.n is None:
            raise ValueError("un derivado «prefijo» necesita `n`")
        if self.de == "capa" and not self.valores:
            raise ValueError("un derivado «capa» necesita `valores` (capa → valor)")
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
    creditos: int = Field(ge=0)
    canario: Canario

    @model_validator(mode="after")
    def _propias(self) -> Self:
        if set(self.canario.entrada) != set(self.entrada):
            raise ValueError("la entrada del canario no coincide con la de la herramienta")
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
}


def _licencia_legible(fuente: Fuente) -> str:
    spdx = fuente.licencia.spdx
    if spdx is None:
        return "por verificar"
    if spdx in LICENCIAS_LEGIBLES:
        return LICENCIAS_LEGIBLES[spdx]
    legible = re.sub(r"^CC-(BY(?:-SA|-NC|-ND)*)-(\d\.\d)$", lambda m: f"CC {m[1]} {m[2]}", spdx)
    return legible


def cargar_cobertura(indice: str, raiz: Path = RAIZ) -> dict[str, Any]:
    """Un índice de cobertura (`catalogo/cobertura/<indice>.yaml`)."""
    datos = yaml.safe_load((raiz / "cobertura" / f"{indice}.yaml").read_text(encoding="utf-8"))
    if not isinstance(datos, dict) or "municipios" not in datos:
        raise CatalogoInvalido([f"cobertura/{indice}.yaml: falta `municipios`"])
    return datos
