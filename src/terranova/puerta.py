"""Puerta mínima del spike F0.3: FastMCP 4.1 con una herramienta, `igac_predio_en_punto`.

La configuración de la fuente está aquí escrita a mano; en F1 sale del catálogo (ADR-0007).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from terranova.conector import Conector, ConectorMCP, ErrorConector
from terranova.sobre import Completitud, Licencia, Procedencia, Sobre, huella

# El nombre del servicio cambia cada mes; el corte vigente se descubre a mano hasta F1.
CORTE_IGAC = "06_2026"
SERVICIO_IGAC = (
    "https://services2.arcgis.com/RVvWzU3lgJISqdke/arcgis/rest/services/"
    f"Base_Catastral_Publica_del_Gestor_IGAC_{CORTE_IGAC}/FeatureServer"
)
CAPAS_TERRENO = {"rural": 14, "urbano": 7}  # R_TERRENO, U_TERRENO
# ADR-0019: sin licencia verificada se trata como BY-SA.
LICENCIA_NO_VERIFICADA = Licencia(
    spdx="CC-BY-SA-4.0",
    url="https://creativecommons.org/licenses/by-sa/4.0/",
    uso_comercial="desconocido",
    verificada=False,
)
CONECTOR_ID = "arcgis-mcp"

_conector: Conector | None = None


def usar_conector(conector: Conector | None) -> None:
    """Inyecta el conector (las pruebas pasan uno falso)."""
    global _conector
    _conector = conector


@asynccontextmanager
async def _ciclo(_servidor: FastMCP) -> AsyncIterator[None]:
    if _conector is not None:
        yield
        return
    conector = ConectorMCP(
        os.environ.get("TERRANOVA_ARCGIS_MCP_URL", "http://127.0.0.1:9400/mcp"),
        os.environ["TERRANOVA_ARCGIS_MCP_KEY"],
    )
    await conector.abrir()
    usar_conector(conector)
    try:
        yield
    finally:
        usar_conector(None)
        await conector.cerrar()


puerta = FastMCP(
    "terranova",
    instructions="Fuentes oficiales colombianas con procedencia y licencia en cada respuesta.",
    lifespan=_ciclo,
)


async def _consultar_capa(conector: Conector, zona: str, lon: float, lat: float) -> dict[str, Any]:
    url = f"{SERVICIO_IGAC}/{CAPAS_TERRENO[zona]}"
    argumentos = {"url": url, "bbox": [lon, lat, lon, lat], "max_features": 5}
    respuesta = await conector.llamar("arcgis_query_features", argumentos)
    return {"zona": zona, "url": url, "consulta": argumentos, "respuesta": respuesta}


def _datos_predio(zona: str, atributos: dict[str, Any]) -> dict[str, Any]:
    codigo = str(atributos.get("CODIGO") or "")
    return {
        "codigo_predial": codigo,
        "codigo_predial_anterior": atributos.get("CODIGO_ANTERIOR"),
        "zona": zona,
        # La fuente trae `codigo_municipio` errado en algunos predios (Chía sale 23175): se toma
        # de los cinco primeros dígitos del código predial.
        "municipio_divipola": codigo[:5] or None,
    }


@puerta.tool(
    description=(
        "Predio catastral (IGAC) que contiene un punto: código predial nacional, código anterior, "
        "zona (rural o urbana) y municipio. Cubre los municipios con gestión catastral del IGAC; "
        "Bogotá, Medellín, Cali y otros gestores no están en esta fuente."
    ),
    annotations=ToolAnnotations(read_only_hint=True, open_world_hint=True),
)
async def igac_predio_en_punto(
    lon: Annotated[float, Field(ge=-180, le=180, description="Longitud EPSG:4326")],
    lat: Annotated[float, Field(ge=-90, le=90, description="Latitud EPSG:4326")],
) -> Sobre:
    conector = _conector
    if conector is None:
        raise ToolError("error_interno: la puerta no tiene conector")
    consultado_en = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        capas = await asyncio.gather(
            *(_consultar_capa(conector, zona, lon, lat) for zona in CAPAS_TERRENO)
        )
    except ErrorConector as exc:
        raise ToolError(f"fuente_no_disponible: {exc}") from exc

    datos: dict[str, Any] = {}
    geo_result: dict[str, Any] | None = None
    procedencia: list[Procedencia] = []
    for capa in capas:
        respuesta = capa["respuesta"]
        artefactos = respuesta.get("artifacts") or []
        rasgos = artefactos[0]["data"]["features"] if artefactos else []
        hechos = respuesta.get("facts") or {}
        datos_capa = _datos_predio(capa["zona"], rasgos[0]["properties"]) if rasgos else {}
        if datos_capa and not datos:
            datos, geo_result = datos_capa, respuesta
        total = hechos.get("total_en_servicio")
        procedencia.append(
            Procedencia(
                fuente_id=f"igac.catastro.terreno_{capa['zona']}",
                entidad="Instituto Geográfico Agustín Codazzi (IGAC)",
                url=capa["url"],
                licencia=LICENCIA_NO_VERIFICADA,
                atribucion=f"Fuente: IGAC, Base catastral pública del gestor ({CORTE_IGAC})",
                servido_desde="fuente",
                consultado_en=consultado_en,
                consulta=capa["consulta"],
                completitud=Completitud(
                    vistos=len(rasgos),
                    total=total if isinstance(total, int) else None,
                    truncado=isinstance(total, int) and len(rasgos) < total,
                ),
                transformaciones=[],
                conector=CONECTOR_ID,
                huella=huella(datos_capa),
            )
        )

    return Sobre(
        herramienta="igac_predio_en_punto@1",
        estado="encontrado" if datos else "no_encontrado",
        entrada={"lon": lon, "lat": lat},
        zona_usada={"tipo": "punto", "valor": [lon, lat], "crs": "EPSG:4326"},
        datos=datos,
        geo_result=geo_result,
        procedencia=procedencia,
        avisos=["Licencia de la fuente sin verificar: se trata como CC BY-SA 4.0 (ADR-0019)."],
        errores=[],
    )


def main() -> None:
    puerta.run(
        transport="http",
        host="127.0.0.1",
        port=int(os.environ.get("TERRANOVA_PUERTO", "8100")),
    )
