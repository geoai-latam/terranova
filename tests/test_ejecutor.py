"""Piezas del ejecutor: entrada, plantillas, saneamiento y conversión de tipos."""

from typing import Any

import pytest

from terranova.catalogo import cargar
from terranova.contrato import MAX_TEXTO, texto_es_limpio
from terranova.ejecutor import convertir, renderizar, sanear, validar_entrada
from terranova.errores import ErrorEntrada

CATALOGO = cargar()


@pytest.mark.parametrize(
    ("herramienta", "entrada", "param"),
    [
        ("igac_predio_en_punto", {"lon": "-74", "lat": 4.8}, "lon"),
        ("igac_predio_en_punto", {"lon": True, "lat": 4.8}, "lon"),
        ("igac_predio_en_punto", {"lon": float("nan"), "lat": 4.8}, "lon"),
        ("igac_predio_en_punto", {"lon": -74.0, "lat": 95}, "lat"),
        ("igac_predio_en_punto", {"lon": -74.0, "lat": 4.8, "x": 1}, "x"),
        ("igac_predio_por_codigo", {"codigo": "25175000000000005006700000000"}, "codigo"),
        (
            "secop_contratos_municipio",
            {"municipio": "Chía' OR '1'='1", "departamento": "C"},
            "municipio",
        ),
        ("pnn_areas_protegidas_en_zona", {"bbox": [-74, 4, -75, 5]}, "bbox"),
        ("pnn_areas_protegidas_en_zona", {"bbox": [-74, 4, -73]}, "bbox"),
    ],
)
def test_entrada_invalida(herramienta: str, entrada: dict[str, Any], param: str) -> None:
    with pytest.raises(ErrorEntrada) as exc:
        validar_entrada(CATALOGO.herramientas[herramienta], entrada)
    assert exc.value.param == param


def test_entrada_valida_se_normaliza() -> None:
    h = CATALOGO.herramientas["pnn_areas_protegidas_en_zona"]
    assert validar_entrada(h, {"bbox": [-74, 4, -73, 5]}) == {"bbox": [-74.0, 4.0, -73.0, 5.0]}
    h = CATALOGO.herramientas["secop_contratos_municipio"]
    assert validar_entrada(h, {"municipio": "Chía", "departamento": "Cundinamarca"})


def test_renderizar_conserva_tipos_y_arma_texto() -> None:
    plantilla = {
        "bbox": ["{lon}", "{lat}", "{lon}", "{lat}"],
        "where": "CODIGO = '{codigo}'",
        "n": 5,
    }
    valores = {"lon": -74.0262, "lat": 4.8619, "codigo": "251750000000000050067000000000"}
    assert renderizar(plantilla, valores) == {
        "bbox": [-74.0262, 4.8619, -74.0262, 4.8619],
        "where": "CODIGO = '251750000000000050067000000000'",
        "n": 5,
    }


@pytest.mark.parametrize("sucio", ["a\u202eb", "a\x00b", "x\u2066y\u2069", "\x1b[31mrojo\x07"])
def test_sanear_quita_control_y_bidi(sucio: str) -> None:
    assert texto_es_limpio(sanear(sucio))


def test_sanear_conserva_saltos_y_corta_lo_largo() -> None:
    assert sanear("línea\ncon\ttab") == "línea\ncon\ttab"
    largo = sanear("a" * (MAX_TEXTO + 50))
    assert len(largo) == MAX_TEXTO and largo.endswith("…")


@pytest.mark.parametrize(
    ("valor", "tipo", "esperado"),
    [
        ("12149", "int", 12149),
        ("1289946058879.80", "float", 1289946058879.8),
        ("no es número", "int", None),
        (1592265600000, "date", "2020-06-16"),
        ("2023-06-26T00:00:00.000", "date", "2023-06-26"),
        ({"url": "https://www.secop.gov.co/x"}, "str", "https://www.secop.gov.co/x"),
        (None, "str", None),
        ("true", "bool", True),
    ],
)
def test_convertir(valor: Any, tipo: str, esperado: Any) -> None:
    assert convertir(valor, tipo) == esperado


def test_zona_por_divipola_dice_el_lugar() -> None:
    """Regla 11 de rt/1: con un código supuesto (05380 por Granada), el sobre dice el lugar."""
    from terranova.catalogo import cargar_cobertura
    from terranova.ejecutor import _zona

    municipios = cargar_cobertura("cobertura_catastral")["municipios"]
    h = CATALOGO.herramientas["cnmh_masacres_municipio"]
    for codigo, nombre in [("05380", "LA ESTRELLA, ANTIOQUIA"), ("05313", "GRANADA, ANTIOQUIA")]:
        zona = _zona(h, {"municipio_divipola": codigo}, municipios)
        assert zona is not None and zona.valor == codigo and zona.nombre == nombre
    desconocido = _zona(h, {"municipio_divipola": "99999"}, municipios)
    assert desconocido is not None and desconocido.nombre is None


def test_un_municipio_con_homonimos_lo_avisa() -> None:
    """Hay cinco «San Andrés»: consultar uno por código avisa de los otros, para que el agente
    pregunte o diga cuál tomó (GEO Copilot, plan de fiabilidad F4)."""
    from terranova.ejecutor import _aviso_de_homonimos, _municipios, homonimos

    otros = homonimos("88001", _municipios())
    assert [o[:5] for o in otros] == ["05647", "23670", "52835", "68669"]
    assert homonimos("25175", _municipios()) == []  # Chía es único
    assert homonimos("52835", _municipios()) == []  # SAN ANDRES DE TUMACO no es «San Andrés»
    h = CATALOGO.herramientas["cnmh_masacres_municipio"]
    aviso = _aviso_de_homonimos(h, {"municipio_divipola": "88001"})
    assert (
        aviso
        and aviso.startswith("Se consultó 88001 = SAN ANDRES")
        and "68669 SAN ANDRES (SANTANDER)" in aviso
    )
    assert _aviso_de_homonimos(h, {"municipio_divipola": "25175"}) is None


def test_la_geometria_sale_en_2d() -> None:
    """Regla 8 de rt/1: lon y lat. USGS manda la profundidad como tercera coordenada."""
    from terranova.ejecutor import a_2d

    assert a_2d({"type": "Point", "coordinates": [-72.6, 4.8, 10]}) == {
        "type": "Point",
        "coordinates": [-72.6, 4.8],
    }
    poligono = {"type": "Polygon", "coordinates": [[[0, 0, 5], [1, 0, 5], [1, 1, 5], [0, 0, 5]]]}
    assert a_2d(poligono)["coordinates"] == [[[0, 0], [1, 0], [1, 1], [0, 0]]]
    coleccion = {
        "type": "GeometryCollection",
        "geometries": [{"type": "Point", "coordinates": [1, 2, 3]}],
    }
    assert a_2d(coleccion)["geometries"][0]["coordinates"] == [1, 2]
    assert a_2d(None) is None


class _SinFilas:
    """datos-abiertos responde una tabla vacía (como Socrata ante un año sin datos)."""

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        return {
            "artifacts": [{"columns": [], "kind": "table", "rows": []}],
            "facts": {"completitud": {"vistos": 0, "total": 0, "truncado": False}},
        }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("anio", "estado"), [(2030, "fuera_de_cobertura"), (2020, "no_encontrado")]
)
async def test_un_anio_fuera_de_la_fuente_no_es_cero_casos(anio: int, estado: str) -> None:
    """Medicina Legal cubre 2015 a 2024 (cosechado): 2030 vacío es «fuera de cobertura», no «no hay
    casos»; un año dentro del rango y vacío sigue siendo `no_encontrado`."""
    from terranova.ejecutor import Ejecutor

    ej = Ejecutor(CATALOGO, {"datos-abiertos-mcp": _SinFilas()})
    sobre = await ej.ejecutar(
        "medicinalegal_homicidios_municipio",
        {"municipio_divipola": "25175", "anio": anio},
        plan="evaluacion",
    )
    assert sobre.estado == estado
    assert any("2015 a 2024" in a for a in sobre.avisos) is (estado == "fuera_de_cobertura")


@pytest.mark.parametrize(
    ("texto", "codigo"),
    [
        ("Chía", "25175"),
        ("chia", "25175"),
        ("San Andrés, Santander", "68669"),
        ("San Andrés, San Andrés y Providencia", "88001"),
        ("Tumaco", "52835"),  # SAN ANDRES DE TUMACO
        ("Bogotá D.C.", "11001"),
        ("Granada, Meta", "50313"),
    ],
)
def test_divipola_por_nombre(texto: str, codigo: str) -> None:
    """Plan de fiabilidad F4: el agente puede dar el nombre y la puerta pone el código."""
    h = CATALOGO.herramientas["cnmh_masacres_municipio"]
    assert validar_entrada(h, {"municipio_divipola": texto}) == {"municipio_divipola": codigo}


def test_divipola_por_nombre_ambiguo_lista_los_codigos() -> None:
    h = CATALOGO.herramientas["cnmh_masacres_municipio"]
    with pytest.raises(ErrorEntrada) as e:
        validar_entrada(h, {"municipio_divipola": "San Andrés"})
    assert "ambiguo" in str(e.value) and "88001" in str(e.value) and "68669" in str(e.value)
    with pytest.raises(ErrorEntrada, match="no hay un municipio"):
        validar_entrada(h, {"municipio_divipola": "Macondo"})
    with pytest.raises(ErrorEntrada, match="formato"):
        validar_entrada(h, {"municipio_divipola": "25175' OR 1=1"})


class _FilaVaciaTabla:
    """La fuente devuelve una fila pero vacía (ninguna columna de la lista blanca): todos los campos
    mapean a None (WS2). Tabla sin geometría (dane.cnpv2018 vía dane-mcp)."""

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        return {
            "artifacts": [{"kind": "table", "columns": [], "rows": [{}]}],
            "facts": {"completitud": {"vistos": 1, "total": 1, "truncado": False}},
        }


@pytest.mark.anyio
async def test_fila_con_todo_none_es_no_encontrado() -> None:
    """WS2: `encontrado` con datos={} es indistinguible de un bug; una fila cuyos campos mapean
    todos a None (forma «uno», sin derivados) se reporta honestamente como `no_encontrado`."""
    from terranova.ejecutor import Ejecutor

    ej = Ejecutor(CATALOGO, {"dane-mcp": _FilaVaciaTabla()})
    sobre = await ej.ejecutar(
        "dane_poblacion_municipio", {"municipio_divipola": "25175"}, plan="evaluacion"
    )
    assert sobre.estado == "no_encontrado"
    assert sobre.datos == {}


_PREDIO_CONSTRUCCIONES = "251750100000000430026000000000"


class _CapaRuralCae:
    """Fuente de dos capas (R_CONSTRUCCION …/12 y U_CONSTRUCCION …/3): la urbana responde con datos
    y la rural se cae. WS6: el sobre sale `parcial`, no en error entero."""

    def __init__(self) -> None:
        import json
        import pathlib

        dorada = pathlib.Path(__file__).parent / "doradas" / "igac_construcciones_en_predio.json"
        llamadas = json.loads(dorada.read_text(encoding="utf-8"))["llamadas"]
        self._urbana: dict[str, Any] = next(
            ll["respuesta"] for ll in llamadas if ll["argumentos"]["url"].endswith("/3")
        )

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        from terranova.conector import ErrorConector

        if str(argumentos.get("url", "")).endswith("/12"):
            raise ErrorConector("capa rural caída", "fuente_no_disponible")
        return self._urbana


class _TodasLasCapasCaen:
    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        from terranova.conector import ErrorConector

        raise ErrorConector("todo caído", "fuente_no_disponible")


def test_paridad_rest_mcp_entero_estricto() -> None:
    """ADR-0004: REST (modelo pydantic estricto) y MCP (`validar_entrada`) aceptan y rechazan la
    misma entrada. Antes `5.0` pasaba por MCP y lo rechazaba REST: misma herramienta, dos reglas."""
    from pydantic import ValidationError

    from terranova.app import modelo_entrada

    h = CATALOGO.herramientas["banrep_dtf_recientes"]  # `ultimas`: int
    modelo = modelo_entrada(h)

    def rest_acepta(e: dict[str, Any]) -> bool:
        try:
            modelo(**e)
            return True
        except ValidationError:
            return False

    def mcp_acepta(e: dict[str, Any]) -> bool:
        try:
            validar_entrada(h, dict(e))
            return True
        except ErrorEntrada:
            return False

    for e in ({"ultimas": 5}, {"ultimas": 5.0}, {"ultimas": "5"}, {"ultimas": True}):
        assert rest_acepta(e) == mcp_acepta(e), e
    assert mcp_acepta({"ultimas": 5}) and not mcp_acepta({"ultimas": 5.0})  # 5.0 no es 5


@pytest.mark.anyio
async def test_una_capa_caida_degrada_a_parcial() -> None:
    """WS6: con una capa caída y otra con datos, el sobre es `parcial` con aviso (no «encontrado»
    ni error entero): «no se pudo» de una parte no se disfraza de dato completo."""
    from terranova.ejecutor import Ejecutor

    ej = Ejecutor(CATALOGO, {"arcgis-mcp": _CapaRuralCae()})
    sobre = await ej.ejecutar(
        "igac_construcciones_en_predio", {"codigo": _PREDIO_CONSTRUCCIONES}, plan="evaluacion"
    )
    assert sobre.estado == "parcial"
    assert any("no respondieron" in a for a in sobre.avisos)
    assert sobre.datos.get("elementos")  # los datos de la capa que sí respondió


@pytest.mark.anyio
async def test_todas_las_capas_caidas_falla_entero() -> None:
    """Si TODAS las capas se caen no hay parcial que valga: se falla como antes (fuente caída)."""
    from terranova.ejecutor import Ejecutor
    from terranova.errores import ErrorEjecucion

    ej = Ejecutor(CATALOGO, {"arcgis-mcp": _TodasLasCapasCaen()})
    with pytest.raises(ErrorEjecucion):
        await ej.ejecutar(
            "igac_construcciones_en_predio", {"codigo": _PREDIO_CONSTRUCCIONES}, plan="evaluacion"
        )
