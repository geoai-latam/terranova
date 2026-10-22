"""F7.2: métricas de Prometheus en /metrics (spec 05 §12.2). Sin red."""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from terranova import metricas, puerta
from terranova.app import crear_api
from terranova.medicion import OutboxSql

DORADAS = Path(__file__).parent / "doradas"
RAIZ = Path(__file__).resolve().parents[1]


class Grabado:
    def __init__(self, llamadas: list[dict[str, Any]]) -> None:
        self.llamadas = llamadas

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.llamadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise AssertionError(f"no grabada: {herramienta}")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _valor(texto: str, nombre: str, **etiquetas: str) -> float:
    for linea in texto.splitlines():
        if linea.startswith(nombre + "{") or linea.startswith(nombre + " "):
            if all(f'{k}="{v}"' in linea for k, v in etiquetas.items()):
                return float(linea.rsplit(" ", 1)[1])
    return 0.0


@pytest.mark.anyio
async def test_una_solicitud_queda_medida(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TERRANOVA_PLAN", "evaluacion")
    grabado = json.loads((DORADAS / "igac_predio_en_punto.json").read_text(encoding="utf-8"))
    puerta.usar_conectores({"arcgis-mcp": Grabado(grabado["llamadas"])})
    transporte = httpx.ASGITransport(app=crear_api())
    try:
        async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
            antes = (await c.get("/metrics")).text
            r = await c.post(
                "/v1/co/territorio/igac_predio_en_punto", json={"lon": -74.0262, "lat": 4.8619}
            )
            mal = await c.post("/v1/co/territorio/igac_predio_por_codigo", json={"codigo": "x"})
            despues = await c.get("/metrics")
    finally:
        puerta.usar_conectores(None)
    assert r.status_code == 200 and mal.status_code == 400
    assert despues.headers["content-type"].startswith("text/plain")
    texto = despues.text
    clave = {"herramienta": "igac_predio_en_punto", "estado": "encontrado"}
    assert (
        _valor(texto, "rt_solicitudes_total", **clave)
        == _valor(antes, "rt_solicitudes_total", **clave) + 1
    )
    assert (
        _valor(
            texto,
            "rt_latencia_segundos_count",
            herramienta="igac_predio_en_punto",
            servido_desde="fuente",
        )
        >= 1
    )
    assert _valor(texto, "rt_fuente_latencia_segundos_count", fuente="igac.catastro.terreno") >= 1


def test_lo_que_se_mide_al_raspar(tmp_path: Path) -> None:
    outbox = OutboxSql(tmp_path / "o.db")
    metricas.AL_RASPAR.circuitos = lambda: [("pnn.runap", True), ("usgs.sismos", False)]
    metricas.AL_RASPAR.canarios = lambda: [("pnn.runap", False), ("pnn.runap", True)]
    metricas.AL_RASPAR.outbox = outbox.pendientes
    try:
        from prometheus_client import generate_latest

        texto = generate_latest(metricas.REGISTRO).decode()
    finally:
        metricas.AL_RASPAR.circuitos = lambda: []
        metricas.AL_RASPAR.canarios = lambda: []
        metricas.AL_RASPAR.outbox = lambda: None
    assert _valor(texto, "rt_circuito_abierto", fuente="pnn.runap") == 1
    assert _valor(texto, "rt_circuito_abierto", fuente="usgs.sismos") == 0
    assert _valor(texto, "rt_canario", fuente="pnn.runap", resultado="rojo") == 1
    assert _valor(texto, "rt_canario", fuente="pnn.runap", resultado="verde") == 1
    assert "rt_outbox_pendientes 0.0" in texto


def test_metrics_no_sale_por_el_borde_ni_en_el_openapi() -> None:
    assert "/metrics" not in crear_api().openapi()["paths"]
    caddy = (RAIZ / "docker" / "Caddyfile").read_text(encoding="utf-8")
    assert "respond /metrics 404" in caddy
