"""ADR-0040: las páginas siguen en la fuente más allá del tope de la consulta.

Un visor que pide la capa entera de la UPME (2 192 elementos, tope de 1 000 por consulta) la tiene
que poder recorrer completa, sin repetidos ni faltantes, y saber el total desde la primera página.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from terranova import puerta
from terranova.app import modelo_entrada
from terranova.contrato import PAGINA, TAM_PAGINA, Sobre
from terranova.errores import ErrorEntrada

UPME = "upme_infraestructura_energetica_en_zona"
ZONA = {"bbox": [-79.0, -4.3, -66.8, 12.5]}
TOTAL = 2192


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def plan_evaluacion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERRANOVA_PLAN", "evaluacion")


class CopiaFalsa:
    """`consultar_copia` sobre 2 192 elementos ordenados, con `limite` y `desde` como la copia."""

    def __init__(self) -> None:
        self.llamadas: list[dict[str, Any]] = []
        self.resumenes: list[dict[str, Any]] = []

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        assert herramienta == "consultar_copia"
        if "agregados" in argumentos:
            return self._resumen(argumentos)
        self.llamadas.append(argumentos)
        desde, limite = int(argumentos.get("desde") or 0), int(argumentos["limite"])
        rasgos = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-74.0 + i / 10000, 4.6]},
                "properties": {
                    "categoria": "subestación" if i % 2 else "línea de transmisión",
                    "nombre": f"Elemento {i:04d}",
                    "capacidad_mw": 1.0,
                },
            }
            for i in range(desde, min(desde + limite, TOTAL))
        ]
        hechos = {
            "servido_desde": "copia",
            "consultado_en": "2026-11-05T00:00:00+00:00",
            "copia": {"version": "v1", "huella": "x", "filas": TOTAL},
            "completitud": {"vistos": len(rasgos), "total": TOTAL, "truncado": len(rasgos) < TOTAL},
        }
        fc = {"type": "FeatureCollection", "features": rasgos}
        return {
            "artifacts": [{"kind": "feature_collection", "crs": "EPSG:4326", "data": fc}],
            "facts": hechos,
        }

    def _resumen(self, argumentos: dict[str, Any]) -> dict[str, Any]:
        """El `group by` o el agregado de la lista entera (P0.7), como lo da la copia."""
        self.resumenes.append(argumentos)
        if argumentos.get("group"):
            filas = [
                {"categoria": "subestación", "n": TOTAL // 2},
                {"categoria": "línea de transmisión", "n": TOTAL - TOTAL // 2},
            ]
        else:
            filas = [{"v": float(TOTAL)}]
        rasgos = [{"type": "Feature", "geometry": None, "properties": f} for f in filas]
        fc = {"type": "FeatureCollection", "features": rasgos}
        hechos = {
            "servido_desde": "copia",
            "consultado_en": "2026-11-05T00:00:00+00:00",
            "copia": {"version": "v1", "huella": "x", "filas": TOTAL},
            "completitud": {"vistos": len(filas), "total": len(filas), "truncado": False},
        }
        return {
            "artifacts": [{"kind": "feature_collection", "crs": "EPSG:4326", "data": fc}],
            "facts": hechos,
        }


def _aviso(sobre: Sobre, texto: str) -> str:
    return next(a for a in sobre.avisos if texto in a)


async def _pagina(copia: CopiaFalsa, **extra: int) -> Sobre:
    puerta.usar_conectores({"copia": copia})
    try:
        return await puerta.ejecutar(UPME, {**ZONA, **extra})
    finally:
        puerta.usar_conectores(None)


@pytest.mark.anyio
async def test_un_visor_recorre_la_capa_entera_de_1000_en_1000() -> None:
    copia = CopiaFalsa()
    nombres: list[str] = []
    for pagina in (1, 2, 3):
        sobre = await _pagina(copia, pagina=pagina, por_pagina=1000)
        assert sobre.datos["total"] == TOTAL  # el total de la fuente, en todas las páginas
        # P0.7: los resúmenes son de la lista entera, iguales en todas las páginas
        assert sum(sobre.datos["por_tipo"].values()) == TOTAL
        assert sobre.datos["capacidad_mw_total"] == TOTAL
        nombres += [e["nombre"] for e in sobre.datos["elementos"]]
        assert sobre.entrada[PAGINA] == pagina
    assert len(nombres) == TOTAL and len(set(nombres)) == TOTAL
    assert nombres[0] == "Elemento 0000" and nombres[-1] == "Elemento 2191"
    # la primera página sale de la consulta de siempre; las otras siguen en la copia con `desde`
    assert [(a.get("desde", 0), a["limite"]) for a in copia.llamadas] == [
        (0, 1000),
        (1000, 1000),
        (2000, 1000),
    ]
    assert _aviso(sobre, "Van los elementos 2001-2192 de 2192 (página 3 de 3)")
    assert not any(a.startswith("Vinieron ") for a in sobre.avisos)


@pytest.mark.anyio
async def test_un_agente_sigue_de_50_en_50_mas_alla_del_tope() -> None:
    copia = CopiaFalsa()
    primera = await _pagina(copia)
    assert len(primera.datos["elementos"]) == 50 and primera.datos["total"] == TOTAL
    assert "`pagina: 2`" in _aviso(primera, "1-50 de 2192 (página 1 de 44)")
    assert not any(a.startswith("Vinieron ") for a in primera.avisos)  # ya no es «acote»
    visor = await _pagina(copia, pagina=1, por_pagina=1000)
    assert "`pagina: 2`" in _aviso(visor, "1-1000 de 2192 (página 1 de 3)")
    assert not any(a.startswith("Vinieron ") for a in visor.avisos)
    # la página 21 (1001-1050) ya no está en lo que trae una consulta: va a la copia
    sobre = await _pagina(copia, pagina=21)
    assert sobre.datos["elementos"][0]["nombre"] == "Elemento 1000"
    assert copia.llamadas[-1]["desde"] == 1000 and copia.llamadas[-1]["limite"] == 50
    assert sobre.geo_result is not None
    assert len(sobre.geo_result.artifacts[0].data["features"]) == 50
    ultima = await _pagina(copia, pagina=44)
    assert len(ultima.datos["elementos"]) == 42
    assert "Pida" not in _aviso(ultima, "2151-2192 de 2192 (página 44 de 44)")
    fuera = await _pagina(copia, pagina=45)
    assert fuera.estado == "encontrado" and fuera.datos["elementos"] == []
    assert _aviso(fuera, "La página 45 no existe: hay 2192 elementos en 44 página(s)")
    assert not any("no hay subestaciones" in a for a in fuera.avisos)


@pytest.mark.anyio
async def test_por_pagina_fuera_de_rango_es_error_de_entrada() -> None:
    with pytest.raises(ErrorEntrada):
        await _pagina(CopiaFalsa(), por_pagina=1001)
    with pytest.raises(ErrorEntrada):
        await _pagina(CopiaFalsa(), por_pagina=0)


def test_mcp_y_rest_publican_por_pagina() -> None:
    h = puerta.CATALOGO.herramientas[UPME]
    assert puerta.esquema_entrada(h)["properties"][TAM_PAGINA]["maximum"] == 1000
    assert TAM_PAGINA in modelo_entrada(h).model_fields


class Grabado:
    """Responde lo grabado en una dorada, para la misma llamada."""

    def __init__(self, llamadas: list[dict[str, Any]]) -> None:
        self.llamadas = llamadas

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.llamadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                respuesta: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return respuesta
        raise AssertionError(f"llamada no grabada: {herramienta} {argumentos}")


@pytest.mark.anyio
async def test_juntar_no_deja_el_total_de_filas_en_el_aviso_de_pagina() -> None:
    """Buscapina (36344): la fuente trae 28 filas, una por vía, que `juntar` deja en 14. El aviso
    decía «van los elementos 1-14 de 28 (página 1 de 1)»."""
    herramienta = "invima_medicamento_en_renovacion_por_expediente"
    dorada = Path(__file__).parent / "doradas" / f"{herramienta}.json"
    llamadas = json.loads(dorada.read_text(encoding="utf-8"))["llamadas"]
    puerta.usar_conectores({"datos-abiertos-mcp": Grabado(llamadas)})
    try:
        sobre = await puerta.ejecutar(herramienta, {"expediente": 36344})
    finally:
        puerta.usar_conectores(None)
    assert len(sobre.datos["elementos"]) == 14
    assert not [a for a in sobre.avisos if "de 28" in a]
