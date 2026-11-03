"""Piezas del ejecutor: entrada, plantillas, saneamiento y conversión de tipos."""

import math
from typing import Any

import pytest

from terranova.catalogo import cargar
from terranova.contrato import MAX_TEXTO, texto_es_limpio
from terranova.ejecutor import convertir, renderizar, sanear, validar_entrada
from terranova.errores import ErrorEntrada

CATALOGO = cargar()
POLIGONO = "urt_microzona_en_poligono"


def _lote(anillo: list[list[Any]]) -> dict[str, Any]:
    return {"type": "Polygon", "coordinates": [anillo]}


def _circulo(vertices: int) -> list[list[float]]:
    """Un anillo cerrado de `vertices` vértices (el último repite el primero)."""
    n = vertices - 1
    pasos = [2 * math.pi * i / n for i in range(n)]
    puntos = [[-74 + 0.1 * math.cos(t), 4 + 0.1 * math.sin(t)] for t in pasos]
    return [*puntos, puntos[0]]


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
        (POLIGONO, {"poligono": {"type": "Point", "coordinates": [-74, 4]}}, "poligono"),
        (POLIGONO, {"poligono": {"type": "MultiPolygon", "coordinates": []}}, "poligono"),
        (POLIGONO, {"poligono": [-74, 4, -73, 5]}, "poligono"),
        (POLIGONO, {"poligono": _lote([[-74, 4], [-73.5, 4], [-74, 4]])}, "poligono"),
        (
            POLIGONO,
            {"poligono": _lote([[-74, 4], [-73.5, 4], [-73.5, 4.5], [-74, 4.5]])},
            "poligono",
        ),
        (POLIGONO, {"poligono": _lote([[-74, 4], ["x", 4], [-73.5, 4.5], [-74, 4]])}, "poligono"),
        (POLIGONO, {"poligono": _lote([[-74, 4], [-73, 95], [-73.5, 4.5], [-74, 4]])}, "poligono"),
        (
            POLIGONO,
            {"poligono": _lote([[-74, 4, 9], [-73, 5, 9], [-74, 5, 9], [-74, 4, 9]])},
            "poligono",
        ),
        (POLIGONO, {"poligono": _lote([[-75, 4], [-73.5, 4], [-73.5, 4.5], [-75, 4]])}, "poligono"),
        (POLIGONO, {"poligono": _lote(_circulo(501))}, "poligono"),
    ],
)
def test_entrada_invalida(herramienta: str, entrada: dict[str, Any], param: str) -> None:
    with pytest.raises(ErrorEntrada) as exc:
        validar_entrada(CATALOGO.herramientas[herramienta], entrada)
    assert exc.value.param == param


def test_entrada_valida_se_normaliza() -> None:
    h = CATALOGO.herramientas["pnn_areas_protegidas_en_zona"]
    assert validar_entrada(h, {"bbox": [-74, 4, -73, 5]}) == {"bbox": [-74.0, 4.0, -73.0, 5.0]}
    h = CATALOGO.herramientas[POLIGONO]
    lote = _lote([[-74, 4], [-73.9, 4], [-73.9, 4.1], [-74, 4]]) | {"crs": "cualquiera"}
    assert validar_entrada(h, {"poligono": lote})["poligono"] == {
        "type": "Polygon",
        "coordinates": [[[-74.0, 4.0], [-73.9, 4.0], [-73.9, 4.1], [-74.0, 4.0]]],
    }  # solo lo suyo: lo que venga de más no llega al SQL
    assert validar_entrada(h, {"poligono": _lote(_circulo(500))})
    h = CATALOGO.herramientas["secop_contratos_municipio"]
    assert validar_entrada(h, {"municipio": "Chía", "departamento": "Cundinamarca"})


@pytest.mark.parametrize(
    ("escrita", "en_la_relatoria"),
    [
        ("T-760-08", "T-760-08"),
        ("t-622-16", "T-622-16"),
        ("C-155A-93", "C-155A-93"),
        # la relatoría guarda las de unificación sin el primer guion: SU-214-16.htm es una página
        # vacía con estado 200
        ("SU-214-16", "SU214-16"),
        ("SU214-16", "SU214-16"),
        (" su-095-18 ", "SU095-18"),
    ],
)
def test_la_sentencia_queda_como_la_guarda_la_relatoria(escrita: str, en_la_relatoria: str) -> None:
    h = CATALOGO.herramientas["corte_constitucional_resuelve"]
    entrada = validar_entrada(h, {"anio": 2016, "sentencia": escrita})
    assert entrada["sentencia"] == en_la_relatoria


def test_la_sentencia_no_acepta_rutas() -> None:
    h = CATALOGO.herramientas["corte_constitucional_resuelve"]
    for mala in ("T-760/08", "../T-760-08", "X-1-08", "T760-08"):
        with pytest.raises(ErrorEntrada):
            validar_entrada(h, {"anio": 2008, "sentencia": mala})


@pytest.mark.parametrize(
    ("anillo", "motivo"),
    [
        # un moño: los lados 1 y 3 se cruzan en el centro
        ([[-74, 4], [-73.9, 4.1], [-73.9, 4], [-74, 4.1], [-74, 4]], "se cruza consigo mismo"),
        ([[-74, 4], [-73.9, 4], [-73.8, 4], [-74, 4]], "no tiene área"),  # alineados
        ([[-74, 4], [-74, 4], [-73.9, 4], [-74, 4]], "menos de 3 vértices distintos"),
    ],
)
def test_un_poligono_degenerado_se_rechaza_con_el_motivo(
    anillo: list[list[float]], motivo: str
) -> None:
    """Antes se reparaba en la base (ST_MakeValid) y salía «no encontrado» (GEO Copilot,
    2026-11-03)."""
    with pytest.raises(ErrorEntrada, match=motivo) as exc:
        validar_entrada(CATALOGO.herramientas[POLIGONO], {"poligono": _lote(anillo)})
    assert exc.value.codigo == "parametro_invalido"


def test_un_vertice_repetido_seguido_no_es_un_cruce() -> None:
    anillo: list[list[Any]] = [[-74, 4], [-73.9, 4], [-73.9, 4], [-73.9, 4.1], [-74, 4.1], [-74, 4]]
    assert validar_entrada(CATALOGO.herramientas[POLIGONO], {"poligono": _lote(anillo)})


@pytest.mark.parametrize(
    "anillo",
    [_circulo(501), [[-75.0, 4.0], [-73.5, 4.0], [-73.5, 4.5], [-75.0, 4.0]]],
)
def test_pasar_los_topes_es_zona_demasiado_grande(anillo: list[list[float]]) -> None:
    """La spec 01 promete `zona_demasiado_grande` para un polígono sobre el tope."""
    with pytest.raises(ErrorEntrada) as exc:
        validar_entrada(CATALOGO.herramientas[POLIGONO], {"poligono": _lote(anillo)})
    assert exc.value.codigo == "zona_demasiado_grande"


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


def test_un_marcador_sin_tildes_busca_con_y_sin_tilde() -> None:
    """El INVIMA escribe ACETAMINOFEN; quien pregunta escribe «acetaminofén» (medido el
    2026-11-02 en i7cb-raxc: 18 productos con la tilde, 289 con el comodín)."""
    where = "upper(p) like upper('%{p:sin_tildes}%') AND x = '{p}'"
    assert renderizar(where, {"p": "acetaminofén"}) == (
        "upper(p) like upper('%acetaminof_n%') AND x = 'acetaminofén'"
    )
    assert renderizar("{p:sin_tildes}", {"p": "Bogotá"}) == "Bogot_"


def test_un_marcador_ascii_quita_tildes_y_enes() -> None:
    """La relatoría de Colombia Compra devuelve sus 7 761 conceptos si la búsqueda trae una letra
    fuera de ASCII (medido el 2026-11-03: «daño antijurídico», 7 761; «dano antijuridico», 8)."""
    assert renderizar("{p:ascii}", {"p": "daño antijurídico"}) == "dano antijuridico"
    assert renderizar("q={p:ascii}&r={p}", {"p": "Ñuñoa"}) == "q=Nunoa&r=Ñuñoa"


def test_el_tema_sale_del_html_sin_etiquetas_ni_entidades() -> None:
    """El tema de un concepto es la primera negrilla de su resumen, con entidades (medido el
    2026-11-03 en C-1491 de 2026)."""
    from terranova.ejecutor import mapear_fila

    h = CATALOGO.herramientas["ancp_conceptos_buscar"]
    contenido = (
        '<p style="text-align: justify;"><strong>MODIFICACIÓN DE LOS CONTRATOS ESTATALES \u2013 '
        "Prórroga &#8211; Procedencia &#8211;\n<em>Autonomía</em> de la voluntad </strong></p>"
        "<p>Texto del concepto…</p>"
    )
    fila = mapear_fila(
        h, CATALOGO.fuentes[h.fuente], {"id": 1, "content.rendered": contenido}, None
    )
    raya = "\u2013"
    assert fila["tema"] == (
        f"MODIFICACIÓN DE LOS CONTRATOS ESTATALES {raya} Prórroga {raya} Procedencia {raya} "
        "Autonomía de la voluntad"
    )
    assert "content.rendered" not in fila and "contenido" not in fila
    sin_negrilla = mapear_fila(
        h, CATALOGO.fuentes[h.fuente], {"id": 2, "content.rendered": "<p>Sin tema</p>"}, None
    )
    assert sin_negrilla["tema"] is None


@pytest.mark.parametrize("sucio", ["a\u202eb", "a\x00b", "x\u2066y\u2069", "\x1b[31mrojo\x07"])
def test_sanear_quita_control_y_bidi(sucio: str) -> None:
    assert texto_es_limpio(sanear(sucio))


def test_sanear_conserva_saltos_y_corta_lo_largo() -> None:
    assert sanear("línea\ncon\ttab") == "línea\ncon\ttab"
    largo = sanear("a" * (MAX_TEXTO + 50))
    assert len(largo) == MAX_TEXTO and largo.endswith("…")


def test_sanear_repara_la_i_partida() -> None:
    """SECOP escribe «Medellín» con la «í» partida: U+FFFD y un guion suave (medido el 2026-11-03
    en gra4-pcp2, 223 466 filas)."""
    assert (
        sanear("Colombia;  Antioquia ;  Medell\ufffd\u00adn") == "Colombia;  Antioquia ;  Medellín"
    )
    assert sanear("Bol\ufffd\u00advar y Quind\ufffd\u00ado") == "Bolívar y Quindío"
    assert sanear("sin guion \ufffd") == "sin guion \ufffd"


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
    mapean a None (WS2). Tabla sin geometría (dane.cnpv2018, por su copia)."""

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        return {
            "artifacts": [{"kind": "table", "columns": [], "rows": [{}]}],
            "facts": {
                "completitud": {"vistos": 1, "total": 1, "truncado": False},
                "consultado_en": "2026-10-29T13:00:00+00:00",  # de cuándo es la copia
            },
        }


@pytest.mark.anyio
async def test_fila_con_todo_none_es_no_encontrado() -> None:
    """WS2: `encontrado` con datos={} es indistinguible de un bug; una fila cuyos campos mapean
    todos a None (forma «uno», sin derivados) se reporta honestamente como `no_encontrado`."""
    from terranova.ejecutor import Ejecutor

    ej = Ejecutor(CATALOGO, {"copia": _FilaVaciaTabla()})
    sobre = await ej.ejecutar(
        "dane_poblacion_municipio", {"municipio_divipola": "25175"}, plan="evaluacion"
    )
    assert sobre.estado == "no_encontrado"
    assert sobre.datos == {}


class _ContoPeroNoEntrego:
    """El conector cuenta N elementos y su página llega vacía (SINCHI, 2026-10-28): los hechos lo
    dicen («vistos 0 de 1, truncado») pero no hay ningún elemento."""

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        return {
            "artifacts": [
                {
                    "kind": "feature_collection",
                    "data": {"type": "FeatureCollection", "features": []},
                }
            ],
            "facts": {"completitud": {"vistos": 0, "total": 1, "truncado": True}},
        }


@pytest.mark.anyio
async def test_vacio_con_total_no_es_no_encontrado() -> None:
    """Si la fuente dice que hay elementos y no entrega ninguno, es «no se pudo», nunca «no
    encontrado» (CLAUDE.md: honestidad de estado)."""
    from terranova.ejecutor import Ejecutor
    from terranova.errores import ErrorEjecucion

    ej = Ejecutor(CATALOGO, {"arcgis-mcp": _ContoPeroNoEntrego()})
    with pytest.raises(ErrorEjecucion) as exc:
        await ej.ejecutar("ant_resguardos_en_punto", {"lon": -70.5, "lat": 0.8})
    assert exc.value.codigo == "fuente_respuesta_invalida"
    assert "no entregó ninguno" in str(exc.value)


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
    misma entrada. `5.0` es un entero en JSON Schema, y Schemathesis lo manda: vale en los dos."""
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

    for e in (
        {"ultimas": 5},
        {"ultimas": 5.0},
        {"ultimas": 5.5},
        {"ultimas": "5"},
        {"ultimas": True},
    ):
        assert rest_acepta(e) == mcp_acepta(e), e
    assert mcp_acepta({"ultimas": 5.0}) and not mcp_acepta({"ultimas": 5.5})


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


def test_enteros_y_fechas_fuera_de_lo_real() -> None:
    from terranova.ejecutor import _valor

    assert _valor("anio", "int", 2030) == 2030  # lo dice la cobertura, no la entrada
    assert _valor("desde", "fecha", "2024-02-29") == "2024-02-29"
    for nombre, tipo, valor in (
        ("anio", "int", 1899),
        ("anio", "int", 2101),
        ("nit_entidad", "int", -1),
        ("nit_entidad", "int", 10**16),
        ("desde", "fecha", "2026-13-45"),
        ("desde", "fecha", "2023-02-29"),
    ):
        with pytest.raises(ErrorEntrada):
            _valor(nombre, tipo, valor)


def test_diferencia_con_la_anterior_vigente() -> None:
    """SECOP da el valor total del contrato tras cada modificación: lo añadido es la diferencia con
    la anterior vigente. Una cancelada no cuenta ni es «la anterior» (CO1.PCCNTR.7143094)."""
    from terranova.ejecutor import derivar_resultado, derivar_secuencia

    h = CATALOGO.herramientas["secop_modificaciones_contrato"]
    elementos: list[dict[str, Any]] = [
        {"vigente": "sí", "valor_contrato_tras_cambio": 24476320.0, "dias_extendidos": 61},
        {"vigente": "no", "valor_contrato_tras_cambio": 99000000.0, "dias_extendidos": 30},
        {"vigente": "sí", "valor_contrato_tras_cambio": 32446432.0, "dias_extendidos": 62},
        {"vigente": None, "valor_contrato_tras_cambio": None, "dias_extendidos": None},
        {"vigente": "sí", "valor_contrato_tras_cambio": 40574368.0, "dias_extendidos": 61},
    ]
    derivar_secuencia(h, elementos)
    assert [e["cambio_valor"] for e in elementos] == [None, None, 7970112.0, None, 8127936.0]

    def agregado(nombre: str) -> Any:
        return derivar_resultado(h.derivados[nombre], elementos, None)

    assert agregado("valor_actual") == 40574368.0
    assert agregado("valor_tras_primera") == 24476320.0
    assert agregado("cambio_valor_desde_primera") == 16098048.0
    assert agregado("dias_extendidos_total") == 184  # sin los 30 de la cancelada
    assert agregado("modificaciones_vigentes") == 3
    assert agregado("numero_registros") == 5


def test_solo_si_no_aplica_a_un_derivado_por_elemento() -> None:
    from pydantic import ValidationError

    from terranova.catalogo import Derivado

    with pytest.raises(ValidationError, match="no usa `solo_si`"):
        Derivado.model_validate(
            {"de": "columna", "campo": "x", "solo_si": {"campo": "y", "valores": ["1"]}}
        )


class _SecopFalso:
    """p6dx da las fases de un proceso de compra (con una basura que no es un id de SECOP) y
    hgi6 contesta solo si la consulta principal pide esas fases."""

    def __init__(self) -> None:
        self.llamadas: list[dict[str, Any]] = []

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        self.llamadas.append(argumentos)
        if argumentos["id"] == "p6dx-8zbt":
            filas = [
                {"id_del_proceso": "CO1.REQ.3004001"},
                {"id_del_proceso": "CO1.REQ.2978420"},
                {"id_del_proceso": "x') OR 1=1 --"},
            ]
        elif "'CO1.REQ.3004001'" in argumentos["where"]:
            filas = [{"id_procedimiento": "CO1.REQ.3004001", "proveedor": "TEAK INGENIERIA S.A.S"}]
        else:
            filas = []
        return {"artifacts": [{"kind": "table", "rows": filas}], "facts": {}}


@pytest.mark.anyio
async def test_la_previa_traduce_el_proceso_de_compra_a_sus_fases() -> None:
    """El contrato trae CO1.BDOS y los proponentes cuelgan de CO1.REQ: la previa traduce, y lo que
    devuelve la fuente solo entra a la consulta si cumple el patrón (nada de inyección)."""
    from terranova.ejecutor import Ejecutor

    falso = _SecopFalso()
    ej = Ejecutor(CATALOGO, {"datos-abiertos-mcp": falso})
    sobre = await ej.ejecutar(
        "secop_proponentes_proceso", {"id_proceso": "CO1.BDOS.2898382"}, plan="evaluacion"
    )
    principal = falso.llamadas[1]["where"]
    assert principal == "id_procedimiento IN ('CO1.REQ.2978420', 'CO1.REQ.3004001')"
    assert sobre.estado == "encontrado" and sobre.datos["numero_proponentes"] == 1
    assert [p.fuente_id for p in sobre.procedencia] == [
        "cce.secop2.procesos",
        "cce.secop2.proponentes",
    ]


@pytest.mark.anyio
async def test_sin_fases_la_previa_no_encuentra_nada() -> None:
    from terranova.ejecutor import Ejecutor

    class _SinFases(_SecopFalso):
        async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
            self.llamadas.append(argumentos)
            return {"artifacts": [{"kind": "table", "rows": []}], "facts": {}}

    falso = _SinFases()
    sobre = await Ejecutor(CATALOGO, {"datos-abiertos-mcp": falso}).ejecutar(
        "secop_proponentes_proceso", {"id_proceso": "CO1.BDOS.1"}, plan="evaluacion"
    )
    assert falso.llamadas[1]["where"] == "id_procedimiento IN ('')"
    assert sobre.estado == "no_encontrado"


def test_avisos_de_la_ficha() -> None:
    """Patrón A: el vacío de garantías no es «no hay garantía», y un solo proponente se avisa."""
    from terranova.contrato import Sobre
    from terranova.ejecutor import avisos_de_la_ficha

    def sobre(estado: str, datos: dict[str, Any]) -> Any:
        return Sobre.model_construct(estado=estado, datos=datos, avisos=[])

    garantias = CATALOGO.herramientas["secop_garantias_contrato"]
    fuente = CATALOGO.fuentes[garantias.fuente]
    assert fuente.cobertura.aviso_vacio
    vacio_garantias = avisos_de_la_ficha(garantias, fuente, sobre("no_encontrado", {}))
    assert vacio_garantias == [fuente.cobertura.aviso_vacio.strip()]
    assert not vacio_garantias[0].endswith("\n")
    assert avisos_de_la_ficha(garantias, fuente, sobre("encontrado", {"x": 1})) == []

    prop = CATALOGO.herramientas["secop_proponentes_proceso"]
    fp = CATALOGO.fuentes[prop.fuente]
    uno = avisos_de_la_ficha(prop, fp, sobre("encontrado", {"numero_proponentes": 1}))
    assert len(uno) == 1 and uno[0].startswith("Un solo proponente")
    assert avisos_de_la_ficha(prop, fp, sobre("encontrado", {"numero_proponentes": 3})) == []
    vacio = avisos_de_la_ficha(prop, fp, sobre("no_encontrado", {}))
    assert vacio == [a.texto for a in prop.avisos if a.cuando == "vacio"]  # la propia reemplaza
    assert avisos_de_la_ficha(prop, fp, sobre("fuera_de_cobertura", {})) == []

    # fuera de cobertura, la ficha dice dónde está lo que no cubre: la serie vieja del MinTIC
    internet = CATALOGO.herramientas["mintic_internet_fijo_municipio"]
    fi = CATALOGO.fuentes[internet.fuente]
    fuera = avisos_de_la_ficha(internet, fi, sobre("fuera_de_cobertura", {}))
    assert len(fuera) == 1 and "mintic_internet_fijo_municipio_2016_2023" in fuera[0]
    assert fuera[0] not in avisos_de_la_ficha(internet, fi, sobre("no_encontrado", {}))


def test_fechas_del_invima_en_iso_y_sin_relleno() -> None:
    """El CUM escribe mm/dd/aaaa y pone años de relleno (3000, 1900, 9999) en el vencimiento:
    salen en ISO, y el relleno sale vacío, no como fecha (medido el 2026-11-02 en i7cb-raxc)."""
    from terranova.catalogo import Campo
    from terranova.ejecutor import _validar, fecha_en_orden

    assert fecha_en_orden("06/15/2016", "mda") == "2016-06-15"
    assert fecha_en_orden("15/06/2016", "dma") == "2016-06-15"
    assert fecha_en_orden("2016-03-25T00:00:00.000", "mda") == "2016-03-25T00:00:00.000"
    campo = Campo(
        nombre="fecha_vencimiento",
        tipo="date",
        desc="vencimiento",
        orden_fecha="mda",
        anios_validos=(1950, 2049),
    )
    for relleno in ("01/01/3000", "12/31/3000", "01/01/1900", "01/01/9999"):
        assert _validar(campo, convertir(fecha_en_orden(relleno, "mda"), "date")) is None
    assert _validar(campo, convertir(fecha_en_orden("04/14/2026", "mda"), "date")) == "2026-04-14"
    with pytest.raises(ValueError):
        Campo(nombre="n", tipo="str", desc="x", orden_fecha="mda")


def test_cifras_con_signo_de_pesos() -> None:
    """Las 10 000 empresas de Supersociedades escriben «$84.95», «$ 2.31» y «-$0.00»: salen como
    número, y el signo de una pérdida pequeña se conserva (medido el 2026-11-02 en 6cat-2gcs)."""
    import math

    from terranova.catalogo import Campo

    h = CATALOGO.herramientas["supersociedades_empresa_grande_por_nit"]
    fuente = CATALOGO.fuentes[h.fuente]
    from terranova.ejecutor import mapear_fila

    fila = mapear_fila(
        h,
        fuente,
        {
            "ingresos_operacionales": "$ 2.31",
            "ganancia_p_rdida": "-$0.00",
            "total_activos": "$84.95",
        },
        None,
    )
    assert fila["ingresos_operacionales"] == 2.31
    assert fila["total_activos"] == 84.95
    assert fila["ganancia_perdida"] == 0 and math.copysign(1, fila["ganancia_perdida"]) == -1
    with pytest.raises(ValueError):
        Campo(nombre="n", tipo="str", desc="x", moneda=True)


class _PoliciaFalsa:
    """La consulta del municipio y la del corte de la fuente (la que pide `hasta_mes`)."""

    def __init__(self, municipio: list[dict[str, Any]], corte_falla: bool = False) -> None:
        self.municipio = municipio
        self.corte_falla = corte_falla

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        if "hasta_mes" in argumentos["select"]:
            if self.corte_falla:
                raise RuntimeError("se cayó")
            filas = [{"hasta_mes": "07", "meses": "7"}]
        else:
            filas = self.municipio
        return {"artifacts": [{"kind": "table", "rows": filas}], "facts": {}}


@pytest.mark.anyio
async def test_el_complemento_dice_hasta_que_mes_publica_la_fuente() -> None:
    """Medellín 2026 tenía 2 955 hurtos de vehículos hasta julio, frente a 5 916 en todo 2025: sin
    decir el corte, «el hurto bajó a la mitad» (medido el 2026-11-02)."""
    from terranova.ejecutor import Ejecutor

    filas = [{"tipo_de_hurto": "HURTO MOTOCICLETAS", "genero": "MASCULINO", "casos": "1913"}]
    ej = Ejecutor(CATALOGO, {"datos-abiertos-mcp": _PoliciaFalsa(filas)})
    entrada = {"municipio_divipola": "05001", "anio": 2026}
    sobre = await ej.ejecutar("policia_hurto_vehiculos_municipio", entrada, plan="evaluacion")
    assert sobre.estado == "encontrado"
    assert sobre.datos["fuente_hasta_mes"] == 7 and sobre.datos["fuente_meses_publicados"] == 7
    assert sobre.datos["total_casos"] == 1913  # el complemento no cuenta en el resultado
    assert any("El año está incompleto" in a for a in sobre.avisos)

    # si el complemento falla, la respuesta sigue y lo dice
    ej = Ejecutor(CATALOGO, {"datos-abiertos-mcp": _PoliciaFalsa(filas, corte_falla=True)})
    sobre = await ej.ejecutar("policia_hurto_vehiculos_municipio", entrada, plan="evaluacion")
    assert sobre.estado == "encontrado" and "fuente_hasta_mes" not in sobre.datos
    assert any("No se pudo saber hasta qué mes" in a for a in sobre.avisos)

    # sin casos en el municipio, el corte no convierte el vacío en «encontrado»
    ej = Ejecutor(CATALOGO, {"datos-abiertos-mcp": _PoliciaFalsa([])})
    sobre = await ej.ejecutar("policia_hurto_vehiculos_municipio", entrada, plan="evaluacion")
    assert sobre.estado == "no_encontrado" and sobre.datos == {}


class _IgacFalso:
    """El terreno (capa 14, rural) y el registro catastral (tabla 17) de un predio."""

    def __init__(self, registro: list[dict[str, Any]] | None) -> None:
        self.registro = registro  # None: la tabla 17 se cae

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        url = argumentos["url"]
        if url.endswith("/17"):
            if self.registro is None:
                raise RuntimeError("se cayó")
            filas = [{"attributes": r} for r in self.registro]
            return {
                "artifacts": [
                    {
                        "kind": "feature_collection",
                        "data": {
                            "features": [
                                {"type": "Feature", "geometry": None, "properties": r}
                                for r in self.registro
                            ]
                        },
                    }
                ]
                if filas
                else [{"kind": "feature_collection", "data": {"features": []}}],
                "facts": {},
            }
        if not url.endswith("/14"):
            return {
                "artifacts": [{"kind": "feature_collection", "data": {"features": []}}],
                "facts": {},
            }
        terreno = {
            "CODIGO": "251750000000000050067000000000",
            "CODIGO_ANTERIOR": "25175000000050067000",
        }
        poligono = {
            "type": "Polygon",
            "coordinates": [[[-74.03, 4.86], [-74.02, 4.86], [-74.02, 4.87], [-74.03, 4.86]]],
        }
        return {
            "artifacts": [
                {
                    "kind": "feature_collection",
                    "data": {
                        "features": [
                            {"type": "Feature", "geometry": poligono, "properties": terreno}
                        ]
                    },
                }
            ],
            "facts": {},
        }


@pytest.mark.anyio
async def test_el_predio_por_codigo_trae_el_registro_con_el_significado_del_destino() -> None:
    """Revisión de valor: devolvía el código que se le daba. El registro del predio del canario
    (medido el 2026-11-03): «KASTILO», destino G (recreacional), 56 069 m² de terreno."""
    from terranova.ejecutor import Ejecutor

    entrada = {"codigo": "251750000000000050067000000000"}
    registro = {
        "DIRECCION": "KASTILO",
        "DESTINO_ECONOMICO": "G",
        "AREA_TERRENO": 56069,
        "AREA_CONSTRUIDA": 6572,
    }
    ej = Ejecutor(CATALOGO, {"arcgis-mcp": _IgacFalso([registro])})
    sobre = await ej.ejecutar("igac_predio_por_codigo", entrada, plan="evaluacion")
    assert sobre.datos["destino_economico"] == "G"
    assert sobre.datos["destino_economico_significado"] == "Recreacional"
    assert sobre.datos["area_terreno_m2"] == 56069 and sobre.datos["direccion"] == "KASTILO"
    assert not any("registro catastral no trae" in a for a in sobre.avisos)

    # sin fila en el registro (Yopal: su catastro no lo lleva el IGAC), lo avisa
    ej = Ejecutor(CATALOGO, {"arcgis-mcp": _IgacFalso([])})
    sobre = await ej.ejecutar("igac_predio_por_codigo", entrada, plan="evaluacion")
    assert sobre.estado == "encontrado" and "destino_economico" not in sobre.datos
    assert any("registro catastral no trae" in a for a in sobre.avisos)

    # si el registro se cae, eso es «no se pudo», no «no lo trae»
    ej = Ejecutor(CATALOGO, {"arcgis-mcp": _IgacFalso(None)})
    sobre = await ej.ejecutar("igac_predio_por_codigo", entrada, plan="evaluacion")
    assert any(a.startswith("No se pudo saber la dirección") for a in sobre.avisos)
    assert not any("registro catastral no trae" in a for a in sobre.avisos)


def test_distintos_cuenta_los_meses_con_datos() -> None:
    """Castilla 2025 trae dos filas en diciembre y ninguna en octubre ni noviembre: 11 filas, 10
    meses (medido el 2026-11-02 en fdvb-hsrf)."""
    from terranova.catalogo import Derivado
    from terranova.ejecutor import derivar_resultado

    meses = [1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 12]
    elementos = [{"mes": m} for m in meses]
    d = Derivado(de="distintos", campo="mes", tipo="int")
    assert derivar_resultado(d, elementos, None) == 10
    assert derivar_resultado(Derivado(de="maximo", campo="mes", tipo="int"), elementos, None) == 12
    with pytest.raises(ValueError):
        Derivado(de="distintos", tipo="int")


def test_relleno_de_la_fuente_sale_vacio_y_el_tipo_con_su_nombre() -> None:
    """La SFC escribe NIT «0» y página web «Pendiente» en las filiales del exterior, y el tipo de
    entidad solo como número (medido el 2026-11-02 en sr9n-792w; los nombres, en el CUIF)."""
    from terranova.ejecutor import mapear_fila

    h = CATALOGO.herramientas["superfinanciera_vigiladas_buscar"]
    fuente = CATALOGO.fuentes[h.fuente]
    exterior = mapear_fila(
        h,
        fuente,
        {"tipo_entidad": "111", "numeroidentificacion": "0", "uripaginaweb": "Pendiente"},
        None,
    )
    assert exterior["nit_con_dv"] is None and exterior["pagina_web"] is None
    assert exterior["tipo_entidad"] == 111 and exterior["tipo_entidad_significado"] is None
    nequi = mapear_fila(
        h, fuente, {"tipo_entidad": "4", "numeroidentificacion": "9016332760"}, None
    )
    assert nequi["tipo_entidad_significado"] == "Compañías de financiamiento"
    assert nequi["nit_con_dv"] == "9016332760"


def test_un_numero_sale_con_los_decimales_que_publica_la_fuente() -> None:
    """El anexo de la GEIH trae la tasa de desempleo con 15 decimales; el DANE la publica con uno
    (medido el 2026-11-02 en anex-GEIH-sep2026.xlsx: 13.608424834543777 es 13,6)."""
    from terranova.ejecutor import mapear_fila

    h = CATALOGO.herramientas["dane_mercado_laboral_nacional"]
    fila = mapear_fila(
        h,
        CATALOGO.fuentes[h.fuente],
        {
            "Concepto": "Tasa de Desocupación (TD)",
            "columna": "2001",
            "subcolumna": "Dic",
            "valor": 13.608424834543777,
        },
        None,
    )
    assert fila["valor"] == 13.6


def test_la_fecha_de_constitucion_y_la_de_modificacion_salen_aparte() -> None:
    """La ANT escribe d/m/aaaa y en dos zonas le pega la modificación al mismo campo (medido el
    2026-11-03): la constitución sale de la primera fecha y la modificación, del `patron`."""
    from terranova.ejecutor import fecha_en_orden, mapear_fila

    assert fecha_en_orden("7/11/2000", "dma") == "2000-11-07"
    assert fecha_en_orden("18/12/1997 Fecha de modificación: 26/09/2024", "dma") == "1997-12-18"
    assert fecha_en_orden("18/12/19975", "dma") == "18/12/19975"  # no es una fecha
    h = CATALOGO.herramientas["ant_zonas_reserva_campesina_en_punto"]
    fuente = CATALOGO.fuentes[h.fuente]
    pato = {
        "NOMBRE_ZON": "Pato",
        "FECHA_CONSTITUCION": "18/12/1997 Fecha de modificación: 26/09/2024",
    }
    fila = mapear_fila(h, fuente, pato, None)
    assert fila["fecha_constitucion"] == "1997-12-18" and fila["fecha_modificacion"] == "2024-09-26"
    cabrera = mapear_fila(
        h, fuente, {"NOMBRE_ZON": "Cabrera", "FECHA_CONSTITUCION": "7/11/2000"}, None
    )
    assert cabrera["fecha_constitucion"] == "2000-11-07" and cabrera["fecha_modificacion"] is None


def test_la_ronda_separa_el_cuerpo_de_agua_del_componente() -> None:
    """La CAR pega el componente al nombre («Quebrada Carrizal - APCA»), lo escribe de dos formas
    («Faja Paralela», «Faja paralela») y a veces repite el nombre en otra línea (medido el
    2026-11-03 en las 203 rondas)."""
    from terranova.ejecutor import mapear_fila

    h = CATALOGO.herramientas["car_ronda_hidrica_en_punto"]
    fuente = CATALOGO.fuentes[h.fuente]
    casos = {
        "Quebrada Carrizal - APCA": ("Quebrada Carrizal", "APCA"),
        "Quebrada Suralá - Faja Paralela": ("Quebrada Suralá", "faja paralela"),
        "Quebrada Chucua Sopó - Faja paralela": ("Quebrada Chucua Sopó", "faja paralela"),
        "Quebrada Artesa \r\nQuebrada Artesa": ("Quebrada Artesa", None),
        "Río Teusacá_parte alta": ("Río Teusacá_parte alta", None),
        "": (None, None),
    }
    for nombre, (cuerpo, componente) in casos.items():
        fila = mapear_fila(h, fuente, {"Fuente": nombre}, None)
        assert (fila["cuerpo_de_agua"], fila["componente"]) == (cuerpo, componente), nombre
        assert fila["nombre_en_la_fuente"] == (nombre or None)  # tal como lo escribe la CAR


def test_patron_y_orden_fecha_solo_en_un_derivado_columna() -> None:
    from terranova.catalogo import Derivado

    with pytest.raises(ValueError, match="solo en un derivado «columna»"):
        Derivado(de="primero", campo="x", patron="(a)")
    with pytest.raises(ValueError, match="exactamente un grupo"):
        Derivado(de="columna", campo="x", patron="a")


def test_un_derivado_fijo_pone_el_mismo_valor_en_cada_elemento() -> None:
    """El IPM municipal es la medida censal de 2018, y la tabla del DANE no trae el año."""
    from terranova.ejecutor import mapear_fila

    h = CATALOGO.herramientas["dane_ipm_municipio"]
    fila = mapear_fila(h, CATALOGO.fuentes[h.fuente], {"ID": "27099", "IPM": 77.1}, None)
    assert fila["anio"] == 2018 and fila["ipm_total"] == 77.1


def test_un_derivado_sale_con_sus_decimales() -> None:
    """El promedio que calcula la consulta trae 16 decimales; la temperatura se lee con uno
    (medido el 2026-10-28 en sbwg-7ju4: 27.2083333333333333 °C es 27,2)."""
    from terranova.ejecutor import mapear_fila

    h = CATALOGO.herramientas["ideam_temperatura_diaria_estacion"]
    crudo = {"promedio": "27.2083333333333333", "minima": "23.5", "observaciones": "24"}
    fila = mapear_fila(h, CATALOGO.fuentes[h.fuente], crudo, None)
    assert fila["promedio_c"] == 27.2 and fila["minima_c"] == 23.5 and fila["observaciones"] == 24


def test_conteo_por_categoria_con_la_mas_frecuente_primero() -> None:
    """169 áreas protegidas alrededor de Bogotá: 110 son reservas de la sociedad civil (medido el
    2026-11-02 en la copia del RUNAP)."""
    from terranova.catalogo import Derivado
    from terranova.ejecutor import derivar_resultado

    d = Derivado(de="conteo_por", campo="categoria")
    elementos = [
        {"categoria": "Reserva Natural"},
        {"categoria": "Parque"},
        {"categoria": "Reserva Natural"},
    ]
    resultado = derivar_resultado(d, elementos, None)
    assert resultado == {"Reserva Natural": 2, "Parque": 1}
    assert list(resultado) == ["Reserva Natural", "Parque"]


def test_suma_por_categoria_con_la_mayor_primero() -> None:
    """Las hectáreas de cada tratamiento dentro de un polígono (medido el 2026-11-03 en la copia del
    POT 555: en la franja del canario, 174,12 ha de consolidación y 113,86 de renovación)."""
    from terranova.catalogo import Derivado
    from terranova.ejecutor import derivar_resultado

    d = Derivado(de="suma_por", campo="tratamiento", sumar="area_ha", decimales=2)
    elementos: list[dict[str, Any]] = [
        {"tratamiento": "Renovación", "area_ha": 29.4059},
        {"tratamiento": "Consolidación", "area_ha": 40.3819},
        {"tratamiento": "Consolidación", "area_ha": 20.2935},
        {"tratamiento": None, "area_ha": 3.0},
        {"tratamiento": "Renovación", "area_ha": None},
    ]
    resultado = derivar_resultado(d, elementos, None)
    assert resultado == {"Consolidación": 60.68, "Renovación": 29.41}
    assert list(resultado) == ["Consolidación", "Renovación"]


def test_suma_por_de_un_conteo_sale_entera() -> None:
    """Los casos de cada delito en Yopal 2025 (medido el 2026-11-03 en d4fr-sbn2): 21 abigeatos,
    no 21.0."""
    from terranova.catalogo import Derivado
    from terranova.ejecutor import derivar_resultado

    d = Derivado(de="suma_por", campo="tipo", sumar="casos", tipo="int")
    elementos: list[dict[str, Any]] = [
        {"tipo": "HURTO ABIGEATO", "casos": 4},
        {"tipo": "HURTO ABIGEATO", "casos": 17},
        {"tipo": "HURTO ENTIDADES FINANCIERAS", "casos": 1},
    ]
    resultado = derivar_resultado(d, elementos, None)
    assert resultado == {"HURTO ABIGEATO": 21, "HURTO ENTIDADES FINANCIERAS": 1}
    assert all(type(v) is int for v in resultado.values())


def test_suma_por_necesita_sumar_y_sumar_va_solo_con_suma_por() -> None:
    from terranova.catalogo import Derivado

    with pytest.raises(ValueError, match="sumar"):
        Derivado(de="suma_por", campo="tratamiento")
    with pytest.raises(ValueError, match="sumar"):
        Derivado(de="suma", campo="area_ha", sumar="area_ha")


class _AlertasFalsas:
    """La copia de las alertas de deslizamiento: las del municipio y, en el complemento, la fecha
    del último boletín de cualquier municipio."""

    def __init__(self, fechas: list[str], ultimo: str | None) -> None:
        self.fechas, self.ultimo = fechas, ultimo

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        if argumentos.get("agregados"):
            filas: list[dict[str, Any]] = [{"ultimo": self.ultimo}]
        else:
            fila = {"COD_DANE": "05002", "MUNICIPIO": "ABEJORRAL", "TEXTO_AMENAZA": "ALTA"}
            filas = [{**fila, "FECHA_EJECUCION": f} for f in self.fechas]
        n = len(filas)
        return {
            "artifacts": [{"kind": "table", "rows": filas}],
            "facts": {
                "completitud": {"vistos": n, "total": n, "truncado": False},
                "consultado_en": "2026-11-02T13:00:00+00:00",
            },
        }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("fechas", "ultimo", "vigente"),
    [
        (["2026-11-01", "2026-10-31"], "2026-11-01", True),  # Abejorral, boletín del 01-11
        (["2026-04-28"], "2026-11-01", False),  # Chía: su última alerta fue en abril
        (["2026-11-01"], None, None),  # sin la fecha del boletín no se afirma nada
    ],
)
async def test_alerta_vigente_si_la_ultima_es_la_del_ultimo_boletin(
    fechas: list[str], ultimo: str | None, vigente: bool | None
) -> None:
    """El IDEAM publica cada noche solo los municipios con alerta ese día. La última alerta de un
    municipio no dice que siga: GEO Copilot llamó «vigente» una de abril (medido el 2026-11-03)."""
    from terranova.ejecutor import Ejecutor

    ej = Ejecutor(CATALOGO, {"copia": _AlertasFalsas(fechas, ultimo)})
    sobre = await ej.ejecutar(
        "ideam_alertas_deslizamiento_municipio", {"municipio_divipola": "05002"}, plan="evaluacion"
    )
    assert sobre.estado == "encontrado"
    assert sobre.datos["ultima_alerta"] == fechas[0]
    assert sobre.datos.get("alerta_vigente") is vigente


def test_igual_lleva_campo_e_igual_a_y_solo_el() -> None:
    from terranova.catalogo import Derivado

    with pytest.raises(ValueError, match="igual"):
        Derivado(de="igual", campo="ultima_alerta")
    with pytest.raises(ValueError, match="igual"):
        Derivado(de="igual", igual_a="ultimo_boletin")
    with pytest.raises(ValueError, match="igual"):
        Derivado(de="primero", campo="fecha", igual_a="ultimo_boletin")


@pytest.mark.parametrize(
    "escrito",
    [
        "899999172",
        "899.999.172",
        "899999172-8",
        "899.999.172-8",
        "8999991728",
        " 899999172 ",
        899999172,
    ],
)
def test_el_nit_de_la_entidad_se_acepta_como_lo_escribe_la_gente(escrito: Any) -> None:
    """Con el dígito de verificación pegado (8999991728), antes se buscaba ese número de 10
    dígitos y salía «no encontrado» sin aviso. Chía: 899.999.172-8."""
    from terranova.ejecutor import validar_entrada

    h = CATALOGO.herramientas["secop_contratos_entidad"]
    entrada = {**h.canario.entrada, "nit_entidad": escrito}
    assert validar_entrada(h, entrada)["nit_entidad"] == "899999172"


@pytest.mark.parametrize(
    ("escrito", "motivo"),
    [
        ("899999172-3", "dígito de verificación no cuadra"),
        ("8999991723", "dígito de verificación no cuadra"),
        ("79999917", "NIT de 9 dígitos"),  # una cédula: ADR-0014
        ("1020304050", "NIT de 9 dígitos"),
        ("899 999 172", "NIT de 9 dígitos"),
    ],
)
def test_un_nit_mal_escrito_se_rechaza_con_el_motivo(escrito: str, motivo: str) -> None:
    from terranova.ejecutor import validar_entrada

    h = CATALOGO.herramientas["rues_empresa_por_nit"]
    with pytest.raises(ErrorEntrada, match=motivo):
        validar_entrada(h, {**h.canario.entrada, "nit": escrito})


def test_el_digito_de_verificacion_de_nit_conocidos() -> None:
    """Bancolombia 890.903.938-8, Bogotá D. C. 899.999.061-9, Davivienda 860.034.313-7."""
    from terranova.catalogo import digito_verificacion

    assert digito_verificacion("890903938") == 8
    assert digito_verificacion("899999061") == 9
    assert digito_verificacion("860034313") == 7


RAYA = chr(0x2013)


class _RelatoriaFalsa:
    """La relatoría: los descriptores que casan (con una basura que no es un id) y los conceptos
    que llevan el descriptor 12021."""

    def __init__(self) -> None:
        self.llamadas: list[dict[str, Any]] = []

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        self.llamadas.append(argumentos)
        if argumentos["url"].endswith("/descriptor"):
            filas: list[dict[str, Any]] = (
                [{"id": 12021}, {"id": 24562}, {"id": "1&per_page=100"}]
                if argumentos["params"]["search"] == "contratacion directa"
                else []
            )
        elif "12021" in str(argumentos["params"]["descriptor"]).split(","):
            filas = [
                {
                    "id": 67400,
                    "date": "2026-10-22T10:00:00",
                    "title.rendered": "C-100",
                    "link": "https://relatoria.colombiacompra.gov.co/conceptos/c-100/",
                    "content.rendered": "<p><strong>CONTRATACIÓN DIRECTA </strong><strong>"
                    + RAYA
                    + "</strong><strong> Deber de planeación</strong></p><p>[…] texto</p>",
                }
            ]
        else:
            filas = []
        n = len(filas)
        return {
            "artifacts": [{"kind": "table", "rows": filas}],
            "facts": {"completitud": {"vistos": n, "total": n, "truncado": False}},
        }


@pytest.mark.anyio
async def test_la_previa_por_coma_pasa_los_descriptores_a_la_url() -> None:
    """`formato: coma`: los ids que cumplen el patrón van separados por coma; sin ninguno, «0»
    (con el parámetro vacío, la relatoría devolvería todo)."""
    from terranova.ejecutor import Ejecutor

    falso = _RelatoriaFalsa()
    ej = Ejecutor(CATALOGO, {"web-mcp": falso})
    sobre = await ej.ejecutar(
        "ancp_conceptos_por_tema", {"texto": "contratación directa"}, plan="evaluacion"
    )
    assert falso.llamadas[1]["params"]["descriptor"] == "12021,24562"
    assert sobre.estado == "encontrado"
    tema = "CONTRATACIÓN DIRECTA " + RAYA + " Deber de planeación"
    assert sobre.datos["elementos"][0]["tema"] == tema

    falso = _RelatoriaFalsa()
    sobre = await Ejecutor(CATALOGO, {"web-mcp": falso}).ejecutar(
        "ancp_conceptos_por_tema", {"texto": "nada"}, plan="evaluacion"
    )
    assert falso.llamadas[1]["params"]["descriptor"] == "0"
    assert sobre.estado == "no_encontrado"
