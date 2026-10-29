"""ADR-0033: una lista larga sale por páginas; los totales de `datos` cuentan la lista completa."""

from typing import Any

import httpx
import pytest
from fastmcp import Client
from test_geometria import _completo
from test_puerta import PREDIO

from terranova import puerta
from terranova.app import crear_api
from terranova.contrato import (
    AVISO_ELEMENTO,
    PAGINA,
    POR_PAGINA,
    Sobre,
    huella,
    paginar,
    resumir_geometria,
)
from terranova.errores import ErrorEntrada

LISTA = "pnn_areas_protegidas_en_zona"
ZONA = {"bbox": [-74.5, 4.0, -73.5, 5.0]}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def plan_evaluacion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERRANOVA_PLAN", "evaluacion")


async def _lista(n: int) -> Sobre:
    """Un sobre con `n` elementos, cada uno con su punto en `geo_result`."""
    try:
        base = await _completo()
    finally:
        puerta.usar_conectores(None)
    elementos = [{"nombre": f"Área {i}", "area_ha": i} for i in range(n)]
    datos = {"total": n, "elementos": elementos}
    rasgos = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-74.0, 4.8]},
            "properties": e,
        }
        for e in elementos
    ]
    assert base.geo_result is not None
    arte = base.geo_result.artifacts[0]
    geo = base.geo_result.model_copy(
        update={"artifacts": [arte.model_copy(update={"data": {**arte.data, "features": rasgos}})]}
    )
    return Sobre.model_validate(
        base.model_copy(
            update={"datos": datos, "huella": huella(datos), "geo_result": geo}
        ).model_dump()
    )


def _rasgos(sobre: Sobre) -> list[dict[str, Any]]:
    assert sobre.geo_result is not None
    rasgos: list[dict[str, Any]] = sobre.geo_result.artifacts[0].data["features"]
    return rasgos


@pytest.mark.anyio
async def test_una_lista_larga_sale_por_paginas() -> None:
    lista = await _lista(120)
    primera = Sobre.model_validate(paginar(lista).model_dump())  # cumple rt/1 (regla 7)
    assert primera.datos["elementos"] == lista.datos["elementos"][:POR_PAGINA]
    assert primera.datos["total"] == 120  # los totales cuentan la lista completa
    assert [r["properties"] for r in _rasgos(primera)] == primera.datos["elementos"]
    assert primera.entrada[PAGINA] == 1
    assert "1-50 de 120 (página 1 de 3)" in primera.avisos[-1]
    assert "`pagina: 2`" in primera.avisos[-1]
    ultima = paginar(lista, 3)
    assert ultima.datos["elementos"] == lista.datos["elementos"][100:]
    assert "101-120 de 120 (página 3 de 3)" in ultima.avisos[-1]
    assert "Pida" not in ultima.avisos[-1]
    fuera = paginar(lista, 4)  # no existe: vacía y dice cuántas hay, no es un error
    assert fuera.datos["elementos"] == [] and fuera.datos["total"] == 120
    assert "La página 4 no existe" in fuera.avisos[-1] and "3 página" in fuera.avisos[-1]


@pytest.mark.anyio
async def test_una_lista_corta_no_cambia() -> None:
    lista = await _lista(POR_PAGINA)
    assert paginar(lista) is lista


@pytest.mark.anyio
async def test_los_puntos_apuntan_a_su_elemento_en_la_pagina() -> None:
    pagina = resumir_geometria(paginar(await _lista(120), 2))
    assert [r["properties"] for r in _rasgos(pagina)] == [{"elemento": i} for i in range(50)]
    assert _rasgos(pagina)[0]["geometry"]["type"] == "Point"  # el punto queda entero
    assert AVISO_ELEMENTO in pagina.avisos


@pytest.mark.anyio
async def test_la_puerta_pagina_y_valida(monkeypatch: pytest.MonkeyPatch) -> None:
    lista = await _lista(120)
    pedidas: list[dict[str, Any]] = []

    async def ejecutar(ficha: str, entrada: dict[str, Any], principal: Any) -> Sobre:
        pedidas.append(entrada)
        return lista

    monkeypatch.setattr(puerta, "_ejecutar", ejecutar)
    segunda = await puerta.ejecutar(LISTA, ZONA | {PAGINA: 2})
    assert segunda.datos["elementos"][0] == {"nombre": "Área 50", "area_ha": 50}
    assert pedidas == [ZONA]  # la fuente (y la caché) ven la consulta sin la página
    assert (await puerta.ejecutar(LISTA, ZONA | {PAGINA: 2.0})).entrada[PAGINA] == 2
    for mala in ("2", 0, True, 2.5):
        with pytest.raises(ErrorEntrada, match="pagina"):
            await puerta.ejecutar(LISTA, ZONA | {PAGINA: mala})


@pytest.mark.anyio
async def test_pagina_solo_en_las_herramientas_de_lista() -> None:
    puerta.usar_conectores({})
    try:
        async with Client(puerta.puerta) as mcp:
            esquemas = {t.name: t.input_schema for t in await mcp.list_tools()}
        transporte = httpx.ASGITransport(app=crear_api())
        async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as rest:
            cero = await rest.post(f"/v1/co/ambiente/{LISTA}", json=ZONA | {PAGINA: 0})
            media = await rest.post(f"/v1/co/ambiente/{LISTA}", json=ZONA | {PAGINA: 1.5})
            texto = await rest.post(f"/v1/co/ambiente/{LISTA}", json=ZONA | {PAGINA: "1"})
            punto = {"lon": -74, "lat": 4.8, PAGINA: 1}
            sobra = await rest.post(f"/v1/co/territorio/{PREDIO}", json=punto)
    finally:
        puerta.usar_conectores(None)
    assert PAGINA in esquemas[LISTA]["properties"] and PAGINA not in esquemas[LISTA]["required"]
    assert PAGINA not in esquemas[PREDIO]["properties"]  # forma «uno»
    assert cero.status_code == 400 and sobra.status_code == 400
    assert media.status_code == 400 and texto.status_code == 400
