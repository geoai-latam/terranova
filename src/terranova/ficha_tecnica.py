"""Ficha técnica de una fuente (spec 08): todo lo que hay que saber antes de consultarla.

Junta tres capas sin mezclarlas:

1. lo **curado** en `catalogo/fuentes/<id>.yaml`: entidad, licencia, cobertura, lista blanca;
2. lo **cosechado** de la propia fuente en `catalogo/metadatos/<id>.yaml` (`cosecha.py`);
3. lo **medido** en el perfil (spec 07): qué es una fila, su clave, sus trampas.

Y calcula las **alertas** que salen de cruzarlas (p. ej. «declara actualización semestral y sus
datos no cambian desde 2023»). La sirven `/v1/fuentes/{id}` y la herramienta MCP
`fuente_describir`; no llama a la fuente ni usa LLM (ADR-0012).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any

from terranova.catalogo import Catalogo, Fuente, Metadatos

# días que caben en cada frecuencia que declaran las fuentes (datos.gov.co la escribe en texto)
_FRECUENCIAS = {
    "diaria": 1,
    "semanal": 7,
    "quincenal": 15,
    "mensual": 31,
    "bimestral": 62,
    "trimestral": 92,
    "cuatrimestral": 123,
    "semestral": 183,
    "anual": 366,
}
_HOLGURA = 2  # una fuente va atrasada si pasó más del doble de su frecuencia declarada


def _llano(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.strip().lower()


def alertas(fuente: Fuente, metadatos: Metadatos | None, hoy: date) -> list[str]:
    """Lo que un agente debe saber antes de usar la fuente, calculado del catálogo."""
    salida: list[str] = []
    if metadatos and metadatos.frecuencia_declarada and metadatos.datos_actualizados:
        dias = _FRECUENCIAS.get(_llano(metadatos.frecuencia_declarada))
        atraso = (hoy - metadatos.datos_actualizados).days
        if dias and atraso > _HOLGURA * dias:
            salida.append(
                f"la fuente declara actualización {metadatos.frecuencia_declarada.lower()} y sus "
                f"datos no cambian desde {metadatos.datos_actualizados.isoformat()}"
            )
    if (rango := _rango(fuente, metadatos)) and (m := _AÑO.match(rango[1])):
        if int(m.group(1)) < hoy.year - _HOLGURA:
            salida.append(f"los datos llegan hasta {rango[1]}: no hay años más recientes")
    if fuente.perfil and fuente.perfil.clave and not fuente.perfil.clave.unica:
        salida.append(
            f"una fila no es un registro único ({fuente.perfil.clave.columna}): contar filas no "
            "es contar registros; ver `perfil`"
        )
    if fuente.licencia.verificada is None:
        salida.append("licencia por verificar (ADR-0019): solo responde con llaves de evaluación")
    if fuente.uso_comercial == "no":
        salida.append("uso comercial no permitido por la fuente")
    if fuente.datos_personales != "ninguno":
        salida.append("la fuente trae datos de personas: solo salen los campos de la lista blanca")
    if metadatos is None:
        salida.append("sin ficha técnica cosechada (spec 08)")
    return salida


_AÑO = re.compile(r"^(\d{4})")


def _legible(valor: str) -> str:
    """«2015-03-31T00:00:00.000» → «2015-03-31»; «2021.00» → «2021»."""
    return valor.split("T")[0].removesuffix(".00")


def _rango(fuente: Fuente, metadatos: Metadatos | None) -> tuple[str, str] | None:
    columna = fuente.cobertura.columna_tiempo
    campo = metadatos.campos.get(columna) if metadatos and columna else None
    if campo and campo.minimo and campo.maximo:
        return _legible(campo.minimo), _legible(campo.maximo)
    return None


def _periodo(fuente: Fuente, metadatos: Metadatos | None) -> str | None:
    if fuente.cobertura.periodo:
        return fuente.cobertura.periodo
    if rango := _rango(fuente, metadatos):
        return f"{rango[0]} a {rango[1]} (mínimo y máximo de {fuente.cobertura.columna_tiempo})"
    return None


def _campos(fuente: Fuente, metadatos: Metadatos | None) -> list[dict[str, Any]]:
    salida = []
    for columna, campo in fuente.campos.items():
        de_la_fuente = metadatos.campos.get(columna) if metadatos else None
        fila: dict[str, Any] = {
            "nombre": campo.nombre,
            "columna_fuente": columna,
            "tipo": campo.tipo,
            "descripcion": campo.desc,
        }
        if de_la_fuente is not None:
            fila["fuente"] = de_la_fuente.model_dump(mode="json", exclude_none=True)
        salida.append(fila)
    return salida


def ficha_tecnica(catalogo: Catalogo, fuente_id: str, hoy: date | None = None) -> dict[str, Any]:
    """La ficha técnica completa de una fuente, como la ve un agente o una persona."""
    f = catalogo.fuentes[fuente_id]
    m = catalogo.metadatos.get(fuente_id)
    hoy = hoy or date.today()
    herramientas = sorted(
        (h for h in catalogo.herramientas.values() if h.fuente == fuente_id), key=lambda h: h.id
    )
    geografia = (
        m.geografia.model_dump(mode="json", exclude_none=True) if m and m.geografia else None
    )
    return {
        "id": f.id,
        "titulo": f.titulo,
        "entidad": f.entidad,
        "competencia": f.competencia,
        "licencia": f.licencia.model_dump(mode="json"),
        "uso_comercial": f.uso_comercial,
        "atribucion": f.atribucion,
        "acceso": {
            "protocolo": f.protocolo,
            "url": f.url,
            "clase": f.clase_acceso,
            "modo": f.modo,
            **(
                {"copia_desde": f.copia.ventana.desde.isoformat()}
                if f.copia and f.copia.ventana
                else {}
            ),
        },
        "cobertura": {
            **f.cobertura.model_dump(mode="json", exclude_none=True, exclude={"columna_tiempo"}),
            "periodo": _periodo(f, m),
            "declarada": m.cobertura_declarada if m else None,
        },
        "frescura": {
            "cache_s": f.frescura.ttl_cache_s,
            "actualizacion_esperada": f.frescura.sla_actualizacion,
            "frecuencia_declarada": m.frecuencia_declarada if m else None,
            "datos_actualizados": m.datos_actualizados.isoformat()
            if m and m.datos_actualizados
            else None,
            "corte": m.corte if m else None,
        },
        "es_geografica": geografia is not None,
        "geografia": geografia,
        "filas": m.filas if m else None,
        "datos_personales": f.datos_personales,
        "campos": _campos(f, m),
        "perfil": f.perfil.model_dump(mode="json", exclude_none=True) if f.perfil else None,
        "herramientas": [
            {"id": h.id, "pregunta": h.pregunta, "operacion": h.consulta.operacion}
            for h in herramientas
        ],
        "alertas": alertas(f, m, hoy),
        "metadatos": (
            m.model_dump(
                mode="json",
                exclude_none=True,
                include={
                    "metodo",
                    "cosechado",
                    "origen",
                    "pagina",
                    "titulo",
                    "descripcion",
                    "publicado",
                    "idioma",
                    "categoria",
                    "etiquetas",
                },
            )
            if m
            else None
        ),
        "estado": f.estado,
    }


def resumen(catalogo: Catalogo, fuente_id: str) -> dict[str, Any]:
    """Una línea por fuente para el listado: lo justo para elegir y pedir la ficha completa."""
    f = catalogo.fuentes[fuente_id]
    m = catalogo.metadatos.get(fuente_id)
    return {
        "id": f.id,
        "titulo": f.titulo,
        "entidad": f.entidad,
        "licencia": {
            "spdx": f.licencia.spdx,
            "url": f.licencia.url,
            "verificada": f.licencia.verificada,
        },
        "uso_comercial": f.uso_comercial,
        "atribucion": f.atribucion,
        "cobertura": f.cobertura.model_dump(
            mode="json", exclude_none=True, exclude={"columna_tiempo"}
        ),
        "modo": f.modo,
        "estado": f.estado,
        "es_geografica": bool(m and m.geografia),
        "periodo": _periodo(f, m),
        "datos_actualizados": m.datos_actualizados.isoformat()
        if m and m.datos_actualizados
        else None,
    }
