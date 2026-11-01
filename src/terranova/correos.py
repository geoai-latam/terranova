"""Los correos que envía Terrnova.

Toman el oficio de los buenos correos de producto de hoy (Linear, Vercel, Stripe, Anthropic,
Cursor): una columna de 600 px sobre el fondo de la marca, el logo arriba, un título, una sola
acción, el dato real como protagonista y un pie corto. Lo propio de Terrnova es la ficha: filas
clave-valor como un recibo, para la llave, la solicitud o una respuesta real con su procedencia.

Trato de «tú» y firma «El equipo de Terrnova». Las respuestas van a soporte (o, en el aviso
interno de contacto, a quien escribió). Ningún correo lleva una llave ni un dato sensible, y cada
uno dice por qué te llegó. Fechas DD-MM-AAAA y horas en hora de Colombia (docs/DISENO.md).

El HTML es de correo: tablas y estilos en línea, porque Gmail y Outlook ignoran casi todo lo demás;
el `<style>` solo ajusta el móvil. Como la web, solo hay tema claro: se declara
`color-scheme: light` para que los clientes no lo inviertan a su manera. Geist donde el
cliente carga fuentes web y la pila del sistema en el resto. Imágenes en PNG a 2x (Gmail no
muestra SVG). Todo lo que escribe la persona se escapa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import escape

URL = "https://terrnova.com"
LOGO = f"{URL}/img/terrnova-correo.png"
HEROE_PREDIO = f"{URL}/img/correo-predio.png"
FIRMA = "El equipo de Terrnova"
COLOMBIA = timezone(timedelta(hours=-5), "COT")

# Tokens del sistema de diseño v4 (web/publico/estilo.css).
FONDO = "#F6F7F4"
PANEL = "#FFFFFF"
TINTA = "#12261F"
SUAVE = "#4E5E57"
TENUE = "#56645E"
LINEA = "#D9DED6"
AMBAR = "#E0A13A"
VERDE = "#236E62"
BOSQUE = "#0B231C"
SANS = "Geist, -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'Geist Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

_MOVIL = """
:root { color-scheme: light; supported-color-schemes: light; }
@media (max-width: 480px) {
  .c-titulo { font-size:24px !important; }
  .c-clave { width:auto !important; display:block !important; padding:10px 16px 0 !important; }
  .c-valor { display:block !important; padding:2px 16px 10px !important; border-top:0 !important; }
  .c-codigo { font-size:11px !important; }
}
"""


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


def fecha(d: date) -> str:
    """16-11-2026, como pide el sistema de diseño."""
    return d.strftime("%d-%m-%Y")


def hora_colombia(t: datetime) -> str:
    """31-10-2026, 21:40 (hora de Colombia)."""
    return t.astimezone(COLOMBIA).strftime("%d-%m-%Y, %H:%M") + " (hora de Colombia)"


# --- piezas ------------------------------------------------------------------------------------


def _p(
    html: str, *, clase: str = "c-tinta", color: str = TINTA, tam: int = 15, abajo: int = 16
) -> str:
    return (
        f'<p class="{clase}" style="margin:0 0 {abajo}px;font-family:{SANS};font-size:{tam}px;'
        f'line-height:1.6;color:{color};">{html}</p>'
    )


def _chico(html: str, *, abajo: int = 12) -> str:
    return _p(html, clase="c-suave", color=SUAVE, tam=13, abajo=abajo)


def _titulo(texto: str) -> str:
    return (
        f'<h1 class="c-tinta c-titulo" style="margin:0 0 16px;font-family:{SANS};font-size:28px;'
        f'line-height:1.2;font-weight:700;letter-spacing:-0.03em;color:{TINTA};">'
        f"{escape(texto)}</h1>"
    )


def _subtitulo(texto: str) -> str:
    return (
        f'<h2 class="c-tinta" style="margin:32px 0 12px;font-family:{SANS};font-size:17px;'
        f'line-height:1.3;font-weight:600;letter-spacing:-0.01em;color:{TINTA};">'
        f"{escape(texto)}</h2>"
    )


def _boton(texto: str, href: str) -> str:
    """El único acento ámbar de la vista. `bgcolor` en la celda: Outlook pinta el fondo."""
    return (
        '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 24px;">'
        f'<tr><td bgcolor="{AMBAR}" style="background:{AMBAR};border-radius:3px;">'
        f'<a href="{escape(href)}" style="display:inline-block;padding:13px 22px;'
        f"font-family:{SANS};font-size:15px;line-height:1;font-weight:600;color:{TINTA};"
        f'text-decoration:none;">{escape(texto)} &rarr;</a></td></tr></table>'
    )


def _enlace(texto: str, href: str, *, mono: bool = False) -> str:
    fuente = f"font-family:{MONO};font-size:12px;word-break:break-all;" if mono else ""
    return (
        f'<a class="c-enlace" href="{escape(href)}" style="{fuente}color:{VERDE};'
        f'text-decoration:underline;">{escape(texto)}</a>'
    )


def _chip(texto: str, *, bien: bool = False) -> str:
    color = VERDE if bien else SUAVE
    clase = "c-enlace" if bien else "c-suave"
    return (
        f'<span class="{clase} c-linea" style="display:inline-block;margin-left:6px;'
        f"padding:0 6px;border:1px solid {LINEA};border-radius:3px;font-family:{MONO};"
        f'font-size:11px;line-height:18px;color:{color};">{escape(texto)}</span>'
    )


def _mono(texto: str) -> str:
    return f'<span style="font-family:{MONO};font-size:13px;">{escape(texto)}</span>'


def _ficha(filas: list[tuple[str, str]], *, titulo: str = "", meta: str = "") -> str:
    """Filas clave-valor sobre un panel, como un recibo. Los valores ya vienen en HTML."""
    cab = ""
    if titulo:
        cab = (
            f'<tr><td class="c-tinta" style="padding:12px 16px;font-family:{MONO};font-size:13px;'
            f'font-weight:600;color:{TINTA};">{titulo}</td>'
            f'<td align="right" style="padding:12px 16px;">{meta}</td></tr>'
        )
    cuerpo = "".join(
        f'<tr><td class="c-tenue c-linea c-clave" width="34%" style="padding:9px 12px 9px 16px;'
        f"border-top:1px solid {LINEA};vertical-align:top;font-family:{SANS};font-size:13px;"
        f'line-height:1.5;color:{TENUE};">{escape(k)}</td>'
        f'<td class="c-tinta c-linea c-valor" style="padding:9px 16px 9px 0;border-top:1px solid '
        f"{LINEA};vertical-align:top;font-family:{SANS};font-size:14px;line-height:1.5;"
        f'color:{TINTA};word-break:break-word;">{v}</td></tr>'
        for k, v in filas
    )
    if not titulo:  # sin cabecera, la primera fila no lleva filete
        cuerpo = cuerpo.replace(f"border-top:1px solid {LINEA};", "border-top:0;", 2)
    return (
        '<table role="presentation" class="c-panel" width="100%" cellpadding="0" cellspacing="0" '
        f'style="margin:0 0 20px;background:{PANEL};border:1px solid {LINEA};border-radius:6px;'
        f'border-collapse:separate;">{cab}{cuerpo}</table>'
    )


def _codigo(texto: str) -> str:
    return (
        '<table role="presentation" class="c-panel" width="100%" cellpadding="0" cellspacing="0" '
        f'style="margin:4px 0 12px;background:{PANEL};border:1px solid {LINEA};border-radius:6px;">'
        '<tr><td class="c-tinta c-codigo" '
        f'style="padding:14px 16px;font-family:{MONO};font-size:12.5px;'
        f'line-height:1.65;color:{TINTA};white-space:pre-wrap;overflow-wrap:anywhere;">'
        f"{escape(texto)}</td></tr></table>"
    )


def _paso(n: int, titulo: str, html: str) -> str:
    """Un paso de una secuencia real (por eso va numerado)."""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin:0 0 8px;"><tr>'
        f'<td class="c-tenue" width="28" style="vertical-align:top;padding-top:1px;'
        f'font-family:{MONO};font-size:13px;line-height:1.6;color:{TENUE};">{n}</td>'
        f'<td style="vertical-align:top;">'
        f'<p class="c-tinta" style="margin:0 0 6px;font-family:{SANS};font-size:15px;'
        f'line-height:1.5;font-weight:600;color:{TINTA};">{escape(titulo)}</p>{html}</td>'
        "</tr></table>"
    )


def _enlaces(items: list[tuple[str, str, str]]) -> str:
    """Enlaces con flecha y una línea de para qué sirven, separados por filetes (como Linear)."""
    filas = "".join(
        f'<tr><td class="c-linea" style="padding:12px 0;border-top:1px solid {LINEA};">'
        f'<a class="c-tinta" href="{escape(href)}" style="font-family:{SANS};font-size:15px;'
        f'font-weight:600;color:{TINTA};text-decoration:none;">{escape(texto)} &rarr;</a><br>'
        f'<span class="c-suave" style="font-family:{SANS};font-size:13px;line-height:1.5;'
        f'color:{SUAVE};">{escape(para)}</span></td></tr>'
        for texto, href, para in items
    )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="margin:0 0 24px;">{filas}</table>'
    )


def _cita(texto: str) -> str:
    """Lo que escribió la persona, citado como en cualquier respuesta de correo."""
    return (
        f'<p class="c-suave c-linea" style="margin:0 0 20px;padding:2px 0 2px 14px;'
        f"border-left:2px solid {LINEA};font-family:{SANS};font-size:14px;line-height:1.6;"
        f'color:{SUAVE};">{escape(texto).replace(chr(10), "<br>")}</p>'
    )


def _firma() -> str:
    return _p(FIRMA, abajo=0)


def _heroe(src: str, alt: str, pie: str) -> str:
    return (
        f'<img src="{src}" width="600" alt="{escape(alt)}" style="display:block;width:100%;'
        f'max-width:600px;height:auto;border:0;border-radius:6px;">'
        f'<p class="c-tenue" style="margin:8px 0 28px;font-family:{MONO};font-size:11.5px;'
        f'line-height:1.5;color:{TENUE};">{escape(pie)}</p>'
    )


_PIE = f"font-family:{SANS};font-size:12px;line-height:1.6;color:{TENUE};"
_RELLENO = "&#847;&zwnj;&nbsp;" * 60  # para que el cliente no complete la vista previa
_PIE_ENLACES = (
    ("Desarrolladores", "/desarrolladores"),
    ("Fuentes", "/fuentes"),
    ("Estado", "/estado"),
    ("Privacidad", "/privacidad"),
)


def _pagina(
    asunto: str, previa: str, cuerpo: str, pie: str, *, etiqueta: str, heroe: str = ""
) -> str:
    enlaces = " &nbsp;·&nbsp; ".join(
        f'<a class="c-tenue" href="{URL}{ruta}" style="color:{TENUE};text-decoration:none;">'
        f"{texto}</a>"
        for texto, ruta in _PIE_ENLACES
    )
    return f"""<!doctype html>
<html lang="es" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{escape(asunto)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;700&amp;family=Geist+Mono:wght@400;600&amp;display=swap">
<style>{_MOVIL}</style>
</head>
<body class="c-fondo" style="margin:0;padding:0;background:{FONDO};">
<div style="display:none;max-height:0;overflow:hidden;">{escape(previa)}{_RELLENO}</div>
<table role="presentation" class="c-fondo" width="100%" cellpadding="0" cellspacing="0"
 style="background:{FONDO};">
<tr><td align="center" style="padding:32px 16px 40px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;">
<tr><td style="padding:0 0 28px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
<td><a href="{URL}"><img src="{LOGO}" width="28" height="28" alt="Terrnova"
 style="display:block;border:0;border-radius:5px;"></a></td>
<td align="right" class="c-tenue"
 style="font-family:{SANS};font-size:13px;color:{TENUE};">{escape(etiqueta)}</td>
</tr></table>
</td></tr>
<tr><td style="padding:0 0 40px;">
{heroe}{cuerpo}
</td></tr>
<tr><td class="c-linea" style="padding:4px 0 0;border-top:1px solid {LINEA};">
<p class="c-tenue" style="margin:24px 0 10px;{_PIE}">{pie}</p>
<p class="c-tenue" style="margin:0 0 10px;{_PIE}">{enlaces}</p>
<p class="c-tenue" style="margin:0;{_PIE}">Terrnova · datos oficiales de Colombia, con su fuente</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _texto(lineas: list[str], pie: str) -> str:
    return "\n\n".join([*lineas, FIRMA, "--", pie, f"Terrnova · {URL}"]) + "\n"


# --- los correos -------------------------------------------------------------------------------


def enlace_llave(
    nombre: str,
    enlace: str,
    *,
    creditos: int,
    dias: int,
    pedida: datetime,
    vence: datetime,
    soporte: str,
) -> Mensaje:
    n = nombre_visible(nombre)
    asunto = "Confirma tu correo para recibir tu llave de Terrnova"
    previa = f"Un clic y tu llave queda lista: {creditos} créditos para {dias} días."
    pie = (
        "Recibes este correo porque se pidió una llave de prueba con esta dirección en "
        "terrnova.com/precios."
    )
    cuerpo = (
        _titulo("Confirma tu correo")
        + _p(
            f"Hola, {escape(n)}. Un clic y tu llave de prueba queda lista: {creditos} créditos "
            f"para usar durante {dias} días desde Claude, Cursor, Copilot o tu propio código."
        )
        + _boton("Confirmar y ver mi llave", enlace)
        + _p(
            "La llave se muestra una sola vez, en la página que abre el botón. Cópiala ahí: no la "
            "enviamos por correo.",
            clase="c-suave",
            color=SUAVE,
        )
        + _ficha(
            [
                ("Solicitada", escape(hora_colombia(pedida))),
                ("Enlace válido hasta", escape(hora_colombia(vence))),
                ("Usos", "Uno"),
            ]
        )
        + _chico(
            "¿El botón no abre? Copia este enlace en tu navegador:<br>"
            + _enlace(enlace, enlace, mono=True)
        )
        + _chico(
            "Si no pediste esta llave, ignora este correo: sin confirmar no se crea nada.", abajo=24
        )
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}. Un clic y tu llave de prueba queda lista: {creditos} créditos para usar "
            f"durante {dias} días.",
            f"Confirma tu correo aquí:\n{enlace}",
            "La llave se muestra una sola vez, en la página que abre el enlace. No la enviamos "
            "por correo.",
            f"Solicitada: {hora_colombia(pedida)}\nEnlace válido hasta: {hora_colombia(vence)}\n"
            "Usos: uno",
            "Si no pediste esta llave, ignora este correo: sin confirmar no se crea nada.",
        ],
        pie,
    )
    html = _pagina(asunto, previa, cuerpo, pie, etiqueta="Llave de prueba")
    return Mensaje(asunto, texto, html, soporte)


def ya_tiene_llave(
    nombre: str, *, desde: date | None, vence: date | None, pedida: datetime, soporte: str
) -> Mensaje:
    n = nombre_visible(nombre)
    asunto = "Ya tienes una llave de Terrnova"
    previa = "No creamos otra. Si la perdiste o necesitas más créditos, responde este correo."
    pie = (
        "Recibes este correo porque se pidió una llave de prueba con esta dirección en "
        "terrnova.com/precios."
    )
    filas = [("Nueva solicitud", escape(hora_colombia(pedida)))]
    if desde:
        filas.insert(0, ("Tu llave, desde", fecha(desde)))
    if vence:
        filas.insert(1 if desde else 0, ("Vence", fecha(vence)))
    cuerpo = (
        _titulo("Ya tienes una llave")
        + _p(
            f"Hola, {escape(n)}. Se pidió otra llave de prueba con este correo. Como ya tiene "
            "una, no creamos otra."
        )
        + _ficha(filas)
        + _p("¿La perdiste o se te acabaron los créditos? Responde este correo y lo resolvemos.")
        + _enlaces(
            [
                (
                    "Guía de conexión",
                    f"{URL}/desarrolladores",
                    "Claude, Cursor, Copilot, Gemini CLI y API REST.",
                ),
                ("Planes y créditos", f"{URL}/precios", "Cuando la prueba se te quede corta."),
            ]
        )
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}. Se pidió otra llave de prueba con este correo. Como ya tiene una, no "
            "creamos otra.",
            "\n".join(f"{k}: {v}" for k, v in filas),
            "¿La perdiste o se te acabaron los créditos? Responde este correo y lo resolvemos.",
            f"Guía de conexión: {URL}/desarrolladores\nPlanes y créditos: {URL}/precios",
        ],
        pie,
    )
    html = _pagina(asunto, previa, cuerpo, pie, etiqueta="Llave de prueba")
    return Mensaje(asunto, texto, html, soporte)


COMANDO_CLAUDE = (
    "claude mcp add --transport http terrnova \\\n"
    "  https://terrnova.com/mcp/catalogo \\\n"
    '  --header "Authorization: Bearer TU_LLAVE"'
)
PRIMERA_PREGUNTA = "¿Qué predio hay en 11,2211 N, 74,1572 W?"

# Una respuesta real de producción a PRIMERA_PREGUNTA (solicitud req_01M6AEQ1Q10XH5SZP1ZYRMS212,
# 01-11-2026). El héroe de la bienvenida dibuja los linderos de web/publico/datos/sm.json alrededor
# de este mismo predio. Si cambia la fuente, se vuelve a medir y se actualiza junto con la imagen.
EJEMPLO: dict[str, str] = {
    "herramienta": "sinic_predio_en_punto",
    "estado": "encontrado",
    "predio": "470010109000002580801800000308",
    "lugar": "Santa Marta, Magdalena · zona urbana",
    "destinacion": "Habitacional · predio privado",
    "entidad": "Instituto Geográfico Agustín Codazzi (IGAC), SINIC",
    "licencia": "CC-BY-SA-4.0",
    "completitud": "1 de 1",
    "servido": "copia del 28-10-2026",
    "creditos": "10",
    "huella": "sha256:7a2cc965…baef1a0f",
}


def bienvenida(nombre: str, *, creditos: int, vence: date, soporte: str) -> Mensaje:
    n = nombre_visible(nombre)
    asunto = "Tu llave de Terrnova está activa"
    previa = f"{creditos} créditos hasta el {fecha(vence)}. Conéctala a tu agente en un minuto."
    pie = (
        "Recibes este correo porque confirmaste una llave de prueba en terrnova.com. Si no fuiste "
        "tú, respóndenos y la revocamos."
    )
    e = EJEMPLO
    respuesta = _ficha(
        [
            ("Predio", _mono(e["predio"])),
            ("Lugar", escape(e["lugar"])),
            ("Destinación", escape(e["destinacion"])),
            ("Entidad", escape(e["entidad"])),
            ("Licencia", _mono(e["licencia"]) + _chip("uso comercial: sí", bien=True)),
            ("Completitud", escape(e["completitud"]) + _chip("completa", bien=True)),
            ("Servido desde", escape(e["servido"])),
            ("Costo", f"{e['creditos']} créditos"),
            ("Huella", _mono(e["huella"])),
        ],
        titulo=escape(e["herramienta"]),
        meta=_chip(e["estado"], bien=True),
    )
    cuerpo = (
        _titulo("Tu llave está activa")
        + _p(
            f"Hola, {escape(n)}. Ya puedes consultar datos oficiales de Colombia desde tu agente "
            "o tu código. Cada respuesta dice qué entidad publica el dato, con qué licencia y qué "
            "tan completo está."
        )
        + _ficha(
            [
                ("Plan", "Prueba"),
                ("Créditos", f"{creditos}"),
                ("Vence", fecha(vence)),
                ("Acceso", "MCP y API REST"),
                ("Llave", "La viste una vez al confirmar. No la enviamos por correo."),
            ]
        )
        + _subtitulo("Empieza en tres pasos")
        + _paso(
            1,
            "Conéctala a tu agente",
            _p(
                "En Claude Code, cambia TU_LLAVE por la tuya:",
                clase="c-suave",
                color=SUAVE,
                abajo=0,
            )
            + _codigo(COMANDO_CLAUDE)
            + _chico(
                f"Para Cursor, Copilot, Gemini CLI o Claude Desktop, sigue la "
                f"{_enlace('guía de conexión', URL + '/desarrolladores')}.",
                abajo=16,
            ),
        )
        + _paso(
            2,
            "Haz tu primera pregunta",
            _p(f"Pídele a tu agente: «{escape(PRIMERA_PREGUNTA)}»", clase="c-suave", color=SUAVE),
        )
        + _paso(
            3,
            "Mira de dónde sale",
            _p("Esta es la respuesta real a esa pregunta:", clase="c-suave", color=SUAVE, abajo=10)
            + respuesta,
        )
        + _boton("Ver la guía de conexión", f"{URL}/desarrolladores")
        + _enlaces(
            [
                (
                    "Fuentes y licencias",
                    f"{URL}/fuentes",
                    "Qué entidad publica cada dato y con qué licencia.",
                ),
                (
                    "Estado de las fuentes",
                    f"{URL}/estado",
                    "Cuáles responden ahora y cuáles van lentas.",
                ),
                ("Planes y créditos", f"{URL}/precios", "Cuando la prueba se te quede corta."),
            ]
        )
        + _p("¿Algo no funciona? Responde este correo: lo lee una persona del equipo.", abajo=24)
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}. Ya puedes consultar datos oficiales de Colombia desde tu agente o tu "
            "código. Cada respuesta dice qué entidad publica el dato, con qué licencia y qué tan "
            "completo está.",
            f"Plan: Prueba\nCréditos: {creditos}\nVence: {fecha(vence)}\nAcceso: MCP y API REST\n"
            "Llave: la viste una vez al confirmar. No la enviamos por correo.",
            f"1. Conéctala a tu agente. En Claude Code, cambia TU_LLAVE por la tuya:\n\n"
            f"{COMANDO_CLAUDE}\n\nCursor, Copilot, Gemini CLI o Claude Desktop: "
            f"{URL}/desarrolladores",
            f"2. Haz tu primera pregunta: «{PRIMERA_PREGUNTA}»",
            "3. Mira de dónde sale. La respuesta real a esa pregunta:\n"
            f"   Predio: {e['predio']}\n   Lugar: {e['lugar']}\n"
            f"   Destinación: {e['destinacion']}\n   Entidad: {e['entidad']}\n"
            f"   Licencia: {e['licencia']} (uso comercial: sí)\n"
            f"   Completitud: {e['completitud']}\n   Servido desde: {e['servido']}\n"
            f"   Costo: {e['creditos']} créditos",
            f"Fuentes y licencias: {URL}/fuentes\nEstado de las fuentes: {URL}/estado\n"
            f"Planes y créditos: {URL}/precios",
            "¿Algo no funciona? Responde este correo: lo lee una persona del equipo.",
        ],
        pie,
    )
    heroe = _heroe(
        HEROE_PREDIO,
        "Linderos de predios en Santa Marta; el predio consultado, en ámbar.",
        "Predios reales del SINIC en Santa Marta. En ámbar, el de la respuesta del paso 3.",
    )
    html = _pagina(asunto, previa, cuerpo, pie, etiqueta="Llave de prueba", heroe=heroe)
    return Mensaje(asunto, texto, html, soporte)


# A dónde mirar mientras respondemos, según el asunto del formulario.
RELACIONADO = {
    "proyecto": ("Servicios", "/servicios", "Cómo trabajamos un proyecto, de punta a punta."),
    "debida-diligencia": (
        "Servicios",
        "/servicios",
        "Revisiones de predios, empresas y contratos.",
    ),
    "tablero": ("Servicios", "/servicios", "Tableros e informes sobre fuentes oficiales."),
    "vigilancia": ("Servicios", "/servicios", "Alertas cuando cambia una fuente."),
    "asistente": ("Servicios", "/servicios", "Asistentes sobre fuentes oficiales."),
    "soporte": ("Guía de conexión", "/desarrolladores", "Errores, perfiles MCP y API REST."),
}
_RELACIONADO_PLANES = ("Planes y créditos", "/precios", "Qué trae cada plan.")


def referencia(huella: str) -> str:
    """TN-7F3A2C: para encontrar la conversación en el buzón."""
    return "TN-" + huella[:6].upper()


def acuse_contacto(
    nombre: str,
    tema: str,
    asunto: str,
    mensaje: str,
    *,
    ref: str,
    recibido: datetime,
    soporte: str,
) -> Mensaje:
    n = nombre_visible(nombre)
    titulo = "Recibimos tu mensaje"
    previa = f"{ref} · te respondemos a este correo en horario hábil."
    pie = (
        "Recibes este correo porque se usó el formulario de terrnova.com/contacto con esta "
        "dirección."
    )
    resumen = mensaje if len(mensaje) <= 600 else mensaje[:600].rstrip() + "…"
    texto_r, ruta, para = RELACIONADO.get(tema, _RELACIONADO_PLANES)
    cuerpo = (
        _titulo(titulo)
        + _p(
            f"Hola, {escape(n)}. Gracias por escribirnos. Una persona del equipo lo lee y te "
            "responde a este mismo correo."
        )
        + _ficha(
            [
                ("Referencia", _mono(ref)),
                ("Recibido", escape(hora_colombia(recibido))),
                ("Tema", escape(asunto)),
                ("Respuesta", "Hasta 3 días hábiles (lunes a viernes, 8:00 a 18:00)"),
            ]
        )
        + _chico("Tu mensaje:", abajo=8)
        + _cita(resumen)
        + _p("Para agregar algo, responde este correo y deja la referencia en el asunto.")
        + _enlaces([(texto_r, URL + ruta, para)])
        + _firma()
    )
    texto = _texto(
        [
            f"Hola, {n}. Gracias por escribirnos. Una persona del equipo lo lee y te responde a "
            "este mismo correo.",
            f"Referencia: {ref}\nRecibido: {hora_colombia(recibido)}\nTema: {asunto}\n"
            "Respuesta: hasta 3 días hábiles (lunes a viernes, 8:00 a 18:00)",
            "Tu mensaje:\n" + "\n".join(f"> {linea}" for linea in resumen.splitlines()),
            "Para agregar algo, responde este correo y deja la referencia en el asunto.",
            f"{texto_r}: {URL}{ruta}",
        ],
        pie,
    )
    html = _pagina(titulo, previa, cuerpo, pie, etiqueta="Contacto")
    return Mensaje(f"{titulo} [{ref}]", texto, html, soporte)


def aviso_contacto(
    nombre: str,
    correo: str,
    organizacion: str,
    asunto: str,
    mensaje: str,
    *,
    ref: str,
    recibido: datetime,
) -> Mensaje:
    """El aviso interno a soporte. Responder le escribe directo a quien llenó el formulario."""
    n = nombre_visible(nombre)
    org = organizacion or "sin organización"
    titulo = f"Nuevo contacto: {asunto}"
    previa = f"{n} ({org}) escribió desde el formulario."
    pie = "Llegó por terrnova.com/contacto. Responde este correo para escribirle."
    cuerpo = (
        _titulo(titulo)
        + _ficha(
            [
                ("Referencia", _mono(ref)),
                ("Recibido", escape(hora_colombia(recibido))),
                ("Nombre", escape(n)),
                ("Correo", escape(correo)),
                ("Organización", escape(org)),
                ("Tema", escape(asunto)),
            ]
        )
        + _cita(mensaje)
        + _chico(f"Responde este correo para escribirle a {escape(n)} directamente.", abajo=0)
    )
    texto = (
        f"Referencia: {ref}\nRecibido: {hora_colombia(recibido)}\nNombre: {n}\nCorreo: {correo}\n"
        f"Organización: {org}\nTema: {asunto}\n\n{mensaje}\n\n-- {pie}\n"
    )
    html = _pagina(titulo, previa, cuerpo, pie, etiqueta="Contacto · interno")
    return Mensaje(f"[Contacto {ref}] {asunto}: {n} ({org})", texto, html, correo)
