"""Los correos que envía Terrnova, con el sistema de diseño del sitio (docs/DISENO.md).

Cada correo sale en HTML y en texto plano, con una sola acción, el trato de «tú» y la firma «El
equipo de Terrnova». Las respuestas van a soporte (o, en el aviso interno de contacto, a quien
escribió). Ningún correo lleva una llave ni un dato sensible, y cada uno dice por qué te llegó.

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

# Colores y fuentes del sistema de diseño v4 (web/publico/estilo.css).
FONDO = "#F6F7F4"
PANEL = "#FFFFFF"
SUPERFICIE = "#ECEEE9"
TINTA = "#12261F"
SUAVE = "#4E5E57"
TENUE = "#56645E"
LINEA = "#D9DED6"
AMBAR = "#E0A13A"
BOSQUE = "#0B231C"
VERDE = "#236E62"
SANS = "Geist, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'Geist Mono', Consolas, Menlo, monospace"


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


# --- piezas ------------------------------------------------------------------------------------


def _p(html: str, *, color: str = SUAVE, tam: int = 16) -> str:
    return (
        f'<p style="margin:0 0 16px;font-family:{SANS};font-size:{tam}px;line-height:1.6;'
        f'color:{color};">{html}</p>'
    )


def _titulo(texto: str) -> str:
    return (
        f'<h1 style="margin:0 0 16px;font-family:{SANS};font-size:24px;line-height:1.25;'
        f'font-weight:700;letter-spacing:-0.02em;color:{TINTA};">{escape(texto)}</h1>'
    )


def _boton(texto: str, href: str) -> str:
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 24px;">'
        f'<tr><td style="background:{AMBAR};border-radius:3px;">'
        f'<a href="{escape(href)}" style="display:inline-block;padding:14px 24px;'
        f"font-family:{SANS};font-size:16px;font-weight:600;color:{BOSQUE};"
        f'text-decoration:none;">{escape(texto)}</a></td></tr></table>'
    )


def _bloque(html: str, *, mono: bool = False) -> str:
    fuente = MONO if mono else SANS
    tam = 13 if mono else 15
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin:0 0 20px;">'
        f'<tr><td style="background:{SUPERFICIE};border-radius:4px;padding:14px 16px;'
        f"font-family:{fuente};font-size:{tam}px;line-height:1.55;color:{TINTA};"
        f'word-break:break-word;">{html}</td></tr></table>'
    )


def _firma() -> str:
    return _p(f"Un saludo,<br>{FIRMA}", color=TINTA)


_OCULTO = "display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;"
_LOGO = "display:block;border:0;border-radius:6px;"
_MARCA = (
    f"vertical-align:middle;padding-left:10px;font-family:{SANS};font-size:20px;"
    f"font-weight:700;letter-spacing:-0.03em;color:{TINTA};"
)
_PANEL = (
    f"background:{PANEL};border-top:3px solid {AMBAR};border-radius:6px;padding:32px 32px 16px;"
)
_PIE = f"padding:20px 4px 0;font-family:{SANS};font-size:13px;line-height:1.55;color:{TENUE};"


def _pagina(asunto: str, previa: str, cuerpo: str, pie: str) -> str:
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{escape(asunto)}</title>
</head>
<body style="margin:0;padding:0;background:{FONDO};">
<span style="{_OCULTO}">{escape(previa)}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{FONDO};">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;">
<tr><td style="padding:0 4px 20px;">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="vertical-align:middle;"><img src="{LOGO}" width="32" height="32" alt=""
 style="{_LOGO}"></td>
<td style="{_MARCA}">Terrnova</td>
</tr></table>
</td></tr>
<tr><td style="{_PANEL}">
{cuerpo}
</td></tr>
<tr><td style="{_PIE}">
{pie}<br><br>
Terrnova · datos oficiales de Colombia con su fuente y su prueba ·
<a href="{URL}" style="color:{VERDE};text-decoration:none;">terrnova.com</a>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _texto(lineas: list[str], pie: str) -> str:
    return "\n\n".join([*lineas, f"Un saludo,\n{FIRMA}", "—", pie, f"Terrnova · {URL}"]) + "\n"


# --- los correos -------------------------------------------------------------------------------


def enlace_llave(nombre: str, enlace: str, *, creditos: int, dias: int, soporte: str) -> Mensaje:
    n = nombre_visible(nombre)
    asunto = "Confirma tu correo para recibir tu llave de Terrnova"
    previa = "El enlace vence en 24 horas y sirve una sola vez."
    pie = (
        "Te escribimos porque alguien pidió una llave de prueba con este correo en terrnova.com. "
        "Si no fuiste tú, ignora este mensaje: sin confirmar no se crea ninguna llave."
    )
    cuerpo = (
        _titulo("Confirma tu correo")
        + _p(f"Hola, {escape(n)}.")
        + _p(
            "Recibimos tu solicitud de una llave de prueba de Terrnova. Para recibirla, confirma "
            "que este correo es tuyo."
        )
        + _boton("Confirmar y ver mi llave", enlace)
        + _p(
            f"La llave trae {creditos} créditos y vence en {dias} días. Se muestra una sola vez "
            "en la página: cópiala y guárdala en un lugar seguro. Nunca te la enviaremos por "
            "correo."
        )
        + _p("Si el botón no funciona, copia este enlace en tu navegador:", tam=14)
        + _bloque(escape(enlace), mono=True)
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}.",
            "Recibimos tu solicitud de una llave de prueba de Terrnova. Para recibirla, confirma "
            "que este correo es tuyo en este enlace (vence en 24 horas y sirve una sola vez):",
            enlace,
            f"La llave trae {creditos} créditos y vence en {dias} días. Se muestra una sola vez "
            "en la página: cópiala y guárdala en un lugar seguro.",
        ],
        pie,
    )
    return Mensaje(asunto, texto, _pagina(asunto, previa, cuerpo, pie), soporte)


def ya_tiene_llave(nombre: str, *, soporte: str) -> Mensaje:
    n = nombre_visible(nombre)
    asunto = "Ya tienes una llave de Terrnova"
    previa = "No creamos otra. Si la perdiste, responde este correo."
    pie = (
        "Te escribimos porque alguien pidió una llave con este correo en terrnova.com. Si no "
        "fuiste tú, ignora este mensaje."
    )
    cuerpo = (
        _titulo("Ya tienes una llave")
        + _p(f"Hola, {escape(n)}.")
        + _p("Este correo ya tiene una llave de prueba de Terrnova, así que no creamos otra.")
        + _p(
            "Si la perdiste o necesitas más créditos, responde este correo y te ayudamos a seguir."
        )
        + _boton("Ver cómo conectarla", f"{URL}/desarrolladores")
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}.",
            "Este correo ya tiene una llave de prueba de Terrnova, así que no creamos otra.",
            "Si la perdiste o necesitas más créditos, responde este correo y te ayudamos.",
            f"Cómo conectarla: {URL}/desarrolladores",
        ],
        pie,
    )
    return Mensaje(asunto, texto, _pagina(asunto, previa, cuerpo, pie), soporte)


COMANDO_CLAUDE = (
    "claude mcp add --transport http terrnova https://terrnova.com/mcp/catalogo \\\n"
    '  --header "Authorization: Bearer TU_LLAVE"'
)
PRIMERAS_PREGUNTAS = (
    "¿Qué predio hay en 4,8619 N, 74,0262 W?",
    "¿La empresa con NIT 899999068 tiene la matrícula al día?",
    "¿La Ley 1581 de 2012 sigue vigente?",
)


def bienvenida(nombre: str, *, creditos: int, vence: date, soporte: str) -> Mensaje:
    n = nombre_visible(nombre)
    fecha = vence.strftime("%d-%m-%Y")
    asunto = "Tu llave de Terrnova está lista: así la conectas"
    previa = f"{creditos} créditos hasta el {fecha}. Conéctala a tu agente en un minuto."
    pie = "Te escribimos porque confirmaste una llave de prueba en terrnova.com."
    preguntas = "".join(f"«{escape(p)}»<br>" for p in PRIMERAS_PREGUNTAS)
    cuerpo = (
        _titulo("Tu llave está lista")
        + _p(f"Hola, {escape(n)}.")
        + _p(
            f"Tu llave ya funciona. Trae {creditos} créditos y vence el {fecha}. Guárdala bien: "
            "no te la volveremos a mostrar."
        )
        + _p("Con Claude Code, conéctala así (cambia <b>TU_LLAVE</b> por la tuya):", color=TINTA)
        + _bloque(escape(COMANDO_CLAUDE).replace("\n", "<br>"), mono=True)
        + _p(
            "Para Cursor, Copilot en VS Code, Gemini CLI o Claude Desktop, y para usarla por API "
            "REST, sigue la guía:"
        )
        + _boton("Ver la guía de conexión", f"{URL}/desarrolladores")
        + _p("Para empezar, pregúntale a tu agente:", color=TINTA)
        + _bloque(preguntas)
        + _p(
            "Cada respuesta trae la entidad que publica el dato, su licencia y su fecha. Cuando "
            "quieras más créditos o un plan, responde este correo."
        )
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}.",
            f"Tu llave ya funciona. Trae {creditos} créditos y vence el {fecha}. Guárdala bien: "
            "no te la volveremos a mostrar.",
            f"Con Claude Code, conéctala así (cambia TU_LLAVE por la tuya):\n\n{COMANDO_CLAUDE}",
            "Para Cursor, Copilot, Gemini CLI, Claude Desktop o la API REST: "
            f"{URL}/desarrolladores",
            "Para empezar, pregúntale a tu agente:\n"
            + "\n".join(f"- {p}" for p in PRIMERAS_PREGUNTAS),
            "Cuando quieras más créditos o un plan, responde este correo.",
        ],
        pie,
    )
    return Mensaje(asunto, texto, _pagina(asunto, previa, cuerpo, pie), soporte)


def acuse_contacto(nombre: str, asunto: str, mensaje: str, *, soporte: str) -> Mensaje:
    n = nombre_visible(nombre)
    titulo = "Recibimos tu mensaje"
    previa = "Te respondemos en horario hábil, a este mismo correo."
    pie = (
        "Te escribimos porque alguien usó el formulario de terrnova.com con este correo. Si no "
        "fuiste tú, ignora este mensaje."
    )
    resumen = mensaje if len(mensaje) <= 600 else mensaje[:600].rstrip() + "…"
    cuerpo = (
        _titulo(titulo)
        + _p(f"Hola, {escape(n)}.")
        + _p(
            f"Recibimos tu mensaje sobre <b>{escape(asunto)}</b>. Te respondemos a este correo en "
            "horario hábil: de lunes a viernes, de 8:00 a 18:00, hora de Colombia."
        )
        + _bloque(escape(resumen).replace("\n", "<br>"))
        + _p("Si quieres agregar algo, responde este correo.")
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}.",
            f"Recibimos tu mensaje sobre «{asunto}». Te respondemos a este correo en horario "
            "hábil: de lunes a viernes, de 8:00 a 18:00, hora de Colombia.",
            f"Tu mensaje:\n{resumen}",
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
    pie = "Llegó por el formulario de terrnova.com/contacto. Responde este correo para escribirle."
    filas = "".join(
        f'<tr><td style="padding:6px 16px 6px 0;font-family:{SANS};font-size:14px;'
        f'color:{TENUE};vertical-align:top;white-space:nowrap;">{k}</td>'
        f'<td style="padding:6px 0;font-family:{SANS};font-size:15px;color:{TINTA};'
        f'word-break:break-word;">{escape(v)}</td></tr>'
        for k, v in (("Nombre", n), ("Correo", correo), ("Organización", org), ("Asunto", asunto))
    )
    cuerpo = (
        _titulo(titulo) + '<table role="presentation" cellpadding="0" cellspacing="0" '
        f'style="margin:0 0 20px;border-top:1px solid {LINEA};">{filas}</table>'
        + _bloque(escape(mensaje).replace("\n", "<br>"))
    )
    texto = (
        f"Nombre: {n}\nCorreo: {correo}\nOrganización: {org}\nAsunto: {asunto}\n\n{mensaje}\n\n"
        f"— {pie}\n"
    )
    return Mensaje(
        f"[Contacto] {asunto}: {n} ({org})", texto, _pagina(titulo, previa, cuerpo, pie), correo
    )
