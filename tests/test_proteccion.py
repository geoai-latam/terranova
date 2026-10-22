"""F2.4: cortacircuitos, bulkhead y reintento con jitter por fuente."""

import asyncio
import time

import pytest

from terranova.errores import ErrorEjecucion
from terranova.proteccion import Proteccion


class Reloj:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


class Fuente:
    def __init__(self, codigo: str | None = "fuente_no_disponible") -> None:
        self.codigo = codigo
        self.llamadas = 0

    async def __call__(self) -> str:
        self.llamadas += 1
        if self.codigo:
            raise ErrorEjecucion(self.codigo, "caída")
        return "ok"


async def _sin_espera(_: float) -> None:
    return None


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _proteccion(reloj: Reloj) -> Proteccion:
    return Proteccion(
        umbral=3, enfriamiento_s=30, reloj=reloj, dormir=_sin_espera, azar=lambda: 0.5
    )


@pytest.mark.anyio
async def test_abre_tras_tres_caidas_y_responde_al_instante_sin_tocar_la_fuente() -> None:
    reloj = Reloj()
    p, fuente = _proteccion(reloj), Fuente("fuente_lenta")
    for _ in range(3):
        with pytest.raises(ErrorEjecucion):
            await p.llamar("pnn.runap", fuente)
    assert p.abierto("pnn.runap") and fuente.llamadas == 3
    t0 = time.perf_counter()
    with pytest.raises(ErrorEjecucion) as exc:
        await p.llamar("pnn.runap", fuente)
    assert time.perf_counter() - t0 < 1.0  # spec F2.4: < 1 s con el circuito abierto
    assert exc.value.codigo == "fuente_no_disponible" and exc.value.reintentar_en_s == 30
    assert fuente.llamadas == 3  # no se tocó la fuente


@pytest.mark.anyio
async def test_medio_abierto_un_fallo_reabre_y_un_exito_cierra() -> None:
    reloj = Reloj()
    p, fuente = _proteccion(reloj), Fuente("fuente_lenta")
    for _ in range(3):
        with pytest.raises(ErrorEjecucion):
            await p.llamar("f.x", fuente)
    reloj.t += 31
    with pytest.raises(ErrorEjecucion):
        await p.llamar("f.x", fuente)  # el intento de prueba falla
    assert p.abierto("f.x")
    reloj.t += 31
    fuente.codigo = None
    assert await p.llamar("f.x", fuente) == "ok"
    assert not p.abierto("f.x") and p.circuitos["f.x"].fallos == 0


@pytest.mark.anyio
async def test_un_circuito_por_fuente() -> None:
    reloj = Reloj()
    p = _proteccion(reloj)
    for _ in range(3):
        with pytest.raises(ErrorEjecucion):
            await p.llamar("pnn.runap", Fuente("fuente_lenta"))
    assert await p.llamar("igac.catastro.terreno", Fuente(None)) == "ok"


@pytest.mark.anyio
async def test_reintenta_una_vez_solo_lo_no_disponible() -> None:
    reloj = Reloj()
    p = _proteccion(reloj)
    no_disponible = Fuente("fuente_no_disponible")
    with pytest.raises(ErrorEjecucion):
        await p.llamar("a.b", no_disponible)
    assert no_disponible.llamadas == 2  # un reintento
    lenta = Fuente("fuente_lenta")
    with pytest.raises(ErrorEjecucion):
        await p.llamar("c.d", lenta)
    assert lenta.llamadas == 1  # un tiempo agotado no se repite


@pytest.mark.anyio
async def test_un_error_de_la_peticion_no_cuenta_para_el_circuito() -> None:
    reloj = Reloj()
    p = _proteccion(reloj)
    for _ in range(5):
        with pytest.raises(ErrorEjecucion):
            await p.llamar("a.b", Fuente("parametro_invalido"))
    assert not p.abierto("a.b")


@pytest.mark.anyio
async def test_bulkhead_limita_las_llamadas_simultaneas() -> None:
    p = Proteccion(concurrencia=4)
    en_vuelo = maximo = 0

    async def lenta() -> str:
        nonlocal en_vuelo, maximo
        en_vuelo += 1
        maximo = max(maximo, en_vuelo)
        await asyncio.sleep(0.01)
        en_vuelo -= 1
        return "ok"

    resultados = await asyncio.gather(*(p.llamar("igac", lenta) for _ in range(20)))
    assert resultados == ["ok"] * 20 and maximo == 4


@pytest.mark.anyio
async def test_con_circuito_abierto_y_copia_sale_obsoleto_sin_tocar_la_fuente() -> None:
    """E2E-05: la fuente cae; con caché previa sale `obsoleto` rápido y el circuito la protege."""
    from test_cache import CATALOGO, TTL, H
    from test_cache import Fuente as FuenteGrabada

    from terranova.cache import AlmacenMemoria
    from terranova.ejecutor import Ejecutor

    reloj, almacen, fuente = Reloj(), AlmacenMemoria(), FuenteGrabada()
    almacen.reloj = reloj
    proteccion = _proteccion(reloj)
    ej = Ejecutor(CATALOGO, {"arcgis-mcp": fuente}, almacen, reloj, proteccion=proteccion)
    await ej.ejecutar(H.id, H.canario.entrada)
    reloj.t += TTL + 1
    fuente.caida = "fuente_lenta"
    for _ in range(2):  # dos capas por consulta: el circuito se abre en la segunda vuelta
        assert (await ej.ejecutar(H.id, H.canario.entrada)).procedencia[
            0
        ].servido_desde == "obsoleto"
    assert proteccion.abierto(H.fuente)
    llamadas = fuente.llamadas
    t0 = time.perf_counter()
    sobre = await ej.ejecutar(H.id, H.canario.entrada)
    assert time.perf_counter() - t0 < 1.0 and fuente.llamadas == llamadas
    assert sobre.procedencia[0].servido_desde == "obsoleto" and sobre.creditos == 0
