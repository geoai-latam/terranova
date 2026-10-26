"""F3.2: llaves, scopes por familia, planes y revocación (ADR-0009)."""

import json
import sqlite3
import time
from collections.abc import AsyncIterator, Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from terranova import puerta
from terranova.app import crear_aplicacion
from terranova.identidad import FORMATO, RegistroSqlite, bearer

PIMIENTA = "p" * 40
DORADAS = Path(__file__).parent / "doradas"


@pytest.fixture
def registro() -> RegistroSqlite:
    return RegistroSqlite(":memory:", PIMIENTA)


def test_la_llave_se_muestra_una_vez_y_solo_se_guarda_su_hmac(tmp_path: Path) -> None:
    r = RegistroSqlite(tmp_path / "t.db", PIMIENTA)
    llave = r.crear("geoai", {"territorio"}, prueba=False, expira=None)
    assert FORMATO.fullmatch(llave) and llave.startswith("rt_live_")
    filas = sqlite3.connect(tmp_path / "t.db").execute("SELECT * FROM llaves").fetchall()
    assert not any(llave in str(f) for f in filas)


def test_verificar_planes_y_scopes(registro: RegistroSqlite) -> None:
    viva = registro.verificar(registro.crear("geoai", {"territorio"}, prueba=False, expira=None))
    prueba = registro.verificar(registro.crear("geoai", {"*"}, prueba=True, expira=None))
    assert viva is not None and viva.plan == "normal" and viva.puede("territorio")
    assert not viva.puede("contratacion")
    assert prueba is not None and prueba.plan == "evaluacion" and prueba.puede("contratacion")


def test_revocada_vencida_o_falsa_no_entra(registro: RegistroSqlite) -> None:
    llave = registro.crear("geoai", {"*"}, prueba=False, expira=None)
    (ll,) = registro.listar("geoai")
    assert registro.revocar(ll.llave_id) and registro.verificar(llave) is None
    assert not registro.revocar(ll.llave_id)  # ya revocada
    ayer = date.today() - timedelta(days=2)
    vencida = registro.crear("geoai", {"*"}, prueba=False, expira=ayer)
    assert registro.verificar(vencida) is None
    assert registro.verificar("rt_live_" + "A" * 43) is None
    assert registro.verificar("no-es-una-llave") is None
    otra_pimienta = RegistroSqlite(":memory:", "q" * 40)
    assert otra_pimienta.verificar(llave) is None


def test_la_pimienta_es_obligatoria_y_larga() -> None:
    with pytest.raises(ValueError, match="32"):
        RegistroSqlite(":memory:", "corta")


def test_bearer() -> None:
    assert bearer("Bearer rt_live_x") == "rt_live_x" and bearer("bearer  y ") == "y"
    assert bearer(None) is None and bearer("Basic x") is None and bearer("Bearer") is None


class Grabado:
    def __init__(self, herramienta: str) -> None:
        self.llamadas = json.loads((DORADAS / f"{herramienta}.json").read_text(encoding="utf-8"))[
            "llamadas"
        ]

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.llamadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise AssertionError(argumentos)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def con_identidad(registro: RegistroSqlite) -> Iterator[RegistroSqlite]:
    puerta.usar_conectores(
        {
            "arcgis-mcp": Grabado("igac_predio_en_punto"),
            "dane-mcp": Grabado("dane_poblacion_municipio"),
        }
    )
    puerta.ESTADO.registro = registro
    try:
        yield registro
    finally:
        puerta.ESTADO.registro = None
        puerta.usar_conectores(None)


@pytest.fixture
async def cliente() -> AsyncIterator[httpx.AsyncClient]:
    transporte = httpx.ASGITransport(app=crear_aplicacion())
    async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
        yield c


PREDIO = "/v1/co/territorio/igac_predio_en_punto"
CHIA = {"lon": -74.0262, "lat": 4.8619}
DANE = "/v1/co/estadisticas/dane_poblacion_municipio"


def _con(llave: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {llave}"}


@pytest.mark.anyio
async def test_rest_sin_llave_401_y_catalogo_publico(
    con_identidad: RegistroSqlite, cliente: httpx.AsyncClient
) -> None:
    r = await cliente.post(PREDIO, json=CHIA)
    assert r.status_code == 401 and r.json()["code"] == "no_autenticado"
    assert (await cliente.get("/v1/fuentes")).status_code == 200
    assert (await cliente.get("/openapi.json")).status_code == 200


@pytest.mark.anyio
async def test_rest_con_llave_scope_y_plan(
    con_identidad: RegistroSqlite, cliente: httpx.AsyncClient
) -> None:
    territorio = con_identidad.crear("geoai", {"territorio"}, prueba=False, expira=None)
    r = await cliente.post(PREDIO, json=CHIA, headers=_con(territorio))
    assert r.status_code == 200 and r.json()["estado"] == "encontrado"
    # sin el scope de la familia
    r = await cliente.post(DANE, json={"municipio_divipola": "11001"}, headers=_con(territorio))
    assert r.status_code == 403 and r.json()["code"] == "sin_permiso"
    # con el scope pero llave normal: DANE tiene licencia por verificar (ADR-0007)
    viva = con_identidad.crear("geoai", {"estadisticas"}, prueba=False, expira=None)
    r = await cliente.post(DANE, json={"municipio_divipola": "11001"}, headers=_con(viva))
    assert r.status_code == 403 and r.json()["code"] == "licencia_no_habilitada"
    # llave de evaluación: responde
    prueba = con_identidad.crear("geoai", {"estadisticas"}, prueba=True, expira=None)
    r = await cliente.post(DANE, json={"municipio_divipola": "11001"}, headers=_con(prueba))
    assert r.status_code == 200 and r.json()["datos"]["poblacion_censada"] == 7181469


@pytest.mark.anyio
async def test_revocacion_surte_efecto_en_menos_de_5_s(
    con_identidad: RegistroSqlite, cliente: httpx.AsyncClient
) -> None:
    llave = con_identidad.crear("geoai", {"*"}, prueba=False, expira=None)
    assert (await cliente.post(PREDIO, json=CHIA, headers=_con(llave))).status_code == 200
    (ll,) = con_identidad.listar("geoai")
    t0 = time.monotonic()
    con_identidad.revocar(ll.llave_id)
    r = await cliente.post(PREDIO, json=CHIA, headers=_con(llave))
    assert r.status_code == 401 and time.monotonic() - t0 < 5
    assert con_identidad.listar("geoai")[0].ultimo_uso is not None


@pytest.mark.anyio
async def test_mcp_sin_llave_401(con_identidad: RegistroSqlite, cliente: httpx.AsyncClient) -> None:
    for ruta in ("/mcp", "/mcp/territorio"):
        r = await cliente.post(ruta, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        assert r.status_code == 401 and r.json()["code"] == "no_autenticado"


@pytest.mark.anyio
async def test_ejecutar_con_identidad_exige_principal_y_scope(
    con_identidad: RegistroSqlite,
) -> None:
    from terranova.errores import ErrorEjecucion

    with pytest.raises(ErrorEjecucion) as exc:
        await puerta.ejecutar("igac_predio_en_punto", CHIA, None)
    assert exc.value.codigo == "no_autenticado"
    principal = con_identidad.verificar(
        con_identidad.crear("g1", {"ambiente"}, prueba=False, expira=None)
    )
    with pytest.raises(ErrorEjecucion) as exc:
        await puerta.ejecutar("igac_predio_en_punto", CHIA, principal)
    assert exc.value.codigo == "sin_permiso"
