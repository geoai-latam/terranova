"""Catálogo como código (ADR-0007, spec 02): una ficha YAML por fuente y una por herramienta.

`cargar()` lee `catalogo/` y `validar()` aplica las reglas que cruzan fichas. Un catálogo inválido
rompe el CI (`scripts/check.py`).
"""

from __future__ import annotations

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
    desc: str


class Frescura(_Ficha):
    ttl_cache_s: int = Field(ge=0)
    sla_actualizacion: str = Field(pattern=DURACION_ISO)


class Cobertura(_Ficha):
    pais: str = Field(pattern=r"^[A-Z]{2}$")
    excluye: list[str] = Field(default_factory=list)
    indice: str | None = None


class Comportamiento(_Ficha):
    p95_ms_medido: int | None = Field(default=None, ge=0)
    max_por_pagina: int | None = Field(default=None, ge=1)
    orden_coordenadas: Literal["lon_lat", "lat_lon"] = "lon_lat"


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
    frescura: Frescura
    cobertura: Cobertura
    datos_personales: Literal["ninguno", "filtrados", "presentes"]
    estado: Literal["borrador", "publicada"]
    campos: dict[str, Campo] = Field(
        min_length=1, description="lista blanca: campo de la fuente → rt/1"
    )
    comportamiento: Comportamiento = Field(default_factory=Comportamiento)
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
        nombres = [c.nombre for c in self.campos.values()]
        if len(nombres) != len(set(nombres)):
            raise ValueError("dos campos de la fuente van al mismo nombre rt/1")
        return self

    @property
    def nombres_rt(self) -> set[str]:
        return {c.nombre for c in self.campos.values()}


class Consulta(_Ficha):
    operacion: Literal["en_punto", "en_zona", "por_codigo", "buscar", "serie"]
    capas: list[int | str] = Field(default_factory=list)
    campos: list[str] = Field(min_length=1, description="campos de la fuente que se piden")


class Canario(_Ficha):
    entrada: dict[str, Any]
    verdad: dict[str, Any] = Field(min_length=1)
    latencia_max_ms: int = Field(ge=1)


class Herramienta(_Ficha):
    id: str = Field(pattern=ID_HERRAMIENTA)
    version: int = Field(ge=1)
    familia: Familia
    fuente: str = Field(pattern=ID_FUENTE)
    pregunta: str
    descripcion: str
    entrada: dict[str, Literal["float", "int", "str", "bool", "bbox", "geojson"]] = Field(
        min_length=1
    )
    consulta: Consulta
    salida: str
    derivados: list[str] = Field(
        default_factory=list, description="campos rt/1 que calcula la puerta"
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
    catalogo = Catalogo(fuentes=fuentes, herramientas=herramientas)
    errores += validar(catalogo)
    if errores:
        raise CatalogoInvalido(errores)
    return catalogo


def validar(catalogo: Catalogo) -> list[str]:
    """Reglas entre fichas (spec 02, §7.3)."""
    errores = []
    for h in catalogo.herramientas.values():
        donde = f"herramientas/{h.id}.yaml"
        fuente = catalogo.fuentes.get(h.fuente)
        if fuente is None:
            errores.append(f"{donde}: la fuente {h.fuente} no existe")
            continue
        if faltan := set(h.consulta.campos) - set(fuente.campos):
            errores.append(f"{donde}: pide campos fuera de la lista blanca: {sorted(faltan)}")
        salen = fuente.nombres_rt | set(h.derivados)
        if fuera := set(h.canario.verdad) - salen:
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


def _licencia_legible(fuente: Fuente) -> str:
    spdx = fuente.licencia.spdx
    if spdx is None:
        return "por verificar"
    legible = re.sub(r"^CC-(BY(?:-SA|-NC|-ND)*)-(\d\.\d)$", lambda m: f"CC {m[1]} {m[2]}", spdx)
    return legible
