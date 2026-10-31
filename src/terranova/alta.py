"""Alta de la llave de prueba con correo verificado y formulario de contacto (ADR-0034).

Quien quiere probar la puerta deja su correo en el sitio; le llega un enlace que vence en 24 h y, al
abrirlo, confirma con un botón y ve su llave una sola vez. El botón existe porque los filtros de
correo abren los enlaces para revisarlos: si la llave se creara con solo abrir el enlace, la
gastaría el filtro. Una llave por correo, pocos créditos (`NIVEL_ALTA`) y un tope de altas por IP.
Nada de acceso sin llave.

El formulario de contacto guarda cada mensaje en la base y lo reenvía a soporte. De la IP solo se
guarda su HMAC con la pimienta del servidor, para el tope por hora; nunca la IP.

Sin correo configurado (`TERRANOVA_SMTP_URL`), el alta responde que no está disponible y remite al
correo de soporte; el contacto se guarda igual.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import ssl
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote, urlparse

from terranova.bd import Conexion
from terranova.contrato import texto_es_limpio
from terranova.identidad import Registro

# La llave del alta automática: pocos créditos y con vencimiento. Para más, el plan Gratis o uno
# de pago se piden a soporte (decisión del dueño, 2026-10-31).
NIVEL_ALTA = "prueba"
VIGENCIA_LLAVE = timedelta(days=30)
VIGENCIA_ENLACE = timedelta(hours=24)
ALTAS_POR_IP_HORA = 5
CONTACTOS_POR_IP_HORA = 10

PATRON_CORREO = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9.-]{1,185}\.[A-Za-z]{2,24}$")
# correos de un solo uso: no dan una llave (la lista corta cubre los más usados)
DESECHABLES = frozenset(
    {
        "mailinator.com",
        "guerrillamail.com",
        "10minutemail.com",
        "tempmail.com",
        "temp-mail.org",
        "yopmail.com",
        "trashmail.com",
        "getnada.com",
        "sharklasers.com",
        "dispostable.com",
        "maildrop.cc",
    }
)
ASUNTOS = frozenset(
    {
        "proyecto",
        "debida-diligencia",
        "tablero",
        "vigilancia",
        "asistente",
        "plan-gratis",
        "plan-basico",
        "plan-pro",
        "plan-empresa",
        "plan-escala",
        "gobierno-academia",
        "soporte",
        "otro",
    }
)


class ErrorAlta(Exception):
    """Lo que quien llena el formulario debe corregir (se le muestra tal cual)."""


class Correo(Protocol):
    async def enviar(self, destino: str, asunto: str, texto: str) -> None: ...


class CorreoSmtp:
    """SMTP con TLS: `smtps://usuario:clave@servidor:465` o `smtp://…:587` (STARTTLS)."""

    def __init__(self, url: str, remitente: str) -> None:
        u = urlparse(url)
        if u.scheme not in ("smtp", "smtps") or not u.hostname:
            raise ValueError("TERRANOVA_SMTP_URL: smtp://… o smtps://…")
        self._seguro = u.scheme == "smtps"
        self._servidor = u.hostname
        self._puerto = u.port or (465 if self._seguro else 587)
        self._usuario = unquote(u.username or "")
        self._clave = unquote(u.password or "")
        self.remitente = remitente

    def _enviar(self, destino: str, asunto: str, texto: str) -> None:
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = self.remitente, destino, asunto
        m.set_content(texto)
        contexto = ssl.create_default_context()
        if self._seguro:
            with smtplib.SMTP_SSL(self._servidor, self._puerto, context=contexto, timeout=20) as s:
                if self._usuario:
                    s.login(self._usuario, self._clave)
                s.send_message(m)
        else:
            with smtplib.SMTP(self._servidor, self._puerto, timeout=20) as s:
                s.starttls(context=contexto)
                if self._usuario:
                    s.login(self._usuario, self._clave)
                s.send_message(m)

    async def enviar(self, destino: str, asunto: str, texto: str) -> None:
        await asyncio.to_thread(self._enviar, destino, asunto, texto)


@dataclass
class Solicitud:
    correo: str
    nombre: str
    organizacion: str
    uso: str


def _ahora() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _texto(campo: str, valor: str, tope: int, *, obligatorio: bool) -> str:
    v = " ".join(valor.split())
    if obligatorio and not v:
        raise ErrorAlta(f"Falta {campo}.")
    if len(v) > tope or not texto_es_limpio(v):
        raise ErrorAlta(
            f"{campo.capitalize()}: hasta {tope} caracteres, sin caracteres de control."
        )
    return v


def validar_correo(correo: str) -> str:
    c = correo.strip().lower()
    if not PATRON_CORREO.fullmatch(c):
        raise ErrorAlta("Ese correo no parece válido.")
    if c.split("@", 1)[1] in DESECHABLES:
        raise ErrorAlta("Usa un correo de tu organización o personal, no uno desechable.")
    return c


class Altas:
    """Altas de llave de prueba y mensajes de contacto, sobre la misma base de las llaves."""

    def __init__(
        self,
        bd: Conexion | str | Path,
        registro: Registro,
        pimienta: str,
        correo: Correo | None,
        *,
        soporte: str = "soporte@terrnova.com",
        url_publica: str = "https://terrnova.com",
    ) -> None:
        self._bd = bd if isinstance(bd, Conexion) else Conexion(bd)
        self._registro = registro
        self._pimienta = pimienta.encode()
        self.correo = correo
        self.soporte = soporte
        self.url_publica = url_publica.rstrip("/")
        for sql in (
            """CREATE TABLE IF NOT EXISTS altas (
                correo TEXT PRIMARY KEY, org TEXT NOT NULL, nombre TEXT NOT NULL,
                organizacion TEXT NOT NULL, uso TEXT NOT NULL, creada TEXT NOT NULL,
                confirmada TEXT, ip TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS altas_enlaces (
                huella TEXT PRIMARY KEY, correo TEXT NOT NULL, vence TEXT NOT NULL,
                usado TEXT)""",
            """CREATE TABLE IF NOT EXISTS contactos (
                creado TEXT NOT NULL, nombre TEXT NOT NULL, correo TEXT NOT NULL,
                organizacion TEXT NOT NULL, asunto TEXT NOT NULL, mensaje TEXT NOT NULL,
                ip TEXT NOT NULL)""",
        ):
            self._bd.ejecutar(sql)

    def _hmac(self, valor: str) -> str:
        return hmac.new(self._pimienta, valor.encode(), hashlib.sha256).hexdigest()

    def _recientes(self, tabla: str, columna: str, ip: str) -> int:
        desde = (_ahora() - timedelta(hours=1)).isoformat()
        filas, _ = self._bd.ejecutar(
            f"SELECT COUNT(*) FROM {tabla} WHERE ip = ? AND {columna} >= ?", (ip, desde)
        )
        return int(filas[0][0])

    # --- alta -------------------------------------------------------------------------------

    def _solicitar(self, s: Solicitud, ip: str) -> tuple[str, str | None]:
        """(correo, enlace o None si ese correo ya tiene llave). Lanza ErrorAlta."""
        if self._recientes("altas", "creada", ip) >= ALTAS_POR_IP_HORA:
            raise ErrorAlta("Demasiadas altas desde tu red en la última hora. Intenta más tarde.")
        filas, _ = self._bd.ejecutar("SELECT confirmada FROM altas WHERE correo = ?", (s.correo,))
        if filas and filas[0][0]:
            return s.correo, None
        org = "alta-" + self._hmac(s.correo)[:12]
        if not filas:
            self._bd.ejecutar(
                "INSERT INTO altas VALUES (?, ?, ?, ?, ?, ?, NULL, ?)",
                (s.correo, org, s.nombre, s.organizacion, s.uso, _ahora().isoformat(), ip),
            )
        token = secrets.token_urlsafe(32)
        self._bd.ejecutar(
            "INSERT INTO altas_enlaces VALUES (?, ?, ?, NULL)",
            (self._hmac(token), s.correo, (_ahora() + VIGENCIA_ENLACE).isoformat()),
        )
        return s.correo, f"{self.url_publica}/v1/alta/confirmar?t={token}"

    async def solicitar(
        self, correo: str, nombre: str, organizacion: str, uso: str, acepto: bool, ip: str
    ) -> None:
        """Valida, guarda y manda el enlace. Responde lo mismo exista o no el correo: no dice
        quién tiene llave."""
        if self.correo is None:
            raise ErrorAlta(
                f"El alta automática todavía no está disponible. Escríbenos a {self.soporte}."
            )
        if not acepto:
            raise ErrorAlta(
                "Para darte una llave necesitamos que aceptes la política de privacidad."
            )
        s = Solicitud(
            validar_correo(correo),
            _texto("tu nombre", nombre, 120, obligatorio=True),
            _texto("la organización", organizacion, 120, obligatorio=False),
            _texto("el uso", uso, 500, obligatorio=False),
        )
        destino, enlace = await asyncio.to_thread(self._solicitar, s, self._hmac(ip))
        if enlace is None:
            texto = (
                f"Hola, {s.nombre}.\n\nEste correo ya tiene una llave de Terrnova. Si la perdiste "
                f"o quieres más créditos, escríbenos a {self.soporte}.\n\nTerrnova"
            )
        else:
            texto = (
                f"Hola, {s.nombre}.\n\nPara recibir tu llave de prueba de Terrnova abre este "
                f"enlace y confirma (vence en 24 horas):\n\n{enlace}\n\nLa llave se muestra una "
                "sola vez. Si no pediste una llave, ignora este correo.\n\nTerrnova"
            )
        await self.correo.enviar(destino, "Tu llave de Terrnova", texto)

    def _confirmar(self, token: str) -> tuple[str, str]:
        """(correo, llave). Lanza ErrorAlta si el enlace no sirve."""
        huella = self._hmac(token)
        _, usados = self._bd.ejecutar(
            "UPDATE altas_enlaces SET usado = ? WHERE huella = ? AND usado IS NULL AND vence > ?",
            (_ahora().isoformat(), huella, _ahora().isoformat()),
        )
        if usados != 1:
            raise ErrorAlta("El enlace venció o ya se usó. Pide uno nuevo desde el sitio.")
        filas, _ = self._bd.ejecutar(
            "SELECT a.correo, a.org, a.confirmada FROM altas_enlaces e "
            "JOIN altas a ON a.correo = e.correo WHERE e.huella = ?",
            (huella,),
        )
        correo, org, confirmada = filas[0]
        if confirmada:
            raise ErrorAlta(f"Este correo ya tiene una llave. Escríbenos a {self.soporte}.")
        _, marcadas = self._bd.ejecutar(
            "UPDATE altas SET confirmada = ? WHERE correo = ? AND confirmada IS NULL",
            (_ahora().isoformat(), correo),
        )
        if marcadas != 1:  # dos confirmaciones a la vez: solo una crea la llave
            raise ErrorAlta(f"Este correo ya tiene una llave. Escríbenos a {self.soporte}.")
        self._registro.fijar_nivel(org, NIVEL_ALTA)
        vence: date = (_ahora() + VIGENCIA_LLAVE).date()
        llave = self._registro.crear(org, {"*"}, prueba=False, expira=vence)
        return correo, llave

    async def confirmar(self, token: str) -> tuple[str, str]:
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", token or ""):
            raise ErrorAlta("El enlace no es válido.")
        return await asyncio.to_thread(self._confirmar, token)

    # --- contacto ---------------------------------------------------------------------------

    def _guardar_contacto(self, campos: tuple[str, str, str, str, str], ip: str) -> None:
        if self._recientes("contactos", "creado", ip) >= CONTACTOS_POR_IP_HORA:
            raise ErrorAlta(
                "Demasiados mensajes desde tu red en la última hora. Intenta más tarde."
            )
        self._bd.ejecutar(
            "INSERT INTO contactos VALUES (?, ?, ?, ?, ?, ?, ?)",
            (_ahora().isoformat(), *campos, ip),
        )

    async def contactar(
        self,
        nombre: str,
        correo: str,
        organizacion: str,
        asunto: str,
        mensaje: str,
        acepto: bool,
        ip: str,
    ) -> None:
        if not acepto:
            raise ErrorAlta("Para responderte necesitamos que aceptes la política de privacidad.")
        n = _texto("tu nombre", nombre, 120, obligatorio=True)
        c = validar_correo(correo)
        o = _texto("la organización", organizacion, 120, obligatorio=False)
        a = asunto if asunto in ASUNTOS else "otro"
        m = mensaje.strip()
        if not m.strip() or len(m) > 4000 or not texto_es_limpio(m.replace("\n", " ")):
            raise ErrorAlta("El mensaje va de 1 a 4.000 caracteres, sin caracteres de control.")
        await asyncio.to_thread(self._guardar_contacto, (n, c, o, a, m), self._hmac(ip))
        if self.correo is not None:
            texto = f"De: {n} <{c}>\nOrganización: {o or '—'}\nAsunto: {a}\n\n{m}\n"
            await self.correo.enviar(self.soporte, f"[Terrnova] {a}: {n}", texto)


def altas_desde_entorno(registro: Registro) -> Altas:
    pimienta = os.environ.get("TERRANOVA_PIMIENTA", "")
    smtp = os.environ.get("TERRANOVA_SMTP_URL")
    remitente = os.environ.get("TERRANOVA_CORREO_DE", "Terrnova <no-responder@terrnova.com>")
    correo = CorreoSmtp(smtp, remitente) if smtp else None
    return Altas(
        os.environ.get("TERRANOVA_BD", "datos_locales/terranova.db"),
        registro,
        pimienta,
        correo,
        soporte=os.environ.get("TERRANOVA_SOPORTE", "soporte@terrnova.com"),
        url_publica=os.environ.get("TERRANOVA_URL_PUBLICA", "https://terrnova.com"),
    )
