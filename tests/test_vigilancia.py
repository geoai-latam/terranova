"""F7.1: canarios diarios. Sin red: los conectores responden lo grabado en las doradas."""

import json
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import httpx
import pytest

from terranova import puerta
from terranova.app import crear_api
from terranova.catalogo import cargar
from terranova.conector import ErrorConector
from terranova.ejecutor import Ejecutor
from terranova.vigilancia import (
    RegistroCanarios,
    Resultado,
    alertar,
    correr,
    estado_por_fuente,
)

DORADAS = Path(__file__).parent / "doradas"
CATALOGO = cargar()


class Grabado:
    def __init__(self, llamadas: list[dict[str, Any]]) -> None:
        self.llamadas = llamadas

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.llamadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise ErrorConector("no grabada", "fuente_respuesta_invalida")


class Caido:
    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        raise ErrorConector("HTTP 503", "fuente_no_disponible", 5)


def _conectores() -> dict[str, Any]:
    por_conector: dict[str, list[dict[str, Any]]] = {}
    for ruta in DORADAS.glob("*.json"):
        for ll in json.loads(ruta.read_text(encoding="utf-8"))["llamadas"]:
            por_conector.setdefault(ll["conector"], []).append(ll)
    return {n: Grabado(ll) for n, ll in por_conector.items()}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_todos_los_canarios_verdes_con_lo_grabado() -> None:
    r = await correr(CATALOGO, Ejecutor(CATALOGO, _conectores()), reloj=lambda: 0.0)
    assert {x.herramienta for x in r} == set(CATALOGO.herramientas)
    assert [x for x in r if not x.ok] == []


@pytest.mark.anyio
async def test_conector_caido_y_lento_salen_rojos() -> None:
    conectores = _conectores() | {"arcgis-mcp": Caido()}
    tiempos = iter([0.0, 9.0] * len(CATALOGO.herramientas))  # 9 s por canario: todos lentos
    r = {
        x.herramienta: x
        for x in await correr(CATALOGO, Ejecutor(CATALOGO, conectores), reloj=lambda: next(tiempos))
    }
    predio = r["igac_predio_en_punto"]
    assert not predio.ok and predio.codigo == "fuente_no_disponible"
    sismos = r["usgs_sismos_en_zona"]
    assert not sismos.ok and sismos.codigo == "lento" and sismos.latencia_ms == 9000


@pytest.mark.anyio
async def test_verdad_distinta_sale_roja() -> None:
    h = CATALOGO.herramientas["igac_vereda_en_punto"]
    otra = h.canario.model_copy(update={"verdad": {**h.canario.verdad, "nombre_vereda": "OTRA"}})
    catalogo = CATALOGO.model_copy(
        update={"herramientas": {h.id: h.model_copy(update={"canario": otra})}}
    )
    (r,) = await correr(catalogo, Ejecutor(catalogo, _conectores()), reloj=lambda: 0.0)
    assert not r.ok and r.codigo == "verdad_distinta" and "nombre_vereda" in r.detalle


@pytest.mark.anyio
async def test_campo_renombrado_en_la_fuente_sale_esquema_cambiado() -> None:
    """F7.3: la fuente renombra CODIGO_ANTERIOR; la lista blanca lo deja fuera sin error y la
    verdad (código y nombre) sigue igual: solo `canario.campos` lo nota."""
    h = CATALOGO.herramientas["igac_vereda_en_punto"]
    catalogo = CATALOGO.model_copy(update={"herramientas": {h.id: h}})
    texto = (DORADAS / f"{h.id}.json").read_text(encoding="utf-8")
    llamadas = json.loads(texto.replace('"CODIGO_ANTERIOR": "', '"COD_ANTERIOR_V2": "'))["llamadas"]
    (r,) = await correr(catalogo, Ejecutor(catalogo, {"arcgis-mcp": Grabado(llamadas)}))
    assert not r.ok and r.codigo == "esquema_cambiado"
    assert "codigo_vereda_anterior" in r.detalle and "nombre_vereda" not in r.detalle


def _r(h: str, f: str, momento: str, ok: bool = True) -> Resultado:
    return Resultado(h, f, momento, ok, "verde" if ok else "fuente_no_disponible", "", 10)


def test_registro_ultimos_y_dias_seguidos(tmp_path: Path) -> None:
    reg = RegistroCanarios(tmp_path / "c.db")
    hoy = datetime.now(UTC)
    for dias in (0, 1, 3):
        momento = (hoy - timedelta(days=dias)).isoformat(timespec="milliseconds")
        reg.registrar(_r("a", "x.y", momento, ok=dias != 0))
    reg.registrar(_r("a", "x.y", hoy.isoformat(timespec="milliseconds")))  # repetido: no duplica
    (ultimo,) = reg.ultimos()
    assert ultimo.herramienta == "a" and not ultimo.ok
    assert reg.dias_seguidos("a") == 2 and reg.dias_seguidos("b") == 0


def test_estado_por_fuente() -> None:
    m = "2026-10-22T00:00:00.000+00:00"
    ultimos = [_r("igac_predio_en_punto", "igac.catastro.terreno", m)]
    ultimos += [_r("pnn_areas_protegidas_en_punto", "pnn.runap", m)]
    ultimos += [_r("pnn_areas_protegidas_en_zona", "pnn.runap", m, ok=False)]
    estado = {e["fuente_id"]: e for e in estado_por_fuente(ultimos, CATALOGO)}
    assert set(estado) == set(CATALOGO.fuentes)
    assert estado["igac.catastro.terreno"]["estado"] == "verde"
    assert estado["pnn.runap"]["estado"] == "rojo" and len(estado["pnn.runap"]["herramientas"]) == 2
    assert estado["usgs.sismos"]["estado"] == "sin_datos"


def test_alerta_solo_con_url_y_con_rojos() -> None:
    recibido: list[dict[str, Any]] = []

    class Receptor(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            recibido.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *_: Any) -> None:
            pass

    servidor = HTTPServer(("127.0.0.1", 0), Receptor)
    hilo = threading.Thread(target=servidor.handle_request, daemon=True)
    hilo.start()
    url = f"http://127.0.0.1:{servidor.server_port}/"
    m = "2026-10-22T00:00:00.000+00:00"
    assert not alertar([_r("a", "x.y", m, ok=False)], None)  # sin URL no sale nada
    assert not alertar([_r("a", "x.y", m)], url)  # todo verde: no se avisa
    assert alertar([_r("a", "x.y", m), _r("b", "x.y", m, ok=False)], url)
    hilo.join(5)
    servidor.server_close()
    assert [r["herramienta"] for r in recibido[0]["canarios_rojos"]] == ["b"]


@pytest.mark.anyio
async def test_v1_estado_es_publico(tmp_path: Path) -> None:
    reg = RegistroCanarios(tmp_path / "c.db")
    reg.registrar(
        _r("igac_predio_en_punto", "igac.catastro.terreno", "2026-10-22T00:00:00.000+00:00")
    )
    puerta.canarios = reg
    try:
        transporte = httpx.ASGITransport(app=crear_api())
        async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
            r = await c.get("/v1/estado")
    finally:
        puerta.canarios = None
    assert r.status_code == 200
    estado = {e["fuente_id"]: e["estado"] for e in r.json()}
    assert estado["igac.catastro.terreno"] == "verde" and estado["pnn.runap"] == "sin_datos"
