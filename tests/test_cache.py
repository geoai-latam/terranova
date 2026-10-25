"""F2.3: caché por frescura de la fuente y `obsoleto` cuando la fuente cae (ADR-0008, ADR-0010)."""

import json
from pathlib import Path
from typing import Any

import pytest

from terranova.cache import AlmacenMemoria
from terranova.catalogo import cargar
from terranova.conector import ErrorConector
from terranova.contrato import Sobre
from terranova.ejecutor import Ejecutor
from terranova.errores import ErrorEjecucion

CATALOGO = cargar()
H = CATALOGO.herramientas["igac_predio_en_punto"]
TTL = CATALOGO.fuentes[H.fuente].frescura.ttl_cache_s
GRABADO = json.loads(
    (Path(__file__).parent / "doradas" / f"{H.id}.json").read_text(encoding="utf-8")
)


class Fuente:
    def __init__(self) -> None:
        self.caida: str | None = None
        self.llamadas = 0

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        self.llamadas += 1
        if self.caida:
            raise ErrorConector("la fuente no respondió", self.caida)
        for ll in GRABADO["llamadas"]:
            if ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise AssertionError(argumentos)


class Reloj:
    def __init__(self) -> None:
        self.t = 1_800_000_000.0

    def __call__(self) -> float:
        return self.t


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def montaje() -> tuple[Ejecutor, Fuente, Reloj]:
    fuente, reloj, almacen = Fuente(), Reloj(), AlmacenMemoria()
    almacen.reloj = reloj
    return Ejecutor(CATALOGO, {"arcgis-mcp": fuente}, almacen, reloj), fuente, reloj


@pytest.mark.anyio
async def test_acierto_de_cache_no_llama_ni_descuenta(
    montaje: tuple[Ejecutor, Fuente, Reloj],
) -> None:
    ej, fuente, reloj = montaje
    primero = await ej.ejecutar(H.id, H.canario.entrada)
    llamadas = fuente.llamadas
    reloj.t += TTL - 1
    segundo = await ej.ejecutar(H.id, H.canario.entrada)
    assert fuente.llamadas == llamadas
    assert segundo.datos == primero.datos and segundo.huella == primero.huella
    assert segundo.creditos == 0 and primero.creditos == H.creditos
    assert segundo.solicitud_id != primero.solicitud_id
    p = segundo.procedencia[0]
    assert p.servido_desde == "cache" and p.cache.acierto and p.cache.edad_s == TTL - 1
    assert p.consultado_en == primero.procedencia[0].consultado_en


@pytest.mark.anyio
async def test_vencido_vuelve_a_la_fuente(montaje: tuple[Ejecutor, Fuente, Reloj]) -> None:
    ej, fuente, reloj = montaje
    await ej.ejecutar(H.id, H.canario.entrada)
    llamadas = fuente.llamadas
    reloj.t += TTL + 1
    sobre = await ej.ejecutar(H.id, H.canario.entrada)
    assert fuente.llamadas > llamadas
    assert sobre.procedencia[0].servido_desde == "fuente" and sobre.creditos == H.creditos


@pytest.mark.anyio
@pytest.mark.parametrize("caida", ["fuente_no_disponible", "fuente_lenta"])
async def test_fuente_caida_sirve_obsoleto_y_lo_dice(
    montaje: tuple[Ejecutor, Fuente, Reloj], caida: str
) -> None:
    ej, fuente, reloj = montaje
    original = await ej.ejecutar(H.id, H.canario.entrada)
    reloj.t += TTL + 3600
    fuente.caida = caida
    sobre = await ej.ejecutar(H.id, H.canario.entrada)
    Sobre.model_validate(sobre.model_dump(mode="json"))  # regla 6: obsoleto ⇒ aviso
    p = sobre.procedencia[0]
    assert p.servido_desde == "obsoleto"
    assert p.consultado_en == original.procedencia[0].consultado_en  # la fecha original
    assert any("no es actual" in a and caida in a for a in sobre.avisos)
    assert sobre.datos == original.datos and sobre.creditos == 0


@pytest.mark.anyio
async def test_frescura_estricta_prefiere_el_error_al_dato_viejo(
    montaje: tuple[Ejecutor, Fuente, Reloj],
) -> None:
    ej, fuente, _ = montaje
    await ej.ejecutar(H.id, H.canario.entrada)
    fuente.caida = "fuente_no_disponible"
    with pytest.raises(ErrorEjecucion) as exc:
        await ej.ejecutar(H.id, H.canario.entrada, frescura="estricta")
    assert exc.value.codigo == "fuente_no_disponible"


@pytest.mark.anyio
async def test_sin_copia_la_caida_es_un_error(montaje: tuple[Ejecutor, Fuente, Reloj]) -> None:
    ej, fuente, _ = montaje
    fuente.caida = "fuente_no_disponible"
    with pytest.raises(ErrorEjecucion):
        await ej.ejecutar(H.id, H.canario.entrada)


@pytest.mark.anyio
async def test_un_error_de_la_peticion_no_se_tapa_con_cache(
    montaje: tuple[Ejecutor, Fuente, Reloj],
) -> None:
    """Solo una caída (no disponible, lenta) justifica el dato viejo; otro error sale tal cual."""
    ej, fuente, reloj = montaje
    await ej.ejecutar(H.id, H.canario.entrada)
    reloj.t += TTL + 1
    fuente.caida = "fuente_respuesta_invalida"
    with pytest.raises(ErrorEjecucion) as exc:
        await ej.ejecutar(H.id, H.canario.entrada)
    assert exc.value.codigo == "fuente_respuesta_invalida"


@pytest.mark.anyio
async def test_el_aviso_de_homonimos_sale_tambien_desde_cache() -> None:
    """Sale del índice de municipios, no de la fuente: no se guarda en la caché, se agrega al
    servir. Un sobre guardado antes del aviso lo trae igual (GEO Copilot, fiabilidad F4)."""
    h = CATALOGO.herramientas["cnmh_masacres_municipio"]
    grabado = json.loads(
        (Path(__file__).parent / "doradas" / f"{h.id}.json").read_text(encoding="utf-8")
    )

    class Grabada(Fuente):
        async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
            self.llamadas += 1
            copia: dict[str, Any] = json.loads(json.dumps(grabado["llamadas"][0]["respuesta"]))
            return copia

    fuente, reloj, almacen = Grabada(), Reloj(), AlmacenMemoria()
    almacen.reloj = reloj
    ej = Ejecutor(CATALOGO, {"datos-abiertos-mcp": fuente}, almacen, reloj)
    primero = await ej.ejecutar(h.id, {"municipio_divipola": "05313"})
    segundo = await ej.ejecutar(h.id, {"municipio_divipola": "05313"})
    assert fuente.llamadas == 1 and segundo.procedencia[0].servido_desde == "cache"
    for sobre in (primero, segundo):
        homonimos = [a for a in sobre.avisos if a.startswith("Se consultó 05313 = GRANADA")]
        assert len(homonimos) == 1 and "50313 GRANADA (META)" in homonimos[0]
    ((_, guardado),) = almacen._datos.values()
    assert not any(a.startswith("Se consultó") for a in guardado["sobre"]["avisos"])


@pytest.mark.anyio
async def test_el_aviso_de_datos_no_recientes_sale_tambien_desde_cache() -> None:
    """ICFES Saber 11 declara actualización semestral y no cambia desde 2023: el sobre solo decía
    la fecha de la consulta, de hoy. El aviso sale de la ficha técnica, no de la fuente."""
    h = CATALOGO.herramientas["icfes_saber11_municipio"]
    grabado = json.loads(
        (Path(__file__).parent / "doradas" / f"{h.id}.json").read_text(encoding="utf-8")
    )

    class Grabada(Fuente):
        async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
            self.llamadas += 1
            for ll in grabado["llamadas"]:
                if ll["argumentos"] == argumentos:
                    copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                    return copia
            raise AssertionError(argumentos)

    fuente, reloj, almacen = Grabada(), Reloj(), AlmacenMemoria()
    almacen.reloj = reloj
    ej = Ejecutor(CATALOGO, {"datos-abiertos-mcp": fuente}, almacen, reloj)
    primero = await ej.ejecutar(h.id, h.canario.entrada)
    segundo = await ej.ejecutar(h.id, h.canario.entrada)
    assert segundo.procedencia[0].servido_desde == "cache"
    for sobre in (primero, segundo):
        recientes = [a for a in sobre.avisos if a.startswith("Datos no recientes")]
        assert any("2023-08-23" in a for a in recientes) and len(recientes) == len(set(recientes))
    ((_, guardado),) = almacen._datos.values()
    assert not any(a.startswith("Datos no recientes") for a in guardado["sobre"]["avisos"])
