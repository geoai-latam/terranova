"""F4.2: la ficha de un lugar. Sin red: cada parte responde el sobre de su dorada."""

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from terranova import ficha as f
from terranova.catalogo import cargar
from terranova.contrato import Sobre
from terranova.ejecutor import Ejecutor, Plan
from terranova.errores import ErrorEjecucion, ErrorEntrada

DORADAS = Path(__file__).parent / "doradas"
CATALOGO = cargar()
HOY = date(2026, 10, 22)


class ConectorGrabado:
    def __init__(self, nombre: str, llamadas: list[dict[str, Any]]) -> None:
        self.grabadas = [ll for ll in llamadas if ll["conector"] == nombre]

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.grabadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise AssertionError(f"llamada no grabada: {herramienta} {argumentos}")


async def _sobre_dorado(herramienta: str) -> Sobre:
    grabado = json.loads((DORADAS / f"{herramienta}.json").read_text(encoding="utf-8"))
    llamadas = grabado["llamadas"]
    ej = Ejecutor(
        CATALOGO, {n["conector"]: ConectorGrabado(n["conector"], llamadas) for n in llamadas}
    )
    return await ej.ejecutar(
        herramienta, CATALOGO.herramientas[herramienta].canario.entrada, plan="evaluacion"
    )


SOBRES: dict[str, Sobre] = {}


@pytest.fixture(scope="module")
def sobres() -> dict[str, Sobre]:
    if not SOBRES:
        for h in f.HERRAMIENTAS:
            SOBRES[h] = asyncio.run(_sobre_dorado(h))
    return SOBRES


class EjecutorFalso(Ejecutor):
    """Responde el sobre dorado de cada herramienta y anota con qué entrada la llamaron."""

    def __init__(
        self,
        sobres: dict[str, Sobre],
        caidas: dict[str, ErrorEjecucion] | None = None,
        lentas: frozenset[str] = frozenset(),
        cambios: dict[str, dict[str, Any]] | None = None,
        espera_s: float = 5,
    ) -> None:
        super().__init__(CATALOGO, {})
        self.sobres, self.caidas, self.lentas = sobres, caidas or {}, lentas
        self.cambios = cambios or {}
        self.llamadas: dict[str, dict[str, Any]] = {}
        self.terminadas: set[str] = set()
        self.espera_s = espera_s

    async def ejecutar(
        self, herramienta: str, entrada: dict[str, Any], *, plan: Plan = "normal", **_: Any
    ) -> Sobre:
        self.llamadas[herramienta] = entrada
        if herramienta in self.lentas:
            await asyncio.sleep(self.espera_s)
        if herramienta in self.caidas:
            raise self.caidas[herramienta]
        s = self.sobres[herramienta]
        self.terminadas.add(herramienta)
        return s.model_copy(update=self.cambios.get(herramienta, {}))


PUNTO = {"lon": -74.0262, "lat": 4.8619}  # predio rural de Chía (canario de igac_predio_en_punto)


def _ida_y_vuelta(s: Sobre) -> Sobre:
    return Sobre.model_validate(s.model_dump(mode="json"))  # reglas 1-9


@pytest.mark.anyio
async def test_ficha_completa(sobres: dict[str, Sobre]) -> None:
    ej = EjecutorFalso(sobres)
    s = _ida_y_vuelta(await f.ficha(ej, PUNTO, plan="evaluacion", hoy=HOY))
    assert s.estado == "encontrado" and s.herramienta == "ficha_lugar@1" and not s.errores
    partes = {p.nombre for p in (f.PREDIO_EN_PUNTO, *f.PARTES_PUNTO, *f.PARTES_PREDIO)}
    assert set(s.datos) == partes
    assert s.datos["predio"]["codigo_predial"] == "251750000000000050067000000000"
    # la segunda etapa sale del predio
    assert ej.llamadas["igac_construcciones_en_predio"] == {
        "codigo": "251750000000000050067000000000"
    }
    assert ej.llamadas["dane_poblacion_municipio"] == {"municipio_divipola": "25175"}
    assert ej.llamadas["usgs_sismos_en_zona"]["desde"] == "2025-10-22"
    assert s.creditos == f.TOPE_CREDITOS  # suma de partes > tope
    fuentes = {p.fuente_id for p in s.procedencia}
    assert {"igac.catastro.terreno", "pnn.runap", "usgs.sismos", "esa.worldcover"} <= fuentes
    assert s.zona_usada is not None and s.zona_usada.valor == [-74.0262, 4.8619]


@pytest.mark.anyio
async def test_una_parte_caida_sale_parcial_con_su_error(sobres: dict[str, Sobre]) -> None:
    caida = ErrorEjecucion("fuente_no_disponible", "ArcGIS 503", reintentar_en_s=30)
    ej = EjecutorFalso(sobres, caidas={"pnn_areas_protegidas_en_punto": caida})
    s = _ida_y_vuelta(await f.ficha(ej, PUNTO, plan="evaluacion", hoy=HOY))
    assert s.estado == "parcial"
    (e,) = s.errores
    assert e.codigo == "fuente_no_disponible" and e.fuente_id == "pnn.runap"
    assert e.reintentar_en_s == 30
    assert "areas_protegidas" not in s.datos and "predio" in s.datos and len(s.datos) == 12
    assert any("areas_protegidas" in a for a in s.avisos)


@pytest.mark.anyio
async def test_lo_que_no_llega_en_el_tope_es_fuente_lenta(sobres: dict[str, Sobre]) -> None:
    ej = EjecutorFalso(sobres, lentas=frozenset({"esa_cobertura_suelo_en_punto"}))
    s = await f.ficha(ej, PUNTO, plan="evaluacion", hoy=HOY, tope_s=0.3)
    assert s.estado == "parcial"
    assert [(e.codigo, e.fuente_id) for e in s.errores] == [("fuente_lenta", "esa.worldcover")]


@pytest.mark.anyio
async def test_la_parte_lenta_termina_en_segundo_plano(sobres: dict[str, Sobre]) -> None:
    ej = EjecutorFalso(sobres, lentas=frozenset({"esa_cobertura_suelo_en_punto"}), espera_s=0.5)
    await f.ficha(ej, PUNTO, plan="evaluacion", hoy=HOY, tope_s=0.2)
    assert "esa_cobertura_suelo_en_punto" not in ej.terminadas  # la ficha no la esperó
    await asyncio.sleep(0.6)
    assert "esa_cobertura_suelo_en_punto" in ej.terminadas  # pero no se canceló: llena la caché
    assert not f._EN_SEGUNDO_PLANO


@pytest.mark.anyio
async def test_sin_licencia_ni_scope_la_parte_no_se_consulta(sobres: dict[str, Sobre]) -> None:
    ej = EjecutorFalso(sobres)
    s = await f.ficha(ej, PUNTO, plan="normal", puede=lambda fam: fam != "ambiente", hoy=HOY)
    assert s.estado == "encontrado" and not s.errores  # omitir no es fallar
    assert "dane_poblacion_municipio" not in ej.llamadas
    assert "usgs_sismos_en_zona" not in ej.llamadas and "sismos_cercanos" not in s.datos
    assert any("poblacion_municipio" in a and "licencia" in a for a in s.avisos)
    assert any("sismos_cercanos" in a and "scope" in a for a in s.avisos)
    assert "dane.cnpv2018.municipio" not in {p.fuente_id for p in s.procedencia}


@pytest.mark.anyio
async def test_predio_no_encontrado_salta_la_segunda_etapa(sobres: dict[str, Sobre]) -> None:
    sin_predio = {"igac_predio_en_punto": {"estado": "no_encontrado", "datos": {}}}
    ej = EjecutorFalso(sobres, cambios=sin_predio)
    s = await f.ficha(ej, PUNTO, plan="evaluacion", hoy=HOY)
    assert s.datos["predio"]["estado"] == "no_encontrado"
    assert not {p.herramienta for p in f.PARTES_PREDIO} & set(ej.llamadas)
    assert any("construcciones" in a and "no_encontrado" in a for a in s.avisos)


@pytest.mark.anyio
async def test_por_codigo_busca_el_predio_y_usa_un_punto_dentro(sobres: dict[str, Sobre]) -> None:
    ej = EjecutorFalso(sobres)
    s = await f.ficha(ej, {"codigo": "251750000000000050067000000000"}, plan="evaluacion", hoy=HOY)
    assert "igac_predio_en_punto" not in ej.llamadas
    assert ej.llamadas["igac_vereda_en_punto"] == {"lon": -74.0247001, "lat": 4.8618487}
    assert s.zona_usada is not None and s.zona_usada.tipo == "codigo"
    assert s.datos["predio"]["municipio_divipola"] == "25175"


@pytest.mark.anyio
async def test_todo_caido_es_un_error_no_un_sobre(sobres: dict[str, Sobre]) -> None:
    caida = ErrorEjecucion("fuente_no_disponible", "caída")
    ej = EjecutorFalso(sobres, caidas=dict.fromkeys(f.HERRAMIENTAS, caida))
    with pytest.raises(ErrorEjecucion) as exc:
        await f.ficha(ej, PUNTO, plan="evaluacion", hoy=HOY)
    assert exc.value.codigo == "fuente_no_disponible"


@pytest.mark.anyio
@pytest.mark.parametrize(
    "entrada",
    [
        {},
        {"lon": 1},
        {"lon": True, "lat": 4},
        {"lon": 200, "lat": 4},
        {"codigo": "123"},
        {"lon": -74, "lat": 4, "codigo": "251750000000000050067000000000"},
    ],
)
async def test_entrada_invalida(sobres: dict[str, Sobre], entrada: dict[str, Any]) -> None:
    with pytest.raises(ErrorEntrada):
        await f.ficha(EjecutorFalso(sobres), entrada, hoy=HOY)


def test_punto_interior_cae_dentro_de_un_poligono_concavo_con_hueco() -> None:
    # una U: el centroide cae en la abertura, fuera del polígono
    u = [[0, 0], [3, 0], [3, 3], [2, 3], [2, 1], [1, 1], [1, 3], [0, 3], [0, 0]]
    x, y = f.punto_interior({"type": "Polygon", "coordinates": [u]})
    assert (0 < x < 1 or 2 < x < 3) and 1 < y < 3
    # cuadrado con hueco en el centro
    caja = [[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]]
    hueco = [[1, 1], [3, 1], [3, 3], [1, 3], [1, 1]]
    x, y = f.punto_interior({"type": "Polygon", "coordinates": [caja, hueco]})
    assert not (1 < x < 3 and 1 < y < 3) and 0 < x < 4
    # multipolígono: el más grande
    chico = [[10, 10], [10.1, 10], [10.1, 10.1], [10, 10.1], [10, 10]]
    x, _ = f.punto_interior({"type": "MultiPolygon", "coordinates": [[chico], [caja]]})
    assert 0 < x < 4
    assert f.punto_interior({"type": "Point", "coordinates": [-74.0, 4.8]}) == (-74.0, 4.8)


@pytest.mark.anyio
@pytest.mark.parametrize("estado", ["no_encontrado", "fuera_de_cobertura"])
async def test_codigo_sin_predio_es_la_ficha_del_predio(
    sobres: dict[str, Sobre], estado: str
) -> None:
    cambio: dict[str, Any] = {"estado": estado, "datos": {}, "geo_result": None}
    cambio |= {"creditos": 0, "avisos": ["fuera"]} if estado == "fuera_de_cobertura" else {}
    ej = EjecutorFalso(sobres, cambios={"igac_predio_por_codigo": cambio})
    s = _ida_y_vuelta(await f.ficha(ej, {"codigo": "0" * 30}, plan="evaluacion", hoy=HOY))
    assert (
        s.estado == estado
        and list(s.datos) == ["predio"]
        and set(ej.llamadas) == {"igac_predio_por_codigo"}
    )


MANIFIESTO = {
    "dataset": "restricciones",
    "version": "v0-2026-10-22-fc56a228",
    "generado": "2026-10-22T11:19:26+00:00",
    "origenes": [
        {"fuente_id": "pnn.runap", "url": "https://storage.googleapis.com/x.zip"},
        {"fuente_id": "ant.resguardos_indigenas", "url": "https://utility.arcgis.com/r"},
        {"fuente_id": "ant.zonas_reserva_campesina", "url": "https://utility.arcgis.com/z"},
    ],
    "excluidas": ["reservas Ley 2.ª (Minambiente): licencia por verificar"],
}


class CuradoFalso:
    def __init__(self, filas: list[dict[str, Any]] | None = None, caido: bool = False) -> None:
        self.filas, self.caido = filas or [], caido
        self.puntos: list[tuple[float, float]] = []

    async def en_punto(self, lon: float, lat: float) -> Any:
        from terranova.curado import Consulta

        self.puntos.append((lon, lat))
        if self.caido:
            raise ErrorEjecucion("fuente_no_disponible", "base curada: OperationalError")
        return Consulta(self.filas, MANIFIESTO)


CHINGAZA = {
    "id": "runap:1",
    "tipo": "area_protegida",
    "nombre": "Chingaza",
    "categoria": "Parque Nacional Natural",
    "acto": None,
    "fecha": "2011-06-30",
    "fuente_id": "pnn.runap",
    "url": "https://runap.parquesnacionales.gov.co/area-protegida/1",
}


@pytest.mark.anyio
async def test_restricciones_desde_el_curado(sobres: dict[str, Sobre]) -> None:
    ej, curado = EjecutorFalso(sobres), CuradoFalso([CHINGAZA])
    s = _ida_y_vuelta(await f.ficha(ej, PUNTO, plan="evaluacion", hoy=HOY, curado=curado))
    assert s.estado == "encontrado" and curado.puntos == [(-74.0262, 4.8619)]
    # una consulta curada en lugar de tres en vivo
    assert not {"pnn_areas_protegidas_en_punto", "ant_resguardos_en_punto"} & set(ej.llamadas)
    r = s.datos["restricciones"]
    assert r["areas_protegidas"] == [
        {k: v for k, v in CHINGAZA.items() if k not in ("tipo", "fuente_id") and v}
    ]
    assert r["resguardos"] == [] and r["version_dataset"] == MANIFIESTO["version"]
    assert "areas_protegidas" not in s.datos
    curadas = [p for p in s.procedencia if p.servido_desde == "curado"]
    assert [p.fuente_id for p in curadas] == list(f.ORIGENES_CURADO)
    assert curadas[0].completitud.vistos == 1 and curadas[1].completitud.vistos == 0
    assert all(p.version_dataset == MANIFIESTO["version"] for p in curadas)
    assert any("dataset curado" in a and "Ley 2.ª" in a for a in s.avisos)


@pytest.mark.anyio
async def test_sin_restricciones_en_el_punto_es_no_encontrado(sobres: dict[str, Sobre]) -> None:
    s = await f.ficha(
        EjecutorFalso(sobres), PUNTO, plan="evaluacion", hoy=HOY, curado=CuradoFalso()
    )
    assert s.estado == "encontrado" and s.datos["restricciones"]["estado"] == "no_encontrado"


@pytest.mark.anyio
async def test_base_curada_caida_sale_parcial(sobres: dict[str, Sobre]) -> None:
    curado = CuradoFalso(caido=True)
    s = _ida_y_vuelta(
        await f.ficha(EjecutorFalso(sobres), PUNTO, plan="evaluacion", hoy=HOY, curado=curado)
    )
    assert s.estado == "parcial" and "restricciones" not in s.datos
    assert {e.fuente_id for e in s.errores} == set(f.ORIGENES_CURADO)
    assert {e.codigo for e in s.errores} == {"fuente_no_disponible"}


@pytest.mark.anyio
async def test_restricciones_curadas_respetan_el_scope(sobres: dict[str, Sobre]) -> None:
    curado = CuradoFalso([CHINGAZA])
    s = await f.ficha(
        EjecutorFalso(sobres),
        PUNTO,
        plan="evaluacion",
        hoy=HOY,
        curado=curado,
        puede=lambda fam: fam != "ambiente",
    )
    assert curado.puntos == [] and "restricciones" not in s.datos
    assert any("restricciones" in a and "ambiente" in a for a in s.avisos)


@pytest.mark.anyio
async def test_sin_dataset_cargado_las_restricciones_van_en_vivo(sobres: dict[str, Sobre]) -> None:
    class SinCargar:
        async def en_punto(self, lon: float, lat: float) -> Any:
            raise ErrorEjecucion("no_existe", "no hay dataset curado cargado")

    ej = EjecutorFalso(sobres)
    s = await f.ficha(ej, PUNTO, plan="evaluacion", hoy=HOY, curado=SinCargar())
    assert s.estado == "encontrado" and "restricciones" not in s.datos
    assert {"areas_protegidas", "resguardos", "reservas_campesinas"} <= set(s.datos)
    assert "pnn_areas_protegidas_en_punto" in ej.llamadas
    assert any("no hay dataset curado" in a for a in s.avisos)
