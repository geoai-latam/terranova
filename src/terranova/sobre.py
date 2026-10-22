"""Subconjunto mínimo de `rt/1` para el spike F0.3. Los modelos completos llegan en F1.1."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel

Estado = Literal["encontrado", "no_encontrado", "fuera_de_cobertura", "parcial"]
ServidoDesde = Literal["fuente", "copia", "curado", "cache", "obsoleto"]


class Licencia(BaseModel):
    spdx: str
    url: str
    uso_comercial: Literal["si", "no", "desconocido"]
    verificada: bool


class Completitud(BaseModel):
    vistos: int
    total: int | None
    truncado: bool


class Procedencia(BaseModel):
    fuente_id: str
    entidad: str
    url: str
    licencia: Licencia
    atribucion: str
    servido_desde: ServidoDesde
    consultado_en: str
    consulta: dict[str, Any]
    completitud: Completitud
    transformaciones: list[str]
    conector: str
    huella: str


class Sobre(BaseModel):
    contrato: Literal["rt/1"] = "rt/1"
    herramienta: str
    estado: Estado
    entrada: dict[str, Any]
    zona_usada: dict[str, Any]
    datos: dict[str, Any]
    geo_result: dict[str, Any] | None
    procedencia: list[Procedencia]
    avisos: list[str]
    errores: list[dict[str, Any]]


def huella(datos: dict[str, Any]) -> str:
    """sha256 del JSON canónico de `datos` (regla 7 del contrato)."""
    canonico = json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonico.encode()).hexdigest()
