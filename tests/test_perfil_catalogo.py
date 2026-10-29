"""El perfil «catálogo» (`/mcp/catalogo`): buscar → consultar sobre las mismas herramientas."""

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from test_puerta import CHIA, CODIGO_CHIA, PREDIO, PREDIO_CHIA, ConectorFalso

from terranova import perfil_catalogo, puerta
from terranova.contrato import Sobre
from terranova.perfil_catalogo import Bm25, Documento, IndiceHerramientas, documentos


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def catalogo_mcp() -> AsyncIterator[Client[Any]]:
    puerta.usar_conectores({"arcgis-mcp": ConectorFalso({14: [PREDIO_CHIA]})})
    try:
        async with Client(puerta.crear_servidor_catalogo(con_ciclo=False)) as cliente:
            yield cliente
    finally:
        puerta.usar_conectores(None)


def _ids(indice: IndiceHerramientas, consulta: str, **kw: Any) -> list[str]:
    return [d.herramienta for d in indice.buscar(consulta, **kw)]


def test_cada_herramienta_del_catalogo_tiene_su_documento() -> None:
    docs = documentos(puerta.CATALOGO)
    assert {d.herramienta for d in docs} == set(puerta.CATALOGO.herramientas) | {"ficha_lugar"}
    assert all(d.texto for d in docs)


@pytest.mark.parametrize(
    ("consulta", "esperada"),
    [
        ("¿cuál es el predio en esta coordenada?", "igac_predio_en_punto"),
        ("población proyectada de Chía en 2026", "dane_poblacion_proyectada_municipio"),
        ("alertas por incendios en un municipio", "ideam_alertas_incendios_municipio"),
        ("código DIVIPOLA de un municipio por su nombre", "dane_divipola_buscar"),
    ],
)
def test_por_palabras_encuentra_la_herramienta(consulta: str, esperada: str) -> None:
    indice = IndiceHerramientas(documentos(puerta.CATALOGO))
    assert indice.modo == "palabras"
    assert esperada in _ids(indice, consulta)


def test_filtra_por_familia() -> None:
    indice = IndiceHerramientas(documentos(puerta.CATALOGO))
    hallados = indice.buscar("contratos del municipio", familia="contratacion")
    assert hallados and {d.familia for d in hallados} == {"contratacion"}


def test_la_ficha_va_despues_de_la_capa_especifica() -> None:
    docs = [
        Documento("ficha_lugar", "territorio", "ficha lugar resguardo area protegida cobertura"),
        Documento("ant_resguardos_en_punto", "territorio", "resguardo indigena en punto"),
        Documento("otra", "territorio", "resguardo"),
    ]
    assert _ids(IndiceHerramientas(docs), "resguardo indigena ficha lugar")[0] == "ficha_lugar"
    assert _ids(IndiceHerramientas(docs), "resguardo indigena en este punto") == [
        "ant_resguardos_en_punto",
        "otra",
        "ficha_lugar",
    ]


def test_bm25_sin_tildes_ni_plurales_ni_numeros() -> None:
    bm25 = Bm25(["Contratación pública del municipio", "Clima diario de la estación en 2024"])
    a, b = bm25.puntajes("contratos municipales de 2024")
    assert a > 0 and b == 0


class EmbebedorFalso:
    """Un vector por tema: lo que casa por significado y no por palabras."""

    def __init__(self, falla: bool = False) -> None:
        self.falla = falla

    def _v(self, texto: str) -> tuple[float, ...]:
        t = texto.lower()
        return (1.0, 0.0) if "lluvia" in t or "clima" in t else (0.0, 1.0)

    def consulta(self, texto: str) -> tuple[float, ...]:
        if self.falla:
            raise RuntimeError("caído")
        return self._v(texto)

    def documentos(self, textos: list[str]) -> list[tuple[float, ...]]:
        return [self._v(t) for t in textos]


def test_el_denso_suma_lo_que_las_palabras_no_ven() -> None:
    docs = [Documento("clima", "ambiente", "clima diario"), Documento("secop", "x", "contratos")]
    indice = IndiceHerramientas(docs, EmbebedorFalso())
    assert _ids(indice, "¿va a llover?") == []  # sin palabras en común y sin vectores
    indice.vectorizar()
    assert indice.modo == "hibrido"
    assert _ids(indice, "lluvia de mañana")[0] == "clima"


def test_si_el_embebedor_cae_busca_por_palabras() -> None:
    docs = [Documento("secop", "x", "contratos públicos")]
    indice = IndiceHerramientas(docs, EmbebedorFalso())
    indice.vectorizar()
    indice._embedder = EmbebedorFalso(falla=True)
    assert _ids(indice, "contratos") == ["secop"]


def test_el_mapa_de_familias_las_nombra_todas() -> None:
    mapa = perfil_catalogo.mapa_de_familias(puerta.CATALOGO)
    for familia in puerta.FAMILIAS:
        assert f"{familia} (" in mapa


@pytest.mark.anyio
async def test_el_perfil_trae_pocas_herramientas(catalogo_mcp: Client[Any]) -> None:
    nombres = {t.name for t in await catalogo_mcp.list_tools()}
    assert nombres == {"buscar_herramienta", "consultar", "fuente_describir"} | set(
        puerta.HERRAMIENTAS_COMUNES
    )
    buscar = next(t for t in await catalogo_mcp.list_tools() if t.name == "buscar_herramienta")
    assert buscar.description is not None and "territorio (" in buscar.description


@pytest.mark.anyio
async def test_buscar_devuelve_la_entrada_lista_para_consultar(catalogo_mcp: Client[Any]) -> None:
    r = await catalogo_mcp.call_tool("buscar_herramienta", {"pregunta": "predio en un punto"})
    hallados = r.structured_content["herramientas"]  # type: ignore[index]
    predio = next(h for h in hallados if h["herramienta"] == PREDIO)
    assert set(predio["entrada"]["required"]) == {"lon", "lat"}
    assert predio["creditos"] == 10


@pytest.mark.anyio
async def test_consultar_es_la_misma_herramienta(catalogo_mcp: Client[Any]) -> None:
    for entrada in (CHIA, '{"lon": -74.0262, "lat": 4.8619}'):
        r = await catalogo_mcp.call_tool("consultar", {"herramienta": PREDIO, "entrada": entrada})
        sobre = Sobre.model_validate(r.structured_content)
        assert sobre.estado == "encontrado" and sobre.creditos == 10
        assert sobre.datos["codigo_predial"] == CODIGO_CHIA


@pytest.mark.anyio
async def test_consultar_valida_igual_y_no_inventa_herramientas(catalogo_mcp: Client[Any]) -> None:
    with pytest.raises(ToolError, match="parametro_invalido"):
        await catalogo_mcp.call_tool("consultar", {"herramienta": PREDIO, "entrada": {"lon": 1}})
    with pytest.raises(ToolError, match=r"no_existe.*igac_predio_en_punto"):
        await catalogo_mcp.call_tool(
            "consultar", {"herramienta": "igac_predio_en_puntos", "entrada": CHIA}
        )
    with pytest.raises(ToolError, match="parametro_invalido: familia"):
        await catalogo_mcp.call_tool("buscar_herramienta", {"pregunta": "x", "familia": "nada"})
