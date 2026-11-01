"""Los correos que envía Terrnova.

Siguen el patrón de los correos transaccionales de Linear, Notion, Vercel o Stripe: fondo blanco
sin tarjeta, el logo arriba, un título corto, una sola acción, el enlace de respaldo en texto y
un pie gris que dice por qué te llegó. Trato de «tú» y firma «El equipo de Terrnova». Las
respuestas van a soporte (o, en el aviso interno de contacto, a quien escribió). Ningún correo
lleva una llave ni un dato sensible.

El HTML es de correo: tablas y estilos en línea, porque Gmail y Outlook ignoran casi todo lo demás;
fuentes del sistema como respaldo de Geist (los clientes de correo no la cargan); el logo en PNG
(Gmail no muestra SVG). Todo lo que escribe la persona se escapa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape

URL = "https://terrnova.com"
LOGO = f"{URL}/img/terrnova-correo.png"
FIRMA = "El equipo de Terrnova"

# Tinta y grises del sistema de diseño v4 (web/publico/estilo.css), sobre blanco.
TINTA = "#12261F"
SUAVE = "#4E5E57"
TENUE = "#7A8781"
LINEA = "#E3E7E1"
CAJA = "#F3F5F1"
BOSQUE = "#0B231C"
VERDE = "#236E62"
SANS = "Geist, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'Geist Mono', Consolas, Menlo, monospace"
MESES = (
    "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre"
).split()


@dataclass(frozen=True)
class Mensaje:
    asunto: str
    texto: str
    html: str
    responder_a: str | None = None


def nombre_visible(nombre: str) -> str:
    """«sebastian forero» → «Sebastian Forero»; respeta lo que ya trae mayúsculas."""
    n = " ".join(nombre.split())
    return n.title() if n == n.lower() else n


def fecha_larga(d: date) -> str:
    """16 de noviembre de 2026."""
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


# --- piezas ------------------------------------------------------------------------------------


def _p(html: str, *, color: str = TINTA, tam: int = 15, abajo: int = 16) -> str:
    return (
        f'<p style="margin:0 0 {abajo}px;font-family:{SANS};font-size:{tam}px;line-height:1.6;'
        f'color:{color};">{html}</p>'
    )


def _titulo(texto: str) -> str:
    return (
        f'<h1 style="margin:28px 0 24px;font-family:{SANS};font-size:24px;line-height:1.3;'
        f'font-weight:500;letter-spacing:-0.4px;color:{TINTA};">{escape(texto)}</h1>'
    )


def _boton(texto: str, href: str) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 28px;">'
        f'<tr><td style="background:{BOSQUE};border-radius:4px;">'
        f'<a href="{escape(href)}" style="display:inline-block;padding:11px 22px;'
        f"font-family:{SANS};font-size:15px;font-weight:600;color:#FFFFFF;"
        f'text-decoration:none;">{escape(texto)}</a></td></tr></table>'
    )


def _enlace(texto: str, href: str) -> str:
    return f'<a href="{escape(href)}" style="color:{VERDE};">{escape(texto)}</a>'


def _varias_lineas(texto: str) -> str:
    return escape(texto).replace("\n", "<br>")


def _codigo(texto: str) -> str:
    """Un bloque de código como el de Notion: gris claro, borde fino, monoespaciado."""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin:0 0 20px;">'
        f'<tr><td style="background:{CAJA};border:1px solid {LINEA};border-radius:6px;'
        f"padding:14px 16px;font-family:{MONO};font-size:13px;line-height:1.6;color:{TINTA};"
        f'white-space:pre-wrap;overflow-wrap:anywhere;">{escape(texto)}</td></tr></table>'
    )


def _cita(texto: str) -> str:
    """Lo que escribió la persona, citado como en cualquier respuesta de correo."""
    return (
        f'<p style="margin:0 0 20px;padding:2px 0 2px 14px;border-left:2px solid {LINEA};'
        f'font-family:{SANS};font-size:14px;line-height:1.6;color:{SUAVE};">'
        f"{_varias_lineas(texto)}</p>"
    )


def _firma() -> str:
    return _p(FIRMA, abajo=0)


_OCULTO = "display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;"
_RAYA = f"border:0;border-top:1px solid {LINEA};margin:40px 0 20px;"
_PIE = f"margin:0;font-family:{SANS};font-size:12px;line-height:1.6;color:{TENUE};"


def _pagina(asunto: str, previa: str, cuerpo: str, pie: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>{escape(asunto)}</title>
</head>
<body style="margin:0;padding:0;background:#FFFFFF;">
<span style="{_OCULTO}">{escape(previa)}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FFF;">
<tr><td style="padding:40px 20px 48px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">
<tr><td>
<img src="{LOGO}" width="36" height="36" alt="Terrnova" style="display:block;border:0;">
{cuerpo}
<hr style="{_RAYA}">
<p style="{_PIE}">{pie}</p>
<p style="{_PIE}margin-top:8px;"><a href="{URL}" style="color:{TENUE};">Terrnova</a>
· datos oficiales de Colombia, con su fuente</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _texto(lineas: list[str], pie: str) -> str:
    return "\n\n".join([*lineas, FIRMA, "--", pie, f"Terrnova · {URL}"]) + "\n"


# --- los correos -------------------------------------------------------------------------------


def enlace_llave(nombre: str, enlace: str, *, creditos: int, dias: int, soporte: str) -> Mensaje:
    n = nombre_visible(nombre)
    asunto = "Confirma tu correo para recibir tu llave de Terrnova"
    previa = "El enlace sirve una vez y vence en 24 horas."
    pie = "Recibes este correo porque se pidió una llave de prueba con él en terrnova.com."
    cuerpo = (
        _titulo("Confirma tu correo")
        + _p(f"Hola, {escape(n)}:")
        + _p("Para recibir tu llave de prueba de Terrnova, confirma que este correo es tuyo.")
        + _boton("Confirmar correo", enlace)
        + _p(
            f"La llave trae {creditos} créditos para {dias} días y se muestra una sola vez, en la "
            "página que abre el botón. El enlace sirve una vez y vence en 24 horas."
        )
        + _p(
            f"Si el botón no funciona, copia este enlace en tu navegador:<br>"
            f"{_enlace(enlace, enlace)}",
            color=SUAVE,
            tam=13,
        )
        + _p("Si no pediste una llave, ignora este correo.", color=SUAVE, tam=13, abajo=24)
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}:",
            "Para recibir tu llave de prueba de Terrnova, confirma que este correo es tuyo en este "
            "enlace:",
            enlace,
            f"La llave trae {creditos} créditos para {dias} días y se muestra una sola vez. El "
            "enlace sirve una vez y vence en 24 horas.",
            "Si no pediste una llave, ignora este correo.",
        ],
        pie,
    )
    return Mensaje(asunto, texto, _pagina(asunto, previa, cuerpo, pie), soporte)


def ya_tiene_llave(nombre: str, *, soporte: str) -> Mensaje:
    n = nombre_visible(nombre)
    asunto = "Ya tienes una llave de Terrnova"
    previa = "No creamos otra. Si la perdiste, responde este correo."
    pie = "Recibes este correo porque se pidió una llave con él en terrnova.com."
    guia = f"{URL}/desarrolladores"
    cuerpo = (
        _titulo("Ya tienes una llave")
        + _p(f"Hola, {escape(n)}:")
        + _p("Este correo ya tiene una llave de prueba de Terrnova, así que no creamos otra.")
        + _p("Si la perdiste o necesitas más créditos, responde este correo y lo resolvemos.")
        + _p(
            f"Para conectarla a tu agente, sigue la {_enlace('guía de conexión', guia)}.", abajo=28
        )
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}:",
            "Este correo ya tiene una llave de prueba de Terrnova, así que no creamos otra.",
            "Si la perdiste o necesitas más créditos, responde este correo y lo resolvemos.",
            f"Guía de conexión: {guia}",
        ],
        pie,
    )
    return Mensaje(asunto, texto, _pagina(asunto, previa, cuerpo, pie), soporte)


COMANDO_CLAUDE = (
    "claude mcp add --transport http terrnova \\\n"
    "  https://terrnova.com/mcp/catalogo \\\n"
    '  --header "Authorization: Bearer TU_LLAVE"'
)
PRIMERAS_PREGUNTAS = (
    "¿Qué predio hay en 4,8619 N, 74,0262 W?",
    "¿La empresa con NIT 899999068 tiene la matrícula al día?",
    "¿La Ley 1581 de 2012 sigue vigente?",
)


def bienvenida(nombre: str, *, creditos: int, vence: date, soporte: str) -> Mensaje:
    n = nombre_visible(nombre)
    fecha = fecha_larga(vence)
    asunto = "Tu llave de Terrnova está activa"
    previa = f"{creditos} créditos hasta el {fecha}. Así la conectas a tu agente."
    pie = "Recibes este correo porque confirmaste una llave de prueba en terrnova.com."
    guia = f"{URL}/desarrolladores"
    preguntas = "<br>".join(escape(p) for p in PRIMERAS_PREGUNTAS)
    cuerpo = (
        _titulo("Tu llave está activa")
        + _p(f"Hola, {escape(n)}:")
        + _p(
            f"Tienes {creditos} créditos hasta el {fecha}. Guarda la llave en un lugar seguro: "
            "no la volveremos a mostrar."
        )
        + _p("Para conectarla a Claude Code, cambia TU_LLAVE por tu llave:")
        + _codigo(COMANDO_CLAUDE)
        + _p("Para Cursor, Copilot, Gemini CLI, Claude Desktop o la API REST, sigue la guía:")
        + _boton("Ver la guía de conexión", guia)
        + _p("Para empezar, pregúntale a tu agente:")
        + _p(preguntas, color=SUAVE)
        + _p(
            "Cada respuesta trae la entidad que publica el dato, su licencia y su fecha. Si "
            "necesitas más créditos o un plan, responde este correo.",
            abajo=24,
        )
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}:",
            f"Tienes {creditos} créditos hasta el {fecha}. Guarda la llave en un lugar seguro: "
            "no la volveremos a mostrar.",
            f"Para conectarla a Claude Code, cambia TU_LLAVE por tu llave:\n\n{COMANDO_CLAUDE}",
            f"Para Cursor, Copilot, Gemini CLI, Claude Desktop o la API REST: {guia}",
            "Para empezar, pregúntale a tu agente:\n"
            + "\n".join(f"- {p}" for p in PRIMERAS_PREGUNTAS),
            "Si necesitas más créditos o un plan, responde este correo.",
        ],
        pie,
    )
    return Mensaje(asunto, texto, _pagina(asunto, previa, cuerpo, pie), soporte)


def acuse_contacto(nombre: str, asunto: str, mensaje: str, *, soporte: str) -> Mensaje:
    n = nombre_visible(nombre)
    titulo = "Recibimos tu mensaje"
    previa = "Te respondemos a este correo en horario hábil."
    pie = "Recibes este correo porque se usó el formulario de terrnova.com/contacto con él."
    resumen = mensaje if len(mensaje) <= 600 else mensaje[:600].rstrip() + "…"
    cuerpo = (
        _titulo(titulo)
        + _p(f"Hola, {escape(n)}:")
        + _p(
            f"Gracias por escribirnos sobre {escape(asunto.lower())}. Te respondemos a este "
            "correo de lunes a viernes, de 8:00 a 18:00, hora de Colombia."
        )
        + _cita(resumen)
        + _p("Si quieres agregar algo, responde este correo.", abajo=24)
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}:",
            f"Gracias por escribirnos sobre {asunto.lower()}. Te respondemos a este correo de "
            "lunes a viernes, de 8:00 a 18:00, hora de Colombia.",
            "\n".join(f"> {linea}" for linea in resumen.splitlines()),
            "Si quieres agregar algo, responde este correo.",
        ],
        pie,
    )
    return Mensaje(f"{titulo} · Terrnova", texto, _pagina(titulo, previa, cuerpo, pie), soporte)


def aviso_contacto(
    nombre: str, correo: str, organizacion: str, asunto: str, mensaje: str
) -> Mensaje:
    """El aviso interno a soporte. Responder le escribe directo a quien llenó el formulario."""
    n = nombre_visible(nombre)
    org = organizacion or "sin organización"
    titulo = f"Contacto: {asunto}"
    previa = f"{n} ({org}) escribió desde el formulario."
    pie = "Llegó por terrnova.com/contacto. Responde este correo para escribirle."
    filas = "".join(
        f'<tr><td style="padding:4px 16px 4px 0;font-family:{SANS};font-size:13px;'
        f'color:{TENUE};vertical-align:top;white-space:nowrap;">{k}</td>'
        f'<td style="padding:4px 0;font-family:{SANS};font-size:14px;color:{TINTA};'
        f'word-break:break-word;">{escape(v)}</td></tr>'
        for k, v in (("Nombre", n), ("Correo", correo), ("Organización", org), ("Asunto", asunto))
    )
    cuerpo = (
        _titulo(titulo)
        + f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 20px;">'
        f"{filas}</table>" + _cita(mensaje)
    )
    texto = (
        f"Nombre: {n}\nCorreo: {correo}\nOrganización: {org}\nAsunto: {asunto}\n\n{mensaje}\n\n"
        f"-- {pie}\n"
    )
    return Mensaje(
        f"[Contacto] {asunto}: {n} ({org})", texto, _pagina(titulo, previa, cuerpo, pie), correo
    )
