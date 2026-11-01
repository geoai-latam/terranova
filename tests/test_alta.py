"""Alta de la llave de prueba con correo verificado y formulario de contacto (ADR-0034)."""

import re
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from terranova import alta as modulo_alta
from terranova import puerta
from terranova.alta import Altas, ErrorAlta
from terranova.app import crear_api
from terranova.bd import Conexion
from terranova.identidad import RegistroSql

PIMIENTA = "p" * 40


class CorreoFalso:
    def __init__(self) -> None:
        self.enviados: list[tuple[str, str, str]] = []
        self.mensajes: list[Any] = []

    async def enviar(self, destino: str, mensaje: Any) -> None:
        self.enviados.append((destino, mensaje.asunto, mensaje.texto))
        self.mensajes.append(mensaje)

    def enlace(self) -> str:
        con_enlace = [e for e in self.enviados if "?t=" in e[2]]
        m = re.search(r"\?t=([A-Za-z0-9_-]+)", con_enlace[-1][2])
        assert m, self.enviados[-1][2]
        return m.group(1)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def entorno() -> tuple[Altas, RegistroSql, CorreoFalso]:
    registro = RegistroSql(":memory:", PIMIENTA)
    correo = CorreoFalso()
    return Altas(Conexion(":memory:"), registro, PIMIENTA, correo), registro, correo


async def _pedir(altas: Altas, correo: str = "ana@ejemplo.co", ip: str = "1.2.3.4") -> None:
    await altas.solicitar(correo, "Ana", "Ejemplo SAS", "probar predios", True, ip)


@pytest.mark.anyio
async def test_el_enlace_da_una_llave_de_prueba_una_sola_vez(entorno: Any) -> None:
    altas, registro, correo = entorno
    await _pedir(altas)
    destino, _, texto = correo.enviados[-1]
    assert destino == "ana@ejemplo.co" and "24 horas" in texto
    assert "rt_live_" not in texto  # la llave nunca va por correo
    token = correo.enlace()
    dueno, llave = await altas.confirmar(token)
    assert dueno == "ana@ejemplo.co"
    p = registro.verificar(llave)
    assert p is not None and p.nivel == modulo_alta.NIVEL_ALTA and p.org.startswith("alta-")
    (ll,) = registro.listar(p.org)
    vence = datetime.fromisoformat(ll.expira).date() if ll.expira else None
    assert vence == (datetime.now(UTC) + modulo_alta.VIGENCIA_LLAVE).date()
    with pytest.raises(ErrorAlta, match="ya se usó"):
        await altas.confirmar(token)


@pytest.mark.anyio
async def test_un_correo_con_llave_no_recibe_otra(entorno: Any) -> None:
    altas, registro, correo = entorno
    await _pedir(altas)
    await altas.confirmar(correo.enlace())
    await _pedir(altas)
    assert "ya tiene una llave" in correo.enviados[-1][2] and "?t=" not in correo.enviados[-1][2]
    assert len(registro.listar()) == 1


@pytest.mark.anyio
async def test_dos_enlaces_del_mismo_correo_dan_una_sola_llave(entorno: Any) -> None:
    altas, registro, correo = entorno
    await _pedir(altas)
    primero = correo.enlace()
    await _pedir(altas)
    segundo = correo.enlace()
    await altas.confirmar(segundo)
    with pytest.raises(ErrorAlta, match="ya tiene una llave"):
        await altas.confirmar(primero)
    assert len(registro.listar()) == 1


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("correo", "acepto", "mensaje"),
    [
        ("no-es-correo", True, "no parece válido"),
        ("x@mailinator.com", True, "desechable"),
        ("ana@ejemplo.co", False, "privacidad"),
    ],
)
async def test_lo_que_no_da_llave(entorno: Any, correo: str, acepto: bool, mensaje: str) -> None:
    altas, _, enviados = entorno
    with pytest.raises(ErrorAlta, match=mensaje):
        await altas.solicitar(correo, "Ana", "", "", acepto, "1.2.3.4")
    assert enviados.enviados == []


@pytest.mark.anyio
async def test_tope_de_altas_por_ip(entorno: Any) -> None:
    altas, _, _ = entorno
    for i in range(modulo_alta.ALTAS_POR_IP_HORA):
        await _pedir(altas, f"p{i}@ejemplo.co")
    with pytest.raises(ErrorAlta, match="Demasiadas"):
        await _pedir(altas, "otra@ejemplo.co")
    await _pedir(altas, "otra@ejemplo.co", ip="5.6.7.8")  # otra red sí puede


@pytest.mark.anyio
async def test_el_enlace_vence(entorno: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    altas, _, correo = entorno
    await _pedir(altas)
    token = correo.enlace()
    luego = datetime.now(UTC) + timedelta(hours=25)
    monkeypatch.setattr(modulo_alta, "_ahora", lambda: luego)
    with pytest.raises(ErrorAlta, match="venció"):
        await altas.confirmar(token)


@pytest.mark.anyio
async def test_sin_correo_configurado_remite_a_soporte() -> None:
    altas = Altas(Conexion(":memory:"), RegistroSql(":memory:", PIMIENTA), PIMIENTA, None)
    with pytest.raises(ErrorAlta, match=r"soporte@terrnova.com"):
        await _pedir(altas)


@pytest.mark.anyio
async def test_contacto_se_guarda_y_llega_a_soporte(entorno: Any) -> None:
    altas, _, correo = entorno
    await altas.contactar(
        "Ana", "ana@ejemplo.co", "Ejemplo SAS", "tablero", "Hola,\nquiero un tablero.", True, "ip"
    )
    (aviso_d, aviso_a, aviso_t), (acuse_d, acuse_a, acuse_t) = correo.enviados[-2:]
    assert (
        aviso_d == "soporte@terrnova.com" and "Tablero" in aviso_a and "ana@ejemplo.co" in aviso_t
    )
    assert correo.mensajes[-2].responder_a == "ana@ejemplo.co"  # responder le escribe a Ana
    assert acuse_d == "ana@ejemplo.co" and "Recibimos tu mensaje" in acuse_a
    assert "quiero un tablero" in acuse_t
    with pytest.raises(ErrorAlta, match="mensaje"):
        await altas.contactar("Ana", "ana@ejemplo.co", "", "otro", "", True, "ip")


@pytest.fixture
async def rest(entorno: Any) -> Any:
    antes = puerta.ESTADO.altas
    puerta.ESTADO.altas = entorno[0]
    transporte = httpx.ASGITransport(app=crear_api())
    async with httpx.AsyncClient(transport=transporte, base_url="http://puerta") as c:
        yield c
    puerta.ESTADO.altas = antes


@pytest.mark.anyio
async def test_el_formulario_del_sitio_de_punta_a_punta(rest: Any, entorno: Any) -> None:
    _, registro, correo = entorno
    r = await rest.post(
        "/v1/alta",
        data={"correo": "ana@ejemplo.co", "nombre": "Ana", "acepto": "si", "web": ""},
        headers={"x-forwarded-for": "9.9.9.9, 10.0.0.1"},
    )
    assert r.status_code == 200 and "Revisa tu correo" in r.text
    token = correo.enlace()
    abrir = await rest.get("/v1/alta/confirmar", params={"t": token})
    assert "Ver mi llave" in abrir.text and "rt_live_" not in abrir.text  # abrir no la crea
    assert registro.listar() == []
    confirmar = await rest.post("/v1/alta/confirmar", data={"t": token})
    assert confirmar.status_code == 200 and "rt_live_" in confirmar.text
    assert confirmar.headers["cache-control"] == "no-store"
    otra = await rest.post("/v1/alta/confirmar", data={"t": token})
    assert otra.status_code == 400 and "rt_live_" not in otra.text


@pytest.mark.anyio
async def test_el_campo_trampa_no_hace_nada(rest: Any, entorno: Any) -> None:
    _, _, correo = entorno
    r = await rest.post(
        "/v1/alta",
        data={"correo": "bot@ejemplo.co", "nombre": "Bot", "acepto": "si", "web": "spam"},
    )
    assert r.status_code == 200 and correo.enviados == []
    c = await rest.post("/v1/contacto", data={"nombre": "Bot", "web": "spam"})
    assert c.status_code == 200 and correo.enviados == []


@pytest.mark.anyio
async def test_un_error_del_formulario_se_ve_en_la_pagina(rest: Any) -> None:
    r = await rest.post(
        "/v1/alta", data={"correo": "x@mailinator.com", "nombre": "X", "acepto": "si"}
    )
    assert r.status_code == 400 and "desechable" in r.text
