"""ADR-0037: OAuth de los conectores remotos, con PKCE, tokens atados a la llave y sin puentes."""

import base64
import hashlib
import re
from collections.abc import AsyncIterator
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from terranova import puerta
from terranova.app import Aplicacion, crear_api
from terranova.identidad import RegistroSqlite
from terranova.oauth import (
    VIDA_ACCESO_S,
    VIDA_CODIGO_S,
    ErrorOAuth,
    ServidorOAuth,
    leer_metadatos_cliente,
    redireccion_valida,
)

PIMIENTA = "p" * 40
BASE = "https://terrnova.test"
VOLVER = "https://cliente.example/callback"
CIMD = "https://cliente.example/oauth/metadata.json"
VERIFICADOR = "v" * 50
DESAFIO = base64.urlsafe_b64encode(hashlib.sha256(VERIFICADOR.encode()).digest()).rstrip(b"=")


class Reloj:
    ahora = 1_000_000.0

    def __call__(self) -> float:
        return self.ahora


async def _metadatos(url: str) -> dict[str, Any]:
    return {"client_id": url, "client_name": "Cliente <b>", "redirect_uris": [VOLVER]}


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def registro(tmp_path: Path) -> RegistroSqlite:
    return RegistroSqlite(tmp_path / "t.db", PIMIENTA)


@pytest.fixture
def servidor(tmp_path: Path, registro: RegistroSqlite, reloj: Reloj) -> ServidorOAuth:
    return ServidorOAuth(tmp_path / "t.db", PIMIENTA, registro, BASE, _metadatos, reloj)


def _consulta(**extra: str) -> dict[str, str]:
    return {
        "client_id": CIMD,
        "redirect_uri": VOLVER,
        "response_type": "code",
        "code_challenge": DESAFIO.decode(),
        "code_challenge_method": "S256",
        "state": "abc",
        **extra,
    }


async def _codigo(servidor: ServidorOAuth, llave: str) -> str:
    q = _consulta()
    cliente, uri = await servidor.validar_redireccion(q)
    destino = servidor.autorizar(servidor.pedido(cliente, uri, q), llave)
    return parse_qs(urlsplit(destino).query)["code"][0]


def _canje(codigo: str, **extra: str) -> dict[str, str]:
    return {
        "grant_type": "authorization_code",
        "code": codigo,
        "client_id": CIMD,
        "redirect_uri": VOLVER,
        "code_verifier": VERIFICADOR,
        **extra,
    }


@pytest.mark.anyio
async def test_el_flujo_completo_da_un_token_que_resuelve_a_la_llave(
    servidor: ServidorOAuth, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"catastro"}, prueba=False, expira=None)
    registro.fijar_nivel("acme", "pro")
    token = servidor.token(_canje(await _codigo(servidor, llave)))
    principal = servidor.verificar_acceso(token["access_token"])
    assert principal is not None
    assert (principal.org, principal.nivel) == ("acme", "pro")
    assert principal.scopes == frozenset({"catastro"})


@pytest.mark.anyio
async def test_el_redirect_lleva_estado_y_emisor(
    servidor: ServidorOAuth, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    q = _consulta()
    cliente, uri = await servidor.validar_redireccion(q)
    partes = parse_qs(urlsplit(servidor.autorizar(servidor.pedido(cliente, uri, q), llave)).query)
    assert partes["state"] == ["abc"]
    assert partes["iss"] == [BASE]


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("campo", "valor", "error"),
    [
        ("code_verifier", "x" * 50, "invalid_grant"),
        ("code_verifier", "", "invalid_grant"),
        ("client_id", "https://otro.example/m.json", "invalid_grant"),
        ("redirect_uri", "https://cliente.example/otra", "invalid_grant"),
        ("resource", f"{BASE}/mcp/catastro", "invalid_target"),
    ],
)
async def test_el_canje_exige_lo_mismo_que_se_autorizo(
    servidor: ServidorOAuth, registro: RegistroSqlite, campo: str, valor: str, error: str
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    with pytest.raises(ErrorOAuth) as exc:
        servidor.token(_canje(await _codigo(servidor, llave), **{campo: valor}))
    assert exc.value.codigo == error


@pytest.mark.anyio
async def test_un_codigo_vencido_no_sirve(
    servidor: ServidorOAuth, registro: RegistroSqlite, reloj: Reloj
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    codigo = await _codigo(servidor, llave)
    reloj.ahora += VIDA_CODIGO_S + 1
    with pytest.raises(ErrorOAuth, match="venció"):
        servidor.token(_canje(codigo))


@pytest.mark.anyio
async def test_reusar_un_codigo_tumba_lo_que_emitio(
    servidor: ServidorOAuth, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    codigo = await _codigo(servidor, llave)
    primero = servidor.token(_canje(codigo))
    with pytest.raises(ErrorOAuth, match="ya se usó"):
        servidor.token(_canje(codigo))
    assert servidor.verificar_acceso(primero["access_token"]) is None


@pytest.mark.anyio
async def test_el_refresco_rota_y_reusarlo_tumba_la_familia(
    servidor: ServidorOAuth, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    primero = servidor.token(_canje(await _codigo(servidor, llave)))
    refresco = {
        "grant_type": "refresh_token",
        "client_id": CIMD,
        "refresh_token": primero["refresh_token"],
    }
    segundo = servidor.token(refresco)
    assert segundo["refresh_token"] != primero["refresh_token"]
    assert servidor.verificar_acceso(segundo["access_token"]) is not None
    with pytest.raises(ErrorOAuth, match="ya usado"):
        servidor.token(refresco)
    assert servidor.verificar_acceso(segundo["access_token"]) is None


@pytest.mark.anyio
async def test_revocar_la_llave_corta_los_tokens(
    servidor: ServidorOAuth, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    token = servidor.token(_canje(await _codigo(servidor, llave)))
    registro.revocar(registro.listar("acme")[0].llave_id)
    assert servidor.verificar_acceso(token["access_token"]) is None
    with pytest.raises(ErrorOAuth, match="vigente"):
        servidor.token(
            {
                "grant_type": "refresh_token",
                "client_id": CIMD,
                "refresh_token": token["refresh_token"],
            }
        )


@pytest.mark.anyio
async def test_el_token_de_acceso_vence(
    servidor: ServidorOAuth, registro: RegistroSqlite, reloj: Reloj
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    token = servidor.token(_canje(await _codigo(servidor, llave)))
    reloj.ahora += VIDA_ACCESO_S + 1
    assert servidor.verificar_acceso(token["access_token"]) is None


def test_ni_el_token_ni_el_codigo_se_guardan_en_claro(tmp_path: Path) -> None:
    import sqlite3

    registro = RegistroSqlite(tmp_path / "t.db", PIMIENTA)
    servidor = ServidorOAuth(tmp_path / "t.db", PIMIENTA, registro, BASE, _metadatos)
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)

    async def correr() -> dict[str, Any]:
        return servidor.token(_canje(await _codigo(servidor, llave)))

    import asyncio

    token = asyncio.run(correr())
    filas = sqlite3.connect(tmp_path / "t.db").execute("SELECT huella FROM oauth_tokens").fetchall()
    assert len(filas) == 2
    assert token["access_token"] not in {f[0] for f in filas}


@pytest.mark.anyio
@pytest.mark.parametrize(
    "cambio",
    [{"redirect_uri": "https://malo.example/x"}, {"client_id": "cualquiera"}],
)
async def test_lo_que_no_es_del_cliente_no_redirige(
    servidor: ServidorOAuth, cambio: dict[str, str]
) -> None:
    with pytest.raises(ErrorOAuth):
        await servidor.validar_redireccion(_consulta(**cambio))


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("cambio", "error"),
    [
        ({"code_challenge_method": "plain"}, "invalid_request"),
        ({"code_challenge": "corto"}, "invalid_request"),
        ({"response_type": "token"}, "unsupported_response_type"),
        ({"resource": "https://otro.example/mcp"}, "invalid_target"),
        ({"resource": f"{BASE}/v1/co"}, "invalid_target"),
    ],
)
async def test_el_pedido_exige_pkce_y_un_recurso_propio(
    servidor: ServidorOAuth, cambio: dict[str, str], error: str
) -> None:
    q = _consulta(**cambio)
    cliente, uri = await servidor.validar_redireccion(q)
    with pytest.raises(ErrorOAuth) as exc:
        servidor.pedido(cliente, uri, q)
    assert exc.value.codigo == error


@pytest.mark.anyio
async def test_una_llave_falsa_no_autoriza(servidor: ServidorOAuth) -> None:
    q = _consulta()
    cliente, uri = await servidor.validar_redireccion(q)
    with pytest.raises(ErrorOAuth) as exc:
        servidor.autorizar(servidor.pedido(cliente, uri, q), "rt_live_falsa")
    assert exc.value.codigo == "access_denied"


@pytest.mark.anyio
async def test_el_registro_dinamico_no_guarda_y_no_se_puede_falsificar(
    servidor: ServidorOAuth,
) -> None:
    datos = servidor.registrar({"client_name": "Otro", "redirect_uris": [VOLVER]})
    cliente = await servidor.cliente(datos["client_id"])
    assert cliente.redirect_uris == (VOLVER,)
    cuerpo, _, firma = datos["client_id"].partition(".")
    with pytest.raises(ErrorOAuth):
        await servidor.cliente(f"{cuerpo}x.{firma}")


@pytest.mark.parametrize(
    ("uri", "valida"),
    [
        ("https://claude.ai/api/mcp/auth_callback", True),
        ("http://localhost:3000/cb", True),
        ("http://127.0.0.1:9/cb", True),
        ("http://cliente.example/cb", False),
        ("javascript:alert(1)", False),
        ("https://x.example/cb#frag", False),
        ("https://user:pw@x.example/cb", False),
        ("https:///cb", False),
    ],
)
def test_redirecciones_permitidas(uri: str, valida: bool) -> None:
    assert redireccion_valida(uri) is valida


@pytest.mark.anyio
@pytest.mark.parametrize(
    "url",
    [
        "http://cliente.example/m.json",
        "https://cliente.example/",
        "https://localhost/m.json",
        "https://127.0.0.1/m.json",
        "https://169.254.169.254/latest/meta-data",
        "https://[::1]/m.json",
        "https://10.0.0.5/m.json",
    ],
)
async def test_el_cimd_no_sirve_de_puente_a_la_red_interna(url: str) -> None:
    with pytest.raises(ErrorOAuth) as exc:
        await leer_metadatos_cliente(url)
    assert exc.value.codigo == "invalid_client"


@pytest.mark.anyio
async def test_los_metadatos_deben_ser_del_mismo_client_id(
    tmp_path: Path, registro: RegistroSqlite
) -> None:
    async def ajenos(url: str) -> dict[str, Any]:
        return {"client_id": "https://otro.example/m.json", "redirect_uris": [VOLVER]}

    servidor = ServidorOAuth(tmp_path / "t.db", PIMIENTA, registro, BASE, ajenos)
    with pytest.raises(ErrorOAuth):
        await servidor.cliente(CIMD)


# --- por HTTP ------------------------------------------------------------------------------------


async def _mcp_falso(scope: Any, receive: Any, send: Any) -> None:
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"mcp"})


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def http(
    registro: RegistroSqlite, servidor: ServidorOAuth
) -> AsyncIterator[httpx.AsyncClient]:
    puerta.ESTADO.registro = registro
    puerta.ESTADO.oauth = servidor
    app = Aplicacion(crear_api(), {"/mcp": _mcp_falso})
    transporte = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transporte, base_url=BASE) as c:
            yield c
    finally:
        puerta.ESTADO.registro = None
        puerta.ESTADO.oauth = None


@pytest.fixture
def sin_oauth() -> None:
    puerta.ESTADO.oauth = None


async def _token_por_http(c: httpx.AsyncClient, llave: str) -> dict[str, Any]:
    pagina = await c.get("/oauth/autorizar", params=_consulta())
    assert pagina.status_code == 200
    assert pagina.headers["x-frame-options"] == "DENY"
    assert "Cliente &lt;b&gt;" in pagina.text  # el nombre lo escribe el cliente: va escapado
    assert "cliente.example" in pagina.text
    sello = re.search(r'name="pedido" value="([^"]+)"', pagina.text)
    assert sello
    datos = {"pedido": unescape(sello[1]), "llave": llave, "decision": "aceptar"}
    r = await c.post("/oauth/autorizar", data=datos)
    assert r.status_code == 303
    assert r.headers["location"].startswith(VOLVER)
    codigo = parse_qs(urlsplit(r.headers["location"]).query)["code"][0]
    token = await c.post("/oauth/token", data=_canje(codigo))
    assert token.status_code == 200
    assert token.headers["cache-control"] == "no-store"
    resultado: dict[str, Any] = token.json()
    return resultado


@pytest.mark.anyio
async def test_mcp_sin_token_dice_donde_autorizar(http: httpx.AsyncClient) -> None:
    r = await http.post("/mcp", json={})
    assert r.status_code == 401
    assert "resource_metadata=" in r.headers["www-authenticate"]
    url = r.headers["www-authenticate"].split('"')[1]
    meta = (await http.get(urlsplit(url).path)).json()
    assert meta["resource"] == f"{BASE}/mcp"
    servidor = (await http.get("/.well-known/oauth-authorization-server")).json()
    assert meta["authorization_servers"] == [servidor["issuer"]]
    assert servidor["code_challenge_methods_supported"] == ["S256"]


@pytest.mark.anyio
async def test_el_token_entra_a_mcp_y_no_a_la_api(
    http: httpx.AsyncClient, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    token = (await _token_por_http(http, llave))["access_token"]
    cabecera = {"Authorization": f"Bearer {token}"}
    assert (await http.post("/mcp", json={}, headers=cabecera)).status_code == 200
    assert (await http.get("/v1/uso", headers=cabecera)).status_code == 401


@pytest.mark.anyio
async def test_la_llave_sigue_entrando_a_mcp(
    http: httpx.AsyncClient, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    r = await http.post("/mcp", json={}, headers={"Authorization": f"Bearer {llave}"})
    assert r.status_code == 200


@pytest.mark.anyio
async def test_una_llave_mala_vuelve_a_la_pagina_sin_redirigir(http: httpx.AsyncClient) -> None:
    pagina = await http.get("/oauth/autorizar", params=_consulta())
    sello = re.search(r'name="pedido" value="([^"]+)"', pagina.text)
    assert sello
    datos = {"pedido": unescape(sello[1]), "llave": "mala", "decision": "aceptar"}
    r = await http.post("/oauth/autorizar", data=datos)
    assert r.status_code == 400
    assert "no es válida" in r.text


@pytest.mark.anyio
async def test_negar_vuelve_al_cliente_con_el_error(http: httpx.AsyncClient) -> None:
    pagina = await http.get("/oauth/autorizar", params=_consulta())
    sello = re.search(r'name="pedido" value="([^"]+)"', pagina.text)
    assert sello
    r = await http.post(
        "/oauth/autorizar", data={"pedido": unescape(sello[1]), "decision": "negar"}
    )
    assert r.status_code == 303
    consulta = parse_qs(urlsplit(r.headers["location"]).query)
    assert consulta["error"] == ["access_denied"]
    assert consulta["state"] == ["abc"]


@pytest.mark.anyio
async def test_un_formulario_alterado_no_vale(http: httpx.AsyncClient) -> None:
    r = await http.post(
        "/oauth/autorizar", data={"pedido": "e30.falso", "llave": "x", "decision": "aceptar"}
    )
    assert r.status_code == 400


@pytest.mark.anyio
async def test_una_redireccion_ajena_se_muestra_y_no_se_sigue(http: httpx.AsyncClient) -> None:
    r = await http.get("/oauth/autorizar", params=_consulta(redirect_uri="https://malo.example/x"))
    assert r.status_code == 400
    assert "location" not in r.headers


@pytest.mark.anyio
async def test_el_error_del_token_usa_el_formato_de_oauth(http: httpx.AsyncClient) -> None:
    r = await http.post("/oauth/token", data={"grant_type": "password"})
    assert r.status_code == 400
    assert r.json()["error"] == "unsupported_grant_type"


@pytest.mark.anyio
async def test_apagado_nada_cambia(http: httpx.AsyncClient, sin_oauth: None) -> None:
    puerta.ESTADO.oauth = None
    r = await http.post("/mcp", json={})
    assert r.status_code == 401
    assert "www-authenticate" not in r.headers
    assert (await http.get("/.well-known/oauth-authorization-server")).status_code == 404
    assert (await http.post("/oauth/token", data={})).status_code == 404


@pytest.mark.anyio
async def test_el_token_de_un_perfil_no_abre_los_demas(
    servidor: ServidorOAuth, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    q = _consulta(resource=f"{BASE}/mcp/catastro")
    cliente, uri = await servidor.validar_redireccion(q)
    destino = servidor.autorizar(servidor.pedido(cliente, uri, q), llave)
    codigo = parse_qs(urlsplit(destino).query)["code"][0]
    token = servidor.token(_canje(codigo))["access_token"]
    assert servidor.verificar_acceso(token, "/mcp/catastro") is not None
    assert servidor.verificar_acceso(token, "/mcp") is None
    assert servidor.verificar_acceso(token, "/mcp/territorio") is None


@pytest.mark.anyio
async def test_el_token_general_vale_en_cualquier_perfil(
    servidor: ServidorOAuth, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    token = servidor.token(_canje(await _codigo(servidor, llave)))["access_token"]
    assert servidor.verificar_acceso(token, "/mcp/catastro") is not None


@pytest.mark.anyio
async def test_un_intento_equivocado_no_quema_el_codigo(
    servidor: ServidorOAuth, registro: RegistroSqlite
) -> None:
    llave = registro.crear("acme", {"*"}, prueba=False, expira=None)
    codigo = await _codigo(servidor, llave)
    with pytest.raises(ErrorOAuth):
        servidor.token(_canje(codigo, code_verifier="x" * 50))
    assert servidor.token(_canje(codigo))["access_token"]


@pytest.mark.anyio
async def test_sin_redirect_uri_no_se_autoriza(servidor: ServidorOAuth) -> None:
    with pytest.raises(ErrorOAuth):
        await servidor.validar_redireccion(_consulta(redirect_uri=""))


@pytest.mark.anyio
async def test_el_cliente_se_recuerda_un_rato(
    tmp_path: Path, registro: RegistroSqlite, reloj: Reloj
) -> None:
    lecturas = 0

    async def contar(url: str) -> dict[str, Any]:
        nonlocal lecturas
        lecturas += 1
        return await _metadatos(url)

    servidor = ServidorOAuth(tmp_path / "t.db", PIMIENTA, registro, BASE, contar, reloj)
    await servidor.cliente(CIMD)
    await servidor.cliente(CIMD)
    assert lecturas == 1
    reloj.ahora += 301
    await servidor.cliente(CIMD)
    assert lecturas == 2


@pytest.mark.anyio
async def test_el_registro_rechaza_con_su_codigo(http: httpx.AsyncClient) -> None:
    r = await http.post("/oauth/registro", json={"redirect_uris": ["http://malo.example"]})
    assert r.status_code == 400
    assert r.json()["error"] == "invalid_client_metadata"


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("ruta", "params"),
    [
        ("/oauth/autorizar", {"client_id": "rt_cliente_abc.ñññ"}),
        ("/oauth/autorizar", {"client_id": "https://[x/m"}),
        ("/oauth/autorizar", {"client_id": "https://x.example:99999/m"}),
        ("/oauth/autorizar", {"client_id": CIMD, "redirect_uri": "http://[x/cb"}),
    ],
)
async def test_la_entrada_rara_es_un_error_y_no_un_500(
    http: httpx.AsyncClient, ruta: str, params: dict[str, str]
) -> None:
    assert (await http.get(ruta, params=params)).status_code == 400


@pytest.mark.anyio
async def test_un_sello_no_ascii_no_tumba_el_formulario(http: httpx.AsyncClient) -> None:
    r = await http.post("/oauth/autorizar", data={"pedido": "abc.ñññ", "decision": "aceptar"})
    assert r.status_code == 400


@pytest.mark.parametrize(
    "uri",
    ["http://evil.com\\@localhost/cb", "http://[x/cb", "http://localhost:99999/cb"],
)
def test_redirecciones_tramposas(uri: str) -> None:
    assert redireccion_valida(uri) is False


def test_los_editores_conectan_con_su_esquema() -> None:
    assert redireccion_valida("cursor://anysphere.cursor-retrieval/oauth/callback")
    assert not redireccion_valida("otroesquema://x/cb")
