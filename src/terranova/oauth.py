"""OAuth 2.1 para los conectores remotos de MCP (ADR-0037), sobre las mismas organizaciones.

La puerta es su propio servidor de autorización, sin servicios aparte. Quien autoriza demuestra que
tiene una llave de Terrnova: el token queda atado a esa llave y hereda su plan, sus scopes y su
revocación, de modo que los dos caminos llegan al mismo principal (ADR-0009).

- Sin secretos de cliente: PKCE S256 obligatorio. Un cliente se identifica con la URL de sus
  metadatos (CIMD) o con un `client_id` firmado que da el registro dinámico, que no guarda nada.
- Códigos, tokens de acceso y de refresco solo se guardan como HMAC. El refresco rota, y reusar uno
  viejo tumba toda la familia.
- Los tokens de acceso solo sirven en MCP (RFC 8707): la API REST sigue pidiendo llave.
"""

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import socket
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx

from terranova.bd import Conexion
from terranova.identidad import Principal, Registro

PREFIJO_ACCESO = "rt_oa_"
PREFIJO_REFRESCO = "rt_or_"
PREFIJO_CODIGO = "rt_oc_"
PREFIJO_CLIENTE = "rt_cliente_"
VIDA_CODIGO_S = 60
VIDA_ACCESO_S = 3_600
VIDA_REFRESCO_S = 30 * 86_400
VIDA_FORMULARIO_S = 600
TOPE_METADATOS = 16_384
MAX_REDIRECCIONES = 5
MAX_URL = 500
LOCALES = {"localhost", "127.0.0.1", "::1"}
ESQUEMAS_NATIVOS = {"cursor", "vscode", "vscode-insiders", "windsurf"}  # editores de escritorio
DESAFIO_PKCE = re.compile(r"[A-Za-z0-9_-]{43}")
VERIFICADOR_PKCE = re.compile(r"[A-Za-z0-9._~-]{43,128}")
TIEMPO_METADATOS_S = 3
VIDA_CACHE_CLIENTE_S = 300
MAX_CACHE_CLIENTES = 256
LECTURAS_A_LA_VEZ = 8


class ErrorOAuth(Exception):
    """Un error del protocolo, con su código de RFC 6749."""

    def __init__(self, codigo: str, descripcion: str) -> None:
        super().__init__(descripcion)
        self.codigo, self.descripcion = codigo, descripcion


@dataclass(frozen=True)
class Cliente:
    client_id: str
    nombre: str
    redirect_uris: tuple[str, ...]


@dataclass(frozen=True)
class Pedido:
    """Una autorización ya validada: lo único que la página de consentimiento puede firmar."""

    client_id: str
    nombre: str
    redirect_uri: str
    desafio: str
    recurso: str
    estado: str | None


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def redireccion_valida(uri: Any) -> bool:
    """https, o http solo hacia la propia máquina (RFC 8252). Sin esquemas raros ni fragmentos."""
    if not isinstance(uri, str) or len(uri) > MAX_URL or "\\" in uri:
        return False
    try:
        partes = urlsplit(uri)
        _ = partes.port
    except ValueError:
        return False
    if partes.scheme in ESQUEMAS_NATIVOS:
        return bool(partes.netloc) and not partes.fragment
    if partes.fragment or partes.username or partes.password or not partes.hostname:
        return False
    return partes.scheme == "https" or (partes.scheme == "http" and partes.hostname in LOCALES)


def _misma_redireccion(pedida: str, registrada: str) -> bool:
    """Exacta; en la propia máquina el puerto puede cambiar en cada arranque (RFC 8252 §7.3)."""
    if not redireccion_valida(pedida):
        return False
    if pedida == registrada:
        return True
    a, b = urlsplit(pedida), urlsplit(registrada)
    return (
        a.scheme == "http"
        and a.hostname in LOCALES
        and (a.scheme, a.hostname, a.path, a.query) == (b.scheme, b.hostname, b.path, b.query)
    )


def _validar_cliente(client_id: str, datos: Any) -> Cliente:
    if not isinstance(datos, dict):
        raise ErrorOAuth("invalid_client", "los metadatos del cliente no son un objeto")
    uris = datos.get("redirect_uris")
    if not isinstance(uris, list) or not 1 <= len(uris) <= MAX_REDIRECCIONES:
        raise ErrorOAuth("invalid_client", "faltan redirect_uris")
    if not all(redireccion_valida(u) for u in uris):
        raise ErrorOAuth("invalid_client", "hay una redirect_uri no permitida")
    nombre = datos.get("client_name")
    nombre = nombre[:100] if isinstance(nombre, str) and nombre.strip() else "Cliente sin nombre"
    return Cliente(client_id, nombre, tuple(uris))


_LECTURAS = asyncio.Semaphore(LECTURAS_A_LA_VEZ)


async def _resuelve_a_publica(host: str, puerto: int) -> bool:
    """El servidor no debe servir de puente hacia su propia red (SSRF)."""
    try:
        direcciones = await asyncio.get_running_loop().getaddrinfo(
            host, puerto, type=socket.SOCK_STREAM
        )
    except (OSError, ValueError):  # UnicodeError es ValueError: una etiqueta de más de 63
        return False
    return bool(direcciones) and all(
        ipaddress.ip_address(str(d[4][0]).split("%")[0]).is_global for d in direcciones
    )


async def leer_metadatos_cliente(url: str) -> Any:
    """CIMD: baja el documento del cliente, sin redirecciones, con tope de tamaño y de tiempo."""
    try:
        partes = urlsplit(url)
        puerto = partes.port or 443
    except ValueError as exc:
        raise ErrorOAuth("invalid_client", "client_id no es una URL válida") from exc
    if (
        len(url) > MAX_URL
        or partes.scheme != "https"
        or not partes.hostname
        or partes.path in ("", "/")
        or partes.username
        or partes.password
        or partes.fragment
        or partes.query
    ):
        raise ErrorOAuth("invalid_client", "client_id no es una URL de metadatos válida")
    if _LECTURAS.locked():
        raise ErrorOAuth("temporarily_unavailable", "hay muchas conexiones a la vez: reintente")
    try:
        async with (
            _LECTURAS,
            asyncio.timeout(TIEMPO_METADATOS_S),
            httpx.AsyncClient(timeout=3, follow_redirects=False, trust_env=False) as cliente,
        ):
            if not await _resuelve_a_publica(partes.hostname, puerto):
                raise ErrorOAuth("invalid_client", "el client_id apunta a una dirección no pública")
            respuesta = await cliente.send(
                cliente.build_request("GET", url, headers={"Accept": "application/json"}),
                stream=True,
            )
            try:
                if respuesta.status_code != 200:
                    raise ErrorOAuth("invalid_client", "no se pudieron leer los metadatos")
                cuerpo = b""
                async for trozo in respuesta.aiter_bytes():
                    cuerpo += trozo
                    if len(cuerpo) > TOPE_METADATOS:
                        raise ErrorOAuth("invalid_client", "los metadatos son muy grandes")
            finally:
                await respuesta.aclose()
    except (httpx.HTTPError, TimeoutError) as exc:
        raise ErrorOAuth("invalid_client", "no se pudieron leer los metadatos") from exc
    try:
        return json.loads(cuerpo)
    except ValueError as exc:
        raise ErrorOAuth("invalid_client", "los metadatos del cliente no son JSON") from exc


class ServidorOAuth:
    def __init__(
        self,
        destino: str | Path,
        pimienta: str,
        registro: Registro,
        url_publica: str = "https://terrnova.com",
        leer_metadatos: Callable[[str], Awaitable[Any]] = leer_metadatos_cliente,
        reloj: Callable[[], float] = time.time,
    ) -> None:
        self._clave = hashlib.sha256(b"oauth:" + pimienta.encode()).digest()
        self.registro = registro
        self.url = url_publica.rstrip("/")
        self._leer_metadatos = leer_metadatos
        self._reloj = reloj
        self._cache_clientes: dict[str, tuple[float, Cliente]] = {}
        self._bd = Conexion(destino)
        self._bd.ejecutar(
            """CREATE TABLE IF NOT EXISTS oauth_codigos (
                huella TEXT PRIMARY KEY, familia TEXT NOT NULL, llave_id TEXT NOT NULL,
                client_id TEXT NOT NULL, redirect_uri TEXT NOT NULL, desafio TEXT NOT NULL,
                recurso TEXT NOT NULL, expira BIGINT NOT NULL, usado BIGINT)"""
        )
        self._bd.ejecutar(
            """CREATE TABLE IF NOT EXISTS oauth_tokens (
                huella TEXT PRIMARY KEY, tipo TEXT NOT NULL, familia TEXT NOT NULL,
                llave_id TEXT NOT NULL, client_id TEXT NOT NULL, recurso TEXT NOT NULL,
                expira BIGINT NOT NULL, usado BIGINT)"""
        )

    # --- descubrimiento ------------------------------------------------------------------------

    def recurso(self, ruta: str = "/mcp") -> str:
        return f"{self.url}{ruta}"

    def metadatos_recurso(self, ruta: str = "/mcp") -> dict[str, Any]:
        """RFC 9728."""
        return {
            "resource": self.recurso(ruta),
            "authorization_servers": [self.url],
            "bearer_methods_supported": ["header"],
            "scopes_supported": ["mcp"],
            "resource_name": "Terrnova",
        }

    def metadatos_servidor(self) -> dict[str, Any]:
        """RFC 8414."""
        return {
            "issuer": self.url,
            "authorization_endpoint": f"{self.url}/oauth/autorizar",
            "token_endpoint": f"{self.url}/oauth/token",
            "registration_endpoint": f"{self.url}/oauth/registro",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["mcp"],
            "client_id_metadata_document_supported": True,
            "authorization_response_iss_parameter_supported": True,
        }

    def desafio_www(self, ruta: str) -> str:
        """La cabecera del 401 de MCP: de ahí arranca el cliente (RFC 9728 §5.1)."""
        metadatos = f"{self.url}/.well-known/oauth-protected-resource{ruta}"
        return f'Bearer resource_metadata="{metadatos}"'

    # --- firmas --------------------------------------------------------------------------------

    def _firma(self, contexto: str, cuerpo: str) -> str:
        return _b64(hmac.new(self._clave, f"{contexto}:{cuerpo}".encode(), hashlib.sha256).digest())

    def _sellar(self, contexto: str, datos: Any) -> str:
        cuerpo = _b64(json.dumps(datos, separators=(",", ":")).encode())
        return f"{cuerpo}.{self._firma(contexto, cuerpo)}"

    def _abrir(self, contexto: str, sello: str) -> Any:
        cuerpo, _, firma = sello.partition(".")
        esperada = self._firma(contexto, cuerpo).encode()
        if not firma or not hmac.compare_digest(firma.encode(errors="replace"), esperada):
            return None
        return json.loads(_de_b64(cuerpo))

    def _huella(self, secreto: str) -> str:
        return hmac.new(self._clave, secreto.encode(), hashlib.sha256).hexdigest()

    # --- clientes ------------------------------------------------------------------------------

    def registrar(self, datos: Any) -> dict[str, Any]:
        """Registro dinámico (RFC 7591) sin estado: el `client_id` lleva firmados sus datos, así que
        registrar no llena ninguna tabla."""
        try:
            provisional = _validar_cliente("", datos)
        except ErrorOAuth as exc:
            raise ErrorOAuth("invalid_client_metadata", exc.descripcion) from exc
        datos_cliente = {"n": provisional.nombre, "r": list(provisional.redirect_uris)}
        client_id = PREFIJO_CLIENTE + self._sellar("cliente", datos_cliente)
        return {
            "client_id": client_id,
            "client_name": provisional.nombre,
            "redirect_uris": list(provisional.redirect_uris),
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }

    async def cliente(self, client_id: str) -> Cliente:
        if client_id.startswith(PREFIJO_CLIENTE):
            datos = self._abrir("cliente", client_id.removeprefix(PREFIJO_CLIENTE))
            if not isinstance(datos, dict):
                raise ErrorOAuth("invalid_client", "client_id no reconocido")
            return Cliente(client_id, datos["n"], tuple(datos["r"]))
        if client_id.startswith("https://"):
            guardado = self._cache_clientes.get(client_id)
            if guardado and guardado[0] > self._reloj():
                return guardado[1]
            datos = await self._leer_metadatos(client_id)
            if not isinstance(datos, dict) or datos.get("client_id") != client_id:
                raise ErrorOAuth("invalid_client", "los metadatos no son de este client_id")
            cliente = _validar_cliente(client_id, datos)
            if len(self._cache_clientes) >= MAX_CACHE_CLIENTES:
                self._cache_clientes.clear()
            self._cache_clientes[client_id] = (self._reloj() + VIDA_CACHE_CLIENTE_S, cliente)
            return cliente
        raise ErrorOAuth("invalid_client", "client_id no reconocido")

    # --- autorización --------------------------------------------------------------------------

    async def validar_redireccion(self, q: dict[str, str]) -> tuple[Cliente, str]:
        """Lo que se valida antes de poder redirigir: si falla, se muestra aquí mismo. Redirigir a
        una URL sin validar sería un redireccionador abierto."""
        cliente = await self.cliente(q.get("client_id", ""))
        uri = q.get("redirect_uri", "")
        if not any(_misma_redireccion(uri, r) for r in cliente.redirect_uris):
            raise ErrorOAuth("invalid_request", "redirect_uri no está registrada para este cliente")
        return cliente, uri

    def pedido(self, cliente: Cliente, uri: str, q: dict[str, str]) -> Pedido:
        """Lo demás: estos errores sí vuelven al cliente por su redirect_uri."""
        if q.get("response_type") != "code":
            raise ErrorOAuth("unsupported_response_type", "solo response_type=code")
        desafio = q.get("code_challenge", "")
        if q.get("code_challenge_method") != "S256" or not DESAFIO_PKCE.fullmatch(desafio):
            raise ErrorOAuth("invalid_request", "hace falta PKCE con S256")
        recurso = q.get("resource") or self.recurso()
        if not self._recurso_valido(recurso):
            raise ErrorOAuth("invalid_target", "resource no es un MCP de Terrnova")
        return Pedido(cliente.client_id, cliente.nombre, uri, desafio, recurso, q.get("state"))

    def _recurso_valido(self, recurso: str) -> bool:
        base = self.recurso()
        return recurso == base or (
            recurso.startswith(f"{base}/") and recurso[len(base) + 1 :].isidentifier()
        )

    def sellar_pedido(self, p: Pedido) -> str:
        datos = [
            p.client_id,
            p.nombre,
            p.redirect_uri,
            p.desafio,
            p.recurso,
            p.estado,
            int(self._reloj()) + VIDA_FORMULARIO_S,
        ]
        return self._sellar("pedido", datos)

    def abrir_pedido(self, sello: str) -> Pedido:
        try:
            datos = self._abrir("pedido", sello)
        except ValueError:
            datos = None
        if not isinstance(datos, list) or len(datos) != 7 or datos[6] < self._reloj():
            raise ErrorOAuth("invalid_request", "el formulario venció: vuelva a empezar")
        return Pedido(*datos[:6])

    def redireccion_con_error(self, uri: str, error: ErrorOAuth, estado: str | None) -> str:
        datos = {"error": error.codigo, "error_description": error.descripcion, "iss": self.url}
        return self._con_query(uri, datos, estado)

    @staticmethod
    def _con_query(uri: str, datos: dict[str, str], estado: str | None) -> str:
        if estado is not None:
            datos = {**datos, "state": estado}
        return f"{uri}{'&' if '?' in uri else '?'}{urlencode(datos)}"

    def autorizar(self, p: Pedido, llave: str) -> str:
        """Comprueba la llave y devuelve a dónde redirigir, con el código. Lanza `access_denied`."""
        principal = self.registro.verificar(llave.strip())
        if principal is None:
            raise ErrorOAuth("access_denied", "Esa llave no es válida, venció o fue revocada.")
        codigo = PREFIJO_CODIGO + secrets.token_urlsafe(32)
        self._bd.ejecutar(
            "INSERT INTO oauth_codigos VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (
                self._huella(codigo),
                secrets.token_hex(16),
                principal.llave_id,
                p.client_id,
                p.redirect_uri,
                p.desafio,
                p.recurso,
                int(self._reloj()) + VIDA_CODIGO_S,
            ),
        )
        return self._con_query(p.redirect_uri, {"code": codigo, "iss": self.url}, p.estado)

    # --- tokens --------------------------------------------------------------------------------

    def token(self, f: dict[str, str]) -> dict[str, Any]:
        tipo = f.get("grant_type")
        self._podar()
        if tipo == "authorization_code":
            return self._por_codigo(f)
        if tipo == "refresh_token":
            return self._por_refresco(f)
        raise ErrorOAuth("unsupported_grant_type", "solo authorization_code y refresh_token")

    def _por_codigo(self, f: dict[str, str]) -> dict[str, Any]:
        huella = self._huella(f.get("code", ""))
        filas, _ = self._bd.ejecutar(
            "SELECT familia, llave_id, client_id, redirect_uri, desafio, recurso, expira, usado "
            "FROM oauth_codigos WHERE huella = ?",
            (huella,),
        )
        if not filas:
            raise ErrorOAuth("invalid_grant", "código no reconocido")
        familia, llave_id, client_id, uri, desafio, recurso, expira, usado = filas[0]
        if usado is not None:  # un código reusado: quien lo tenga no debe seguir entrando
            self._tumbar(familia)
            raise ErrorOAuth("invalid_grant", "el código ya se usó")
        if expira < self._reloj():
            raise ErrorOAuth("invalid_grant", "el código venció")
        if f.get("client_id") != client_id:
            raise ErrorOAuth("invalid_grant", "el código es de otro cliente")
        if not _misma_redireccion(f.get("redirect_uri", ""), uri):
            raise ErrorOAuth("invalid_grant", "redirect_uri no coincide")
        verificador = f.get("code_verifier", "")
        if not VERIFICADOR_PKCE.fullmatch(verificador) or not hmac.compare_digest(
            _b64(hashlib.sha256(verificador.encode()).digest()), desafio
        ):
            raise ErrorOAuth("invalid_grant", "code_verifier no coincide")
        if f.get("resource") and f["resource"] != recurso:
            raise ErrorOAuth("invalid_target", "resource no coincide con el autorizado")
        # Se marca al final: un intento equivocado no le quema el código a su dueño.
        _, marcados = self._bd.ejecutar(
            "UPDATE oauth_codigos SET usado = ? WHERE huella = ? AND usado IS NULL",
            (int(self._reloj()), huella),
        )
        if marcados != 1:  # dos canjes a la vez
            self._tumbar(familia)
            raise ErrorOAuth("invalid_grant", "el código ya se usó")
        return self._emitir(familia, llave_id, client_id, recurso)

    def _por_refresco(self, f: dict[str, str]) -> dict[str, Any]:
        huella = self._huella(f.get("refresh_token", ""))
        filas, _ = self._bd.ejecutar(
            "SELECT familia, llave_id, client_id, recurso, expira FROM oauth_tokens "
            "WHERE huella = ? AND tipo = 'refresco'",
            (huella,),
        )
        if not filas:
            raise ErrorOAuth("invalid_grant", "token de refresco no reconocido")
        familia, llave_id, client_id, recurso, expira = filas[0]
        if f.get("client_id") != client_id:
            raise ErrorOAuth("invalid_grant", "el token es de otro cliente")
        _, marcados = self._bd.ejecutar(
            "UPDATE oauth_tokens SET usado = ? WHERE huella = ? AND usado IS NULL",
            (int(self._reloj()), huella),
        )
        if marcados != 1:  # reusar uno rotado es señal de robo (OAuth 2.1 §4.3.1)
            self._tumbar(familia)
            raise ErrorOAuth("invalid_grant", "token de refresco ya usado")
        if expira < self._reloj():
            raise ErrorOAuth("invalid_grant", "el token de refresco venció")
        if self.registro.principal_de(llave_id) is None:
            self._tumbar(familia)
            raise ErrorOAuth("invalid_grant", "la llave ya no está vigente")
        return self._emitir(familia, llave_id, client_id, recurso)

    def _emitir(self, familia: str, llave_id: str, client_id: str, recurso: str) -> dict[str, Any]:
        acceso = PREFIJO_ACCESO + secrets.token_urlsafe(32)
        refresco = PREFIJO_REFRESCO + secrets.token_urlsafe(32)
        ahora = int(self._reloj())
        for secreto, tipo, vida in (
            (acceso, "acceso", VIDA_ACCESO_S),
            (refresco, "refresco", VIDA_REFRESCO_S),
        ):
            self._bd.ejecutar(
                "INSERT INTO oauth_tokens VALUES (?, ?, ?, ?, ?, ?, ?, NULL)",
                (self._huella(secreto), tipo, familia, llave_id, client_id, recurso, ahora + vida),
            )
        return {
            "access_token": acceso,
            "token_type": "Bearer",
            "expires_in": VIDA_ACCESO_S,
            "refresh_token": refresco,
            "scope": "mcp",
        }

    def _tumbar(self, familia: str) -> None:
        self._bd.ejecutar("DELETE FROM oauth_tokens WHERE familia = ?", (familia,))

    def _podar(self) -> None:
        """Lo vencido ya no sirve ni para detectar un reuso."""
        ahora = int(self._reloj())
        self._bd.ejecutar("DELETE FROM oauth_tokens WHERE expira < ?", (ahora,))
        self._bd.ejecutar("DELETE FROM oauth_codigos WHERE expira < ?", (ahora - VIDA_CODIGO_S,))

    def verificar_acceso(self, token: str, ruta: str = "/mcp") -> Principal | None:
        """El principal de un token vigente para esa ruta. Uno de `/mcp` vale en todos los
        perfiles; el de un perfil, solo en ese (RFC 8707). Revocar la llave lo corta al momento."""
        if not token.startswith(PREFIJO_ACCESO):
            return None
        filas, _ = self._bd.ejecutar(
            "SELECT llave_id, expira, recurso FROM oauth_tokens "
            "WHERE huella = ? AND tipo = 'acceso'",
            (self._huella(token),),
        )
        if not filas or filas[0][1] < self._reloj():
            return None
        if filas[0][2] not in (self.recurso(), self.recurso(ruta)):
            return None
        return self.registro.principal_de(filas[0][0])


def oauth_desde_entorno(registro: Registro) -> ServidorOAuth | None:
    """Apagado salvo `TERRANOVA_OAUTH=1`: sin él, la puerta se comporta como siempre."""
    if os.environ.get("TERRANOVA_OAUTH") != "1":
        return None
    return ServidorOAuth(
        os.environ.get("TERRANOVA_BD", "datos_locales/terranova.db"),
        os.environ["TERRANOVA_PIMIENTA"],
        registro,
        os.environ.get("TERRANOVA_URL_PUBLICA", "https://terrnova.com"),
    )
