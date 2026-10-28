"""Página pública de estado (`GET /estado`): solo lo medido por los canarios, sin porcentajes."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from terranova import puerta
from terranova.app import crear_api
from terranova.catalogo import cargar
from terranova.pagina_estado import estado_fuentes, pagina_estado
from terranova.vigilancia import RegistroCanarios, Resultado

CATALOGO = cargar()
AHORA = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


def _r(herramienta: str, fuente: str, momento: str, *, ok: bool = True) -> Resultado:
    return Resultado(
        herramienta, fuente, momento, ok, "verde" if ok else "fuente_no_disponible", "", 100
    )


def _herramientas_de(fuente_id: str) -> list[str]:
    return [h.id for h in CATALOGO.herramientas.values() if h.fuente == fuente_id]


CON_HERRAMIENTAS = [f for f in sorted(CATALOGO.fuentes) if _herramientas_de(f)]


def _fuente_con_dos_herramientas() -> str:
    return next(f for f in sorted(CATALOGO.fuentes) if len(_herramientas_de(f)) >= 2)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_verde_ambar_rojo_y_sin_datos() -> None:
    dos = _fuente_con_dos_herramientas()
    h1, h2 = _herramientas_de(dos)[:2]
    otras = [f for f in CON_HERRAMIENTAS if f != dos]
    roja, vieja = otras[0], otras[1]
    ultimos = [
        _r(h1, dos, "2026-10-28T06:00:00.000+00:00"),
        _r(h2, dos, "2026-10-28T06:00:00.000+00:00", ok=False),  # una de dos: ámbar
        _r(_herramientas_de(roja)[0], roja, "2026-10-28T06:00:00.000+00:00", ok=False),
        _r(_herramientas_de(vieja)[0], vieja, "2026-10-25T06:00:00.000+00:00"),  # 3,25 días
    ]
    estado = {e["fuente_id"]: e for e in estado_fuentes(ultimos, CATALOGO, AHORA)}
    assert estado[dos]["estado"] == "ambar" and (estado[dos]["pasan"], estado[dos]["total"]) == (
        1,
        2,
    )
    assert estado[roja]["estado"] == "rojo"
    assert estado[vieja]["estado"] == "ambar"  # pasó, pero hace más de 48 h: sin verificar
    assert estado[otras[2]]["estado"] == "sin_datos"
    assert len(estado) == len(CATALOGO.fuentes)  # toda fuente del catálogo sale


def test_verde_reciente_y_orden_por_gravedad() -> None:
    f, otra = CON_HERRAMIENTAS[:2]
    ultimos = [_r(h, f, "2026-10-28T06:00:00.000+00:00") for h in _herramientas_de(f)] + [
        _r(_herramientas_de(otra)[0], otra, "2026-10-28T06:00:00.000+00:00", ok=False)
    ]
    estados = [e["estado"] for e in estado_fuentes(ultimos, CATALOGO, AHORA)]
    assert estados[0] == "rojo" and "verde" in estados
    assert estados == sorted(estados, key=["rojo", "ambar", "verde", "sin_datos"].index)


def test_la_pagina_no_inventa_disponibilidad_y_escapa_el_html() -> None:
    f = CON_HERRAMIENTAS[0]
    html = pagina_estado(
        [_r(_herramientas_de(f)[0], f, "2026-10-28T06:00:00.000+00:00")], CATALOGO, AHORA
    )
    assert "%" not in html.split("</style>")[1]  # sin porcentajes de uptime: no se miden
    assert "2026-10-28 01:00 (hora de Colombia)" in html  # 06:00 UTC, la última verificación
    assert "<script" not in html and "http://" not in html and "https://" not in html
    assert 'name="viewport"' in html
    sin_canarios = pagina_estado([], CATALOGO, AHORA)
    assert "todavía no hay canarios registrados" in sin_canarios
    trampa = CATALOGO.fuentes[f].model_copy(update={"titulo": "<script>x</script>"})
    falso = SimpleNamespace(fuentes={f: trampa})
    escapada = pagina_estado([], falso, AHORA)  # type: ignore[arg-type]
    assert "&lt;script&gt;x&lt;/script&gt;" in escapada and "<script>" not in escapada


@pytest.mark.anyio
async def test_get_estado_es_publico_y_html(tmp_path: Path) -> None:
    reg = RegistroCanarios(tmp_path / "c.db")
    reg.registrar(
        _r("igac_predio_en_punto", "igac.catastro.terreno", datetime.now(UTC).isoformat())
    )
    puerta.ESTADO.canarios = reg
    try:
        transporte = httpx.ASGITransport(app=crear_api())
        async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
            r = await c.get("/estado")
            esquema = (await c.get("/openapi.json")).json()
    finally:
        puerta.ESTADO.canarios = None
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    assert "max-age=60" in r.headers["cache-control"]
    assert CATALOGO.fuentes["igac.catastro.terreno"].titulo in r.text
    assert "/estado" not in esquema["paths"]  # fuera del OpenAPI, como /llms.txt
