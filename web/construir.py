"""Construye el sitio público de Terrnova (terrnova.com) en web/publico/.

Las páginas se arman aquí con el catálogo real: conteos, familias, fuentes y licencias salen de
`catalogo/`, nunca escritos a mano. Lo estático (estilo.css, js/, datos/sm.json, datos/co.json, img/)
vive ya en web/publico/ y no se toca.

    uv run python web/construir.py            # escribe las páginas
    uv run python web/construir.py --revisar  # falla si alguna página no está al día (lo usa la prueba)
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from html import escape
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PUBLICO = RAIZ / "publico"
sys.path.insert(0, str(RAIZ.parent / "src"))

from terranova.alta import ASUNTOS, VIGENCIA_LLAVE  # noqa: E402
from terranova.cache import RETENCION_S  # noqa: E402
from terranova.catalogo import TARIFA as TARIFA_CATALOGO  # noqa: E402
from terranova.catalogo import cargar  # noqa: E402
from terranova.compuestas import COMPUESTAS  # noqa: E402
from terranova.correos import COMANDO_CLAUDE, EJEMPLO, PRIMERA_PREGUNTA  # noqa: E402
from terranova.cuota import NIVELES  # noqa: E402

DOMINIO = "https://terrnova.com"
CORREO = "soporte@terrnova.com"
# La misma versión que importa web/publico/js/comun3d.js.
THREE_URL = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"

# Precios de lanzamiento (decisión del dueño, 01-11-2026): pesos al mes, más IVA; el anual, 20 %
# menos. Los créditos de cada plan salen de NIVELES (cuota.py, ADR-0029). El plan Gratis de
# NIVELES["con_llave"] no se anuncia: el sitio ofrece solo la llave de prueba (decisión 2).
PLANES = [
    ("basico", "Básico", 79_000, 758_400),
    ("pro", "Pro", 299_000, 2_870_400),
    ("empresa", "Empresa", 899_000, 8_630_400),
    ("escala", "Escala", 2_390_000, 22_944_000),
]
assert all(anual == mes * 12 * 8 // 10 for _, _, mes, anual in PLANES), (
    "anual = 12 meses menos el 20 %"
)
CREDITOS_AMPLIADO = NIVELES["ampliado"]  # entidades públicas, academia y veedurías, a pedido
# La llave del alta automática (ADR-0034): pocos créditos y vencimiento. Salen del código.
CREDITOS_PRUEBA = NIVELES["prueba"]
TOPE_FICHA = COMPUESTAS["ficha_lugar"].tope_creditos
DIAS_PRUEBA = VIGENCIA_LLAVE.days

# Créditos por tipo de pregunta (catalogo.TARIFA, enmienda de la ADR-0010), dichos en palabras de
# quien pregunta, con una herramienta real de ese tipo (la construcción comprueba el tipo).
TARIFA = [
    ("codigo", "de nombre a código", "el código de un municipio", "dane_divipola_buscar"),
    ("registro", "un registro", "una empresa por NIT, una norma", "rues_empresa_por_nit"),
    (
        "agregado",
        "un conteo o una búsqueda",
        "los contratos de una entidad",
        "secop_contratos_entidad",
    ),
    ("punto", "un punto del mapa", "el predio en una coordenada", "sinic_predio_en_punto"),
    ("zona", "una zona", "las áreas protegidas de una zona", "pnn_areas_protegidas_en_zona"),
]
assert [t[0] for t in TARIFA] == list(TARIFA_CATALOGO)
FAMILIAS = {
    "estadisticas": "Estadísticas",
    "territorio": "Territorio",
    "contratacion": "Contratación",
    "justicia": "Justicia",
    "ambiente": "Ambiente",
    "empresas": "Empresas",
    "normativa": "Normativa",
    "meta": "Catálogo",
}
NAV = [
    ("/", "Producto"),
    ("/servicios", "Servicios"),
    ("/fuentes", "Fuentes"),
    ("/precios", "Precios"),
    ("/desarrolladores", "Desarrolladores"),
]


def miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def corta(entidad: str) -> str:
    m = re.search(r"\(([^()]{2,24})\)\s*$", entidad)
    return m.group(1) if m else entidad


# Nombre corto de cada entidad: la sigla del catálogo o un nombre de uso común. También une las
# entidades que el catálogo escribe de dos formas (Confecámaras).
NOMBRE_CORTO = {
    "ANCP-CCE": "Colombia Compra Eficiente",
    "CNMH": "Centro Nacional de Memoria Histórica",
    "Policía Nacional de Colombia": "Policía Nacional",
    "Superintendencia de Sociedades": "Supersociedades",
    "CAR": "CAR Cundinamarca",
    "DAFP": "Función Pública",
    "SDP": "Planeación de Bogotá",
    "Instituto Nacional de Medicina Legal y Ciencias Forenses": "Medicina Legal",
    "MEN": "MinEducación",
    "UARIV": "Unidad para las Víctimas",
    "ANT": "Agencia Nacional de Tierras",
    "Ministerio de Hacienda y Crédito Público": "MinHacienda",
    "Ministerio de Justicia y del Derecho": "MinJusticia",
    "Ministerio de Salud y Protección Social": "MinSalud",
    "Superintendencia de la Economía Solidaria": "Supersolidaria",
    "SFC": "Superfinanciera",
    "PNN": "Parques Nacionales",
    "UAECD": "Catastro de Bogotá",
    "URT": "Unidad de Restitución de Tierras",
    "consorcio WorldCover": "ESA WorldCover",
    "LANCE/FIRMS": "NASA FIRMS",
}
GLOBALES = ("USGS", "ESA WorldCover", "NASA FIRMS")


def nombre_entidad(entidad: str) -> str:
    if entidad.startswith("Presidencia de la República"):
        return "Presidencia"
    c = corta(entidad)
    return NOMBRE_CORTO.get(c, c)


# ---------------------------------------------------------------- catálogo real
CAT = cargar(RAIZ.parent / "catalogo")
_IDS_PUBLICADAS = {
    f.id for f in CAT.fuentes.values() if f.estado == "publicada" and f.uso_comercial == "si"
}
HERR = sorted(
    (h for h in CAT.herramientas.values() if h.fuente in _IDS_PUBLICADAS),
    key=lambda h: (h.familia, h.id),
)
N_HERR = len(HERR)
# Solo se anuncia lo que se puede vender: fuentes publicadas y con uso comercial. Un borrador no se
# sirve, y una fuente «sin fines de lucro» (la DIAN, usuarios aduaneros) no se anuncia (DISENO.md).
PUBLICADAS = [
    f for f in CAT.fuentes.values() if f.estado == "publicada" and f.uso_comercial == "si"
]
assert all(f.uso_comercial == "si" for f in PUBLICADAS)
N_FUENTES = len(PUBLICADAS)
# Fuentes por entidad, sin el índice propio de Terrnova, que no es una fuente oficial.
ENTIDADES = Counter(
    nombre_entidad(f.entidad) for f in PUBLICADAS if not f.entidad.startswith("Terrnova")
)
N_ENTIDADES = len(ENTIDADES)
# Las fuentes globales (USGS, ESA, NASA) también cuentan: «de Colombia» a secas no sería verdad.
N_GLOBALES = sum(1 for f in PUBLICADAS if nombre_entidad(f.entidad) in GLOBALES)
assert 0 < N_GLOBALES < N_FUENTES
FUENTES_DE = f"{N_FUENTES} fuentes oficiales, de Colombia y globales"
POR_FAMILIA = Counter(h.familia for h in HERR)
MODOS = Counter(f.modo for f in PUBLICADAS)
LICENCIAS = Counter(f.licencia.spdx or "dato público, sin SPDX" for f in PUBLICADAS)
N_VERIFICADAS = sum(f.licencia.verificada is not None for f in PUBLICADAS)


def catalogo_json() -> str:
    fuentes = {
        fid: {
            "titulo": f.titulo,
            "entidad": f.entidad,
            "entidad_corta": corta(f.entidad),
            "licencia": f.licencia.spdx or "por verificar",
            "uso_comercial": f.uso_comercial,
            "modo": f.modo,
        }
        for fid, f in sorted((f.id, f) for f in PUBLICADAS)
    }
    herramientas = [
        {
            "id": h.id,
            "familia": h.familia,
            "pregunta": h.pregunta,
            "fuente": h.fuente,
            "creditos": h.creditos,
            "cobro": h.cobro,
        }
        for h in HERR
    ]
    return json.dumps(
        {"herramientas": herramientas, "fuentes": fuentes},
        ensure_ascii=False,
        separators=(",", ":"),
    )


for _cobro, _, _, _hid in TARIFA:
    assert CAT.herramientas[_hid].cobro == _cobro, f"{_hid} no se cobra como {_cobro}"

TRAMPA = (
    '<label class="trampa" aria-hidden="true">No llenes este campo'
    '<input name="web" tabindex="-1" autocomplete="off"></label>'
)
ACEPTO = (
    '<label class="casilla"><input type="checkbox" name="acepto" value="si" required><span>Acepto la '
    '<a class="enlace" href="/privacidad">política de privacidad</a>.</span></label>'
)


def formulario_alta() -> str:
    return f"""<form class="formulario" method="post" action="/v1/alta">
<label>Tu nombre<input name="nombre" required maxlength="120" autocomplete="name"></label>
<label>Tu correo<input name="correo" type="email" required maxlength="254" autocomplete="email"></label>
<label>Organización <small>(opcional)</small><input name="organizacion" maxlength="120" autocomplete="organization"></label>
<label>Qué quieres consultar <small>(opcional)</small><textarea name="uso" rows="2" maxlength="500"></textarea></label>
{ACEPTO}{TRAMPA}
<button class="boton p" type="submit">Enviarme el enlace</button>
</form>"""


# Los mismos que acepta la puerta, menos el plan Gratis, que el sitio no anuncia (decisión 2).
ASUNTOS_CONTACTO = [(v, t) for v, t in ASUNTOS.items() if v != "plan-gratis"]
assert all(f"plan-{c}" in ASUNTOS for c, *_ in PLANES) and "gobierno-academia" in ASUNTOS


def formulario_contacto() -> str:
    opciones = "".join(f'<option value="{v}">{t}</option>' for v, t in ASUNTOS_CONTACTO)
    return f"""<form class="formulario" method="post" action="/v1/contacto" data-asunto>
<label>Tu nombre<input name="nombre" required maxlength="120" autocomplete="name"></label>
<label>Tu correo<input name="correo" type="email" required maxlength="254" autocomplete="email"></label>
<label>Organización <small>(opcional)</small><input name="organizacion" maxlength="120" autocomplete="organization"></label>
<label>Asunto<select name="asunto">{opciones}</select></label>
<label>Mensaje<textarea name="mensaje" rows="6" required maxlength="4000"></textarea></label>
{ACEPTO}{TRAMPA}
<button class="boton p" type="submit">Enviar</button>
</form>"""


# ---------------------------------------------------------------- piezas comunes
def simbolo(trazo="#0E2A22", dentro="#0E2A22", punto="#E0A13A", clase="") -> str:
    return (
        f'<svg class="{clase}" viewBox="0 0 64 64" aria-hidden="true"><g fill="none" stroke="{trazo}" stroke-width="4">'
        '<path d="M6 58V30a26 26 0 0 1 52 0v28"/><path d="M15 58V30a17 17 0 0 1 34 0v28"/></g>'
        f'<path d="M24 58V30a8 8 0 0 1 16 0v28z" fill="{dentro}"/><circle cx="32" cy="46" r="3.5" fill="{punto}"/></svg>'
    )


PULSO = (
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>'
)


def encabezado(ruta: str) -> str:
    menu = "".join(
        f'<a href="{h}"{' aria-current="page"' if h == ruta else ""}>{t}</a>' for h, t in NAV
    )
    return f"""<header class="barra"><div class="envoltura">
<a class="marca" href="/" aria-label="Terrnova, inicio">{simbolo()}Terrnova</a>
<nav class="menu" id="menu-principal" aria-label="Principal">{menu}</nav>
<div class="der" id="menu-der"><a href="/estado">{PULSO}Estado</a><a href="/contacto">Contacto</a><a class="boton s chico" href="/precios#empezar">Prueba gratis</a></div>
<button class="abrir" type="button" aria-expanded="false" aria-controls="menu-principal menu-der" aria-label="Abrir el menú"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
</div></header>"""


PIE = f"""<footer class="pie-sitio"><div class="envoltura">
<div class="arr">
<div><a class="marca" href="/">{simbolo("#F3EFE4", "#F3EFE4", "#E0A13A")}Terrnova</a>
<p class="desc">Datos oficiales de Colombia, con su fuente, su licencia y su fecha.</p></div>
<div><h2>Producto</h2><ul><li><a href="/fuentes">Fuentes y herramientas</a></li><li><a href="/precios">Precios</a></li><li><a href="/estado">Estado del servicio</a></li><li><a href="/servicios">Servicios</a></li></ul></div>
<div><h2>Desarrolladores</h2><ul><li><a href="/desarrolladores">Guía de conexión</a></li><li><a href="/docs">API REST (OpenAPI)</a></li><li><a href="/llms.txt">llms.txt</a></li><li><a href="/desarrolladores#contrato">Contrato rt/1</a></li></ul></div>
<div><h2>Empresa</h2><ul><li><a href="/aliados">Aliados</a></li><li><a href="/contacto">Contacto</a></li><li><a href="mailto:{CORREO}">{CORREO}</a></li><li><a href="/terminos">Términos</a> · <a href="/privacidad">Privacidad</a></li></ul></div>
</div>
<div class="ab"><span>© 2026 Terrnova · terrnova.com</span><span>4,6097 N · 74,0817 W · Bogotá</span></div>
</div></footer>"""


def version(ruta: str) -> str:
    """Huella corta del archivo, para `?v=`: lo versionado se puede guardar en caché mucho tiempo."""
    import hashlib

    datos = (PUBLICO / ruta.lstrip("/")).read_bytes().replace(b"\r\n", b"\n")
    return f"{ruta}?v={hashlib.sha256(datos).hexdigest()[:10]}"


# Imagen para compartir (1200 x 630) por página: una figura del sitio con el titular de la página.
# Las dibuja `web/og.py` (Playwright) en img/og/; las páginas sin la suya usan la de la portada.
OG = {
    "/": "portada",
    "/servicios": "servicios",
    "/fuentes": "fuentes",
    "/precios": "precios",
    "/desarrolladores": "desarrolladores",
}


def pagina(
    ruta: str,
    titulo: str,
    descripcion: str,
    cuerpo: str,
    scripts: tuple[str, ...] = (),
    indexar: bool = True,
) -> str:
    canon = DOMINIO + (ruta if ruta != "/" else "/")
    tit = titulo if ruta == "/" else f"{titulo} · Terrnova"
    mods = "".join(
        f'\n<script type="module" src="{version("/js/" + s)}"></script>' for s in scripts
    )
    if any(s.startswith("escena-") for s in scripts):
        # three.js empieza a bajar con la página, no cuando el módulo de la escena lo pide.
        mods = f'\n<link rel="modulepreload" href="{THREE_URL}" crossorigin>' + mods
    og = f"{DOMINIO}/img/og/{OG.get(ruta, 'portada')}.png"
    # La 404 no se indexa ni tiene canónica: es la respuesta a una página que no existe.
    if indexar:
        indice = f'<link rel="canonical" href="{canon}">'
        og_url = f'<meta property="og:url" content="{canon}">\n'
    else:
        indice, og_url = '<meta name="robots" content="noindex">', ""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(tit)}</title>
<meta name="description" content="{escape(descripcion)}">
{indice}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Terrnova">
<meta property="og:title" content="{escape(tit)}">
<meta property="og:description" content="{escape(descripcion)}">
{og_url}<meta property="og:locale" content="es_CO">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{escape(tit)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{og}">
<meta name="theme-color" content="#F6F7F4">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/img/tipos/geist-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/img/tipos/geist-mono-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{version("/estilo.css")}">
<script src="{version("/js/sitio.js")}" defer></script>{mods}
</head>
<body>
<a class="saltar" href="#contenido">Saltar al contenido</a>
{encabezado(ruta)}
<main id="contenido">
{cuerpo.strip()}
</main>
{PIE}
</body>
</html>
"""


def portada(rotulo: str, titulo: str, entrada: str, extra: str = "", lado: str = "") -> str:
    clase = "envoltura con-lado" if lado else "envoltura"
    rot = f'<span class="rotulo">{rotulo}</span>' if rotulo else ""
    return f"""<section class="portada"><div class="{clase}"><div class="cab">
{rot}<h1 class="t1">{titulo}</h1><p class="entrada">{entrada}</p>{extra}
</div>{lado}</div></section>"""


# ---------------------------------------------------------------- figuras de portada (datos reales)
def lado_familias() -> str:
    tope = max(POR_FAMILIA.values())
    filas = "".join(
        f'<a class="fila" href="/fuentes?familia={f}"><span>{FAMILIAS[f]}</span>'
        f'<i style="--v:{n / tope:.3f}"></i><b>{n}</b></a>'
        for f, n in POR_FAMILIA.most_common()
        if f != "meta"
    )
    return f"""<figure class="lado-fig barras"><figcaption>Herramientas por familia</figcaption>{filas}
<p class="fuente-dato">catálogo de producción · {N_HERR} herramientas</p></figure>"""


def lado_tarifa() -> str:
    tope = max(TARIFA_CATALOGO.values())
    cols = "".join(
        f'<div class="col"><b>{TARIFA_CATALOGO[k]}</b><i style="--v:{TARIFA_CATALOGO[k] / tope:.3f}"></i>'
        f"<span>{t}</span></div>"
        for k, t, _, _ in TARIFA
    )
    return f"""<figure class="lado-fig escalera"><figcaption>Créditos por consulta</figcaption><div class="cols">{cols}</div>
<p class="fuente-dato">errores, caché y fuera de cobertura no descuentan</p></figure>"""


def lado_puertas() -> str:
    return """<figure class="lado-fig puertas"><figcaption>Dos puertas, un contrato</figcaption>
<div class="p"><span class="et">agentes</span><code>POST /mcp</code><small>MCP · streamable HTTP · perfiles por familia</small></div>
<div class="p"><span class="et">sistemas</span><code>POST /v1/co/&lt;familia&gt;/&lt;herramienta&gt;</code><small>REST · OpenAPI en /docs</small></div>
<div class="p uno"><span class="et">las dos</span><code>Authorization: Bearer rt_live_…</code><small>misma llave · respuesta rt/1</small></div></figure>"""


# Los sistemas que la gente reconoce, por entidad. Cada uno se valida contra los títulos de las
# fuentes del catálogo: si un sistema deja de estar, la construcción falla.
SISTEMAS = {
    "Colombia Compra Eficiente": ["SECOP I", "SECOP II", "SECOP Integrado", "Relatoría"],
    "IGAC": [
        "Catastro",
        "SINIC",
        "Valor del suelo",
        "Uso de las tierras",
        "Transacciones inmobiliarias",
    ],
    "DANE": [
        "Censo Nacional de Población y Vivienda 2018",
        "DIVIPOLA",
        "IPC",
        "GEIH",
        "Pobreza multidimensional",
        "PIB",
        "Exportaciones",
    ],
    "Centro Nacional de Memoria Histórica": ["SIEVCAC"],
    "IDEAM": ["Alertas", "SISAIRE", "Estaciones", "Normales climatológicas"],
    "Policía Nacional": ["Reporte de delitos"],
    "INVIMA": ["CUM", "Registros sanitarios"],
    "Supersociedades": ["Estados financieros NIIF", "10 000 empresas más grandes"],
    "Banco de la República": ["TRM", "DTF", "IBR", "UVR", "Tasa de política monetaria"],
    "ANI": ["Peajes", "Concesiones viales"],
    "Agencia Nacional de Tierras": [
        "Resguardos indígenas",
        "Consejos comunitarios",
        "Zonas de reserva campesina",
        "UAF",
    ],
    "CAR Cundinamarca": ["POMCA", "Rondas hídricas"],
    "Función Pública": ["SIGEP", "SUIT", "Gestor Normativo"],
    "Planeación de Bogotá": ["POT", "Estrato"],
    "ANH": ["Producción fiscalizada de crudo", "Gas", "Regalías"],
    "INVÍAS": ["Red vial nacional", "Puentes", "Peajes"],
    "Medicina Legal": ["Homicidios", "Suicidios", "Muertes accidentales"],
    "MinEducación": ["Estadísticas de educación"],
    "Unidad para las Víctimas": ["RUV"],
    "UPRA": ["EVA", "Precios comerciales de la tierra"],
    "ADRES": ["BDUA"],
    "Aerocivil": ["Pasajeros y carga", "Operaciones aéreas"],
    "Confecámaras": ["RUES"],
    "Corte Constitucional": ["Relatoría", "Sentencias"],
    "DIAN": ["Normograma"],
    "Supertransporte": ["Tráfico portuario", "Contenedores"],
    "ANM": ["RUCOM"],
    "CREG": ["Alejandría"],
    "DNP": ["Sistema General de Regalías"],
    "ESA WorldCover": ["WorldCover"],
    "ICFES": ["Saber 11"],
    "INS": ["IRCA"],
    "MinHacienda": ["Regalías"],
    "MinJusticia": ["SUIN-Juriscol"],
    "MinSalud": ["REPS"],
    "MinTIC": ["Internet fijo"],
    "Parques Nacionales": ["RUNAP"],
    "Presidencia": ["Descontamina Colombia"],
    "SIC": ["Sanciones"],
    "SINCHI": ["Pérdida de bosque"],
    "Superfinanciera": ["Entidades vigiladas"],
    "Supersolidaria": ["Sector solidario"],
    "Catastro de Bogotá": ["Valor de referencia del m²"],
    "UNGRD": ["Emergencias"],
    "Unidad de Restitución de Tierras": ["Restitución de tierras"],
    "USGS": ["Sismos"],
}


def sistemas_validados() -> dict[str, list[str]]:
    titulos: dict[str, str] = {}
    for f in PUBLICADAS:
        n = nombre_entidad(f.entidad)
        titulos[n] = titulos.get(n, "") + " " + f.titulo.casefold()
    assert set(SISTEMAS) == set(ENTIDADES), set(SISTEMAS) ^ set(ENTIDADES)
    for ent, sis in SISTEMAS.items():
        for x in sis:
            assert x.casefold() in titulos[ent], f"{ent}: «{x}» no está en sus fuentes"
    return SISTEMAS


def miles_en_texto(s: str) -> str:
    """«10 000» (como lo escriben algunos títulos del catálogo) → «10.000», en formato colombiano."""
    return re.sub(r"(?<!\d)(\d{1,3}) (\d{3})(?!\d)", r"\1.\2", s)


def y_lista(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]


def indice_fuentes() -> str:
    # Tamaño del nombre por número de fuentes (raíz cuadrada, para que las de una fuente se lean).
    sis = sistemas_validados()
    out = []
    for nom, n in sorted(ENTIDADES.items(), key=lambda x: (-x[1], x[0])):
        clase = ' class="glob"' if nom in GLOBALES else ""
        fuentes = "fuente" if n == 1 else "fuentes"
        out.append(
            f'<li{clase} style="--t:{17 + 4.2 * n**0.5:.1f}px"><h3>{escape(nom)}'
            f'<span class="sr">, </span><sup>{n}<span class="sr"> {fuentes}</span></sup></h3>'
            f"<p>{escape(miles_en_texto(y_lista(sis[nom])))}</p></li>"
        )
    return '<ul class="indice">' + "".join(out) + "</ul>"


# Lo que copia el botón «Copiar instrucción para tu agente».
INSTRUCCION = (
    "Conéctate al servidor MCP de Terrnova en https://terrnova.com/mcp/catalogo (transporte HTTP) con la "
    "cabecera «Authorization: Bearer» y mi llave, que está en la variable TERRNOVA_LLAVE. Úsalo "
    "para responder con datos oficiales de Colombia: predios, estadísticas, contratación pública, "
    "ambiente, justicia, empresas y normas. Cita la entidad y la licencia que vienen en "
    "«procedencia» y no confundas «no_encontrado» con un error de la fuente. Guía para agentes: "
    "https://terrnova.com/llms.txt"
)

# Tres respuestas reales de producción, recortadas, de familias distintas. La consola del héroe las reproduce por turnos.
TURNOS = [
    {
        "k": "predio",
        "boton": "Predio",
        "pregunta": "¿Qué predio hay en 11,2211 N, 74,1572 W?",
        "herr": "sinic_predio_en_punto",
        "filas": [
            ("estado", '<span class="ok">encontrado</span>'),
            ("predial", "4700101090000025808…"),
            ("destinación", "Habitacional, urbano"),
            ("entidad", "IGAC, SINIC"),
            ("licencia", "CC-BY-SA-4.0, uso comercial sí"),
            ("servido", "copia del 28-10-2026 en 0,56 s"),
        ],
        "huella": "sha256:7a2cc965…",
        "fecha": "29-10-2026",
    },
    {
        "k": "empresa",
        "boton": "Empresa",
        "pregunta": "¿La empresa con NIT 899999068 tiene la matrícula al día?",
        "herr": "rues_empresa_por_nit",
        "filas": [
            ("estado", '<span class="ok">encontrado</span>'),
            ("empresa", "ECOPETROL S A"),
            ("matrícula", "1291197, cámara de Bogotá"),
            ("situación", "ACTIVA, renovada en 2026"),
            ("entidad", "Confecámaras, RUES"),
            ("licencia", "CC-BY-SA-4.0, uso comercial sí"),
            ("servido", "fuente en vivo en 2,4 s"),
        ],
        "huella": "sha256:2acc04ec…",
        "fecha": "30-10-2026",
    },
    {
        "k": "norma",
        "boton": "Norma",
        "pregunta": "¿La Ley 1581 de 2012 sigue vigente?",
        "herr": "suin_norma",
        "filas": [
            ("estado", '<span class="ok">encontrado</span>'),
            ("norma", "Ley estatutaria 1581 de 2012"),
            ("vigencia", "Vigente"),
            ("expedida", "Congreso de Colombia, 30 artículos"),
            ("entidad", "MinJusticia, SUIN-Juriscol"),
            ("licencia", "CC-BY-SA-4.0, uso comercial sí"),
            ("servido", "fuente en vivo en 2,9 s"),
        ],
        "huella": "sha256:6fcc3fe7…",
        "fecha": "30-10-2026",
    },
]


def consola() -> str:
    ids = {h.id for h in HERR}
    pest, turnos = [], []
    for i, t in enumerate(TURNOS):
        assert t["herr"] in ids, t["herr"]
        sel = "true" if i == 0 else "false"
        pest.append(
            f'<button type="button" role="tab" id="c-p{i}" aria-controls="c-t{i}" aria-selected="{sel}"'
            f"{'' if i == 0 else ' tabindex="-1"'}><i></i>{t['boton']}</button>"
        )
        filas = "".join(f"<dt>{a}</dt><dd>{b}</dd>" for a, b in t["filas"])
        turnos.append(
            f'<div class="turno" role="tabpanel" id="c-t{i}" aria-labelledby="c-p{i}" data-k="{t["k"]}"{"" if i == 0 else " hidden"}>'
            f'<p class="preg"><span class="tu">Tu agente</span><span class="txt">{t["pregunta"]}</span></p>'
            f'<p class="llama"><span>llama a</span><code>{t["herr"]}</code></p>'
            f"<dl>{filas}</dl>"
            f'<p class="pie"><span>huella <b>{t["huella"]}</b></span><span class="sello">capturado el {t["fecha"]}</span></p></div>'
        )
    return (
        '<div class="consola" data-consola>'
        f'<div class="pest" role="tablist" aria-label="Respuestas capturadas">{"".join(pest)}</div>'
        + "".join(turnos)
        + "</div>"
    )


# Soluciones por sector, para quien decide: qué decide el área, lo que se construye encima (ilustrativo:
# lo posible, no clientes) y con qué entidades, sacadas de herramientas reales del catálogo (la
# construcción falla si alguna no existe o no se vende). Sin el DANE (decisión 4) ni las alertas del
# IDEAM (su copia se refresca a mano).
CAPAS = ("Datos", "Analítica", "Automatización", "Agentes")
SECTORES = [
    (
        "Banca y crédito",
        "Aprobar un crédito con la empresa y la garantía revisadas en la fuente.",
        [
            ("Analítica", "La empresa y el predio en garantía, revisados antes del crédito."),
            ("Automatización", "Aviso si un cliente cambia su matrícula mercantil."),
        ],
        [
            "rues_empresa_por_nit",
            "supersociedades_situacion_financiera",
            "igac_predio_en_punto",
            "upra_precio_tierra_en_punto",
        ],
    ),
    (
        "Contratación pública",
        "Adjudicar sabiendo qué contrató antes el proveedor y si tiene multas.",
        [
            ("Analítica", "Contratos, multas y sanciones de un contratista antes de adjudicar."),
            ("Agentes", "Un asistente que dice cuánto contrató el municipio y con quién."),
        ],
        [
            "secop_contratos_proveedor",
            "secop_sanciones_contrato",
            "secop_contratos_municipio",
            "dnp_proyectos_sgr_municipio",
        ],
    ),
    (
        "Legal y cumplimiento",
        "Firmar un concepto con la norma vigente y la sentencia que la interpreta.",
        [
            ("Agentes", "Conceptos que citan la norma vigente y la sentencia."),
            ("Automatización", "Aviso cuando cambia una norma que sigues."),
        ],
        [
            "suin_norma",
            "corte_constitucional_sentencia",
            "funcionpublica_normas_buscar",
            "sic_sanciones_por_sector",
        ],
    ),
    (
        "Agro y exportación",
        "Comprar a una finca sabiendo si toca un área protegida o un territorio étnico.",
        [
            (
                "Analítica",
                "Revisión ambiental por finca: áreas protegidas, territorios étnicos y, en la "
                "Amazonia, pérdida de bosque.",
            ),
            ("Automatización", "Revisión periódica de las fincas de tus proveedores."),
        ],
        [
            "pnn_areas_protegidas_en_punto",
            "ant_resguardos_en_punto",
            "sinchi_perdida_bosque_en_punto",
            "esa_cobertura_suelo_en_punto",
        ],
    ),
    (
        "Inmobiliario y construcción",
        "Ofertar por un lote sabiendo qué permite el POT y qué amenazas tiene.",
        [
            ("Analítica", "La ficha de un predio: catastro, POT, amenazas y valor del suelo."),
            ("Agentes", "Qué se puede construir en un lote de Bogotá, para el equipo comercial."),
        ],
        [
            "igac_predio_en_punto",
            "sdp_tratamiento_urbanistico_en_punto",
            "sdp_amenaza_movimiento_masa_en_punto",
            "igac_zona_geoeconomica_en_punto",
        ],
    ),
    (
        "Gobierno y territorio",
        "Priorizar la inversión de un municipio comparado con sus pares.",
        [
            ("Analítica", "Un tablero municipal comparado con sus pares."),
            ("Automatización", "Aviso cuando cambia un contrato o un proyecto de regalías."),
        ],
        [
            "men_educacion_municipio",
            "ins_calidad_agua_municipio",
            "policia_hurto_comercio_residencias_municipio",
            "dnp_proyectos_sgr_municipio",
        ],
    ),
]
SECTORES_USADAS = [i for *_, ids in SECTORES for i in ids]


def sectores() -> str:
    por_id = {h.id: h for h in HERR}
    assert all(c in CAPAS for _, _, sols, _ in SECTORES for c, _ in sols)
    pest, paneles = [], []
    for i, (nombre, decide, sols, ids) in enumerate(SECTORES):
        assert all(h in por_id for h in ids), f"{nombre}: herramienta que no se vende"
        ents = list(
            dict.fromkeys(nombre_entidad(CAT.fuentes[por_id[h].fuente].entidad) for h in ids)
        )
        assert not any("DANE" in e for e in ents), nombre
        sel = "true" if i == 0 else "false"
        pest.append(
            f'<button type="button" role="tab" id="s-p{i}" aria-controls="s-t{i}" aria-selected="{sel}"'
            f"{'' if i == 0 else ' tabindex="-1"'}>{nombre}</button>"
        )
        filas = "".join(
            f'<li><span class="rotulo">{c}</span><p>{escape(s)}</p></li>' for c, s in sols
        )
        paneles.append(
            f'<div class="panel-s" role="tabpanel" id="s-t{i}" aria-labelledby="s-p{i}" '
            f'data-herramientas="{" ".join(ids)}"{"" if i == 0 else " hidden"}>'
            f'<h3 class="decide">{con_sello(escape(decide))}</h3>'
            f'<ul class="soluciones">{filas}</ul>'
            f'<p class="con-s">Con datos de {escape(y_lista(ents))}</p></div>'
        )
    return f"""<div class="sectores">
<div class="lista-s" role="tablist" aria-label="Sectores" aria-orientation="vertical">{"".join(pest)}</div>
<div>{"".join(paneles)}</div>
</div>"""


# Lo que cruza la revisión de una lista, por tipo de ítem: herramientas reales del catálogo.
CRUCES = [
    (
        "Predios y parcelas",
        [
            ("pnn_areas_protegidas_en_punto", "Áreas protegidas (RUNAP)"),
            ("sinchi_perdida_bosque_en_punto", "Pérdida de bosque"),
            ("ant_resguardos_en_punto", "Resguardos indígenas"),
            ("igac_predio_en_punto", "Predio en el catastro"),
        ],
    ),
    (
        "Empresas y proveedores",
        [
            ("rues_empresa_por_nit", "Registro mercantil (RUES)"),
            ("supersociedades_situacion_financiera", "Estados financieros"),
            ("superfinanciera_vigilada_por_nit", "Vigilancia de la Superfinanciera"),
            ("rues_establecimientos_por_nit", "Establecimientos de comercio (RUES)"),
        ],
    ),
    (
        "Contratos de SECOP II",
        [
            ("secop_contrato_por_id", "Contrato (SECOP II)"),
            ("secop_sanciones_contrato", "Multas y sanciones"),
            ("secop_modificaciones_contrato", "Modificaciones"),
            ("secop_pagos_contrato", "Pagos"),
        ],
    ),
]

# Los servicios: qué hace, qué recibes y con qué fuentes. La portada muestra el título y la frase;
# /servicios, además, lo que recibes.
SERVICIOS = [
    {
        "id": "revision",
        "titulo": "Debida diligencia",
        "texto": "Revisamos tu lista de predios, empresas o contratos contra las fuentes oficiales. Recibes un expediente por ítem.",
        "recibes": [
            "Un expediente por ítem: cada hallazgo con su entidad, su fecha y la huella de la respuesta",
            "Los casos dudosos, aparte, para que los revise una persona",
            "El formato se acuerda por proyecto: hoja de cálculo, GeoJSON o el de tu sistema",
        ],
        "con": "revision",
        "asunto": "debida-diligencia",
        "boton": "Pide una revisión",
    },
    {
        "id": "tablero",
        "titulo": "Tableros e informes",
        "texto": "Los indicadores que sigues, actualizados desde la fuente y comparables entre municipios.",
        "recibes": [
            "Los indicadores que eliges, comparados con municipios pares",
            "Cada cifra con su entidad y su fecha de corte",
            "Dónde se publica y cada cuánto se actualiza, se acuerda por proyecto",
        ],
        "con": "tablero",
        "asunto": "tablero",
        "boton": "Pide tu tablero",
    },
    {
        "id": "vigilancia",
        "titulo": "Vigilancia y alertas",
        "texto": "Te avisamos cuando cambia un contrato, una norma o una sanción que sigues.",
        "recibes": [
            "Un aviso por correo o en tu sistema cuando cambia lo que sigues",
            "El registro de cada cambio, con fecha y fuente",
            "Qué se vigila y cada cuánto, se acuerda por proyecto",
        ],
        "con": "vigilancia",
        "asunto": "vigilancia",
        "boton": "Pide tus alertas",
    },
    {
        "id": "asistente",
        "titulo": "Asistentes a la medida",
        "texto": "Un asistente que responde con datos oficiales dentro de tu sistema y cita la fuente.",
        "recibes": [
            "El asistente en tu entorno",
            "Conectado a las fuentes de tu equipo",
            "Cada respuesta con su fuente y su licencia",
        ],
        "con": "asistente",
        "asunto": "asistente",
        "boton": "Cuéntanos tu idea",
    },
]


def licencia_corta(spdx: str | None) -> str:
    if not spdx:
        return "licencia por verificar"
    if spdx.startswith("CC-"):
        return (
            spdx.replace("-", " ").replace("CC BY SA", "CC BY-SA").replace("CC BY ND", "CC BY-ND")
        )
    return {
        "LicenseRef-banrep-aviso-legal": "aviso legal del Banco",
        "LicenseRef-dane-terminos": "términos del DANE",
    }.get(spdx, "licencia propia de la entidad")


# Ilustrativo: valor de tu municipio, franja de los comparables y serie, por indicador (0 a 1 en la
# escala del reloj). Los indicadores y sus entidades son del catálogo, y cada fuente publica una
# serie (año por año o por periodo): sin serie no hay tendencia que dibujar.
CIFRAS_TABLERO = [
    (0.72, (0.55, 0.85), (0.58, 0.61, 0.63, 0.62, 0.66, 0.68, 0.70, 0.72)),
    (0.30, (0.18, 0.48), (0.52, 0.47, 0.44, 0.40, 0.38, 0.35, 0.31, 0.30)),
    (0.56, (0.42, 0.66), (0.48, 0.50, 0.49, 0.52, 0.51, 0.54, 0.55, 0.56)),
    (0.64, (0.35, 0.70), (0.38, 0.42, 0.40, 0.47, 0.52, 0.55, 0.60, 0.64)),
]

# Ilustrativo: en qué fuente aparece algo que revisar, por tipo (predio, empresa, contrato).
HALLAZGO_REVISION = [1, None, 1]

# Lo que muestran las figuras de los servicios sale del catálogo: herramientas, entidades y licencias reales.
TIPOS_REVISION = {
    "Predios y parcelas": ("Predio", "por coordenada"),
    "Empresas y proveedores": ("Empresa", "por NIT"),
    "Contratos de SECOP II": ("Contrato", "por id de SECOP II"),
}
# Cada «como» exige el tipo de entrada que de verdad recibe la herramienta (datos_servicio lo comprueba).
ENTRADA_REVISION = {
    "por coordenada": {"lon", "lat"},
    "por NIT": "nit_empresa",
    "por id de SECOP II": "id_secop",
}
# Sin el DANE (sin base legal para venderlo en servicios) ni las alertas del IDEAM (su copia se
# refresca a mano): preguntas de fuentes en vivo o con su fecha de corte.
PREGUNTAS_ASISTENTE = [
    "suin_norma",
    "ins_calidad_agua_municipio",
    "pnn_areas_protegidas_en_punto",
    "secop_contratos_municipio",
    "rues_empresa_por_nit",
    "igac_predio_en_punto",
    "upra_precio_tierra_rural_municipio",
    "men_educacion_municipio",
]
# La pregunta de cada una, corta, para que la lectura quepa en una línea (la entera va en la etiqueta).
PREGUNTA_CORTA = {
    "suin_norma": "¿Sigue vigente esta ley?",
    "ins_calidad_agua_municipio": "¿Es potable el agua aquí?",
    "pnn_areas_protegidas_en_punto": "¿Hay un área protegida aquí?",
    "secop_contratos_municipio": "¿Cuánto contrata este municipio?",
    "rues_empresa_por_nit": "¿Qué dice el RUES de esta empresa?",
    "igac_predio_en_punto": "¿Qué predio hay aquí?",
    "upra_precio_tierra_rural_municipio": "¿Cuánto vale la tierra aquí?",
    "men_educacion_municipio": "¿Cómo va la educación aquí?",
}
# Sigla grabada en la placa de cada boca del tablero del asistente (las que no están, van con su nombre).
SIGLA_ENTIDAD = {
    "Parques Nacionales": "PNN",
    "Colombia Compra Eficiente": "CCE",
    "Policía Nacional": "Policía",
}
OTRAS_ASISTENTE = [
    "reps_sedes_municipio",
    "invima_registro_sanitario_por_expediente",
    "anh_crudo_municipio",
    "policia_hurto_vehiculos_municipio",
]
CARRILES_VIGILANCIA = [
    ("SECOP II", "Colombia Compra Eficiente", "Nuevo contrato de una entidad que vigilas"),
    ("SUIN-Juriscol", "MinJusticia", "Cambió una norma que sigues"),
    ("SECOP I", "Colombia Compra Eficiente", "Nueva multa a un contratista que sigues"),
    ("SIC", "SIC", "Nueva sanción en el sector que sigues"),
]
# Indicadores con serie publicada por su entidad (sin el DANE): herramienta, nombre y qué serie es.
INDICADORES_TABLERO = [
    ("men_educacion_municipio", "Educación", "cobertura neta, año por año"),
    ("ins_calidad_agua_municipio", "Agua potable", "riesgo del agua (IRCA), año por año"),
    (
        "policia_hurto_comercio_residencias_municipio",
        "Seguridad",
        "hurtos a comercio y residencias, año por año",
    ),
    ("igac_compraventas_municipio", "Compraventas", "compraventas de inmuebles, año por año"),
]


def datos_servicio(tipo: str) -> object:
    por_id = {h.id: h for h in HERR}

    def entidad(hid: str) -> str:
        return nombre_entidad(CAT.fuentes[por_id[hid].fuente].entidad)

    if tipo == "revision":
        for g, items in CRUCES:
            pide = ENTRADA_REVISION[TIPOS_REVISION[g][1]]
            for i, _ in items:
                tipos = (
                    set(por_id[i].entrada)
                    if isinstance(pide, set)
                    else set(por_id[i].entrada.values())
                )
                assert (pide <= tipos) if isinstance(pide, set) else (pide in tipos), (
                    f"{i} no va {TIPOS_REVISION[g][1]}"
                )
        return [
            {
                "tipo": TIPOS_REVISION[g][0],
                "como": TIPOS_REVISION[g][1],
                "fuentes": [{"t": t, "e": entidad(i)} for i, t in items],
            }
            for g, items in CRUCES
        ]
    if tipo == "asistente":
        preguntas = []
        for i in PREGUNTAS_ASISTENTE:
            f = CAT.fuentes[por_id[i].fuente]
            preguntas.append(
                {
                    "p": por_id[i].pregunta,
                    "corta": PREGUNTA_CORTA[i],
                    "e": entidad(i),
                    "l": licencia_corta(f.licencia.spdx),
                }
            )
        nodos = list(
            dict.fromkeys([p["e"] for p in preguntas] + [entidad(i) for i in OTRAS_ASISTENTE])
        )
        siglas = [SIGLA_ENTIDAD.get(e, e) for e in nodos]
        assert all(len(x) <= 12 for x in siglas), siglas
        return {"preguntas": preguntas, "nodos": nodos, "siglas": siglas}
    if tipo == "vigilancia":
        sistemas = sistemas_validados()
        for s, e, _ in CARRILES_VIGILANCIA:
            assert s == e or s in sistemas[e], f"{s} no es un sistema de {e}"
        return [{"s": s, "e": e, "ev": ev} for s, e, ev in CARRILES_VIGILANCIA]
    if tipo == "tablero":
        return [{"t": t, "e": entidad(i), "m": m} for i, t, m in INDICADORES_TABLERO]
    return None


# ---------------------------------------------------------------- figuras isométricas (Anatomy)
# Dos figuras de la portada dibujadas con el kit de Anatomy (web/figuras/kit, MIT). Este archivo
# escribe lo que muestran (web/figuras/datos.json, todo del catálogo) y `node
# web/figuras/construir.mjs` dibuja los SVG; aquí se incrustan. La huella de los datos va en cada SVG:
# si el catálogo cambia y el dibujo no, la construcción falla.
FIGURAS = RAIZ / "figuras"
# Lo que se monta sobre la capa de datos y por qué puerta entra (lado_puertas: agentes por MCP,
# sistemas por REST).
MODULOS = [
    ("Analítica", "REST", "cruces, revisiones y tableros"),
    ("Automatización", "REST", "vigilancias, alertas y reportes"),
    ("Agentes", "MCP", "asistentes que citan la fuente"),
]
# La ruta de una pregunta: tres herramientas reales de familias distintas.
RUTA = ["igac_predio_en_punto", "secop_contratos_entidad", "pnn_areas_protegidas_en_punto"]
# La pregunta de cada turno, corta, para que la lectura quepa en una línea (la entera va en la etiqueta).
RUTA_CORTA = {
    "igac_predio_en_punto": "¿Qué predio hay aquí?",
    "secop_contratos_entidad": "¿Cuánto contrata?",
    "pnn_areas_protegidas_en_punto": "¿Área protegida aquí?",
}
SERVIDO = {"en_vivo": "la fuente, en vivo", "copia": "una copia del archivo oficial"}
# Herramientas cuyo canario no está en verde en producción (01-11-2026): siguen en el catálogo, pero
# ninguna página ni figura las usa de ejemplo. Si una vuelve a verde, se puede sacar de aquí.
SIN_CANARIO_VERDE = {
    "banrep_dtf_recientes",
    "banrep_ibr_recientes",
    "banrep_tasa_politica_recientes",
    "banrep_trm_recientes",
    "banrep_uvr_recientes",
    "secop1_modificaciones_adjudicacion",
    "dian_normograma_buscar",
    "icfes_saber11_municipio",
    "icfes_saber11_estrato_municipio",
    "ideam_alertas_deslizamiento_municipio",
    "ideam_alertas_incendios_municipio",
    "ideam_calidad_aire_municipio",
    "invias_puentes_en_zona",
    "urt_microzona_en_punto",
}


# Cobertura SINIC: la muestra del 3 % (datos/co.json, hexágonos de 0,07°) se suma en hexágonos tres
# veces más grandes para que el dibujo quepa; las ciudades son para la lectura, no se rotulan.
CO_JSON = PUBLICO / "datos" / "co.json"
FACTOR_COBERTURA = 3
CIUDADES = [
    ("Bogotá", -74.08, 4.61),
    ("Medellín", -75.57, 6.25),
    ("Cali", -76.53, 3.45),
    ("Barranquilla", -74.80, 10.96),
    ("Cartagena", -75.51, 10.39),
    ("Santa Marta", -74.20, 11.24),
    ("Bucaramanga", -73.12, 7.12),
    ("Cúcuta", -72.50, 7.89),
    ("Pereira", -75.69, 4.81),
    ("Ibagué", -75.23, 4.44),
    ("Villavicencio", -73.63, 4.14),
    ("Montería", -75.88, 8.75),
]


def datos_cobertura() -> dict:
    import math

    co = json.loads(CO_JSON.read_text(encoding="utf-8"))
    r = round(co["R"] * FACTOR_COBERTURA, 4)
    lon0, lat0 = -74.6, 6.4

    def axial(lon: float, lat: float) -> tuple[int, int]:
        x = (lon - lon0) / (r * math.sqrt(3))
        fr = (lat - lat0) / (1.5 * r)
        fq = x - fr / 2
        cx, cz = fq, fr
        cy = -cx - cz
        rx, ry, rz = round(cx), round(cy), round(cz)
        dx, dy, dz = abs(rx - cx), abs(ry - cy), abs(rz - cz)
        if dx > dy and dx > dz:
            rx = -ry - rz
        elif dy > dz:
            ry = -rx - rz
        else:
            rz = -rx - ry
        return rx, rz

    def centro(q: int, s: int) -> list[float]:
        return [round(lon0 + r * math.sqrt(3) * (q + s / 2), 4), round(lat0 + 1.5 * r * s, 4)]

    celdas: dict[tuple[int, int], int] = {}
    for lon, lat, n in co["bins"]:
        k = axial(lon, lat)
        celdas[k] = celdas.get(k, 0) + n
    tierra = {axial(lon, lat) for lon, lat in co["land"]} | set(celdas)
    return {
        "R": r,
        "celdas": [[*centro(*k), n] for k, n in sorted(celdas.items())],
        "tierra": [centro(*k) for k in sorted(tierra)],
        "ciudades": [list(c) for c in CIUDADES],
        "total": sum(n for *_, n in co["bins"]),
    }


def datos_figuras() -> dict:
    por_id = {h.id: h for h in HERR}
    turnos = []
    for hid in RUTA:
        h = por_id[hid]
        f = CAT.fuentes[h.fuente]
        turnos.append(
            {
                "herramienta": h.id,
                "pregunta": h.pregunta,
                "entidad": nombre_entidad(f.entidad),
                "licencia": licencia_corta(f.licencia.spdx),
                "servido": SERVIDO[f.modo],
                "corta": RUTA_CORTA[hid],
            }
        )
    nombradas = {t["entidad"] for t in turnos}
    assert len(nombradas) == len(turnos), "cada turno va a una entidad distinta"
    ejemplos = set(RUTA + SECTORES_USADAS + PREGUNTAS_ASISTENTE + OTRAS_ASISTENTE)
    ejemplos |= {i for i, _, _ in INDICADORES_TABLERO} | {t["herr"] for t in TURNOS}
    ejemplos |= {i for _, items in CRUCES for i, _ in items} | {t[3] for t in TARIFA}
    ejemplos.add(EJEMPLO["herramienta"])
    assert not ejemplos & SIN_CANARIO_VERDE, ejemplos & SIN_CANARIO_VERDE
    return {
        "capas": {
            "fuentes": N_FUENTES,
            "herramientas": N_HERR,
            "familias": [[FAMILIAS[f], n] for f, n in POR_FAMILIA.most_common() if f != "meta"],
            "modulos": [{"nombre": n, "puerta": p, "que": q} for n, p, q in MODULOS],
        },
        "ruta": {
            "turnos": [{**t, "fuentes": ENTIDADES[t["entidad"]]} for t in turnos],
            # Las demás entidades van sin nombre: solo cuántas fuentes publica cada una.
            "otras": sorted((n for e, n in ENTIDADES.items() if e not in nombradas), reverse=True),
        },
        "prueba": {"capas": [{"campo": c, "valor": v} for c, v, _ in CAPAS_PRUEBA]},
        # Los tipos y sus fuentes son los del catálogo; qué estación encuentra algo es ilustrativo.
        "revision": {"tipos": datos_servicio("revision"), "hallazgo": HALLAZGO_REVISION},
        # Los sistemas vigilados salen del catálogo (validados en datos_servicio); lo que cambia, no.
        "vigilancia": {"carriles": datos_servicio("vigilancia")},
        "asistente": datos_servicio("asistente"),
        "cobertura": datos_cobertura(),
        "usadas": {
            "ruta": RUTA,
            "prueba": [EJEMPLO["herramienta"]],
            "revision": [i for _, items in CRUCES for i, _ in items],
            "tablero": [i for i, _, _ in INDICADORES_TABLERO],
            "asistente": PREGUNTAS_ASISTENTE + OTRAS_ASISTENTE,
        },
        "tablero": {
            "indicadores": [
                {
                    "t": t,
                    "e": nombre_entidad(CAT.fuentes[por_id[hid].fuente].entidad),
                    "m": medida,
                    "valor": v,
                    "comparables": list(c),
                    "serie": list(serie),
                }
                for (hid, t, medida), (v, c, serie) in zip(
                    INDICADORES_TABLERO, CIFRAS_TABLERO, strict=True
                )
            ]
        },
    }


def datos_figuras_json() -> str:
    return json.dumps(datos_figuras(), ensure_ascii=False, indent=1) + "\n"


def huella_figuras() -> str:
    """Huella de lo que decide el dibujo: los datos, los scripts que dibujan, el kit y la hoja
    del sitio (la capa fija lleva dentro sus reglas)."""
    import hashlib

    h = hashlib.sha256(datos_figuras_json().encode("utf-8"))
    scripts = sorted(f.name for f in FIGURAS.glob("*.mjs"))
    for f in [*scripts, "kit/iso-kit.mjs", "../publico/estilo.css"]:
        h.update((FIGURAS / f).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:12]


SVG_FIGURAS = PUBLICO / "img" / "figuras"
NOMBRES_FIGURAS = (
    "capas",
    "ruta",
    "prueba",
    "revision",
    "tablero",
    "vigilancia",
    "asistente",
    "cobertura",
)
# La ruta y la prueba ya no van en ninguna página (la portada las cuenta en 3D, js/fig-*.js): las
# siguen usando las imágenes para compartir (web/og.py), por eso se siguen construyendo.
FIGURAS_SOLO_OG = ("ruta", "prueba")


def figura(
    nombre: str, lectura: str, pista: str = "", clase: str = "", ilustrativo: bool = False
) -> str:
    """Una figura integrada en la sección: sin marco, con su lectura en una línea debajo.

    El SVG vive aparte (web/publico/img/figuras) en dos archivos: la capa fija, que va como <img>,
    y la viva, que figuras.js pone encima en línea cuando la figura se acerca a la vista; el hueco ya
    tiene su proporción, así la página no salta."""
    svg = (SVG_FIGURAS / f"{nombre}.svg").read_text(encoding="utf-8")
    huella = re.search(r'data-datos="([0-9a-f]{12})"', svg)
    if not huella or huella.group(1) != huella_figuras():
        raise SystemExit(
            f"La figura {nombre}.svg no está al día con el catálogo: corre "
            "uv run python web/construir.py (escribe web/figuras/datos.json) y luego "
            "node web/figuras/construir.mjs"
        )
    caja = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    etiqueta = re.search(r'aria-label="([^"]*)"', svg)
    assert caja and etiqueta, nombre
    w, h = caja.groups()
    # la capa fija va en trozos (cada uno una imagen): nombre.svg, nombre-2.svg…
    trozos = re.search(r'data-trozos="(\d+)"', svg)
    assert trozos, nombre
    v = huella.group(1)
    fijas = ",".join(
        f"/img/figuras/{nombre}{f'-{i}' if i > 1 else ''}.svg?v={v}"
        for i in range(1, int(trozos.group(1)) + 1)
    )
    pista_html = f'<span class="pista">{pista}</span>' if pista else ""
    # el sello va al final de la lectura (la lectura cambia; el sello se queda en su sitio)
    sello = SELLO_I if ilustrativo else ""
    return (
        f'<figure class="fig-iso{" " + clase if clase else ""}" data-figura="{nombre}">'
        f'<div class="lienzo" tabindex="0" role="group" aria-label="{etiqueta.group(1)}" '
        f'data-src="{fijas}" '
        f'data-viva="/img/figuras/{nombre}-viva.svg?v={huella.group(1)}" style="aspect-ratio:{w}/{h}"></div>'
        f'<figcaption class="lectura-l"><span class="lin"><span data-lectura aria-live="off">{lectura}</span>{sello}</span>{pista_html}</figcaption>'
        "</figure>"
    )


def figura_capas() -> str:
    d = datos_figuras()["capas"]
    return figura(
        "capas",
        f"datos · {d['fuentes']} fuentes · {d['herramientas']} herramientas",
        "pasa el puntero por los módulos",
    )


LECTURA_SERVICIO = {
    "revision": ("predio · por coordenada · 4 fuentes", "flechas: otro tipo"),
    "tablero": (
        "{t} · {e} · {m} · tu municipio frente a sus comparables",
        "pasa el puntero por los relojes",
    ),
    "vigilancia": (
        "SECOP II · Colombia Compra Eficiente · nuevo contrato de una entidad que vigilas",
        "flechas: otro cambio",
    ),
}


def con_sello(texto: str) -> str:
    """El sello «ilustrativo» al final de un título, pegado a su última palabra (no queda solo en
    un renglón)."""
    cabeza, _, ultima = texto.rpartition(" ")
    return f'{cabeza} <span class="pegado">{ultima} {SELLO_I}</span>'.lstrip()


def figura_servicio(sid: str, sello: bool = True) -> str:
    """La figura de un servicio; vacía si todavía no tiene (la fila queda a una columna). Sin
    sello cuando el título que la acompaña ya lo lleva (la franja de la portada)."""
    if sid not in NOMBRES_FIGURAS:
        return ""
    if sid == "asistente":  # preguntas, entidades y licencias reales: sin sello
        q = datos_figuras()["asistente"]["preguntas"][0]
        lectura = f"{escape(q['corta'])} → {q['e']}"
        return figura(sid, lectura, "pasa el puntero por las tomas")
    lectura, pista = LECTURA_SERVICIO[sid]
    if sid == "tablero":
        i0 = datos_figuras()["tablero"]["indicadores"][0]
        lectura = lectura.format(t=i0["t"].lower(), e=i0["e"], m=i0["m"])
    return figura(sid, lectura, pista, ilustrativo=sello)


def con_datos(sid: str) -> str:
    """Las entidades que usa la figura de un servicio, del catálogo (todas publicadas)."""
    d = datos_figuras()
    if sid == "revision":
        ents = [f["e"] for t in d["revision"]["tipos"] for f in t["fuentes"]]
    elif sid == "tablero":
        ents = [x["e"] for x in d["tablero"]["indicadores"]]
    elif sid == "vigilancia":
        ents = [c["e"] for c in d["vigilancia"]["carriles"]]
    else:  # el asistente: las entidades de su tablero (sin el DANE, decisión 4)
        ents = d["asistente"]["nodos"]
    return y_lista(list(dict.fromkeys(ents)))


def servicio_fila(s: dict, i: int) -> str:
    """Un servicio en /servicios: título, frase, lo que recibes y su figura, alternando el lado."""
    recibes = "".join(f"<li>{x}</li>" for x in s["recibes"])
    pie = (
        f'<ul class="lista">{recibes}</ul><p class="con">Con datos de {con_datos(s["con"])}</p>'
        f'<a class="boton s" href="/contacto?asunto={s["asunto"]}">{s["boton"]}</a>'
    )
    tit = f'<h2 class="t2">{s["titulo"]}</h2>'
    fig = figura_servicio(str(s["id"]))
    clase = (" con-fig" + (" inv-l" if i % 2 else "")) if fig else ""
    return (
        f'<article class="serv{clase}" id="{s["id"]}">'
        f'<div class="cab">{tit}<p class="entrada">{s["texto"]}</p>{pie}</div>'
        f"{fig}</article>"
    )


# Las capas de la prueba: la respuesta real del predio de Santa Marta (correos.EJEMPLO, la misma
# del héroe y de /desarrolladores), comprobada contra EJEMPLO.
CAPAS_PRUEBA = [
    ("dato", "predio 47001…0308, habitacional", "Santa Marta, zona urbana · encontrado"),
    ("procedencia", "IGAC, SINIC", "la entidad que publica el dato"),
    ("licencia", "CC BY-SA 4.0, uso comercial sí", "verificada para esta fuente"),
    ("servido_desde", "copia del 28-10-2026", "la copia oficial, con su fecha"),
    ("huella", "sha256:7a2cc965…", "para comprobar que no cambió"),
]
assert EJEMPLO["herramienta"] == "sinic_predio_en_punto" and EJEMPLO["estado"] == "encontrado"
assert EJEMPLO["predio"].startswith("47001") and EJEMPLO["predio"].endswith("0308")
assert EJEMPLO["destinacion"].casefold().startswith("habitacional")
assert EJEMPLO["entidad"].startswith("Instituto Geográfico Agustín Codazzi (IGAC), SINIC")
assert EJEMPLO["licencia"] == "CC-BY-SA-4.0" and EJEMPLO["servido"] == CAPAS_PRUEBA[3][1]
assert EJEMPLO["huella"].startswith(CAPAS_PRUEBA[4][1].rstrip("…"))
NOTAS_PRUEBA = [
    ("El dato", "Encontrado, no encontrado o fuera de cobertura."),
    ("Quién lo publica", "La entidad, la consulta y la norma."),
    (
        "Licencia",
        f"Revisada por fuente: {N_VERIFICADAS} verificadas, {N_FUENTES - N_VERIFICADAS} con aviso.",
    ),
    ("De dónde salió", "En vivo o de una copia oficial, con su fecha."),
    ("Huella", "Para comprobar en una auditoría que no cambió."),
]


def pesos(n: int) -> str:
    return f"${miles(n)}"


def plan_boton(clave: str) -> str:
    return f'<a class="boton s" href="/contacto?asunto=plan-{clave}">Pedir este plan</a>'


def planes_html() -> str:
    """Los cuatro planes de la portada: precio al mes, créditos y el botón para pedirlo."""
    filas = "".join(
        f'<div class="plan"><h3>{n}</h3><b>{pesos(mes)}</b><span>al mes + IVA</span>'
        f'<span class="cr">{miles(NIVELES[k])} créditos<small>≈ {miles(NIVELES[k] // TARIFA_CATALOGO["punto"])} consultas de predio</small></span>'
        f"{plan_boton(k)}</div>"
        for k, n, mes, _ in PLANES
    )
    return f'<div class="planes">{filas}</div>'


def tabla_planes() -> str:
    """/precios: precio al mes y al año, créditos y cuánto alcanza en las consultas más comunes."""
    punto, registro = TARIFA_CATALOGO["punto"], TARIFA_CATALOGO["registro"]
    filas = "".join(
        f'<tr><th scope="row">{n}</th><td class="n" data-et="Al mes">{pesos(mes)}</td>'
        f'<td class="n" data-et="Al año">{pesos(anual)}</td>'
        f'<td class="n" data-et="Créditos al mes">{miles(NIVELES[k])}</td>'
        f'<td class="alc" data-et="Alcanza para">{miles(NIVELES[k] // punto)} predios o {miles(NIVELES[k] // registro)} empresas por NIT</td>'
        f'<td class="ped">{plan_boton(k)}</td></tr>'
        for k, n, mes, anual in PLANES
    )
    return f"""<div class="desliza"><table class="tabla t-planes"><caption class="sr">Planes de Terrnova, en pesos colombianos más IVA</caption>
<thead><tr><th scope="col">Plan</th><th scope="col">Al mes</th><th scope="col">Al año (20 % menos)</th><th scope="col">Créditos al mes</th><th scope="col">Alcanza para</th><th scope="col"><span class="sr">Pedir</span></th></tr></thead>
<tbody>{filas}</tbody></table></div>"""


def tarifa_html() -> str:
    """Créditos por tipo de pregunta y cuántas consultas de cada tipo trae cada plan."""
    cab = "".join(f'<th scope="col">{n}</th>' for _, n, _, _ in PLANES)
    filas = []
    for k, t, ej, _ in TARIFA:
        c = TARIFA_CATALOGO[k]
        celdas = "".join(f'<td class="n">{miles(NIVELES[p] // c)}</td>' for p, *_ in PLANES)
        filas.append(
            f'<tr><th scope="row">{t}<small>{ej}</small></th><td class="n">{c}</td>{celdas}</tr>'
        )
    return f"""<div class="desliza"><table class="tabla t-tarifa"><caption class="sr">Créditos por tipo de consulta y consultas al mes por plan</caption>
<thead><tr><th scope="col">Consulta</th><th scope="col">Créditos</th>{cab}</tr></thead>
<tbody>{"".join(filas)}<tr><th scope="row">la ficha de un lugar<small>varias fuentes en una respuesta</small></th><td class="n">≤ {TOPE_FICHA}</td><td colspan="4">la suma de sus partes</td></tr></tbody></table></div>"""


def chips_familias(como_boton=False) -> str:
    out = []
    for f, n in POR_FAMILIA.most_common():
        if f == "meta":
            continue
        if como_boton:
            out.append(
                f'<button class="chip" type="button" data-familia="{f}">{FAMILIAS[f]} <b>{n}</b></button>'
            )
        else:
            out.append(f'<a class="chip" href="/fuentes?familia={f}">{FAMILIAS[f]} <b>{n}</b></a>')
    return '<div class="chips">' + "".join(out) + "</div>"


# ---------------------------------------------------------------- páginas
INSPOW = "Inspow, nuestro aliado de facturación,"
# Clientes con guía probada en /desarrolladores (docs/CLIENTES.md); los que piden OAuth, dichos aparte.
FUNCIONA_CON = ["Claude Code", "Cursor", "Claude Desktop"]
PIDEN_OAUTH = ["claude.ai", "ChatGPT en la web"]

# Las preguntas de quien decide. Las respuestas salen del código: el contrato rt/1 (estado,
# procedencia, huella), la caché (ADR-0008, hasta RETENCION_S como respaldo «obsoleto»), la medición
# (medicion.py guarda herramienta, créditos, resultado y hora; no la entrada) y la ADR-0014.
RETENCION_DIAS = RETENCION_S // 86_400


def preguntas_frecuentes() -> list[tuple[str, str]]:
    return [
        (
            "¿Necesito un equipo técnico?",
            "No. Si tu organización no tiene analistas ni desarrolladores, construimos la solución "
            "y te la entregamos donde ya trabajas. Si tu equipo ya programa, conecta sus sistemas o "
            'sus agentes siguiendo la <a class="enlace" href="/desarrolladores">guía</a>.',
        ),
        (
            "¿Sirve para cumplimiento y auditoría?",
            "Cada respuesta dice qué entidad publica el dato, con qué licencia, de qué fecha y "
            "trae una huella para comprobar después que no cambió. No reemplaza un certificado "
            "que expide la entidad.",
        ),
        (
            "¿Qué tan actualizado está?",
            f"{MODOS['en_vivo']} fuentes se consultan en vivo y {MODOS['copia']} desde una copia "
            "oficial con su fecha de corte. Cada respuesta dice de dónde salió y un dato viejo "
            'llega con aviso. Cada fuente se prueba a diario: <a class="enlace" href="/estado">'
            "estado</a>.",
        ),
        (
            "¿Y si la fuente oficial se cae?",
            "Te decimos «no se pudo», con el motivo; nunca lo disfrazamos de «no encontrado». Si "
            f"hay una respuesta de los últimos {RETENCION_DIAS} días, llega marcada como vieja y "
            "con su fecha.",
        ),
        (
            "¿Qué licencia tiene cada dato?",
            f"La de su entidad, revisada fuente por fuente: {N_VERIFICADAS} verificadas y "
            f"{N_FUENTES - N_VERIFICADAS} como dato público, con aviso. Cada respuesta trae la "
            'atribución que debes citar. <a class="enlace" href="/fuentes#licencias">Ver las '
            "licencias</a>.",
        ),
        (
            "¿Guardan lo que pregunto?",
            "Para tu saldo guardamos qué herramienta usó tu llave, lo que costó, su resultado y la "
            "hora; lo que preguntaste no queda ligado a tu llave. Nada se busca por cédula ni por "
            "nombre. "
            '<a class="enlace" href="/privacidad">Privacidad</a>.',
        ),
        (
            "¿Cómo se paga?",
            f"Pides el plan e {INSPOW} te factura por mes o por año, con factura electrónica. No "
            "hay cobro automático.",
        ),
        (
            "¿Funciona con los asistentes de mi equipo?",
            "Con los que se conectan por MCP con una llave; la "
            '<a class="enlace" href="/desarrolladores">guía para desarrolladores</a> dice cuáles '
            "están probados. Los que piden un inicio de sesión (OAuth) todavía no: llegará.",
        ),
    ]


def faq_html() -> str:
    return "".join(
        f"<details><summary>{p}</summary><p>{r}</p></details>" for p, r in preguntas_frecuentes()
    )


# ---------------------------------------------------------------------------------------------
# La portada: «el dato es la figura» (DISENO.md). Cada figura muestra un dato real con su prueba:
# el problema (cinco portales para una pregunta), la prueba (las tres capas del predio del héroe),
# el motor (la criba de los 1.335 linderos del SINIC alrededor de ese predio), los servicios (un
# expediente, una cifra con su corte, la bitácora de un contrato y el índice del catálogo), la
# cobertura del SINIC y cómo trabajamos (un dato del INS en cuatro destinos). Los números salen del catálogo, de las respuestas
# capturadas (TURNOS, correos.EJEMPLO) y de datos/portada.json, que prepara web/portada_datos.py con
# copias locales (sin consultas a la fuente). Las figuras las mueven los módulos de MODULOS_PORTADA.
PORTADA_JSON = PUBLICO / "datos" / "portada.json"


def datos_portada() -> dict:
    return json.loads(PORTADA_JSON.read_text(encoding="utf-8"))


def coma(x: float) -> str:
    """Decimal con coma, sin ceros de más: 3.36 → «3,36», 3.6 → «3,6»."""
    return f"{x:g}".replace(".", ",")


def dma(iso: str) -> str:
    """AAAA-MM-DD → DD-MM-AAAA, como fecha el sitio."""
    return f"{iso[8:10]}-{iso[5:7]}-{iso[:4]}"


def corto_predio(codigo: str) -> str:
    return f"{codigo[:5]}…{codigo[-4:]}"


TURNO_PREDIO = TURNOS[0]
assert TURNO_PREDIO["herr"] == EJEMPLO["herramienta"] == "sinic_predio_en_punto"
TURNO_NORMA = TURNOS[2]
assert TURNO_NORMA["herr"] == "suin_norma"
PRED = corto_predio(EJEMPLO["predio"])
COPIA_SINIC = CAPAS_PRUEBA[3][1]  # «copia del 28-10-2026», comprobada contra EJEMPLO
_m_punto = re.search(r"en ([\d,]+ N, [\d,]+ W)", TURNO_PREDIO["pregunta"])
assert _m_punto, "la pregunta del predio ya no trae su punto"
PUNTO = _m_punto.group(1)


def fila_turno(t: dict, clave: str) -> str:
    return dict(t["filas"])[clave]


# El problema (vuelta 4, el deck): una decisión de organización, no un lote. «¿Le damos crédito a
# este proveedor?» El mismo NIT en tres portales, cada uno con su forma de escribirlo (campos tal como
# los publica la fuente, que deben existir en su ficha), y la respuesta en palabras, con quién dice
# cada cosa. La empresa es Ecopetrol S.A., una sociedad (nunca una persona): datos/portada.json.
VENTANAS = [
    ("confecamaras.rues", "Confecámaras · RUES", ["nit", "fecha_matricula"]),
    ("confecamaras.rues_establecimientos", "Confecámaras · establecimientos", ["estado_matricula"]),
    ("supersociedades.empresas_grandes", "Supersociedades · 10.000 empresas", ["nit", "ingresos_operacionales"]),
]
_PUBLICADAS_IDS = {f.id for f in PUBLICADAS}
for _fid, _tit, _campos in VENTANAS:
    assert _fid in _PUBLICADAS_IDS, f"{_fid} no está publicada"
    _f = CAT.fuentes[_fid]
    assert _tit.split(" · ")[0] == nombre_entidad(_f.entidad), (_fid, nombre_entidad(_f.entidad))
    assert all(c in set(_f.campos or {}) for c in _campos), f"{_fid}: campos {_campos}"
PASOS_PROBLEMA = [
    "encontrar quién publica",
    "descubrir el servicio",
    "limpiar cada formato",
    "cruzar a mano",
    "repetir con el siguiente",
]


def _cifra_b(x: float) -> str:
    """Billones con una cifra decimal y coma: 144.82 → «144,8»."""
    return f"{x:.1f}".replace(".", ",")


def seccion_problema() -> str:
    P = datos_portada()
    E, pit = P["empresa"], P["pitalito"]
    assert E["nit"] == "899999068" and E["estado"] == "activa"
    camara = {"Bogota": "Bogotá"}.get(E["camara"], E["camara"])
    crudos = [
        f"nit {E['nit']} · fecha_matricula {E['fecha_matricula_tal_cual']}",
        f"estado_matricula · {E['establecimientos']} filas, {E['establecimientos_cancelados']} CANCELADA",
        f'nit {E["nit_tal_cual_super"]} · ingresos_operacionales "{E["ingresos_tal_cual"]}"',
    ]
    notas = ["la fecha, sin guiones", "otra consulta para la misma empresa", "el NIT con decimales; la cifra, texto"]
    vent = "".join(
        f'<div class="v" style="--k:{i}"><b>{t}</b><code>{escape(c)}</code><i>{n}</i></div>'
        for i, ((_, t, _c), c, n) in enumerate(zip(VENTANAS, crudos, notas, strict=True))
    )
    pasos = "".join(f'<li style="--k:{i}">{p}</li>' for i, p in enumerate(PASOS_PROBLEMA))
    pasos += f'<li class="horas" style="--k:{len(PASOS_PROBLEMA)}">horas o días por empresa</li>'
    A = E["anios"]
    pico = max(A, key=lambda a: a["ingresos"])
    ult = A[-1]
    tope = pico["ingresos"]
    barras = "".join(
        f'<div class="pb3-a" style="--k:{k}"><span class="v">{_cifra_b(a["ingresos"])}</span>'
        f'<i class="ing" style="--h:{100 * a["ingresos"] / tope:.1f}%"><i class="gan" style="--h:{100 * a["ganancia"] / a["ingresos"]:.1f}%"></i></i>'
        f'<span class="a">{a["a"]}</span></div>'
        for k, a in enumerate(A)
    )
    tal_cual = pit["tal_cual_M"]
    bien = round(pit["valor"] / 1_000_000)
    ancho = f"{100 * bien / tal_cual:.1f}%"
    return f"""<section class="seccion" id="problema"><div class="envoltura">
<div class="con-fig inv-l pr3-sec">
<figure class="fig-iso pr3" tabindex="0" role="group" aria-label="Tres portales, una pregunta sobre una empresa. Toca o pulsa Enter para repetir.">
<p class="pr3-preg"><span>la pregunta · NIT {E["nit"]}</span>¿Le damos crédito a este proveedor?</p>
<div class="pr3-esc">
<div class="pr3-vent" aria-label="Los tres portales">
{vent}
</div>
<ol class="pr3-pasos">
{pasos}
</ol>
<p class="pr3-puerta" aria-hidden="true">las tres, detrás de una puerta</p>
<div class="pr3-res">
<p class="pr3-et">la respuesta, en palabras</p>
<p class="pr3-frase">{E["razon_social"]} tiene la matrícula <b>{E["estado"]}</b> en la Cámara de Comercio de {camara}, renovada en <b>{E["renovado"]}</b>.<span class="cita"><span class="m"></span>Confecámaras</span> La vigila la <b>{E["supervisor"]}</b>, y sus ingresos pasaron de <b>{_cifra_b(pico["ingresos"])}</b> billones de pesos en {pico["a"]} a <b>{_cifra_b(ult["ingresos"])}</b> en {ult["a"]}.<span class="cita"><span class="m"></span>Supersociedades</span></p>
<div class="pb3" aria-hidden="true">{barras}</div>
<p class="pb3-ley" aria-hidden="true"><span><i class="ing"></i>ingresos</span><span><i class="gan"></i>ganancia</span><span>billones de pesos, por año</span></p>
</div>
</div>
<figcaption class="lectura-l"><span class="lin"><span data-lectura aria-live="off">tres portales, tres formas de escribir el mismo NIT</span></span><span class="pista">toca la figura para repetir</span></figcaption>
</figure>
<div class="cab">
<h2 class="t2">El dato público existe. Usarlo para decidir sigue costando semanas.</h2>
<p class="entrada">Una sola decisión recorre varios portales, cada uno con su formato, su corte y su licencia. Con Terrnova es una llamada, y vuelve en palabras, con quién dice cada cosa.</p>
<ul class="lista-l">
<li><b>Un solo formato</b><span>{N_ENTIDADES} entidades. El NIT con o sin decimales, la fecha con o sin guiones: llega igual.</span></li>
<li><b>Sin equipo propio</b><span>Si tu organización no tiene analistas ni desarrolladores, la solución la construimos nosotros.</span></li>
<li><b>Bien contado</b><span>SECOP lista cada contrato varias veces; lo contamos una vez.</span></li>
</ul>
<figure class="bc3" aria-label="Pitalito, 2025: {miles(tal_cual)} millones sumando SECOP tal cual; {miles(bien)} millones contando cada contrato una vez, {miles(pit["contratos"])} contratos.">
<div class="bc3-f"><span class="k">SECOP tal cual</span><i class="b tal" style="--w:100%"></i><b>${miles(tal_cual)} M</b></div>
<div class="bc3-f"><span class="k">contado una vez</span><i class="b una" style="--w:{ancho}"></i><b>${miles(bien)} M</b></div>
<figcaption class="fuente-dato">Pitalito, 2025 · {miles(pit["contratos"])} contratos en SECOP II · perfil de la fuente del {dma(pit["perfil"])}, respuesta capturada el {dma(pit["grabado"])}</figcaption>
</figure>
</div>
</div>
<p class="fuente-dato pr3-fd">{E["razon_social"]} (NIT {E["nit"]}), una sociedad · Confecámaras (RUES): respuestas capturadas el {dma(E["grabado_rues"])} y el {dma(E["grabado_est"])} · Supersociedades, las 10.000 empresas: capturada el {dma(E["grabado_super"])}, cifras en billones de pesos redondeadas por la fuente · los pasos y las horas no se miden</p>
</div></section>"""


def seccion_prueba() -> str:
    filas = []
    grupos = [
        ("r", "estado", "estado"),
        ("r", "predial", "predial"),
        ("r", "destinacion", "destinación"),
        ("c", "servido", "servido"),
        ("f", "entidad", "entidad"),
        ("f", "licencia", "licencia"),
    ]
    for g, k, et in grupos:
        v = PRED if k == "predial" else fila_turno(TURNO_PREDIO, et)
        filas.append(f'<dt data-g="{g}" data-k="{k}">{et}</dt><dd>{v}</dd>')
    notas = "".join(
        f'<li data-p="{i}"><b>{t}</b><span>{d}</span></li>' for i, (t, d) in enumerate(NOTAS_PRUEBA)
    )
    lic = licencia_corta(EJEMPLO["licencia"])
    destino = fila_turno(TURNO_PREDIO, "destinación").split(",")[0].lower()
    final = f"predio {PRED} · {COPIA_SINIC} · IGAC SINIC · {lic}"
    return f"""<section class="seccion sup" id="prueba"><div class="envoltura" data-f3-sec>
<div class="p3-cab"><h2 class="t2">Cada respuesta trae su prueba</h2>
<p class="entrada">Lo que necesitas para defender una decisión va dentro de la respuesta, no en un anexo.</p></div>
<figure class="fig-iso p3" data-f3="prueba" data-predio="{PRED}" data-copia="{COPIA_SINIC}" data-punto="{PUNTO}" data-destino="{destino}">
<div class="p3-escena lienzo" tabindex="0" role="group" aria-label="La prueba de una respuesta, en tres capas. Toca o pulsa Enter para repetir.">
<canvas role="img" aria-label="Tres capas reales del mismo lote de Santa Marta, apiladas: abajo la fuente, el catastro del IGAC (SINIC) con sus linderos; en medio la {COPIA_SINIC.replace("copia", "copia de consulta")}; arriba el resultado, solo el predio {PRED}. La fuente va en trazo, como se publica; la copia, sólida y con su fecha. Una sonda baja por el punto {PUNTO}, el lindero del predio se enciende en la copia, la copia se ata a su fuente y el predio real sube. Un hilo ámbar baja del predio a la copia y de la copia a la fuente: la cadena de la prueba. Al lado, la respuesta se llena campo por campo, cada uno con una guía a la capa que lo prueba. La separación entre capas y las alturas son simbólicas."></canvas>
<div class="p3-rot" aria-hidden="true"><span class="p3-capa" data-capa="r"><b><span class="l">Resultado</span></b><i>predio {PRED}</i></span><span class="p3-capa" data-capa="c"><b><span class="l">Copia de consulta</span><span class="c">Copia</span></b><i class="sellito">{COPIA_SINIC}</i></span><span class="p3-capa" data-capa="f"><b><span class="l">Fuente: IGAC SINIC</span><span class="c">Fuente</span></b><i>como se publica: el trazo</i></span></div>
</div>
<div class="consola p3-con"><div class="turno">
<p class="preg"><span class="tu">Tu agente</span><span class="txt">{TURNO_PREDIO["pregunta"]}</span></p>
<p class="llama"><span>llama a</span><code>{TURNO_PREDIO["herr"]}</code></p>
<dl>{"".join(filas)}</dl>
<p class="pie"><span>huella <b>{TURNO_PREDIO["huella"]}</b></span><span class="sello">capturado el {TURNO_PREDIO["fecha"]}</span></p>
</div></div>
<svg class="p3-guias" aria-hidden="true"></svg>
<figcaption class="lectura-l"><span class="lin"><span data-lectura aria-live="off">{final}</span></span><span class="pista">Linderos reales del SINIC en un cuadro de 60 m de lado alrededor del punto. La separación entre capas y las alturas son simbólicas.</span></figcaption>
</figure>
<ul class="lista-l p3-notas">{notas}</ul>
<p class="fuente-dato">El predio del mapa de arriba, IGAC SINIC · <span class="sello">respuesta capturada el {TURNO_PREDIO["fecha"]}</span></p>
</div></section>"""


def _cercana(K: dict, tipo: str) -> dict:
    return next(c for c in K["cercanas"] if c["tipo"] == tipo)


def seccion_motor() -> str:
    K = datos_portada()["criba"]
    n, rev = K["n"], len(K["revision"])
    desp = n - rev
    ap, rg = _cercana(K, "area_protegida"), _cercana(K, "resguardo_indigena")
    umbral = coma(K["umbral_m2"])
    sinic = next(e for e in K["expediente"] if e["fuente"] == "igac.sinic_terreno")
    assert dma(sinic["copia"]) in COPIA_SINIC
    return f"""<section class="seccion" id="motor"><div class="envoltura" data-f3-sec>
<div class="p3-cab"><h2 class="t2">Tu lista entera, revisada ítem por ítem</h2>
<p class="entrada">Lotes, empresas o contratos: lo claro se despeja solo, lo dudoso lo revisa una persona y de cada ítem queda un expediente. Aquí, {miles(n)} lotes de Santa Marta contra cuatro entidades.</p></div>
<figure class="fig-iso cri" data-f3="criba">
<div class="cr-escena lienzo f3-lienzo" tabindex="0" role="group" aria-label="La criba de una lista. Toca o pulsa Enter para repetir.">
<canvas role="img" aria-label="Los {miles(n)} predios del SINIC alrededor del punto del héroe, en Santa Marta, como una lista. Una regla los recorre y los revisa contra cuatro fuentes: áreas protegidas del RUNAP, resguardos de la ANT, pérdida de bosque del SINCHI y el catastro del IGAC. {miles(desp)} se asientan, despejados; {rev} se levantan porque su lindero se monta sobre el de un vecino; ninguno toca un área protegida ni un resguardo. La cámara se acerca al dudoso {K["dudoso_corto"]}, a {K["dudoso_dist_heroe_m"]} m del predio del héroe, y se abre su expediente."></canvas>
<div class="f3-rot" aria-hidden="true"></div>
</div>
<div class="consola cr-exp" aria-live="off">
<div class="turno">
<p class="cr-tit">expediente · predio {K["dudoso_corto"]}</p>
<ul class="exp">
<li data-fila><span class="m m-vacio" aria-hidden="true"></span><b>Áreas protegidas</b><i>Parques Nacionales, RUNAP</i><em>ninguna · la más cercana, {escape(ap["nombre"])}, a {coma(ap["km_dudoso"])} km</em></li>
<li data-fila><span class="m m-vacio" aria-hidden="true"></span><b>Resguardos</b><i>Agencia Nacional de Tierras</i><em>ninguno · el más cercano a {coma(rg["km_dudoso"])} km</em></li>
<li data-fila><span class="m m-fuera" aria-hidden="true"></span><b>Pérdida de bosque</b><i>SINCHI</i><em class="fuera">fuera de cobertura: solo Amazonia</em></li>
<li data-fila class="dudosa"><span class="m m-revisar" aria-hidden="true"></span><b>Catastro</b><i>IGAC, SINIC · {COPIA_SINIC}</i><em class="revisar">por revisar: su lindero se monta {coma(K["dudoso_m2"])} m² sobre el de {K["dudoso_vecino"]}</em></li>
</ul>
<p class="pie"><span>decide una persona</span><span>cruce del {dma(K["cruce"])}</span></p>
</div></div>
<figcaption class="lectura-l"><span class="lin"><span data-lectura aria-live="off">expediente de {K["dudoso_corto"]}</span></span><span class="pista">toca la figura para repetir</span></figcaption>
</figure>
<ul class="lista-l cr-cuentas">
<li><b>{miles(desp)} despejados</b><span>{coma(round(100 * desp / n, 1))} %. Ninguno de los {miles(n)} toca un área protegida ni un resguardo.</span></li>
<li><b>{rev} a revisión</b><span>{coma(round(100 * rev / n, 1))} %. Su lindero se monta más de {umbral} m² sobre el de un vecino en la copia del SINIC.</span></li>
<li><b>{K["sin_poligono"]} sin polígono</b><span>Todos tienen lindero en esta lista. Si faltara, quedaría vacío, no despejado.</span></li>
</ul>
<p class="fuente-dato">Linderos: IGAC SINIC, {COPIA_SINIC} · RUNAP (Parques Nacionales) y resguardos (ANT), copias del {dma(K["version"])} · SINCHI: fuera de cobertura · cruce local, sin consultas a la fuente</p>
</div></section>"""


def _valor(d: dict, v: float) -> str:
    s = miles(v) if isinstance(v, int) else coma(v)
    return f"{s} %" if d.get("u") == "%" else s


def seccion_servicios_portada() -> str:
    P = datos_portada()
    K, ind, B, mun = P["criba"], P["indicadores"], P["bitacora"], P["municipio"]
    vendibles = {h.id for h in HERR}
    assert {d["tool"] for d in ind} <= vendibles
    # el expediente del dudoso
    marca = {
        "no_encontrado": "m-vacio",
        "fuera_de_cobertura": "m-fuera",
        "por_revisar": "m-revisar",
    }
    texto = {
        "pnn.runap": ("Áreas protegidas", "ninguna"),
        "ant.resguardos_indigenas": ("Resguardos", "ninguno"),
        "sinchi.perdida_bosque": ("Pérdida de bosque", "fuera de cobertura"),
        "igac.sinic_terreno": ("Catastro", "por revisar"),
    }
    clase_em = {"fuera_de_cobertura": ' class="fuera"', "por_revisar": ' class="revisar"'}
    filas_ex, ents = [], []
    for e in K["expediente"]:
        fuente = CAT.fuentes[e["fuente"]]
        ent = nombre_entidad(fuente.entidad)
        if e["fuente"] == "igac.sinic_terreno":
            ent = "IGAC, SINIC"
        ents.append(ent)
        tit, est = texto[e["fuente"]]
        dud = ' class="dudosa"' if e["estado"] == "por_revisar" else ""
        filas_ex.append(
            f"<li data-fila{dud}><b>{tit}</b><i>{ent}</i><em{clase_em.get(e['estado'], '')}>"
            f'<span class="m {marca[e["estado"]]}"></span>{est}</em></li>'
        )
    huella_ex = f"sha256:{K['huella'][:8]}…"
    # la cifra con su corte: el indicador del INS cambia de corte
    i_nuevo = next(i for i, d in enumerate(ind) if d["tool"] == "ins_calidad_agua_municipio")
    cifras = []
    for i, d in enumerate(ind):
        corte = f"{d['entidad']} · corte {d['corte']}"
        if i == i_nuevo:
            nota = f" · {d['nota'].lower()}" if d.get("nota") else ""
            cifras.append(
                f'<div class="ci3-i nuevo" data-i="{i}"><span class="k">{d["k"]}</span>'
                f'<b><span class="v" data-v="{_valor(d, d["v"])}" data-antes="{_valor(d, d["antes"])}">{_valor(d, d["v"])}</span>'
                f'<span class="antes">antes {_valor(d, d["antes"])}</span></b>'
                f'<small><span class="c" data-c="corte {d["corte"]}" data-cantes="corte {d["corte_antes"]}">{corte}</span>{nota}</small></div>'
            )
        else:
            cifras.append(
                f'<div class="ci3-i" data-i="{i}"><span class="k">{d["k"]}</span><b>{_valor(d, d["v"])}</b><small>{corte}</small></div>'
            )
    dn = ind[i_nuevo]
    lect_cifra = f"IRCA de {mun['nombre']}: {_valor(dn, dn['antes'])} en {dn['corte_antes']}, {_valor(dn, dn['v'])} en {dn['corte']} · {dn['entidad']}"
    grabados = sorted(d["grabado"] for d in ind)
    # la bitácora: la última prórroga publicada (el aviso que llegaría hoy, con su antes y después)
    pub = [m for m in B["mods"] if m["estado"] == "Publicado"]
    clave = max((m for m in pub if m["dias"] > 0), key=lambda m: m["f"])
    antes = sum(m["dias"] for m in pub if m["f"] < clave["f"])
    num = re.search(r"Consultor[ií]a N\S* (\d+-\d{4})", " ".join(m["prop"] for m in B["mods"]))
    assert num, "el registro ya no nombra el número del contrato"
    meses = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
    f0, f1 = B["mods"][0]["f"], B["mods"][-1]["f"]
    lapso = f"de {meses[int(f0[5:7]) - 1]} de {f0[:4]} a {meses[int(f1[5:7]) - 1]} de {f1[:4]}"
    # el índice del catálogo y la pregunta que lo atraviesa
    fams = sorted(
        ((FAMILIAS[k], n) for k, n in POR_FAMILIA.items() if k != "meta"), key=lambda x: -x[1]
    )
    n_fam = len(fams)
    lista_fam = ", ".join(f"{f} {n}" for f, n in fams)
    lic_norma = fila_turno(TURNO_NORMA, "licencia").split(",")[0]
    return f"""<section class="seccion sup" id="servicios"><div class="envoltura" data-f3-sec>
<div class="cab"><h2 class="t2">Cuatro decisiones, cada una con su prueba</h2>
<p class="entrada">Lo que una organización decide cada semana, resuelto sobre la misma capa de datos con analítica, desarrollo y automatización. Un agente hace el trabajo, otro lo evalúa y una persona lo aprueba antes de que te llegue.</p></div>
<div class="sv3">

<article class="sv3-c" data-sv="bitacora">
<figure class="fig-iso bi3" tabindex="0" role="group" aria-label="La bitácora de un contrato de SECOP II, día por día, {lapso}. Toca o pulsa Enter para repetir.">
<p class="bi3-tit"><b>Contrato de consultoría {num.group(1)}</b><span>SECOP II · {B["contrato"]}</span></p>
<div class="bi3-cuerpo"><div class="bi3-cal"></div>
<div class="bi3-ley" aria-hidden="true"><span><i class="d"></i>sin cambios</span><span><i class="d p"></i>modificación publicada</span><span><i class="d c"></i>cancelada o rechazada</span><span><i class="m m-aspa"></i>la fuente no respondió (no pasó aquí)</span></div>
<div class="consola bi3-aviso" aria-hidden="true"><p class="cr-tit">aviso · el contrato que sigues</p><dl>
<dt>cambio</dt><dd class="amb">prórroga de {clave["dias"]} días</dd>
<dt>motivo</dt><dd>«{escape(clave["prop"])}»</dd>
<dt>fecha</dt><dd>{dma(clave["f"])}, {clave["estado"].lower()}</dd>
<dt>antes</dt><dd>{antes} días de prórroga</dd>
<dt>ahora</dt><dd>{antes + clave["dias"]} días de prórroga</dd>
<dt>entidad</dt><dd>Colombia Compra Eficiente, SECOP II</dd></dl>
<p class="pie"><span>{len(B["mods"])} registros, completos</span><span class="sello">capturado el {dma(B["grabado"])}</span></p></div></div>
<figcaption class="lectura-l"><span class="lin"><span data-lectura aria-live="off">{dma(clave["f"])}: prórroga de {clave["dias"]} días</span></span><span class="pista">reconstruida del registro de modificaciones del contrato</span></figcaption>
</figure>
<div><p class="sv3-capa">Contratación · automatización</p><h4>¿Qué cambió en el contrato?</h4><p>Lo que sigues se revisa cada día; casi siempre no pasa nada, y el día que cambia llega el aviso con el antes y el después.</p><a class="enlace" href="/servicios#vigilancia">Ver el servicio</a></div>
</article>

<article class="sv3-c" data-sv="indice">
<figure class="fig-iso in3" tabindex="0" role="group" aria-label="El catálogo de Terrnova: {N_HERR} herramientas en {n_fam} familias, una raya por herramienta. Toca o pulsa Enter para repetir.">
<p class="in3-preg"><span class="txt">¿Sigue vigente esta ley?</span></p>
<svg class="in3-svg" role="img" aria-label="{lista_fam}. La pregunta enciende Normativa y la herramienta {TURNO_NORMA["herr"]}."></svg>
<div class="in3-tip" hidden></div>
<div class="consola in3-res" aria-hidden="true"><p class="cr-tit">tu asistente responde y cita</p><dl>
<dt>respuesta</dt><dd><span class="ok">{fila_turno(TURNO_NORMA, "vigencia").lower()}</span></dd>
<dt>norma</dt><dd>{fila_turno(TURNO_NORMA, "norma")}</dd>
<dt>entidad</dt><dd>{fila_turno(TURNO_NORMA, "entidad")}</dd>
<dt>licencia</dt><dd>{lic_norma}</dd></dl>
<p class="pie"><span>huella <b>{TURNO_NORMA["huella"]}</b></span><span class="sello">capturado el {TURNO_NORMA["fecha"]}</span></p></div>
<figcaption class="lectura-l"><span class="lin"><span data-lectura aria-live="off">{N_HERR} herramientas, {n_fam} familias</span></span><span class="pista">pasa el puntero por las rayas</span></figcaption>
</figure>
<div><p class="sv3-capa">Legal · desarrollo</p><h4>¿Sigue vigente esta ley?</h4><p>Un asistente hecho para tu equipo: sabe qué entidad responde cada pregunta y la cita en la respuesta.</p><a class="enlace" href="/servicios#asistente">Ver el servicio</a></div>
</article>

<article class="sv3-c" data-sv="cifra">
<figure class="fig-iso ci3" tabindex="0" role="group" aria-label="Cuatro indicadores reales de {mun["nombre"]}, cada uno con su entidad y su corte. Toca o pulsa Enter para repetir.">
<p class="ci3-mun">{mun["nombre"]} <span>{mun["divipola"]}</span></p>
<div class="ci3-rej">
{chr(10).join(cifras)}
</div>
<p class="ci3-aviso" aria-hidden="true">el {dn["entidad"]} publica el corte {dn["corte"]}</p>
<div class="consola ci3-tip" aria-hidden="true"><dl></dl></div>
<figcaption class="lectura-l"><span class="lin"><span data-lectura aria-live="off">{lect_cifra}</span></span><span class="pista">pasa el puntero por las cifras</span></figcaption>
</figure>
<div><p class="sv3-capa">Gobierno · analítica</p><h4>¿Cómo va el municipio?</h4><p>Un tablero donde cada cifra dice qué entidad la publica y de qué corte es; cuando sale uno nuevo, el anterior queda a la vista.</p><a class="enlace" href="/servicios#tablero">Ver el servicio</a></div>
</article>

<article class="sv3-c" data-sv="expediente">
<figure class="fig-iso ex3" data-f3="expediente" tabindex="0" role="group" aria-label="El expediente de un ítem. Toca o pulsa Enter para repetir.">
<div class="ex3-escena f3-lienzo"><canvas role="img" aria-label="El predio {K["dudoso_corto"]} de Santa Marta, el dudoso de la criba, con sus vecinos. Salen sus cuatro preguntas, una por entidad, y cada una vuelve con su estado: {ents[0]}, ninguna área protegida; {ents[1]}, ningún resguardo; {ents[2]}, fuera de cobertura; IGAC, por revisar. El expediente se cierra con su huella."></canvas><div class="f3-rot" aria-hidden="true"></div></div>
<ul class="ex3-filas">
{chr(10).join(filas_ex)}
</ul>
<svg class="ex3-guias" aria-hidden="true"></svg>
<figcaption class="lectura-l"><span class="lin"><span data-lectura aria-live="off">expediente · {K["dudoso_corto"]} · huella {huella_ex}</span></span></figcaption>
</figure>
<div><p class="sv3-capa">Territorio · analítica</p><h4>¿Puedo comprar este lote?</h4><p>Cada lote de tu lista vuelve con un expediente: qué respondió cada entidad y qué queda por revisar.</p><a class="enlace" href="/servicios#revision">Ver el servicio</a></div>
</article>

</div>
<p class="fuente-dato">Expediente: cruce local del {dma(K["cruce"])} con las copias de RUNAP y ANT ({dma(K["version"])}) y del SINIC ({COPIA_SINIC.removeprefix("copia del ")}) · {mun["nombre"]}: respuestas capturadas del {dma(grabados[0])} al {dma(grabados[-1])} · contrato: registro de SECOP II capturado el {dma(B["grabado"])} · catálogo: {N_HERR} herramientas, hoy</p>
</div></section>"""


def seccion_cobertura() -> str:
    co = json.loads(CO_JSON.read_text(encoding="utf-8"))
    km = round(co["R"] * 111.32)
    total, celdas = sum(n for *_, n in co["bins"]), len(co["bins"])
    return f"""<section class="seccion" id="cobertura"><div class="envoltura" data-f3-sec>
<div class="con-fig cob3">
<div class="cab">
<p class="sv3-capa">Una fuente, de cerca · IGAC SINIC</p>
<h2 class="t2">Cuánto cubre cada fuente, medido</h2>
<p class="entrada">Antes de responder sabemos qué cubre cada fuente. La del catastro SINIC, en el país: cada columna es una celda de unos {km} km de radio y su altura cuenta los predios de la muestra que caen en ella.</p>
<p class="cob3-plana">Una celda plana no es un cero inventado: es territorio sin predios en la muestra. El SINIC cubre los {SINIC_MUNICIPIOS} municipios con gestor catastral propio; el resto lo responde la base del IGAC.</p>
<ul class="lista-l"><li><b>{SINIC_TERRENOS}</b><span>terrenos en la copia SINIC ({SINIC_MUNICIPIOS} municipios)</span></li><li><b>{miles(total)}</b><span>en la muestra (3 %)</span></li><li><b>{miles(celdas)}</b><span>celdas con predios</span></li></ul>
<div class="cob3-ley" aria-hidden="true"><span>menos</span><i><b style="background:#A6D8CC"></b><b style="background:#7DB5A8"></b><b style="background:#559385"></b><b style="background:#2D7062"></b><b style="background:#14564A"></b></i><span>más predios por celda</span></div>
<p class="fuente-dato">IGAC SINIC · conteo de la ficha de la fuente, medido el {SINIC_MEDIDO} · muestra del 3 %</p>
</div>
<figure class="fig-iso f3-cob" data-f3="cobertura"><div class="lienzo f3-lienzo" tabindex="0" role="group" aria-label="Mapa de cobertura del SINIC. Arrastra o usa las flechas para girar."><canvas role="img" aria-label="Columnas hexagonales sobre Colombia con los predios SINIC de la muestra del 3 %: {miles(total)} predios en {miles(celdas)} celdas. Las columnas suben desde la celda de Santa Marta hacia afuera y el mapa gira despacio; las más altas y oscuras cuentan más predios. Las celdas planas son territorio sin predios en la muestra."></canvas><div class="f3-rot" aria-hidden="true"></div></div><figcaption class="lectura-l"><span class="lin"><span data-lectura aria-live="polite">{miles(total)} predios de la muestra (3 %) en {miles(celdas)} celdas</span></span><span class="pista">gira sola; pasa el puntero por las columnas o arrastra para girarla</span></figcaption></figure>
</div>
</div></section>"""


# Cómo trabajamos (la lámina «soluciones» del deck): el cliente no maneja agentes; dice la pregunta y
# recibe el resultado donde ya trabaja. La figura es una sola respuesta real del INS (el IRCA de Chía,
# serie 2007-2024 capturada en tests/doradas) en cuatro destinos: el tablero, el informe, la capa del
# mapa y el aviso. Los valores son reales; los cuatro formatos, ilustrativos.
PASOS_COMO = [
    ("La pregunta", "Nos dices qué decisión tienes que tomar, en tus palabras."),
    (
        "Construimos",
        "Nuestro equipo, con sus agentes, arma el análisis o el sistema sobre la capa de datos.",
    ),
    ("Evaluamos", "Otro agente lo revisa contra la fuente y una persona lo aprueba."),
    ("Entregamos", "En tu tablero, tu informe, tu mapa o tu correo, con la prueba adjunta."),
]
IRCA_SIN_RIESGO = 5.0  # Resolución 2115 de 2007: de 0 a 5, «sin riesgo»


def _chispa(serie: list, w: int = 260, h: int = 64) -> str:
    """La serie del IRCA como una línea, con el tope de «sin riesgo» punteado y el último año marcado."""
    a0, a1 = serie[0][0], serie[-1][0]
    top = max(max(v for _, v in serie), IRCA_SIN_RIESGO) * 1.1
    x = lambda a: 4 + (a - a0) * (w - 8) / (a1 - a0)  # noqa: E731
    y = lambda v: h - 14 - v * (h - 22) / top  # noqa: E731
    pts = " ".join(f"{x(a):.1f},{y(v):.1f}" for a, v in serie)
    ax, ay = x(a1), y(serie[-1][1])
    ty = y(IRCA_SIN_RIESGO)
    return (
        f'<svg class="en3-chispa" viewBox="0 0 {w} {h}" aria-hidden="true">'
        f'<line class="tope" x1="4" x2="{w - 4}" y1="{ty:.1f}" y2="{ty:.1f}"/>'
        f'<text class="tope-t" x="{w - 4}" y="{ty - 4:.1f}" text-anchor="end">hasta 5: sin riesgo</text>'
        f'<polyline class="linea" points="{pts}"/>'
        f'<circle class="ult" cx="{ax:.1f}" cy="{ay:.1f}" r="3.2"/>'
        f'<text class="eje" x="4" y="{h - 1}">{a0}</text>'
        f'<text class="eje" x="{w - 4}" y="{h - 1}" text-anchor="end">{a1}</text></svg>'
    )


def seccion_como() -> str:
    P = datos_portada()
    mun = P["municipio"]
    d = next(x for x in P["indicadores"] if x["tool"] == "ins_calidad_agua_municipio")
    serie = d["serie"]
    assert serie[-1] == [int(d["corte"]), d["v"]] and serie[-2] == [
        int(d["corte_antes"]),
        d["antes"],
    ]
    assert d["v"] <= IRCA_SIN_RIESGO and d["nota"] == "Sin riesgo"
    ent = nombre_entidad(CAT.fuentes[next(h for h in HERR if h.id == d["tool"]).fuente].entidad)
    lic = licencia_corta(d["licencia"])
    v, antes = coma(d["v"]), coma(d["antes"])
    cita = f"{d['entidad']} · corte {d['corte']}"
    pasos = "".join(
        f'<li><b><span class="n">{i + 1}</span>{t}</b><span>{x}</span></li>'
        for i, (t, x) in enumerate(PASOS_COMO)
    )
    return f"""<section class="seccion sup" id="como"><div class="envoltura">
<div class="cab"><h2 class="t2">Cómo trabajamos</h2>
<p class="entrada">Tu organización no tiene que manejar agentes ni programar. Nos cuentas la decisión y te entregamos el resultado donde ya trabajas, con la prueba adjunta.</p></div>
<ol class="cm3-pasos">{pasos}</ol>
<figure class="en3" tabindex="0" role="group" aria-label="Una misma respuesta del {ent} en cuatro destinos: el tablero, el informe, la capa del mapa y el aviso por correo. Toca o pulsa Enter para repetir.">
<div class="en3-rej">
<div class="en3-c" style="--k:0"><p class="en3-d">en tu tablero</p>
<p class="en3-k">Riesgo del agua (IRCA) · {mun["nombre"]}</p>
<p class="en3-v"><b>{v}</b><span>{d["nota"].lower()}</span></p>
{_chispa(serie)}
<p class="en3-cita"><span class="m"></span>{cita}</p></div>
<div class="en3-c" style="--k:1"><p class="en3-d">en tu informe</p>
<p class="en3-p">En {d["corte"]}, el índice de riesgo de la calidad del agua (IRCA) de {mun["nombre"]} fue {v}, nivel sin riesgo, frente a {antes} en {d["corte_antes"]}.<sup>1</sup></p>
<p class="en3-cita"><span class="m"></span>1. {ent}, corte {d["corte"]}. Licencia {lic}. Consultado el {dma(d["grabado"])}.</p></div>
<div class="en3-c" style="--k:2"><p class="en3-d">en tu mapa</p>
<p class="en3-k">capa · calidad del agua por municipio</p>
<dl class="en3-tab"><dt>divipola</dt><dd>{mun["divipola"]}</dd><dt>municipio</dt><dd>{mun["nombre"]}</dd><dt>irca_{d["corte"]}</dt><dd>{v}</dd><dt>nivel</dt><dd>{d["nota"].lower()}</dd></dl>
<p class="en3-cita"><span class="m"></span>fuente: {cita}</p></div>
<div class="en3-c" style="--k:3"><p class="en3-d">en tu correo</p>
<p class="en3-k">Aviso · {mun["nombre"]}: el IRCA pasó de {antes} a {v}</p>
<p class="en3-p">El {d["entidad"]} publicó el corte {d["corte"]}. El valor sigue en «sin riesgo», que llega hasta 5.</p>
<p class="en3-cita"><span class="m"></span>{cita}</p></div>
</div>
<figcaption class="fuente-dato">Una sola respuesta del {ent} para {mun["nombre"]}, capturada el {dma(d["grabado"])}: los valores son reales y la cita es la misma en los cuatro. Los formatos son {SELLO_I}. El tope de «sin riesgo» es el de la Resolución 2115 de 2007.</figcaption>
</figure>
<p class="cm3-capa">¿Tu equipo ya tiene sistemas o agentes? Puede consultar la capa directamente, por API o MCP, y pagar por consulta. <a class="enlace" href="/desarrolladores">Ver la guía</a></p>
</div></section>"""


# Los módulos de la portada, en orden: cada uno después de los que importa. construir.py pone la
# huella (?v=) de cada import, así la caché larga no sirve un módulo viejo con uno nuevo.
MODULOS_PORTADA = [
    "ambar.js",
    "motor3d.js",
    "tipo.js",
    "fig-prueba.js",
    "fig-criba.js",
    "fig-cobertura.js",
    "fig-expediente.js",
    "servicios3.js",
    "portada-tipo.js",
    "figuras3d.js",
]


def _huella_texto(texto: str) -> str:
    import hashlib

    return hashlib.sha256(texto.replace("\r\n", "\n").encode("utf-8")).hexdigest()[:10]


def modulos_versionados() -> dict[str, str]:
    """El texto de cada módulo de la portada con la huella de lo que importa (`'./x.js?v=…'`)."""
    huellas = {"comun3d.js": version("/js/comun3d.js").split("?v=")[1]}
    textos: dict[str, str] = {}
    for nombre in MODULOS_PORTADA:
        texto = (PUBLICO / "js" / nombre).read_text(encoding="utf-8")

        def poner(m: re.Match[str], nombre: str = nombre) -> str:
            dep = m.group(1) + ".js"
            assert dep in huellas, f"{nombre} importa {dep} antes de tener su huella"
            return f"'./{dep}?v={huellas[dep]}'"

        texto = re.sub(r"'\./([a-z0-9-]+)\.js(?:\?v=[0-9a-f]+)?'", poner, texto)
        textos[nombre] = texto
        huellas[nombre] = _huella_texto(texto)
    return textos


def inicio() -> str:
    c = f"""
<section class="heroe">
<div class="escena" data-escena="predios" data-etiqueta="Predios reales del barrio 11 de Noviembre, en Santa Marta, en 3D. El predio consultado sube cuando llega su respuesta. Arrastra para girar.">
<img class="respaldo" src="/img/predio-santamarta.webp" alt="Predios reales del barrio 11 de Noviembre, en Santa Marta, en 3D." width="900" height="900">
<svg class="guia" aria-hidden="true"><line/><circle r="4"/></svg>
<div class="rotulos" aria-hidden="true"></div>
<p class="lectura"><b>11,2211 N, 74,1572 W</b> Santa Marta. Predios IGAC SINIC (CC BY-SA 4.0), calles © <a href="https://www.openstreetmap.org/copyright">colaboradores de OpenStreetMap</a></p>
<div class="mueble" aria-hidden="true"><div class="escala"><i style="width:80px"></i><span>100 m</span></div><div class="norte"><svg width="18" height="22" viewBox="-9 -11 18 22"><path d="M0 -10 L6 8 L0 4 L-6 8 Z" fill="currentColor"/></svg><span>N</span></div></div>
</div>
<div class="envoltura h-texto"><div class="izq">
<h1 class="t0"><span class="l">El dato oficial de Colombia,</span> <span class="l">con su prueba,</span> <span class="l">y la solución encima</span></h1>
<p class="entrada">Una capa de {N_FUENTES} fuentes oficiales, de empresas y contratos a normas, estadísticas y territorio, y un equipo que construye encima la analítica, el desarrollo y la automatización que tu organización necesita. Cada respuesta dice quién publica el dato, su licencia y su fecha.</p>
<div class="botones"><a class="boton p" href="/precios#empezar">Prueba gratis {DIAS_PRUEBA} días</a><a class="boton s" href="/contacto?asunto=proyecto">Cuéntanos qué quieres resolver</a></div>
<p class="h-api">¿Programas? <a class="enlace" href="/desarrolladores">Ver la API</a></p>
</div></div>
<div class="envoltura h-consola">{consola()}</div>
</section>

{seccion_problema()}

{seccion_prueba()}

{seccion_servicios_portada()}

{seccion_como()}

<section class="seccion" id="soluciones"><div class="envoltura">
<div class="cab">
<h2 class="t2">Soluciones por sector</h2>
<p class="entrada">Lo que decide cada área y de qué entidades sale cada dato.</p>
</div>
{sectores()}
</div></section>

{seccion_cobertura()}

<section class="seccion" id="no-hacemos"><div class="envoltura">
<div class="cab"><h2 class="t2">Qué no hacemos</h2></div>
<div class="columnas c3 no-h">
<div><h3>Buscar personas</h3><p>Nada por cédula ni por nombre, ni perfiles de nadie.</p></div>
<div><h3>Saltar barreras</h3><p>Ni captchas ni cuentas ajenas: solo lo que la entidad publica.</p></div>
<div><h3>Rellenar</h3><p>Si la fuente no responde, lo decimos. «No encontrado» no es «no se pudo».</p></div>
</div>
</div></section>

<section class="seccion sup" id="precios"><div class="envoltura">
<div class="cab">
<h2 class="t2">Precios de lanzamiento</h2>
<p class="entrada">Planes mensuales en pesos, más IVA. Pagas solo lo que responde: errores, caché y fuera de cobertura no descuentan.</p>
</div>
{planes_html()}
<div class="columnas c3 mas-p">
<div><h3>Prueba gratis</h3><p>{miles(CREDITOS_PRUEBA)} créditos por {DIAS_PRUEBA} días, con tu correo.</p><a class="boton p" href="/precios#empezar">Pedir la llave de prueba</a></div>
<div><h3>Estado y academia</h3><p>Entidades públicas, academia y veedurías: {miles(CREDITOS_AMPLIADO)} créditos al mes, a pedido.</p><a class="enlace" href="/contacto?asunto=gobierno-academia">Pedirlo</a></div>
<div><h3>Piloto de dos semanas</h3><p>Sobre tu caso, a precio fijo antes de empezar.</p><a class="enlace" href="/servicios#piloto">Ver el piloto</a></div>
</div>
<p class="pie-p"><span class="anual">20 % menos pagando el año.</span> <a class="enlace" href="/precios">Precio anual y créditos por consulta</a></p>
</div></section>

<section class="seccion" id="preguntas"><div class="envoltura">
<div class="faq-l">
<div class="cab"><h2 class="t2">Preguntas frecuentes</h2></div>
<div class="faq">{faq_html()}</div>
<aside class="quien" aria-labelledby="quien-t">
<h2 class="t3" id="quien-t">Quién está detrás</h2>
<p>{QUIEN}</p>
<ul class="lista">
<li><a class="enlace" href="/estado">Estado del servicio</a></li>
<li><a class="enlace" href="/llms.txt">llms.txt</a>, el catálogo para agentes</li>
<li><a class="enlace" href="/contacto">Escríbenos</a></li>
</ul>
</aside>
</div>
</div></section>
"""
    return pagina(
        "/",
        "Terrnova · El dato oficial de Colombia, con su prueba, y la solución encima",
        f"Empresas, contratos, normas, estadísticas y territorio de {FUENTES_DE}, cada respuesta con quién publica el dato, su licencia y su fecha. Encima, la analítica, el desarrollo y la automatización que tu organización necesita.",
        c,
        ("escena-predios.js", "figuras3d.js", "portada-tipo.js"),
    )


# Decisión 3 del dueño (01-11-2026): sin nombre de persona.
QUIEN = f"Terrnova es un producto de GeoAI LATAM, en Colombia. Factura {INSPOW} con factura electrónica."


# Lo inventado lleva el sello.
SELLO_I = '<span class="sello-i">ilustrativo</span>'


# El piloto, de punta a punta: cómo trabajamos y las dos semanas, en una sola secuencia.
PILOTO = [
    ("Nos cuentas", "Qué quieres decidir, dónde y para cuándo."),
    (
        "Precio fijo",
        "Acordamos la pregunta, las fuentes y el entregable, con su precio, antes de empezar.",
    ),
    ("Semana 1", "Corremos una primera muestra y la revisamos contigo."),
    ("Semana 2", "Lo corremos sobre tu caso completo, revisamos los dudosos y te lo entregamos."),
]


def servicios() -> str:
    indice = "".join(f'<a href="#{s["id"]}">{s["titulo"]}</a>' for s in SERVICIOS)
    bloques = "".join(
        f'<section class="sv-det{" par" if i % 2 else ""}"><div class="envoltura">'
        f"{servicio_fila(s, i)}</div></section>"
        for i, s in enumerate(SERVICIOS)
    )
    semanas = "".join(f"<li><b>{a}</b><span>{b}</span></li>" for a, b in PILOTO)
    c = f"""
<section class="sv-heroe"><div class="envoltura">
<div class="txt">
<h1 class="t1">Te entregamos el trabajo hecho</h1>
<p class="entrada">Revisiones, tableros, alertas y asistentes sobre {N_FUENTES} fuentes oficiales, con la fuente de cada dato. Empieza con un piloto de dos semanas a precio fijo.</p>
<div class="botones"><a class="boton p" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a><a class="boton s inv-b" href="#piloto">Ver el piloto</a></div>
</div>
<nav class="sv-indice" aria-label="Servicios">{indice}<a href="#piloto">Piloto</a></nav>
</div></section>
<section class="seccion" id="capa"><div class="envoltura">
<div class="con-fig">
<div class="cab"><h2 class="t2">Una capa de datos y, encima, tu solución</h2>
<p class="entrada">Terrnova es la capa: {N_FUENTES} fuentes oficiales con una sola forma de preguntar. Encima montamos la analítica, la automatización o el agente que necesitas, y cada dato llega con su fuente.</p></div>
{figura_capas()}
</div>
</div></section>
{bloques}
<section class="seccion inv" id="piloto"><div class="envoltura">
<div class="con-lado-p">
<div class="cab"><h2 class="t2">Piloto de dos semanas</h2>
<p class="entrada">Una solución sobre tu caso, con un entregable que se nombra antes de empezar y un precio fijo que no cambia.</p>
<a class="boton s" href="/contacto?asunto=proyecto">Proponer un piloto</a></div>
<div>
<ol class="pasos-sv dos">{semanas}</ol>
<h3 class="t3 entrega-t">Lo que recibes</h3>
<ul class="lista">
<li>El entregable acordado, cada cifra contrastada con su fuente: por ejemplo, una hoja con cada ítem, su resultado, la entidad, la fecha y la huella de cada respuesta.</li>
<li>Los casos dudosos, aparte, con el motivo.</li>
<li>Para repetirlo: la misma consulta, lista para correrla otra vez con tu plan.</li>
</ul>
</div>
</div>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><h2 class="t2">Cómo se cobra</h2><p class="entrada">Precio antes de empezar. Nunca por hora.</p></div>
<div class="columnas c3">
<div><h3>Por entrega</h3><p>Revisiones, tableros, informes y asistentes.</p></div>
<div><h3>Por proceso</h3><p>Las alertas y los procesos que corren solos, por mes.</p></div>
<div><h3>Los datos, por plan</h3><p>Si tu equipo consulta por su cuenta. <a class="enlace" href="/precios">Ver los planes</a></p></div>
</div>
</div></section>
"""
    return pagina(
        "/servicios",
        "Servicios",
        "Revisiones de predios, empresas y contratos, tableros, alertas y asistentes sobre fuentes oficiales de Colombia, con la fuente de cada dato. Piloto de dos semanas a precio fijo.",
        c,
        ("figuras.js",),
    )


# Terrenos de la copia SINIC: los cita la ficha de la fuente (perfil medido en la fuente, spec 07).
_SINIC = CAT.fuentes["igac.sinic_terreno"].perfil
assert _SINIC is not None
_m = re.search(r"([\d,]+ M) en los (\d+) municipios", _SINIC.fila)
assert _m, "la ficha de igac.sinic_terreno ya no dice cuántos terrenos tiene"
SINIC_TERRENOS, SINIC_MUNICIPIOS = _m.groups()
SINIC_MEDIDO = _SINIC.medido.strftime("%d-%m-%Y")


def fuentes() -> str:
    lic = "".join(
        f'<tr><td><code>{escape(k)}</code></td><td class="n">{v}</td></tr>'
        for k, v in LICENCIAS.most_common()
    )
    cob = datos_figuras()["cobertura"]
    km = round(cob["R"] * 111.32)
    figura_cob = figura(
        "cobertura",
        f"{miles(cob['total'])} predios de la muestra (3 %) en {len(cob['celdas'])} celdas",
        "pasa el puntero por las columnas",
    )
    c = (
        portada(
            "",
            f"{N_HERR} herramientas sobre {N_FUENTES} fuentes oficiales",
            "Cada herramienta responde una pregunta concreta. Busca por tema, entidad o nombre.",
            lado=lado_familias(),
        )
        + f"""
<section class="seccion"><div class="envoltura" data-catalogo>
<h2 class="sr">Buscar una herramienta</h2>
<div class="buscador"><label class="sr" for="q">Buscar en el catálogo</label><input id="q" type="search" placeholder="Busca: predio, contratos, normas, áreas protegidas…" autocomplete="off"></div>
{chips_familias(como_boton=True)}
<p class="conteo" aria-live="polite">Cargando el catálogo…</p>
<div class="herramientas"></div>
<button class="boton s mas" type="button" hidden>Ver más</button>
<noscript><p class="suave">El catálogo completo también está en <a class="enlace" href="/v1/herramientas">/v1/herramientas</a> y en <a class="enlace" href="/llms.txt">/llms.txt</a>.</p></noscript>
</div></section>

<section class="seccion sup" id="entidades"><div class="envoltura">
<div class="cab"><h2 class="t2">Quién publica los datos</h2>
<p class="entrada">{N_ENTIDADES} entidades. {MODOS["en_vivo"]} fuentes en vivo y {MODOS["copia"]} desde una copia oficial, con su fecha de corte.</p></div>
{indice_fuentes()}
<p class="pie-muro">El número es cuántas fuentes publica cada entidad. En gris, las globales.</p>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="con-fig">
<div class="cab">
<h2 class="t2">Dónde hay predio SINIC hoy</h2>
<p class="entrada">Cada columna suma los predios de la muestra en una celda de unos {km} km de radio; la altura y el color, de teal a ámbar, crecen con el conteo.</p>
<ul class="lista-l">
<li><b>{SINIC_TERRENOS}</b><span>terrenos en la copia SINIC ({SINIC_MUNICIPIOS} municipios)</span></li>
<li><b>{miles(cob["total"])}</b><span>en la muestra (3 %)</span></li>
<li><b>{len(cob["celdas"])}</b><span>celdas con predios</span></li>
</ul>
<p class="fuente-dato">IGAC SINIC · conteo de la ficha de la fuente, medido el {SINIC_MEDIDO} · muestra del 3 %</p>
</div>
{figura_cob}
</div>
</div></section>

<section class="seccion" id="licencias"><div class="envoltura">
<div class="cab"><h2 class="t2">La licencia de cada fuente</h2>
<p class="entrada">Cada respuesta trae su licencia y la atribución que debes citar.</p></div>
<div class="desliza lic"><table class="tabla"><thead><tr><th>Licencia (SPDX)</th><th>Fuentes</th></tr></thead><tbody>{lic}</tbody></table></div>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><h2 class="t2">El catálogo, en formato abierto</h2></div>
<ul class="lista-l abierto">
<li><b><a class="enlace" href="/v1/herramientas"><code>GET /v1/herramientas</code></a></b><span>Pregunta, fuente, créditos y ruta de cada herramienta</span></li>
<li><b><a class="enlace" href="/v1/fuentes"><code>GET /v1/fuentes/&#123;id&#125;</code></a></b><span>La ficha técnica de una fuente</span></li>
<li><b><a class="enlace" href="/llms.txt"><code>/llms.txt</code></a></b><span>El catálogo en texto, para agentes</span></li>
</ul>
</div></section>
"""
    )
    return pagina(
        "/fuentes",
        "Fuentes y herramientas",
        f"Busca entre {N_HERR} herramientas sobre {N_FUENTES} fuentes oficiales: territorio, contratación, estadísticas, justicia, ambiente, empresas y normativa.",
        c,
        ("figuras.js",),
    )


def precios() -> str:
    c = (
        portada(
            "",
            "Precios de lanzamiento",
            "Planes mensuales en pesos, más IVA. Pagas solo lo que responde: errores, caché y fuera de cobertura no descuentan.",
            lado=lado_tarifa(),
        )
        + f"""
<section class="seccion"><div class="envoltura">
<div class="cab"><h2 class="t2">Los planes</h2>
<p class="entrada">Pides el plan, te enviamos la factura y activamos tus créditos. Sin cobro automático.</p></div>
{tabla_planes()}
<p class="fuente-dato" style="margin-top:14px">Precios de lanzamiento en pesos colombianos, más IVA. Factura {INSPOW} con factura electrónica.</p>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><h2 class="t2">Cuánto alcanza cada plan</h2>
<p class="entrada">Cada consulta cuesta según lo que preguntas, no según cómo se trae el dato. Cada respuesta dice cuánto costó.</p></div>
{tarifa_html()}
<div class="rejilla r2" style="margin-top:32px">
<div class="bloque"><h3 class="t3">No descuentan</h3><ul class="lista"><li>Lo que ya estaba en caché</li><li>Lo que está fuera de la cobertura de la fuente</li><li>Los errores, incluido «no se pudo»</li><li>Consultar el catálogo</li></ul></div>
<div class="bloque"><h3 class="t3">El saldo del mes</h3><p>Se renueva el día 1 a las 00:00 UTC y no se acumula. Si se acaba, las consultas se detienen hasta el día 1 o hasta que subas de plan: nunca se cobra de más.</p></div>
</div>
</div></section>

<section class="seccion" id="empezar"><div class="envoltura">
<div class="rejilla r2" style="gap:48px;align-items:start">
<div class="cab" style="margin:0"><h2 class="t2">Prueba gratis {DIAS_PRUEBA} días</h2>
<p class="entrada">{miles(CREDITOS_PRUEBA)} créditos para probar con tus propias preguntas. Te llega un enlace a tu correo: lo confirmas y ves tu llave una sola vez.</p>
{formulario_alta()}</div>
<div class="otras">
<div class="bloque"><h3 class="t3">Estado y academia</h3><p>Entidades públicas, academia y veedurías: {miles(CREDITOS_AMPLIADO)} créditos al mes, a pedido.</p><a class="enlace" href="/contacto?asunto=gobierno-academia">Pedirlo</a></div>
<div class="bloque"><h3 class="t3">Servicios</h3><p>Revisiones, tableros, alertas y asistentes, a precio fijo antes de empezar. Empiezan con un piloto de dos semanas.</p><a class="enlace" href="/servicios#piloto">Ver el piloto</a></div>
</div>
</div>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><h2 class="t2">Preguntas frecuentes</h2></div>
<div class="faq" style="max-width:860px">
<details><summary>¿Puedo cambiar de plan?</summary><p>Sí: nos escribes y activamos el plan nuevo al emitir la factura.</p></details>
<details><summary>¿Puedo usar los datos en mi negocio?</summary><p>Sí, con su licencia: cada respuesta trae la de su entidad y la atribución que debes citar; CC BY-SA exige compartir igual. Las fuentes con licencia por verificar no salen en producción.</p></details>
<details><summary>¿Y los datos personales?</summary><p>Nada de búsquedas por cédula ni por nombre, ni perfiles de personas. Cada fuente sale con una lista cerrada de campos.</p></details>
<details><summary>¿Hay un límite de velocidad?</summary><p>Hasta 20 consultas seguidas y 60 por minuto por llave.</p></details>
<details><summary>¿Cómo se paga?</summary><p>Pides el plan e {INSPOW} te factura por mes o por año, con factura electrónica. No hay cobro automático.</p></details>
</div>
</div></section>
"""
    )
    return pagina(
        "/precios",
        "Precios",
        f"Precios de lanzamiento en pesos, más IVA: Básico, Pro, Empresa y Escala. Prueba gratis de {DIAS_PRUEBA} días con {miles(CREDITOS_PRUEBA)} créditos. Errores, caché y fuera de cobertura no descuentan.",
        c,
    )


# La respuesta real de producción a PRIMERA_PREGUNTA (correos.EJEMPLO, solicitud
# req_01M6AEQ1Q10XH5SZP1ZYRMS212, 01-11-2026), recortada: sin la consulta interna ni la geometría.
SOBRE_PREDIO = {
    "contrato": "rt/1",
    "herramienta": "sinic_predio_en_punto@1",
    "estado": "encontrado",
    "datos": {
        "municipio": "SANTA MARTA",
        "numero_predial": "470010109000002580801800000308",
        "zona": "Urbana",
        "destinacion_economica": "Habitacional",
        "tipo_predio": "Predio.Privado",
    },
    "huella": "sha256:7a2cc96586df0f0f88c8a7231ba60a8888ae13e2741df86b5e1f1466baef1a0f",
    "procedencia": [
        {
            "entidad": "Instituto Geográfico Agustín Codazzi (IGAC)",
            "licencia": {"spdx": "CC-BY-SA-4.0", "uso_comercial": "si"},
            "servido_desde": "copia",
            "consultado_en": "2026-10-28T18:53:19Z",
            "completitud": {"vistos": 1, "total": 1, "truncado": False},
        }
    ],
    "avisos": ["Sale de la copia de Terrnova del 2026-10-28, no de la fuente en vivo."],
    "creditos": 10,
}
assert SOBRE_PREDIO["datos"]["numero_predial"] == EJEMPLO["predio"]
assert SOBRE_PREDIO["huella"].startswith(EJEMPLO["huella"].split("…")[0])
assert SOBRE_PREDIO["huella"].endswith(EJEMPLO["huella"].split("…")[1])
assert SOBRE_PREDIO["procedencia"][0]["licencia"]["spdx"] == EJEMPLO["licencia"]
assert str(SOBRE_PREDIO["creditos"]) == EJEMPLO["creditos"]
assert SOBRE_PREDIO["herramienta"].split("@")[0] == EJEMPLO["herramienta"]


def misma_consulta() -> str:
    """Pestañas: pegar en Claude Code, MCP y REST; al lado, la respuesta real (la misma por las tres)."""
    lon, lat = -74.1572, 11.2211
    hid = EJEMPLO["herramienta"]
    fam = CAT.herramientas[hid].familia
    pasos = {
        "claude": (
            "Pega en Claude Code",
            escape(COMANDO_CLAUDE.replace("TU_LLAVE", "$TERRNOVA_LLAVE"))
            + f'\n\n<span class="c"># y pregúntale:</span>\n{escape(PRIMERA_PREGUNTA)}',
        ),
        "mcp": (
            "MCP",
            f"POST https://terrnova.com/mcp/{fam}\nAuthorization: Bearer $TERRNOVA_LLAVE\n"
            "Content-Type: application/json\nAccept: application/json, text/event-stream\n\n"
            + escape(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {"name": hid, "arguments": {"lon": lon, "lat": lat}},
                    },
                    ensure_ascii=False,
                    indent=1,
                )
            ),
        ),
        "rest": (
            "REST",
            f"curl -s -X POST https://terrnova.com/v1/co/{fam}/{hid} \\\n"
            '  -H "Authorization: Bearer $TERRNOVA_LLAVE" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            + escape(f"  -d '{json.dumps({'lon': lon, 'lat': lat})}'"),
        ),
    }
    pest = "".join(
        f'<button type="button" role="tab" data-t="{k}" aria-selected="{"true" if i == 0 else "false"}"'
        f"{'' if i == 0 else ' tabindex="-1"'}>{t}</button>"
        for i, (k, (t, _)) in enumerate(pasos.items())
    )
    pres = "".join(
        f'<pre data-t="{k}" tabindex="0"{"" if i == 0 else " hidden"}><code>{cod}</code></pre>'
        for i, (k, (_, cod)) in enumerate(pasos.items())
    )
    resp = escape(json.dumps(SOBRE_PREDIO, ensure_ascii=False, indent=1))
    return f"""<div class="codigo apilado">
<div class="panel"><div class="pest" role="tablist" aria-label="Cómo hacer la consulta">{pest}</div>{pres}
<button class="copiar" type="button" data-copiar-pre>Copiar</button></div>
<div class="panel"><div class="pest"><span class="meta">respuesta real, recortada · 01-11-2026</span></div><pre tabindex="0" aria-label="Respuesta"><code>{resp}</code></pre></div>
</div>"""


def desarrolladores() -> str:
    perfiles = ", ".join(f"<code>{f}</code>" for f in POR_FAMILIA if f != "meta")
    c = (
        portada(
            "",
            "Conecta tu agente o tu sistema",
            "MCP para agentes, API REST para sistemas. La misma llave y el mismo contrato rt/1.",
            lado=lado_puertas(),
        )
        + f"""
<section class="seccion"><div class="envoltura doc">
<nav aria-label="En esta página"><a href="#inicio">Inicio rápido</a><a href="#consulta">Una consulta</a><a href="#mcp">MCP</a><a href="#perfiles">Perfiles</a><a href="#rest">API REST</a><a href="#contrato">Contrato rt/1</a><a href="#llaves">Llaves</a><a href="#errores">Errores</a><a href="#recursos">Recursos</a></nav>
<div class="prosa">
<h2 id="inicio" style="margin-top:0">Inicio rápido</h2>
<div class="instruccion">
<p class="et">Dale esta instrucción a tu agente y se configura solo.</p>
<p id="instruccion">{INSTRUCCION}</p>
<button class="boton s chico" type="button" data-copiar="#instruccion">Copiar instrucción</button>
</div>
<ol><li><b>Pide tu llave de prueba</b> (<a href="/precios#empezar">{miles(CREDITOS_PRUEBA)} créditos por {DIAS_PRUEBA} días</a>). Guárdala como secreto, nunca en el código.</li>
<li><b>Haz la primera consulta</b> (1 crédito):</li></ol>
<pre class="suelto"><code>export TERRNOVA_LLAVE=rt_live_...
curl -s -X POST https://terrnova.com/v1/co/territorio/dane_divipola_buscar \\
  -H "Authorization: Bearer $TERRNOVA_LLAVE" \\
  -H "Content-Type: application/json" \\
  -d '{{"nombre":"Cali"}}'</code></pre>
<p>Trae <code>"estado":"encontrado"</code>, los municipios en <code>datos.elementos</code> y la fuente (DANE) con su licencia en <code>procedencia</code>. Respeta las tildes: «Bogota» no encuentra «Bogotá».</p>
<ol start="3"><li><b>Mira tu saldo</b> con <code>GET /v1/uso</code>.</li></ol>

<h2 id="consulta">La misma consulta, tres caminos</h2>
<p>El predio en un punto de Santa Marta, pegado en Claude Code, por MCP o por la API REST. Por los tres llega el mismo sobre rt/1.</p>
{misma_consulta()}
<p>Funciona con {y_lista(FUNCIONA_CON)}, con las configuraciones de abajo. {y_lista(PIDEN_OAUTH)} todavía no conectan: sus conectores piden OAuth y Terrnova usa una llave en la cabecera. El inicio de sesión con OAuth llegará; mientras tanto, usa Claude Desktop con <code>mcp-remote</code> o la API.</p>

<h2 id="mcp">MCP</h2>
<p><i>Streamable HTTP</i>, con la llave en <code>Authorization</code>.</p>
<p>Claude Code:</p>
<pre class="suelto"><code>claude mcp add --transport http terrnova https://terrnova.com/mcp \\
  --header "Authorization: Bearer $TERRNOVA_LLAVE"</code></pre>
<p>Cursor y clientes con <code>url</code> y <code>headers</code>:</p>
<pre class="suelto"><code>{{
  "mcpServers": {{
    "terrnova": {{
      "url": "https://terrnova.com/mcp/territorio",
      "headers": {{ "Authorization": "Bearer rt_live_..." }}
    }}
  }}
}}</code></pre>
<p>Clientes solo stdio (Claude Desktop), con <code>mcp-remote</code>:</p>
<pre class="suelto"><code>{{
  "mcpServers": {{
    "terrnova": {{
      "command": "npx",
      "args": ["mcp-remote", "https://terrnova.com/mcp/ambiente",
               "--header", "Authorization:${{TERRNOVA_AUTH}}"],
      "env": {{ "TERRNOVA_AUTH": "Bearer rt_live_..." }}
    }}
  }}
}}</code></pre>

<h2 id="perfiles">Perfiles</h2>
<div class="desliza"><table class="tabla"><thead><tr><th>Ruta</th><th>Qué expone</th><th>Para</th></tr></thead><tbody>
<tr><td><code>/mcp</code></td><td>Las {N_HERR} herramientas, <code>ficha_lugar</code>, <code>ficha_empresa</code>, <code>ficha_lote</code>, <code>predio_en_punto</code> y <code>fuente_describir</code></td><td>Clientes que buscan herramientas solos, como Claude</td></tr>
<tr><td><code>/mcp/&lt;familia&gt;</code></td><td>Las de una familia</td><td>Un solo tema: lo más preciso y rápido</td></tr>
<tr><td><code>/mcp/catalogo</code></td><td>Pocas herramientas que buscan en el catálogo</td><td>Clientes con tope de herramientas (OpenAI: 128)</td></tr>
</tbody></table></div>
<p>Familias: {perfiles}. Todos traen las de nombre a código (1 crédito) y <code>fuente_describir</code> (gratis).</p>

<h2 id="rest">API REST</h2>
<p><code>POST /v1/co/&lt;familia&gt;/&lt;herramienta&gt;</code> con la entrada en JSON; la ficha de un lugar, <code>POST /v1/fichas</code>. Esquema en <a href="/openapi.json"><code>/openapi.json</code></a> y <a href="/docs"><code>/docs</code></a>.</p>
<div class="desliza"><table class="tabla"><thead><tr><th>Para</th><th>Dónde</th></tr></thead><tbody>
<tr><td>Lista de herramientas con su costo</td><td><code>GET /v1/herramientas</code></td></tr>
<tr><td>Ficha técnica de una fuente</td><td><code>GET /v1/fuentes/&#123;fuente_id&#125;</code></td></tr>
<tr><td>Saldo del mes</td><td><code>GET /v1/uso</code></td></tr>
<tr><td>Estado por fuente</td><td><code>GET /v1/estado</code></td></tr>
</tbody></table></div>
<p>Las rutas de catálogo son públicas y gratis.</p>

<h2 id="contrato">Contrato rt/1</h2>
<p>Toda consulta devuelve el mismo sobre:</p>
<div class="desliza"><table class="tabla"><thead><tr><th>Campo</th><th>Contenido</th></tr></thead><tbody>
<tr><td><code>estado</code></td><td><code>encontrado</code>, <code>no_encontrado</code>, <code>fuera_de_cobertura</code> o <code>parcial</code></td></tr>
<tr><td><code>datos</code></td><td>El resultado</td></tr>
<tr><td><code>huella</code></td><td><code>sha256</code> de <code>datos</code>, para verificar que no cambió</td></tr>
<tr><td><code>procedencia</code></td><td>Por fuente: entidad, URL, norma (si la hay), licencia, atribución, <code>servido_desde</code>, <code>consultado_en</code> y <code>completitud</code></td></tr>
<tr><td><code>avisos</code></td><td>Lo que debes saber: total desconocido, datos no recientes, copia vencida…</td></tr>
<tr><td><code>geo_result</code></td><td>Las geometrías, en EPSG:4326 (lon, lat)</td></tr>
<tr><td><code>creditos</code></td><td>Lo que costó esa consulta</td></tr>
</tbody></table></div>
<p><b>«No encontrado» no es «no se pudo».</b> Si la fuente no responde llega un error, nunca un sobre vacío; un dato viejo (<code>servido_desde: obsoleto</code>) siempre llega con aviso.</p>

<h2 id="llaves">Llaves</h2>
<div class="desliza"><table class="tabla"><thead><tr><th>Prefijo</th><th>Para qué</th></tr></thead><tbody>
<tr><td><code>rt_live_</code></td><td>Producción: licencia abierta verificada y dato público reutilizable, con aviso.</td></tr>
<tr><td><code>rt_test_</code></td><td>Evaluación: además, las fuentes con licencia por verificar, con aviso.</td></tr></tbody></table></div>
<p>Si una llave se filtra, la revocamos y te damos otra con el mismo saldo.</p>

<h2 id="errores">Errores</h2>
<p>En <code>application/problem+json</code> (RFC 9457), con un <code>code</code> estable y el <code>solicitud_id</code> para soporte.</p>
<div class="desliza"><table class="tabla"><thead><tr><th>HTTP</th><th><code>code</code></th><th>Qué hacer</th></tr></thead><tbody>
<tr><td class="n">400</td><td><code>parametro_invalido</code></td><td>Corregir la entrada; <code>param</code> dice cuál</td></tr>
<tr><td class="n">401</td><td><code>no_autenticado</code></td><td>Falta la llave o no es válida</td></tr>
<tr><td class="n">402</td><td><code>saldo_agotado</code></td><td>Se acabaron los créditos del mes; dice cuándo se renuevan</td></tr>
<tr><td class="n">403</td><td><code>sin_permiso</code>, <code>licencia_no_habilitada</code></td><td>La llave no cubre esa familia o esa fuente</td></tr>
<tr><td class="n">404</td><td><code>no_existe</code></td><td>La herramienta o la fuente no existe; la ficha de fuente sugiere ids parecidos</td></tr>
<tr><td class="n">429</td><td><code>limite_tasa</code></td><td>Espera lo que dice <code>Retry-After</code></td></tr>
<tr><td class="n">502</td><td><code>fuente_no_disponible</code>, <code>fuente_respuesta_invalida</code></td><td><b>No se pudo:</b> la fuente oficial falló o respondió algo que no se puede leer; reintenta más tarde</td></tr>
<tr><td class="n">504</td><td><code>fuente_lenta</code></td><td><b>No se pudo:</b> la fuente no respondió a tiempo</td></tr>
<tr><td class="n">500</td><td><code>error_interno</code></td><td>Falla nuestra; escríbenos con el <code>solicitud_id</code></td></tr>
</tbody></table></div>
<p>Ráfaga de 20 consultas y 60 por minuto por llave. Reintenta con espera creciente.</p>

<h2 id="recursos">Recursos</h2>
<ul><li><a href="/llms.txt"><code>/llms.txt</code></a>: el catálogo en texto para agentes.</li>
<li><a href="/.well-known/mcp/server-card.json"><code>/.well-known/mcp/server-card.json</code></a>: la tarjeta del servidor MCP.</li>
<li><a href="/estado"><code>/estado</code></a>: el estado de la puerta y de cada fuente según su canario diario.</li>
<li>Soporte: <a href="mailto:{CORREO}">{CORREO}</a>, de lunes a viernes de 8:00 a 18:00, hora de Colombia, sin festivos.</li></ul>
</div>
</div></section>
"""
    )
    return pagina(
        "/desarrolladores",
        "Desarrolladores",
        "Conecta tu agente por MCP o tu sistema por API REST. Inicio rápido, perfiles por familia, contrato rt/1 y errores.",
        c,
    )


def aliados() -> str:
    c = (
        portada(
            "",
            "Quién hace Terrnova",
            "GeoAI LATAM hace Terrnova y mantiene una comunidad abierta de inteligencia geoespacial. Atalaya Mapas es un proyecto aliado de cartografía.",
        )
        + """
<section class="seccion"><div class="envoltura" style="display:grid;gap:0">
<div class="aliado"><img src="/img/geoai-latam.webp" alt="GeoAI LATAM" width="640" height="144">
<div><h2 class="t3">GeoAI LATAM</h2><p class="suave" style="margin-top:8px">GeoAI LATAM hace Terrnova y mantiene una comunidad abierta de inteligencia geoespacial para Latinoamérica: proyectos abiertos y tutoriales.</p>
<p style="margin-top:12px"><a class="enlace dominio" href="https://geoailatam.terrnova.com/">geoailatam.terrnova.com</a></p></div></div>
<div class="aliado"><div class="pendiente">Atalaya Mapas</div>
<div><h2 class="t3">Atalaya Mapas</h2><p class="suave" style="margin-top:8px">Proyecto aliado de cartografía.</p></div></div>
</div></section>
"""
    )
    return pagina(
        "/aliados",
        "Aliados",
        "GeoAI LATAM hace Terrnova y mantiene una comunidad abierta de inteligencia geoespacial. Atalaya Mapas, proyecto aliado de cartografía.",
        c,
    )


def contacto() -> str:
    c = (
        portada(
            "",
            "Escríbenos",
            "Respondemos de lunes a viernes, de 8:00 a 18:00 (hora de Colombia), sin festivos.",
        )
        + f"""
<section class="seccion"><div class="envoltura">
<div class="rejilla r2" style="gap:48px;align-items:start">
<div>{formulario_contacto()}</div>
<div class="bloque"><h2 class="t3">Atajos</h2><ul class="lista">
<li>Llave de prueba: <a class="enlace" href="/precios#empezar">pídela aquí</a>. Te llega un enlace al correo; al confirmarlo ves tu llave.</li>
<li>Un proyecto: qué quieres decidir, dónde y para cuándo.</li>
<li>Soporte: incluye el <code>solicitud_id</code> y mira antes <a class="enlace" href="/estado">el estado</a>.</li>
</ul></div>
</div>
<p class="fuente-dato" style="margin-top:24px">{CORREO}</p>
</div></section>
"""
    )
    return pagina(
        "/contacto",
        "Contacto",
        "Escríbenos para un proyecto, para pedir tu llave o para soporte.",
        c,
    )


def legal(ruta: str, titulo: str, entrada: str, puntos: list[str]) -> str:
    c = (
        portada("", titulo, entrada)
        + f"""
<section class="seccion"><div class="envoltura"><div class="prosa">
<p>El texto completo está en revisión legal y se publicará en esta página. Mientras tanto, estas reglas ya se cumplen en el producto:</p>
<ul>{"".join(f"<li>{p}</li>" for p in puntos)}</ul>
<p>Preguntas: <a href="mailto:{CORREO}">{CORREO}</a>.</p>
</div></div></section>
"""
    )
    return pagina(ruta, titulo, entrada, c)


def no_encontrada() -> str:
    c = portada(
        "",
        "Aquí no hay nada",
        "La página no existe o cambió de lugar.",
        '<div class="botones" style="margin-top:8px"><a class="boton p" href="/">Ir al inicio</a><a class="boton s" href="/fuentes">Buscar una herramienta</a></div>',
    )
    return pagina("/404", "Página no encontrada", "La página no existe.", c, indexar=False)


FAVICON = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#0E2A22"/>'
    '<path d="M7 28V15a9 9 0 0 1 18 0v13" fill="none" stroke="#F3EFE4" stroke-width="2.6"/>'
    '<path d="M12 28V15.5a4 4 0 0 1 8 0V28z" fill="#E0A13A"/></svg>\n'
)


def paginas() -> dict[str, str]:
    p = {
        "index.html": inicio(),
        "servicios.html": servicios(),
        "fuentes.html": fuentes(),
        "precios.html": precios(),
        "desarrolladores.html": desarrolladores(),
        "aliados.html": aliados(),
        "contacto.html": contacto(),
        "terminos.html": legal(
            "/terminos",
            "Términos de servicio",
            "Las condiciones de uso de Terrnova.",
            [
                "Los datos vienen de fuentes oficiales con su licencia; al reutilizarlos, citas la atribución que trae cada respuesta.",
                "Las llaves de producción no ven fuentes con licencia por verificar; cada respuesta dice su licencia.",
                "Los créditos se renuevan el día 1 de cada mes y no se acumulan.",
                "Los errores, la caché y lo que está fuera de cobertura no descuentan créditos.",
            ],
        ),
        "privacidad.html": legal(
            "/privacidad",
            "Privacidad",
            "Qué datos tratamos y cómo.",
            [
                "No hay búsquedas de personas por cédula ni por nombre, ni perfiles de personas.",
                "Los campos que salen de cada fuente están en una lista blanca.",
                "Guardamos de tu llave solo su huella (HMAC), nunca la llave.",
                "Medimos el uso de cada llave; los créditos se descuentan del saldo de tu organización.",
                f"Por cada consulta guardamos, ligados a tu llave, la herramienta, los créditos, el resultado y la hora; lo que preguntaste, no. Las respuestas quedan en caché hasta {RETENCION_DIAS} días, sin saber quién las pidió.",
                "Si pides una llave o nos escribes, guardamos tu nombre, tu correo, tu organización y lo que nos cuentes, para darte la llave y responderte. De tu conexión solo guardamos una huella (HMAC) de la IP, para limitar abusos; nunca la IP.",
                "No vendemos ni compartimos esos datos. Para verlos, corregirlos o borrarlos, escríbenos.",
            ],
        ),
        "404.html": no_encontrada(),
    }
    rutas = [
        "/",
        "/servicios",
        "/fuentes",
        "/precios",
        "/desarrolladores",
        "/aliados",
        "/contacto",
        "/terminos",
        "/privacidad",
    ]
    p["sitemap.xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{DOMINIO}{r}</loc></url>\n" for r in rutas)
        + "</urlset>\n"
    )
    p["robots.txt"] = (
        f"User-agent: *\nAllow: /\nDisallow: /v1/\nDisallow: /mcp\nSitemap: {DOMINIO}/sitemap.xml\n"
    )
    p["favicon.svg"] = FAVICON
    p["datos/catalogo.json"] = catalogo_json() + "\n"
    return p


# La escena del héroe importa comun3d.js: el import lleva la huella del archivo (?v=), así se puede
# guardar en caché mucho tiempo como lo demás. Es lo único que se toca de escena-predios.js.
ESCENA = PUBLICO / "js" / "escena-predios.js"


def escena_versionada() -> str:
    texto = ESCENA.read_text(encoding="utf-8")
    v = version("/js/comun3d.js").split("?v=")[1]
    nuevo, n = re.subn(
        r"from '\./comun3d\.js(?:\?v=[0-9a-f]+)?'", f"from './comun3d.js?v={v}'", texto
    )
    assert n == 1, "escena-predios.js ya no importa comun3d.js"
    return nuevo


def main() -> int:
    revisar = "--revisar" in sys.argv
    viejas = []
    if revisar:
        if ESCENA.read_text(encoding="utf-8") != escena_versionada():
            viejas.append("js/escena-predios.js")
    else:
        ESCENA.write_text(escena_versionada(), encoding="utf-8", newline="\n")
    for nombre, texto in modulos_versionados().items():
        f = PUBLICO / "js" / nombre
        if revisar:
            if f.read_text(encoding="utf-8") != texto:
                viejas.append(f"js/{nombre}")
        else:
            f.write_text(texto, encoding="utf-8", newline="\n")
    datos_fig = FIGURAS / "datos.json"
    if revisar:
        if datos_fig.read_text(encoding="utf-8") != datos_figuras_json():
            viejas.append("figuras/datos.json")
    else:
        datos_fig.write_text(datos_figuras_json(), encoding="utf-8", newline="\n")
        sello = f'data-datos="{huella_figuras()}"'
        svgs = [SVG_FIGURAS / f"{n}{c}.svg" for n in NOMBRES_FIGURAS for c in ("", "-viva", "-2")]
        svgs = [s for s in svgs if not s.name.endswith("-2.svg") or s.exists()]
        if not all(s.exists() and sello in s.read_text(encoding="utf-8") for s in svgs):
            import shutil
            import subprocess

            if shutil.which("node"):
                # svgo (web/figuras/package.json) optimiza los SVG; se instala la primera vez
                if not (FIGURAS / "node_modules" / "svgo").exists():
                    npm = shutil.which("npm") or "npm"
                    subprocess.run([npm, "ci", "--no-audit", "--no-fund"], cwd=FIGURAS, check=True)
                subprocess.run(["node", str(FIGURAS / "construir.mjs")], check=True)
    for nombre, texto in paginas().items():
        f = PUBLICO / nombre
        if revisar:
            if not f.exists() or f.read_text(encoding="utf-8") != texto:
                viejas.append(nombre)
        else:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(texto, encoding="utf-8", newline="\n")
    if viejas:
        print("Páginas desactualizadas (corre uv run python web/construir.py):", ", ".join(viejas))
        return 1
    if not revisar:
        print(f"Sitio construido en {PUBLICO} ({N_HERR} herramientas, {N_FUENTES} fuentes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
