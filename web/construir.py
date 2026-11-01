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

from terranova.catalogo import cargar  # noqa: E402

DOMINIO = "https://terrnova.com"
CORREO = "soporte@terrnova.com"
# La misma versión que importa web/publico/js/comun3d.js.
THREE_URL = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"

# Créditos al mes por plan (cuota.py, ADR-0029) y tarifa por tipo de pregunta (enmienda de la ADR-0010).
PLANES = [
    ("Gratis", 1_500),
    ("Básico", 25_000),
    ("Pro", 110_000),
    ("Empresa", 375_000),
    ("Escala", 1_100_000),
]
TARIFA = [
    ("código", 1, "de nombre a código", "dane_divipola_buscar"),
    ("registro", 2, "un registro o una serie simple", "banrep_trm_recientes"),
    ("agregado", 5, "agregados o búsqueda de texto", "contratos de una entidad"),
    ("punto", 10, "espacial en un punto", "sinic_predio_en_punto"),
    ("zona", 20, "espacial en una zona o un ráster", "áreas protegidas en una zona"),
]
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
    ("/#precios", "Precios"),
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


# La llave del alta automática (ADR-0034): pocos créditos y vencimiento. Salen del código.
sys.path.insert(0, str(RAIZ.parent / "src"))
from terranova.alta import ASUNTOS, VIGENCIA_LLAVE  # noqa: E402
from terranova.cuota import NIVELES  # noqa: E402

CREDITOS_PRUEBA = NIVELES["prueba"]
DIAS_PRUEBA = VIGENCIA_LLAVE.days

TRAMPA = (
    '<label class="trampa" aria-hidden="true">No llenes este campo'
    '<input name="web" tabindex="-1" autocomplete="off"></label>'
)
ACEPTO = (
    '<label class="casilla"><input type="checkbox" name="acepto" value="si" required> Acepto la '
    '<a class="enlace" href="/privacidad">política de privacidad</a>.</label>'
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


ASUNTOS_CONTACTO = list(ASUNTOS.items())  # los mismos que acepta la puerta


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
<nav class="menu" aria-label="Principal">{menu}</nav>
<div class="der"><a href="/estado">{PULSO}Estado</a><a href="/contacto">Contacto</a><a class="boton s chico" href="/precios#empezar">Empieza gratis</a></div>
<button class="abrir" type="button" aria-expanded="false" aria-label="Abrir el menú"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
</div></header>"""


PIE = f"""<footer class="pie-sitio"><div class="envoltura">
<div class="arr">
<div><a class="marca" href="/">{simbolo("#F3EFE4", "#F3EFE4", "#E0A13A")}Terrnova</a>
<p class="desc">Datos oficiales de Colombia con su fuente y su prueba, y la analítica, la automatización y los agentes encima. Licencia revisada por fuente y nunca perfiles de personas.</p></div>
<div><h2>Producto</h2><ul><li><a href="/fuentes">Fuentes y herramientas</a></li><li><a href="/precios">Precios</a></li><li><a href="/estado">Estado del servicio</a></li><li><a href="/servicios">Servicios</a></li></ul></div>
<div><h2>Desarrolladores</h2><ul><li><a href="/desarrolladores">Guía de conexión</a></li><li><a href="/docs">API REST (OpenAPI)</a></li><li><a href="/llms.txt">llms.txt</a></li><li><a href="/desarrolladores#contrato">Contrato rt/1</a></li></ul></div>
<div><h2>Empresa</h2><ul><li><a href="/aliados">Aliados</a></li><li><a href="/contacto">Contacto</a></li><li><a href="mailto:{CORREO}">{CORREO}</a></li><li><a href="/terminos">Términos</a> · <a href="/privacidad">Privacidad</a></li></ul></div>
</div>
<div class="ab"><span>© 2026 Terrnova · terrnova.com</span><span>4,6097 N · 74,0817 W · Bogotá</span></div>
</div></footer>"""


def pagina(
    ruta: str, titulo: str, descripcion: str, cuerpo: str, scripts: tuple[str, ...] = ()
) -> str:
    canon = DOMINIO + (ruta if ruta != "/" else "/")
    tit = titulo if ruta == "/" else f"{titulo} · Terrnova"
    mods = "".join(f'\n<script type="module" src="/js/{s}"></script>' for s in scripts)
    if any(s.startswith("escena-") for s in scripts):
        # three.js empieza a bajar con la página, no cuando el módulo de la escena lo pide.
        mods = f'\n<link rel="modulepreload" href="{THREE_URL}" crossorigin>' + mods
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(tit)}</title>
<meta name="description" content="{escape(descripcion)}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Terrnova">
<meta property="og:title" content="{escape(tit)}">
<meta property="og:description" content="{escape(descripcion)}">
<meta property="og:url" content="{canon}">
<meta property="og:locale" content="es_CO">
<meta name="theme-color" content="#F6F7F4">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="/estilo.css">
<script src="/js/sitio.js" defer></script>{mods}
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
    tope = max(c for _, c, _, _ in TARIFA)
    cols = "".join(
        f'<div class="col"><b>{c}</b><i style="--v:{c / tope:.3f}"></i><span>{t}</span></div>'
        for t, c, _, _ in TARIFA
    )
    return f"""<figure class="lado-fig escalera"><figcaption>Créditos por consulta</figcaption><div class="cols">{cols}</div>
<p class="fuente-dato">caché, errores y «fuera de cobertura» no descuentan</p></figure>"""


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
            f"<p>{escape(y_lista(sis[nom]))}</p></li>"
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


# Preguntas por sector: herramientas reales del catálogo (la construcción falla si alguna no existe).
SECTORES = [
    (
        "Legal y cumplimiento",
        "Normas vigentes, jurisprudencia y sanciones, para conceptos, auditorías y debida diligencia.",
        [
            "suin_norma",
            "corte_constitucional_sentencia",
            "funcionpublica_normas_buscar",
            "creg_resolucion_buscar",
            "sic_sanciones_por_sector",
        ],
    ),
    (
        "Agro y exportación",
        "Debida diligencia de un lote antes de exportar: áreas protegidas, pérdida de bosque, cobertura del suelo y territorios étnicos.",
        [
            "pnn_areas_protegidas_en_punto",
            "sinchi_perdida_bosque_en_punto",
            "esa_cobertura_suelo_en_punto",
            "ant_resguardos_en_punto",
            "upra_eva_cultivos_municipio",
        ],
    ),
    (
        "Inmobiliario y construcción",
        "El predio, lo que dice el POT, las amenazas y el valor del suelo, antes de comprar o de diseñar.",
        [
            "igac_predio_en_punto",
            "sdp_tratamiento_urbanistico_en_punto",
            "sdp_amenaza_movimiento_masa_en_punto",
            "igac_zona_geoeconomica_en_punto",
            "igac_compraventas_municipio",
        ],
    ),
    (
        "Banca y crédito",
        "Contexto de una empresa o de un crédito rural: registro mercantil, estados financieros, precio de la tierra e indicadores.",
        [
            "rues_empresa_por_nit",
            "supersociedades_situacion_financiera",
            "upra_precio_tierra_en_punto",
            "banrep_trm_recientes",
            "dane_ipm_municipio",
        ],
    ),
    (
        "Contratación pública",
        "Seguimiento de contratos, entidades y proyectos de regalías en SECOP y en el DNP.",
        [
            "secop_contratos_entidad",
            "secop_ejecucion_contrato",
            "secop_contratos_proveedor",
            "secop_sanciones_contrato",
            "dnp_proyectos_sgr_municipio",
        ],
    ),
    (
        "Gobierno y territorio",
        "Los indicadores de un municipio para planear, priorizar o reportar.",
        [
            "dane_poblacion_proyectada_municipio",
            "men_educacion_municipio",
            "ins_calidad_agua_municipio",
            "ideam_alertas_deslizamiento_municipio",
            "uariv_victimas_municipio",
        ],
    ),
]


# Soluciones de ejemplo por sector: lo que se construye encima de la puerta con las herramientas del
# panel. Son ilustrativas (lo posible, no clientes) y van selladas.
CAPAS = ("Datos", "Analítica", "Automatización", "Agentes")
SOLUCIONES = {
    "Banca y crédito": [
        ("Analítica", "La empresa y el predio en garantía, revisados antes del crédito."),
        ("Automatización", "Aviso si un cliente cambia su matrícula mercantil."),
    ],
    "Contratación pública": [
        ("Analítica", "Contratos, multas y sanciones de un contratista antes de adjudicar."),
        ("Agentes", "Un asistente que dice cuánto contrató el municipio y con quién."),
    ],
    "Legal y cumplimiento": [
        ("Agentes", "Conceptos que citan la norma vigente y la sentencia."),
        ("Automatización", "Alertas cuando cambia una norma que sigues."),
    ],
    "Agro y exportación": [
        (
            "Analítica",
            "Debida diligencia EUDR por finca: áreas protegidas, bosque y territorios étnicos.",
        ),
        ("Automatización", "Revisión periódica de las fincas de tus proveedores."),
    ],
    "Inmobiliario y construcción": [
        ("Analítica", "La ficha de un predio: catastro, POT, amenazas y valor del suelo."),
        ("Agentes", "Qué se puede construir en un lote de Bogotá, para el equipo comercial."),
    ],
    "Gobierno y territorio": [
        ("Analítica", "Un tablero municipal comparado con sus pares."),
        ("Automatización", "Aviso cuando cambia un contrato o un proyecto de regalías."),
    ],
}
ORDEN_SECTORES = [
    "Banca y crédito",
    "Contratación pública",
    "Legal y cumplimiento",
    "Agro y exportación",
    "Inmobiliario y construcción",
    "Gobierno y territorio",
]


def sectores() -> str:
    por_id = {h.id: h for h in HERR}
    assert sorted(ORDEN_SECTORES) == sorted(s[0] for s in SECTORES) == sorted(SOLUCIONES)
    assert all(c in CAPAS for v in SOLUCIONES.values() for c, _ in v)
    orden = sorted(SECTORES, key=lambda s: ORDEN_SECTORES.index(s[0]))
    pest, paneles = [], []
    for i, (nombre, _, ids) in enumerate(orden):
        sel = "true" if i == 0 else "false"
        pest.append(
            f'<button type="button" role="tab" id="s-p{i}" aria-controls="s-t{i}" aria-selected="{sel}"'
            f"{'' if i == 0 else ' tabindex="-1"'}>{nombre}</button>"
        )
        filas = []
        for hid in ids[:3]:
            h = por_id[hid]
            ent = nombre_entidad(CAT.fuentes[h.fuente].entidad)
            filas.append(
                f'<li><p>{escape(h.pregunta)}</p><span class="id"><code>{h.id}</code> {escape(ent)}</span></li>'
            )
        sols = "".join(
            f'<li><span class="rotulo">{c}</span><p>{escape(s)}</p></li>'
            for c, s in SOLUCIONES[nombre]
        )
        paneles.append(
            f'<div class="panel-s" role="tabpanel" id="s-t{i}" aria-labelledby="s-p{i}"{"" if i == 0 else " hidden"}>'
            f'<h4 class="sub-s">Lo que se construye {SELLO_I}</h4><ul class="soluciones">{sols}</ul>'
            f'<h4 class="sub-s">Con herramientas como</h4><ol>{"".join(filas)}</ol></div>'
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
            "Un expediente por ítem, en PDF y en datos",
            "Cada hallazgo con su entidad y su fecha",
            "Los casos dudosos, aparte",
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
            "Un tablero web con tu marca",
            "Un informe periódico",
            "Cada cifra enlazada a su entidad",
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
            "Alertas por correo o en tu sistema",
            "Un resumen semanal",
            "El registro de cada cambio, con fecha y fuente",
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

METODO = [
    ("Nos cuentas", "Qué quieres decidir."),
    ("Precio fijo", "Antes de empezar."),
    ("Hacemos el trabajo", "Cada cifra contrastada con su fuente."),
    ("Recibes el resultado", "Con la prueba de cada dato."),
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
HALLAZGO_REVISION = [1, None, 2]

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
    "banrep_trm_recientes",
    "ins_calidad_agua_municipio",
    "pnn_areas_protegidas_en_punto",
    "secop_contratos_municipio",
    "rues_empresa_por_nit",
    "igac_predio_en_punto",
    "upra_precio_tierra_rural_municipio",
    "men_educacion_municipio",
]
OTRAS_ASISTENTE = [
    "icfes_saber11_municipio",
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
    ("icfes_saber11_municipio", "Saber 11", "puntaje promedio, por periodo"),
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
                {"p": por_id[i].pregunta, "e": entidad(i), "l": licencia_corta(f.licencia.spdx)}
            )
        nodos = list(
            dict.fromkeys([p["e"] for p in preguntas] + [entidad(i) for i in OTRAS_ASISTENTE])
        )
        return {"preguntas": preguntas, "nodos": nodos}
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
            "prueba": ["banrep_trm_recientes"],
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
    """Huella de lo que decide el dibujo: los datos, los scripts que dibujan y el kit."""
    import hashlib

    h = hashlib.sha256(datos_figuras_json().encode("utf-8"))
    scripts = sorted(f.name for f in FIGURAS.glob("*.mjs"))
    for f in [*scripts, "kit/iso-kit.mjs"]:
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


def figura(
    nombre: str, lectura: str, pista: str = "", clase: str = "", ilustrativo: bool = False
) -> str:
    """Una figura integrada en la sección: sin marco, con su lectura en una línea debajo.

    El SVG vive aparte (web/publico/img/figuras) y figuras.js lo trae cuando se acerca a la vista;
    el hueco ya tiene su proporción, así la página no salta."""
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
    pista_html = f'<span class="pista">{pista}</span>' if pista else ""
    if ilustrativo:
        pista_html = f"<span>{pista_html}{SELLO_I}</span>"
    return (
        f'<figure class="fig-iso{" " + clase if clase else ""}" data-figura="{nombre}">'
        f'<div class="lienzo" tabindex="0" role="group" aria-label="{etiqueta.group(1)}" '
        f'data-src="/img/figuras/{nombre}.svg?v={huella.group(1)}" style="aspect-ratio:{w}/{h}"></div>'
        f'<figcaption class="lectura-l"><span data-lectura aria-live="off">{lectura}</span>{pista_html}</figcaption>'
        "</figure>"
    )


def figura_capas() -> str:
    d = datos_figuras()["capas"]
    return figura(
        "capas",
        f"datos · {d['fuentes']} fuentes · {d['herramientas']} herramientas",
        "pasa el puntero por los módulos",
    )


def figura_ruta() -> str:
    t0 = datos_figuras()["ruta"]["turnos"][0]
    return figura(
        "ruta",
        f"{escape(t0['corta'])} → <code>{t0['herramienta']}</code> → {t0['entidad']}",
        "flechas o puntero: otra pregunta",
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


def figura_servicio(sid: str) -> str:
    """La figura de un servicio; vacía si todavía no tiene (la fila queda a una columna)."""
    if sid not in NOMBRES_FIGURAS:
        return ""
    if sid == "asistente":  # preguntas, entidades y licencias reales: sin sello
        q = datos_figuras()["asistente"]["preguntas"][0]
        lectura = f"{escape(q['p'])} → {q['e']} · {q['l']}"
        return figura(sid, lectura, "pasa el puntero por las tomas")
    lectura, pista = LECTURA_SERVICIO[sid]
    if sid == "tablero":
        i0 = datos_figuras()["tablero"]["indicadores"][0]
        lectura = lectura.format(t=i0["t"].lower(), e=i0["e"], m=i0["m"])
    return figura(sid, lectura, pista, ilustrativo=True)


def con_datos(sid: str) -> str:
    """Las entidades que usa la figura de un servicio, del catálogo (todas publicadas)."""
    d = datos_figuras()
    if sid == "revision":
        ents = [f["e"] for t in d["revision"]["tipos"] for f in t["fuentes"]]
    elif sid == "tablero":
        ents = [x["e"] for x in d["tablero"]["indicadores"]]
    elif sid == "vigilancia":
        ents = [c["e"] for c in d["vigilancia"]["carriles"]]
    else:
        return f"las {N_HERR} herramientas del catálogo"
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


def servicios_landing() -> str:
    """En la portada, los cuatro servicios en una rejilla de dos por dos: figura, título y una frase."""
    celdas = "".join(
        f'<article class="serv-c" id="{s["id"]}">{figura_servicio(str(s["id"]))}'
        f'<h3 class="t3">{s["titulo"]}</h3><p>{s["texto"]}</p>'
        f'<a class="enlace" href="/servicios#{s["id"]}">Ver el servicio</a></article>'
        for s in SERVICIOS
    )
    return f'<div class="servs-c">{celdas}</div>'


# Las capas de la prueba: valores de la respuesta real de banrep_trm_recientes, capturada el
# 2026-10-29.
CAPAS_PRUEBA = [
    ("dato", "3.162,35 pesos por dólar", "TRM del 29-10-2026 · encontrado"),
    ("procedencia", "Banco de la República", "la entidad que publica el dato"),
    ("licencia", "aviso legal del Banco, uso comercial sí", "verificada para esta fuente"),
    ("servido_desde", "la fuente, en vivo", "consultado el 29-10-2026, 07:14 UTC"),
    ("huella", "sha256:ac30c9f5…", "para comprobar que no cambió"),
]
NOTAS_PRUEBA = [
    ("El dato y su estado", "Encontrado, no encontrado, parcial o fuera de cobertura."),
    ("Procedencia", "La entidad, la URL de la consulta y la norma."),
    (
        "Licencia",
        f"{N_VERIFICADAS} fuentes verificadas; {N_FUENTES - N_VERIFICADAS} de dato público, con aviso.",
    ),
    ("De dónde se sirvió", "En vivo, copia oficial o caché. Lo viejo llega con aviso."),
    ("Huella", "Para comprobar después que no cambió."),
]


def prueba_html() -> str:
    notas = "".join(
        f'<li data-capa="{i}"><b>{t}</b><span>{d}</span></li>'
        for i, (t, d) in enumerate(NOTAS_PRUEBA)
    )
    d0 = CAPAS_PRUEBA[0]
    fig = figura("prueba", f"{d0[0]} · {d0[1]}", "pasa el puntero por las pestañas")
    return f"""<div class="con-fig inv-l prueba">
{fig}
<div class="cab"><h2 class="t2">Cada respuesta trae su prueba</h2>
<p class="entrada">Quién publica el dato, con qué licencia, de dónde salió y su huella. En la respuesta, no en un anexo.</p>
<ul class="lista-l notas-p">{notas}</ul>
<p class="fuente-dato">banrep_trm_recientes · <span class="sello">capturado el 29-10-2026</span> · <a class="enlace" href="/desarrolladores#contrato">ver el contrato rt/1</a></p></div>
</div>"""


def planes_html(detalle: bool = True) -> str:
    # Un solo botón primario (Gratis): ningún plan de pago se destaca sin un dato que lo respalde.
    filas = []
    for n, c in PLANES:
        boton = (
            '<a class="boton p" href="/precios#empezar">Empieza gratis</a>'
            if n == "Gratis"
            else f'<a class="boton s" href="/contacto?asunto=plan-{n.lower().replace("á", "a")}">Pedir este plan</a>'
        )
        filas.append(
            f'<div class="plan"><h3>{n}</h3><b>{miles(c)}</b><span>créditos al mes</span>'
            + (
                f'<span class="eq">≈ {miles(c // 10)} consultas de predio por punto</span>'
                if detalle
                else ""
            )
            + f"{boton}</div>"
        )
    return '<div class="planes">' + "".join(filas) + "</div>"


def tarifa_html() -> str:
    filas = "".join(
        f'<tr><td>{t}</td><td class="n">{c}</td><td>{d}</td><td><code>{e}</code></td></tr>'
        if "_" in e
        else f'<tr><td>{t}</td><td class="n">{c}</td><td>{d}</td><td>{e}</td></tr>'
        for t, c, d, e in TARIFA
    )
    return f"""<div class="desliza"><table class="tabla"><thead><tr><th>Tipo de pregunta</th><th>Créditos</th><th>Qué es</th><th>Ejemplo</th></tr></thead>
<tbody>{filas}<tr><td>ficha de un lugar</td><td class="n">≤ 50</td><td>la suma de sus partes</td><td><code>POST /v1/fichas</code></td></tr></tbody></table></div>"""


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
<h1 class="t0">Del dato oficial a la solución</h1>
<p class="entrada">{N_FUENTES} fuentes oficiales de {N_ENTIDADES} entidades, cada dato con su fuente y su licencia. Encima, la analítica, la automatización y los agentes de tu equipo.</p>
<div class="botones"><a class="boton p" href="/precios#empezar">Conecta tu agente gratis</a><a class="boton s" href="/contacto?asunto=proyecto">Cuéntanos qué quieres resolver</a></div>
</div></div>
<div class="envoltura h-consola">{consola()}</div>
</section>

<section class="seccion capas-l" id="capas"><div class="envoltura">
<div class="con-fig">
<div class="cab">
<h2 class="t2">Una capa de datos y tres encima</h2>
<p class="entrada">La capa de datos es el producto y empieza gratis. Lo demás se construye sobre ella.</p>
<ul class="lista-l">
<li class="vivo"><b>Datos</b><span>{N_FUENTES} fuentes por MCP o API REST</span></li>
<li><b>Analítica</b><span>Cruces, revisiones y tableros</span></li>
<li><b>Automatización</b><span>Vigilancias y alertas con registro</span></li>
<li><b>Agentes</b><span>Asistentes que citan la fuente</span></li>
</ul>
<p class="enlaces"><a class="enlace" href="/desarrolladores">Cómo se conecta</a><a class="enlace" href="#servicios">O lo construimos contigo</a></p>
</div>
{figura_capas()}
</div>
</div></section>

<section class="seccion" id="fuentes"><div class="envoltura">
<div class="cab">
<h2 class="t2">Soluciones por sector</h2>
<p class="entrada">Lo que se construye en cada sector y con qué herramientas.</p>
</div>
{sectores()}
<p class="mas-s"><a class="enlace" href="/fuentes">Ver las {N_HERR} herramientas</a></p>
</div></section>

<section class="seccion sup servicios-l" id="servicios"><div class="envoltura">
<div class="cab">
<h2 class="t1">O lo construimos contigo</h2>
<p class="entrada">Nos cuentas qué quieres resolver y lo construimos sobre la capa de datos, a precio fijo.</p>
</div>
{servicios_landing()}
<div class="botones fin-serv"><a class="boton s" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a><a class="boton s" href="/servicios">Ver los servicios</a></div>
</div></section>

<section class="seccion" id="por-que"><div class="envoltura">
<div class="con-fig inv-l">
{figura_ruta()}
<div class="cab">
<h2 class="t2">Por qué no basta con buscar en la web</h2>
<p class="entrada">Una decisión necesita el dato oficial, de dónde salió y si se puede usar.</p>
<ul class="lista-l">
<li><b>Un contrato</b><span>{N_ENTIDADES} entidades que publican a su manera responden igual.</span></li>
<li><b>Bien contado</b><span>SECOP repite un contrato por cada estado; lo contamos una vez.</span></li>
<li><b>Probado a diario</b><span>Contra un dato medido en la fuente. <a class="enlace" href="/estado">Ver el estado</a></span></li>
<li><b>Sin LLM ni personas</b><span>Misma pregunta, misma consulta. Nada por cédula o nombre.</span></li>
</ul>
<p class="fuente-dato">Pitalito 2025 en SECOP: $174.000 M sumado tal cual, $63.157 M contado bien · medido el 22-10-2026</p>
</div>
</div>
</div></section>

<section class="seccion"><div class="envoltura">
{prueba_html()}
</div></section>

<section class="seccion" id="precios"><div class="envoltura">
<div class="cab">
<h2 class="t2">Precios</h2>
<p class="entrada">La capa de datos, por plan mensual y desde gratis. Los servicios, a precio fijo.</p>
</div>
{planes_html(detalle=False)}
<p class="pie-p"><a class="enlace" href="/precios">Créditos por tipo de consulta</a></p>
</div></section>

<section class="seccion sup"><div class="envoltura cierre">
<div class="cab" style="margin:0"><h2 class="t2">Empieza por lo que quieres resolver</h2></div>
<div class="botones"><a class="boton p" href="/precios#empezar">Conecta tu agente gratis</a><a class="boton s" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a></div>
</div>
<div class="envoltura aliados-fila">
<span class="rotulo">Aliados</span>
<a href="/aliados"><img src="/img/geoai-latam.webp" alt="GeoAI LATAM" width="200" height="45" loading="lazy"></a>
<a href="/aliados" class="t3">Atalaya Mapas</a>
</div></section>
"""
    return pagina(
        "/",
        "Terrnova · Del dato oficial a la solución",
        f"Una capa de datos con {N_FUENTES} fuentes oficiales, de Colombia y algunas globales, y, encima, analítica, automatizaciones y agentes, con la fuente y la licencia de cada dato.",
        c,
        ("escena-predios.js", "figuras.js"),
    )


# Lo inventado lleva el sello.
SELLO_I = '<span class="sello-i">ilustrativo</span>'


def servicios() -> str:
    indice = "".join(f'<a href="#{s["id"]}">{s["titulo"]}</a>' for s in SERVICIOS)
    bloques = "".join(
        f'<section class="sv-det{" par" if i % 2 else ""}"><div class="envoltura">'
        f"{servicio_fila(s, i)}</div></section>"
        for i, s in enumerate(SERVICIOS)
    )
    pasos = "".join(f"<li><b>{a}</b><span>{b}</span></li>" for a, b in METODO)
    c = f"""
<section class="sv-heroe"><div class="envoltura">
<div class="txt">
<h1 class="t1">Te entregamos el trabajo hecho</h1>
<p class="entrada">Revisiones, tableros, alertas y asistentes sobre {N_FUENTES} fuentes oficiales. Precio fijo antes de empezar.</p>
<div class="botones"><a class="boton p" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a></div>
</div>
<nav class="sv-indice" aria-label="Servicios">{indice}</nav>
</div></section>
{bloques}
<section class="seccion inv"><div class="envoltura">
<div class="cab"><h2 class="t2">Cómo trabajamos</h2></div>
<ol class="pasos-sv">{pasos}</ol>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cab"><h2 class="t2">Cómo se cobra</h2><p class="entrada">Precio antes de empezar. Nunca por hora.</p></div>
<div class="columnas c3">
<div><h3>Por entrega</h3><p>Revisiones, tableros, informes y asistentes.</p></div>
<div><h3>Por proceso o licencia</h3><p>Las alertas y los procesos que corren solos.</p></div>
<div><h3>La capa de datos, por plan</h3><p>Si tu equipo consulta por su cuenta. <a class="enlace" href="/precios">Ver los planes</a></p></div>
</div>
</div></section>

"""
    return pagina(
        "/servicios",
        "Servicios",
        "Revisiones de predios, empresas y contratos, tableros, alertas y asistentes sobre fuentes oficiales, con la fuente de cada dato y precio fijo antes de empezar.",
        c,
        ("figuras.js",),
    )


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
<div class="buscador"><label class="sr" for="q">Buscar en el catálogo</label><input id="q" type="search" placeholder="Busca: predio, contratos, TRM, áreas protegidas…" autocomplete="off"></div>
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
<li><b>6,1 M</b><span>terrenos en la copia SINIC (333 municipios)</span></li>
<li><b>{miles(cob["total"])}</b><span>en la muestra (3 %)</span></li>
<li><b>{len(cob["celdas"])}</b><span>celdas con predios</span></li>
</ul>
<p class="fuente-dato">IGAC SINIC, muestra del 3 %, 28-10-2026</p>
</div>
{figura_cob}
</div>
</div></section>

<section class="seccion"><div class="envoltura">
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
            "Pagas por consulta, no por el dato",
            "Cada plan trae créditos al mes. Una consulta cuesta de 1 a 20 según el tipo de pregunta; la ficha de un lugar, hasta 50.",
            lado=lado_tarifa(),
        )
        + f"""
<section class="seccion"><div class="envoltura">
{planes_html()}
<p class="fuente-dato" style="margin-top:14px">El precio en pesos se confirma al pedir el plan. Los servicios se cotizan aparte.</p>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><h2 class="t2">Créditos por tipo de pregunta</h2>
<p class="entrada">Cada respuesta dice cuánto costó. Servirse desde una copia no cambia el precio.</p></div>
{tarifa_html()}
<div class="rejilla r2" style="margin-top:32px">
<div class="bloque"><h3 class="t3">No descuentan</h3><ul class="lista"><li>La caché</li><li><code>fuera_de_cobertura</code></li><li>Los errores, incluido «no se pudo»</li><li>Las rutas del catálogo</li></ul></div>
<div class="bloque"><h3 class="t3">El saldo del mes</h3><p>Se renueva el día 1 a las 00:00 UTC y no se acumula. <code>GET /v1/uso</code> dice cuánto queda.</p></div>
</div>
</div></section>

<section class="seccion" id="empezar"><div class="envoltura">
<div class="rejilla r2" style="gap:48px;align-items:start">
<div class="cab" style="margin:0"><h2 class="t2">Pide tu llave de prueba</h2>
<p class="entrada">Te llega un enlace al correo y ves la llave una sola vez. Trae {miles(CREDITOS_PRUEBA)} créditos y vence en {DIAS_PRUEBA} días. Para el plan Gratis o uno de pago, <a class="enlace" href="/contacto?asunto=plan-gratis">escríbenos</a>.</p>
{formulario_alta()}</div>
<div class="bloque"><h3 class="t3">Llaves</h3>
<div class="desliza"><table class="tabla"><thead><tr><th>Prefijo</th><th>Para qué</th></tr></thead><tbody>
<tr><td><code>rt_live_</code></td><td>Producción: licencia abierta verificada y dato público reutilizable, con aviso.</td></tr>
<tr><td><code>rt_test_</code></td><td>Evaluación: además, las fuentes con licencia por verificar, con aviso.</td></tr></tbody></table></div>
<p>Si una llave se filtra, la revocamos y te damos otra con el mismo saldo.</p></div>
</div>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><h2 class="t2">Preguntas frecuentes</h2></div>
<div class="prosa" style="max-width:860px">
<h3>¿Y si se me acaban los créditos?</h3><p>La puerta responde <code>402 saldo_agotado</code> con la fecha de renovación. Para subir de plan, escríbenos.</p>
<h3>¿Puedo usar los datos comercialmente?</h3><p>Las llaves de producción no ven fuentes con licencia por verificar. Cada respuesta trae su licencia y la atribución que debes citar; CC BY-SA exige compartir igual.</p>
<h3>¿Y los datos personales?</h3><p>Nada de búsquedas por cédula o nombre ni perfiles de personas. Cada fuente sale con una lista blanca de campos.</p>
<h3>¿Hay límite de tasa?</h3><p>Ráfaga de 20 consultas y 60 por minuto por llave. Las cabeceras <code>RateLimit</code> dicen cuánto queda.</p>
<h3>¿Y los servicios?</h3><p>Van aparte, a precio fijo y nunca por hora. <a href="/servicios">Ver servicios</a>.</p>
</div>
</div></section>
"""
    )
    return pagina(
        "/precios",
        "Precios",
        "Planes por créditos al mes. Una consulta cuesta de 1 a 20 créditos según el tipo de pregunta (la ficha de un lugar, hasta 50); los errores y la caché no descuentan.",
        c,
    )


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
<nav aria-label="En esta página"><a href="#inicio">Inicio rápido</a><a href="#mcp">MCP</a><a href="#perfiles">Perfiles</a><a href="#rest">API REST</a><a href="#contrato">Contrato rt/1</a><a href="#errores">Errores</a><a href="#recursos">Recursos</a></nav>
<div class="prosa">
<h2 id="inicio" style="margin-top:0">Inicio rápido</h2>
<div class="instruccion">
<p class="et">Dale esta instrucción a tu agente y se configura solo.</p>
<p id="instruccion">{INSTRUCCION}</p>
<button class="boton s chico" type="button" data-copiar="#instruccion">Copiar instrucción</button>
</div>
<ol><li><b>Pide tu llave</b> (<a href="/precios#empezar">plan Gratis</a>: 1.500 créditos al mes). Guárdala como secreto, nunca en el código.</li>
<li><b>Haz la primera consulta</b> (1 crédito):</li></ol>
<pre class="suelto"><code>export TERRNOVA_LLAVE=rt_live_...
curl -s -X POST https://terrnova.com/v1/co/territorio/dane_divipola_buscar \\
  -H "Authorization: Bearer $TERRNOVA_LLAVE" \\
  -H "Content-Type: application/json" \\
  -d '{{"nombre":"Cali"}}'</code></pre>
<p>Trae <code>"estado":"encontrado"</code>, los municipios en <code>datos.elementos</code> y la fuente (DANE) con su licencia en <code>procedencia</code>. Respeta las tildes: «Bogota» no encuentra «Bogotá».</p>
<ol start="3"><li><b>Mira tu saldo</b> con <code>GET /v1/uso</code>.</li></ol>

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
<tr><td><code>/mcp</code></td><td>Las {N_HERR} herramientas, <code>ficha_lugar</code> y <code>fuente_describir</code></td><td>Clientes que buscan herramientas solos, como Claude</td></tr>
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
            "Proyectos hermanos",
            "Dos proyectos de la comunidad geoespacial latinoamericana. Aliados, no clientes.",
        )
        + """
<section class="seccion"><div class="envoltura" style="display:grid;gap:0">
<div class="aliado"><img src="/img/geoai-latam.webp" alt="GeoAI LATAM" width="640" height="144">
<div><h2 class="t3">GeoAI LATAM</h2><p class="suave" style="margin-top:8px">Comunidad de inteligencia geoespacial para Latinoamérica: proyectos abiertos y tutoriales.</p>
<p style="margin-top:12px"><a class="enlace" href="https://geoailatam.terrnova.com/">geoailatam.terrnova.com</a></p></div></div>
<div class="aliado"><div class="pendiente">Atalaya Mapas</div>
<div><h2 class="t3">Atalaya Mapas</h2><p class="suave" style="margin-top:8px">Proyecto aliado de cartografía.</p></div></div>
</div></section>
"""
    )
    return pagina(
        "/aliados", "Aliados", "GeoAI LATAM y Atalaya Mapas, proyectos hermanos de Terrnova.", c
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
<div class="bloque"><h3 class="t3">Atajos</h3><ul class="lista">
<li>Llave de prueba: <a class="enlace" href="/precios#empezar">pídela aquí</a>, llega al instante.</li>
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
    return pagina("/404", "Página no encontrada", "La página no existe.", c)


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


def main() -> int:
    revisar = "--revisar" in sys.argv
    viejas = []
    datos_fig = FIGURAS / "datos.json"
    if revisar:
        if datos_fig.read_text(encoding="utf-8") != datos_figuras_json():
            viejas.append("figuras/datos.json")
    else:
        datos_fig.write_text(datos_figuras_json(), encoding="utf-8", newline="\n")
        sello = f'data-datos="{huella_figuras()}"'
        svgs = [SVG_FIGURAS / f"{n}.svg" for n in NOMBRES_FIGURAS]
        if not all(s.exists() and sello in s.read_text(encoding="utf-8") for s in svgs):
            import shutil
            import subprocess

            if shutil.which("node"):
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
