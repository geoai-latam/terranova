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
HERR = sorted(CAT.herramientas.values(), key=lambda h: (h.familia, h.id))
N_HERR = len(HERR)
# Solo cuentan las fuentes publicadas: un borrador no se sirve y no se anuncia.
PUBLICADAS = [f for f in CAT.fuentes.values() if f.estado == "publicada"]
N_FUENTES = len(PUBLICADAS)
# Fuentes por entidad, sin el índice propio de Terrnova, que no es una fuente oficial.
ENTIDADES = Counter(
    nombre_entidad(f.entidad) for f in PUBLICADAS if not f.entidad.startswith("Terrnova")
)
N_ENTIDADES = len(ENTIDADES)
POR_FAMILIA = Counter(h.familia for h in HERR)
MODOS = Counter(f.modo for f in PUBLICADAS)
LICENCIAS = Counter(f.licencia.spdx or "dato público, sin SPDX" for f in PUBLICADAS)


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
        for fid, f in sorted(CAT.fuentes.items())
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
<div class="der"><a href="/estado">{PULSO}Estado</a><a href="/contacto">Contacto</a><a class="boton p chico" href="/precios#empezar">Empieza gratis</a></div>
<button class="abrir" type="button" aria-expanded="false" aria-label="Abrir el menú"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
</div></header>"""


PIE = f"""<footer class="pie-sitio"><div class="envoltura">
<div class="arr">
<div><a class="marca" href="/">{simbolo("#F3EFE4", "#E0A13A", "#0B231C")}Terrnova</a>
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
    return f"""<section class="portada"><div class="{clase}"><div class="cab">
<span class="rotulo">{rotulo}</span><h1 class="t1">{titulo}</h1><p class="entrada">{entrada}</p>{extra}
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
    "DIAN": ["Normograma", "Usuarios aduaneros"],
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
    "Conéctate al servidor MCP de Terrnova en https://terrnova.com/mcp (transporte HTTP) con la "
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
            ("servido", "copia del 2026-10-28 en 0,56 s"),
        ],
        "huella": "sha256:7a2cc965…",
        "fecha": "2026-10-29",
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
        "fecha": "2026-10-30",
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
        "fecha": "2026-10-30",
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
        (
            "Analítica",
            "Antes de aprobar un crédito: la empresa en el RUES y en Supersociedades, y el predio en garantía en el catastro.",
        ),
        (
            "Automatización",
            "Un aviso cuando un cliente cambia el estado de su matrícula mercantil.",
        ),
        (
            "Analítica",
            "Precio de la tierra, vocación del suelo e indicadores del municipio para originar crédito agropecuario.",
        ),
    ],
    "Contratación pública": [
        (
            "Analítica",
            "Revisar a un contratista antes de adjudicar: sus contratos, multas y sanciones en SECOP.",
        ),
        (
            "Automatización",
            "Vigilar los contratos de una entidad y avisar cuando hay adiciones o modificaciones.",
        ),
        (
            "Agentes",
            "Un asistente que responde cuánto contrató el municipio, con quién y cómo va cada contrato.",
        ),
    ],
    "Legal y cumplimiento": [
        (
            "Agentes",
            "Un asistente de conceptos que cita la norma vigente y la sentencia de la Corte.",
        ),
        ("Automatización", "Alertas cuando sale o cambia una norma del tema que sigues."),
        (
            "Analítica",
            "La vigencia de cada norma citada en un informe, revisada antes de entregarlo.",
        ),
    ],
    "Agro y exportación": [
        (
            "Analítica",
            "Debida diligencia por finca para la EUDR: áreas protegidas, pérdida de bosque y territorios étnicos.",
        ),
        (
            "Automatización",
            "Las alertas de incendio del IDEAM en los municipios de tus proveedores, cada día.",
        ),
        (
            "Analítica",
            "Qué se cultiva, cuánto y dónde, por municipio, para planear compras o expansión.",
        ),
    ],
    "Inmobiliario y construcción": [
        (
            "Analítica",
            "La ficha de un predio antes de comprar: catastro, POT, amenazas y valor del suelo.",
        ),
        (
            "Analítica",
            "Compraventas por municipio para valorar un portafolio o elegir dónde construir.",
        ),
        (
            "Agentes",
            "Un asistente para el equipo comercial que responde qué se puede construir en un lote de Bogotá.",
        ),
    ],
    "Gobierno y territorio": [
        (
            "Analítica",
            "Un tablero municipal comparado: población, pobreza, educación, salud y seguridad.",
        ),
        ("Automatización", "Un informe periódico que se arma solo con las cifras de cada fuente."),
        (
            "Automatización",
            "Alertas de deslizamiento e incendio del IDEAM para los municipios que atiendes.",
        ),
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
    for i, (nombre, para, ids) in enumerate(orden):
        sel = "true" if i == 0 else "false"
        pest.append(
            f'<button type="button" role="tab" id="s-p{i}" aria-controls="s-t{i}" aria-selected="{sel}"'
            f"{'' if i == 0 else ' tabindex="-1"'}>{nombre}</button>"
        )
        filas = []
        for hid in ids:
            h = por_id[hid]
            ent = nombre_entidad(CAT.fuentes[h.fuente].entidad)
            filas.append(
                f'<li><p>{escape(h.pregunta)}</p><span class="id"><code>{h.id}</code> {escape(ent)}</span></li>'
            )
        sols = "".join(
            f'<li><span class="capa">{c}</span><p>{escape(s)}</p></li>'
            for c, s in SOLUCIONES[nombre]
        )
        paneles.append(
            f'<div class="panel-s" role="tabpanel" id="s-t{i}" aria-labelledby="s-p{i}"{"" if i == 0 else " hidden"}>'
            f'<p class="para">{para}</p>'
            f'<h4 class="sub-s">Soluciones que se construyen {SELLO_I}</h4><ul class="soluciones">{sols}</ul>'
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
        "Contratos y sanciones",
        [
            ("secop_contratos_proveedor", "Contratos públicos (SECOP II)"),
            ("secop_sanciones_contrato", "Sanciones en contratos"),
            ("secop1_multas_municipio", "Multas (SECOP I)"),
            ("sic_sanciones_por_sector", "Sanciones de la SIC"),
        ],
    ),
]

# Los servicios: para quién, qué hace, qué recibe y con qué fuentes. La landing muestra el resumen
# y /servicios el detalle con el entregable.
SERVICIOS = [
    {
        "id": "revision",
        "para": "Para bancos, aseguradoras, exportadores, compradores de tierra y áreas de cumplimiento",
        "titulo": "Debida diligencia: revisamos tu lista contra las fuentes oficiales",
        "texto": "Nos das una lista de predios, empresas o contratos. Revisamos cada uno contra las fuentes oficiales y te entregamos un expediente por ítem, con la fuente de cada hallazgo y los casos dudosos señalados. Sirve para aprobar un crédito, vincular un proveedor, comprar tierra o cumplir la regulación europea contra la deforestación (EUDR).",
        "recibes": [
            "Un expediente por ítem, en PDF y en datos",
            "Cada hallazgo con su entidad, su consulta y su fecha",
            "Los casos dudosos aparte, para que decidas tú",
        ],
        "con": "IGAC, Parques Nacionales, SINCHI, RUES, Supersociedades, SECOP y la SIC",
        "asunto": "debida-diligencia",
        "boton": "Pide una revisión",
    },
    {
        "id": "tablero",
        "para": "Para empresas, gremios, alcaldías, gobernaciones y ONG",
        "titulo": "Analítica: tableros e informes",
        "texto": "Los indicadores que sigues en un solo lugar: población, pobreza, educación, salud, seguridad, contratación, empresas y ambiente, actualizados desde la fuente y comparables entre municipios, sectores y años.",
        "recibes": [
            "Un tablero en la web, con tu marca",
            "Un informe periódico listo para presentar",
            "Cada cifra enlazada a la entidad que la publica",
        ],
        "con": "DANE, MinEducación, ADRES, Policía Nacional y SECOP",
        "asunto": "tablero",
        "boton": "Pide tu tablero",
    },
    {
        "id": "vigilancia",
        "para": "Para veedurías y áreas legales, de compras y de cumplimiento",
        "titulo": "Automatización: vigilancia, alertas y procesos",
        "texto": "Te avisamos cuando cambia algo que te importa: un contrato en SECOP, una norma, una alerta del IDEAM o una nueva sanción, con el registro de cada cambio. Y automatizamos los cruces y reportes que tu equipo hoy hace a mano.",
        "recibes": [
            "Alertas por correo o en tu sistema",
            "Un resumen semanal de lo que cambió",
            "El registro de cada cambio, con su fecha y su fuente",
        ],
        "con": "SECOP, SUIN-Juriscol, IDEAM y la SIC",
        "asunto": "vigilancia",
        "boton": "Pide tus alertas",
    },
    {
        "id": "asistente",
        "para": "Para equipos que quieren su propio asistente",
        "titulo": "Agentes: asistentes y aplicaciones a la medida",
        "texto": "Un asistente que responde con los datos oficiales de tu sector, dentro de tu sistema, tu SIG o tu ERP, y con la fuente de cada respuesta.",
        "recibes": [
            "El asistente funcionando en tu entorno",
            "Conectado a las fuentes que tu equipo usa",
            "Cada respuesta con su fuente y su licencia",
        ],
        "con": f"las {N_HERR} herramientas del catálogo",
        "asunto": "asistente",
        "boton": "Cuéntanos tu idea",
    },
]

ETIQUETAS = {
    "revision": "Esquema animado: predios, empresas y contratos pasan por una compuerta; salen en verde si no hay hallazgos y en ámbar si hay algo que revisar.",
    "tablero": "Esquema animado: un tablero despiezado en capas, con el mapa de Colombia por zonas, tu municipio frente a los comparables y la tendencia de cada indicador; con cada indicador cambian las tres capas.",
    "vigilancia": "Esquema animado: un barrido recorre lo que vigilas y una señal sube donde algo cambió.",
    "asistente": "Esquema animado: la pregunta viaja a las fuentes que hacen falta y vuelve con la respuesta.",
}

METODO = [
    ("Nos cuentas", "qué necesitas decidir y con qué información cuentas."),
    ("Te damos un precio fijo", "antes de empezar, nunca por hora."),
    (
        "Nuestro equipo hace el trabajo",
        "y una segunda revisión lo verifica contra las fuentes antes de entregarlo.",
    ),
    ("Recibes el resultado", "con la prueba de cada dato."),
]


def cruces_html() -> str:
    por_id = {h.id: h for h in HERR}
    grupos = []
    for g, items in CRUCES:
        filas = "".join(
            f"<li>{t}<span>{escape(nombre_entidad(CAT.fuentes[por_id[i].fuente].entidad))}</span></li>"
            for i, t in items
        )
        grupos.append(f'<div class="grupo"><h4>{g}</h4><ul>{filas}</ul></div>')
    return '<div class="cruces">' + "".join(grupos) + "</div>"


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


# Lo que muestran las viñetas sale del catálogo: herramientas, entidades y licencias reales.
TIPOS_REVISION = {
    "Predios y parcelas": ("Predio", "por coordenada"),
    "Empresas y proveedores": ("Empresa", "por NIT"),
    "Contratos y sanciones": ("Contratista", "por NIT"),
}
PREGUNTAS_ASISTENTE = [
    "banrep_trm_recientes",
    "dane_poblacion_proyectada_municipio",
    "pnn_areas_protegidas_en_punto",
    "secop_contratos_municipio",
    "rues_empresa_por_nit",
    "igac_predio_en_punto",
    "upra_precio_tierra_rural_municipio",
    "ideam_alertas_incendios_municipio",
]
OTRAS_ASISTENTE = [
    "ins_calidad_agua_municipio",
    "invima_registro_sanitario_por_expediente",
    "anh_crudo_municipio",
    "policia_hurto_vehiculos_municipio",
]
CARRILES_VIGILANCIA = [
    ("SECOP II", "Colombia Compra Eficiente", "Nuevo contrato de una entidad que vigilas"),
    ("SUIN-Juriscol", "MinJusticia", "Cambió una norma que sigues"),
    ("IDEAM", "IDEAM", "Alerta de incendio en un municipio que vigilas"),
    ("SIC", "SIC", "Nueva sanción en el sector que sigues"),
]
INDICADORES_TABLERO = [
    ("dane_poblacion_proyectada_municipio", "Población"),
    ("dane_ipm_municipio", "Pobreza"),
    ("men_educacion_municipio", "Educación"),
    ("adres_afiliados_subsidiado_municipio", "Salud"),
]


def datos_vineta(tipo: str) -> object:
    por_id = {h.id: h for h in HERR}

    def entidad(hid: str) -> str:
        return nombre_entidad(CAT.fuentes[por_id[hid].fuente].entidad)

    if tipo == "revision":
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
        return [{"t": t, "e": entidad(i)} for i, t in INDICADORES_TABLERO]
    return None


def vineta(tipo: str) -> str:
    datos = datos_vineta(tipo)
    attr = (
        f' data-datos="{escape(json.dumps(datos, ensure_ascii=False))}"'
        if datos is not None
        else ""
    )
    return f'<div class="vineta" data-vineta="{tipo}"{attr} role="img" aria-label="{ETIQUETAS[tipo]}"><div class="rotulos-v" aria-hidden="true"></div></div>'


def metodo_html() -> str:
    pasos = "".join(f"<li><b>{a}</b> {b}</li>" for a, b in METODO)
    return f'<div class="metodo"><h3>Cómo trabajamos</h3><ol>{pasos}</ol></div>'


def servicios_landing() -> str:
    p, *otros = SERVICIOS
    filas = "".join(
        f'<article class="serv">{vineta(str(s["id"]))}<div class="txt"><p class="para">{s["para"]}</p><h3>{s["titulo"]}</h3>'
        f'<p>{s["texto"]}</p><p class="con">Con datos de {s["con"]}</p>'
        f'<a class="enlace" href="/servicios#{s["id"]}">Ver el servicio</a></div></article>'
        for s in otros
    )
    return f"""<article class="serv-grande">
<div class="txt">
<p class="para">{p["para"]}</p>
<h3>{p["titulo"]}</h3>
<p>{p["texto"]}</p>
<a class="boton p" href="/contacto?asunto={p["asunto"]}">{p["boton"]}</a>
</div>
{vineta("revision")}
{cruces_html()}
</article>
<div class="servs">{filas}</div>"""


# Las capas de la prueba: valores de la respuesta real de banrep_trm_recientes, capturada el
# 2026-10-29.
CAPAS_PRUEBA = [
    ("dato", "3.162,35 pesos por dólar", "TRM del 29-10-2026 · encontrado"),
    ("procedencia", "Banco de la República", "la entidad que publica el dato"),
    ("licencia", "Aviso legal del Banco, uso comercial sí", "verificada para esta fuente"),
    ("servido_desde", "La fuente, en vivo", "consultado el 29-10-2026, 07:14 UTC"),
    ("huella", "sha256:ac30c9f5…", "para comprobar que no cambió"),
]
NOTAS_PRUEBA = [
    (
        "El dato y su estado",
        "Encontrado, no encontrado, fuera de cobertura o parcial. «No se pudo» nunca es un estado: es un error con su código.",
    ),
    (
        "Procedencia",
        "La entidad que publica el dato, la URL de la consulta y la norma que le da la competencia.",
    ),
    ("Licencia", "Si permite uso comercial, verificada fuente por fuente."),
    (
        "De dónde se sirvió",
        "En vivo, desde una copia del archivo oficial o desde caché. Un dato viejo siempre llega con aviso.",
    ),
    ("Huella", "Una firma de los datos, para comprobar después que no cambiaron."),
]


def prueba_html() -> str:
    capas = json.dumps(
        [{"campo": c, "valor": v, "nota": n} for c, v, n in CAPAS_PRUEBA], ensure_ascii=False
    )
    respaldo = "".join(f"<li><code>{c}</code> {v}</li>" for c, v, _ in CAPAS_PRUEBA)
    notas = "".join(
        f'<div data-capa="{i}"><h3>{t}</h3><p>{d}</p></div>'
        for i, (t, d) in enumerate(NOTAS_PRUEBA)
    )
    return f"""<div class="prueba">
<figure class="pila">
<div class="vineta" data-vineta="prueba" data-fondo="claro" data-capas="{escape(capas)}" role="img" aria-label="Una respuesta real de la TRM y sus capas de prueba, que se separan para leerse y se vuelven a juntar.">
<ul class="respaldo-capas">{respaldo}</ul>
</div>
<figcaption><span>banrep_trm_recientes, respuesta real</span><span class="sello">capturado el 2026-10-29</span></figcaption>
</figure>
<div class="notas">{notas}<p class="mas"><a class="enlace" href="/desarrolladores#contrato">Ver la respuesta completa en JSON</a></p></div>
</div>"""


def planes_html(detalle: bool = True) -> str:
    # Un solo botón primario (Gratis): ningún plan de pago se destaca sin un dato que lo respalde.
    filas = []
    for n, c in PLANES:
        boton = (
            '<a class="boton p" href="/precios#empezar">Empieza gratis</a>'
            if n == "Gratis"
            else f'<a class="boton s" href="/contacto?asunto=plan-{n.lower()}">Pedir este plan</a>'
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
<div class="escena" data-escena="predios" role="img" aria-label="Predios reales del barrio 11 de Noviembre, en Santa Marta, en 3D. El predio consultado sube cuando llega su respuesta. Arrastra para girar.">
<img class="respaldo" src="/img/predio-santamarta.webp" alt="" width="900" height="900">
<svg class="guia" aria-hidden="true"><line/><circle r="4"/></svg>
<div class="rotulos" aria-hidden="true"></div>
<p class="lectura"><b>11,2211 N, 74,1572 W</b> Santa Marta. Predios IGAC SINIC, calles © OpenStreetMap</p>
<div class="mueble" aria-hidden="true"><div class="escala"><i style="width:80px"></i><span>100 m</span></div><div class="norte"><svg width="18" height="22" viewBox="-9 -11 18 22"><path d="M0 -10 L6 8 L0 4 L-6 8 Z" fill="currentColor"/></svg><span>N</span></div></div>
</div>
<div class="envoltura h-texto"><div class="izq">
<h1 class="t0">Del dato oficial a la solución</h1>
<p class="entrada">Una capa de datos con {N_FUENTES} fuentes de {N_ENTIDADES} entidades (empresas, contratos, normas, estadísticas, territorio y ambiente) y, encima, la analítica, las automatizaciones y los agentes que tu equipo necesita. Lo construyes tú con tu agente o lo construimos contigo.</p>
<div class="botones"><a class="boton p" href="/precios#empezar">Conecta tu agente gratis</a><a class="boton s" href="/contacto?asunto=proyecto">Cuéntanos qué quieres resolver</a></div>
</div></div>
<div class="envoltura h-consola">{consola()}</div>
</section>

<section class="seccion capas-l" id="capas"><div class="envoltura">
<div class="cab ancha">
<h2 class="t2">Una puerta a los datos y tres capas encima</h2>
<p class="entrada">La capa de datos es el producto: se paga con un plan mensual y empieza gratis. Las otras tres son soluciones que se construyen sobre ella, con la fuente oficial de cada dato.</p>
</div>
<div class="columnas c4">
<div class="capa-d"><span class="et">el producto</span><h3>Datos</h3><p>{N_FUENTES} fuentes oficiales por MCP o API REST, con la entidad, la licencia y la fecha en cada respuesta. Tu agente las consulta solo.</p><a class="enlace" href="/desarrolladores">Cómo se conecta</a></div>
<div><span class="et">encima</span><h3>Analítica</h3><p>Cruces, revisiones y tableros: una empresa, un predio o un contrato revisados contra varias fuentes, o los indicadores que sigues, actualizados desde la fuente.</p></div>
<div><span class="et">encima</span><h3>Automatización</h3><p>Vigilancias, alertas y reportes que corren solos y dejan registro de cada cambio, con su fecha y su fuente.</p></div>
<div><span class="et">encima</span><h3>Agentes</h3><p>Asistentes que responden con el dato oficial dentro de tu sistema, tu SIG o tu ERP, y citan la fuente de cada respuesta.</p></div>
</div>
<div class="dos-formas">
<p><b>Tú, con tu agente.</b> Conecta la puerta y construye encima. El plan gratis trae {miles(PLANES[0][1])} créditos al mes. <a class="enlace" href="/precios#empezar">Conecta tu agente gratis</a></p>
<p><b>Nosotros, contigo.</b> Nuestro equipo construye la solución a precio fijo, acordado antes de empezar. <a class="enlace" href="#servicios">Ver cómo trabajamos</a></p>
</div>
</div></section>


<section class="seccion" id="fuentes"><div class="envoltura">
<div class="cab ancha">
<h2 class="t2">Soluciones para cada sector</h2>
<p class="entrada">Lo que se construye sobre la puerta en cada sector y las herramientas que usa. Son {N_HERR} herramientas en siete familias; cada una responde una pregunta concreta.</p>
</div>
{chips_familias()}
{sectores()}
<p class="mas-s"><a class="enlace" href="/fuentes#entidades">Ver las {N_ENTIDADES} entidades y sus fuentes</a><a class="enlace" href="/fuentes">Buscar entre las {N_HERR} herramientas</a></p>
</div></section>

<section class="seccion sup servicios-l" id="servicios"><div class="envoltura">
<div class="cab ancha">
<h2 class="t1">O lo construimos contigo</h2>
<p class="entrada">No necesitas programar ni conocer las fuentes. Nos cuentas qué quieres resolver y nuestro equipo construye la solución sobre la capa de datos, con la fuente oficial y la licencia de cada dato.</p>
</div>
{servicios_landing()}
{metodo_html()}
<div class="botones fin-serv"><a class="boton p" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a><a class="boton s" href="/servicios">Ver los servicios en detalle</a></div>
</div></section>


<section class="seccion" id="por-que"><div class="envoltura">
<div class="cab ancha">
<h2 class="t2">Por qué no basta con buscar en la web</h2>
<p class="entrada">Un agente con buscador encuentra páginas. Una decisión necesita el dato oficial, saber de dónde salió y si se puede usar.</p>
</div>
<div class="columnas c4">
<div><h3>Cada entidad publica a su manera</h3><p>{N_ENTIDADES} entidades y {N_FUENTES} fuentes, entre portales de datos abiertos, servicios de mapas, archivos y páginas. Aquí todas responden con el mismo contrato.</p></div>
<div><h3>Sumar mal es fácil</h3><p>El SECOP Integrado repite un contrato por cada estado. Sumados tal cual, los de Pitalito en 2025 dan $174.000 M; contados bien, $63.157 M. Las herramientas ya cuentan bien.</p></div>
<div><h3>Probado cada madrugada</h3><p>Cada herramienta se prueba a diario contra un dato medido en la fuente, y el resultado es público. <a class="enlace" href="/estado">Ver el estado</a></p></div>
<div><h3>Empresas y lugares, no personas</h3><p>La puerta no usa un modelo de lenguaje: la misma pregunta da la misma consulta. Y no busca personas por cédula ni por nombre: cumple la ley de datos personales por diseño.</p></div>
</div>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cab">
<h2 class="t2">Cada respuesta trae su prueba</h2>
<p class="entrada">Todas las respuestas, de las {N_HERR} herramientas, llegan con lo que necesitas para confiar en el dato: quién lo publica, con qué licencia, de dónde salió y una huella para comprobarlo. Viene en la respuesta, no en un documento aparte.</p>
</div>
{prueba_html()}
</div></section>


<section class="seccion" id="precios"><div class="envoltura">
<div class="cab">
<h2 class="t2">Precios</h2>
<p class="entrada">La capa de datos se paga con un plan mensual y empieza gratis. Los servicios tienen un precio fijo por proyecto, acordado antes de empezar.</p>
</div>
<h3 class="sub-p">Capa de datos</h3>
{planes_html(detalle=False)}
<p class="pie-p"><a class="enlace" href="/precios">Ver cuántos créditos usa cada tipo de consulta</a></p>
<div class="banda-serv">
<div><h3>Servicios</h3><p>Precio fijo por entrega, acordado antes de empezar y nunca por hora. Las automatizaciones se cobran por proceso o por licencia.</p></div>
<a class="boton p" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a>
</div>
</div></section>

<section class="seccion sup"><div class="envoltura cierre">
<div class="cab" style="margin:0"><h2 class="t2">Empieza por lo que quieres resolver</h2><p class="entrada">Conecta tu agente gratis o cuéntanos el problema y te proponemos la solución con un precio fijo.</p></div>
<div class="botones"><a class="boton p" href="/precios#empezar">Conecta tu agente gratis</a><a class="boton s" href="/contacto?asunto=proyecto">Cuéntanos qué quieres resolver</a></div>
</div>
<div class="envoltura aliados-fila">
<span>Aliados</span>
<a href="/aliados"><img src="/img/geoai-latam.webp" alt="GeoAI LATAM" width="200" height="45" loading="lazy"></a>
<a href="/aliados" class="t3">Atalaya Mapas</a>
</div></section>
"""
    return pagina(
        "/",
        "Terrnova · Del dato oficial a la solución",
        f"Una capa de datos con {N_FUENTES} fuentes oficiales de Colombia y, encima, analítica, automatizaciones y agentes, con la fuente y la licencia de cada dato.",
        c,
        ("escena-predios.js", "escena-vinetas.js"),
    )


# Cómo se ve lo que recibe el cliente. Las maquetas sin datos reales van selladas como ilustrativas;
# la del asistente usa la respuesta real de la TRM.
SELLO_I = '<span class="sello-i">ilustrativo</span>'


def entregable(sid: str) -> str:
    if sid == "revision":
        filas = [
            ("Áreas protegidas (RUNAP)", "Parques Nacionales", "ok", "Sin hallazgos"),
            ("Pérdida de bosque", "SINCHI", "rev", "Revisar"),
            ("Resguardos indígenas", "Agencia Nacional de Tierras", "ok", "Sin hallazgos"),
            ("Predio en el catastro", "IGAC", "ok", "Encontrado"),
        ]
        cuerpo = "".join(
            f'<li><span class="q">{q}<small>{e}</small></span><span class="chip-e {c}">{t}</span></li>'
            for q, e, c, t in filas
        )
        return f"""<div class="maqueta exp"><div class="m-cab"><b>Expediente del predio</b><span>4 de 4 fuentes consultadas</span></div>
<ul>{cuerpo}</ul><div class="m-pie"><span>Un caso para revisión humana</span>{SELLO_I}</div></div>"""
    if sid == "tablero":
        tiles = [
            ("Población", "DANE", [3, 4, 4, 5, 6, 6, 7]),
            ("Pobreza multidimensional", "DANE", [7, 6, 6, 5, 5, 4, 4]),
            ("Matrícula escolar", "MinEducación", [4, 5, 5, 5, 6, 7, 7]),
            ("Afiliados a salud", "ADRES", [5, 5, 6, 6, 6, 7, 8]),
        ]
        cuerpo = "".join(
            f'<div class="tile"><span>{t}</span><small>{e}</small><div class="barras">'
            + "".join(f'<i style="--h:{h * 12}%"></i>' for h in bs)
            + "</div></div>"
            for t, e, bs in tiles
        )
        return f"""<div class="maqueta tab"><div class="m-cab"><b>Tu municipio</b><span>actualizado desde la fuente</span></div>
<div class="tiles">{cuerpo}</div><div class="m-pie"><span>Cada cifra enlaza a su entidad</span>{SELLO_I}</div></div>"""
    if sid == "vigilancia":
        items = [
            ("SECOP II", "Nuevo contrato de una entidad que vigilas", "hoy"),
            ("SUIN-Juriscol", "Cambió una norma que sigues", "ayer"),
            ("IDEAM", "Alerta de incendio en un municipio que vigilas", "ayer"),
            ("SIC", "Nueva sanción en el sector que sigues", "lunes"),
        ]
        cuerpo = "".join(
            f'<li><i></i><span class="q"><small>{f}</small>{t}</span><span class="cuando">{c}</span></li>'
            for f, t, c in items
        )
        return f"""<div class="maqueta alr"><div class="m-cab"><b>Tus alertas</b><span>con el registro de cada cambio</span></div>
<ul>{cuerpo}</ul><div class="m-pie"><span>Por correo o en tu sistema</span>{SELLO_I}</div></div>"""
    return """<div class="maqueta chat"><div class="m-cab"><b>Asistente de tu equipo</b><span>dentro de tu sistema</span></div>
<p class="yo">¿A cuánto está la TRM hoy?</p>
<div class="el"><p>La TRM del 29 de octubre de 2026 es de <b>3.162,35 pesos por dólar</b>.</p>
<p class="cita">Banco de la República · uso comercial permitido · consultado en vivo</p></div>
<div class="m-pie"><span>Respuesta real</span><span class="sello">capturado el 2026-10-29</span></div></div>"""


def servicios() -> str:
    indice = "".join(f'<a href="#{s["id"]}">{s["titulo"]}</a>' for s in SERVICIOS)
    bloques = []
    for i, s in enumerate(SERVICIOS):
        recibes = "".join(f"<li>{x}</li>" for x in s["recibes"])
        extra = cruces_html() if s["id"] == "revision" else ""
        bloques.append(f"""<section class="sv-det{" par" if i % 2 else ""}" id="{s["id"]}"><div class="envoltura">
<div class="txt">
<p class="para">{s["para"]}</p>
<h2 class="t2">{s["titulo"]}</h2>
<p class="entrada">{s["texto"]}</p>
<h3>Qué recibes</h3><ul class="lista">{recibes}</ul>
<p class="con">Con datos de {s["con"]}</p>
<a class="boton p" href="/contacto?asunto={s["asunto"]}">{s["boton"]}</a>
</div>
<div class="fig">{vineta(str(s["id"]))}{entregable(str(s["id"]))}</div>
{extra}
</div></section>""")
    pasos = "".join(f"<li><b>{a}</b><span>{b[0].upper() + b[1:]}</span></li>" for a, b in METODO)
    c = f"""
<section class="sv-heroe"><div class="envoltura">
<div class="txt">
<h1 class="t1">Te entregamos el trabajo hecho</h1>
<p class="entrada">Revisiones, tableros, alertas y asistentes sobre {N_FUENTES} fuentes oficiales de {N_ENTIDADES} entidades. Con la fuente y la licencia de cada dato, y un precio fijo antes de empezar.</p>
<div class="botones"><a class="boton p" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a><a class="boton s" href="#revision">Ver los servicios</a></div>
</div>
{vineta("asistente")}
</div>
<nav class="sv-indice envoltura" aria-label="Servicios">{indice}</nav>
</section>
{"".join(bloques)}
<section class="seccion inv"><div class="envoltura">
<div class="cab"><h2 class="t2">Cómo trabajamos</h2>
<p class="entrada">Cada entrega pasa por una segunda revisión contra las fuentes antes de llegar a ti. Lo que no cuadra vuelve.</p></div>
<ol class="pasos-sv">{pasos}</ol>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cab"><h2 class="t2">Cómo se cobra</h2><p class="entrada">Sabes el precio antes de empezar. Nunca cobramos por hora.</p></div>
<div class="columnas c3">
<div><h3>Por entrega</h3><p>Revisiones, tableros, informes y asistentes: un precio fijo por proyecto, acordado antes de empezar.</p></div>
<div><h3>Por proceso o licencia</h3><p>Las alertas y los procesos que corren solos se cobran por proceso en marcha o por licencia.</p></div>
<div><h3>La capa de datos, por plan</h3><p>Si tu equipo consulta las fuentes por su cuenta, hay planes mensuales que empiezan gratis. <a class="enlace" href="/precios">Ver los planes</a></p></div>
</div>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><h2 class="t2">Lo que ya existe, con su alcance</h2></div>
<div class="columnas c2">
<div><h3>GEO Copilot</h3><p>Un asistente territorial, proyecto del fundador. Hoy es un cliente más de la capa de datos: se conecta por el MCP de Terrnova, como cualquier otro sistema.</p></div>
<div><h3>Vectorización de ortofotos del IGAC</h3><p>Un modelo de segmentación sobre ortofotos del IGAC, desarrollado como tesis de maestría del fundador (mIoU 0,694). Es investigación, no un modelo de producción.</p></div>
</div>
</div></section>

<section class="seccion"><div class="envoltura cierre">
<div class="cab" style="margin:0"><h2 class="t2">¿Tienes un proyecto?</h2><p class="entrada">Escríbenos con la decisión que quieres tomar. Respondemos con lo que se puede probar y un precio fijo.</p></div>
<div class="botones"><a class="boton p" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a></div>
</div></section>
"""
    return pagina(
        "/servicios",
        "Servicios",
        "Revisiones de predios, empresas y contratos, tableros, alertas y asistentes sobre fuentes oficiales, con la fuente de cada dato y precio fijo antes de empezar.",
        c,
        ("escena-vinetas.js",),
    )


def fuentes() -> str:
    lic = "".join(
        f'<tr><td><code>{escape(k)}</code></td><td class="n">{v}</td></tr>'
        for k, v in LICENCIAS.most_common()
    )
    c = (
        portada(
            "Fuentes y herramientas",
            f"{N_HERR} herramientas sobre {N_FUENTES} fuentes oficiales",
            f"Cada herramienta responde una pregunta concreta con una fuente de una de las {N_ENTIDADES} entidades del catálogo. Busca por tema, entidad o nombre.",
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
<div class="cab ancha"><h2 class="t2">Quién publica los datos</h2>
<p class="entrada">{N_ENTIDADES} entidades y los sistemas que publican. {MODOS["en_vivo"]} fuentes se consultan en vivo y {MODOS["copia"]} desde una copia del archivo oficial, con su fecha de corte en cada respuesta.</p></div>
{indice_fuentes()}
<p class="pie-muro">El número es cuántas fuentes publica cada entidad. En gris, las fuentes globales.</p>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cobertura">
<div class="texto-cob">
<h2 class="t2">Dónde hay predio SINIC hoy</h2>
<p class="suave">Cada columna es una celda de unos 8 km. Su altura cuenta los predios de la muestra que caen en ella; las celdas planas son territorio sin predios en la muestra.</p>
<div class="filas"><div><b>6,1 M</b><span>predios en el SINIC</span></div><div><b>186.988</b><span>en esta muestra (3 %)</span></div><div><b>949</b><span>celdas con predios</span></div></div>
<div class="leyenda"><span>menos</span><i></i><span>más predios por celda</span></div>
<p class="fuente-dato">IGAC SINIC, muestra del 3 %, 28-10-2026</p>
</div>
<div class="escena" data-escena="cobertura" role="img" aria-label="Columnas hexagonales sobre Colombia con los predios SINIC de la muestra. Arrastra para girar.">
<img class="respaldo" src="/img/mapa-colombia.webp" alt="" loading="lazy">
<div class="rotulos" aria-hidden="true"></div>
<p class="gira">Arrastra para girar</p>
<p class="lectura">Pasa sobre una columna</p>
</div>
</div>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="rejilla r2" style="gap:48px">
<div><span class="rotulo">Licencias</span><h2 class="t2" style="margin:12px 0 20px">La licencia de cada fuente</h2>
<div class="desliza"><table class="tabla"><thead><tr><th>Licencia (SPDX)</th><th>Fuentes</th></tr></thead><tbody>{lic}</tbody></table></div>
<p class="suave" style="margin-top:12px">Cada respuesta trae la licencia y la atribución que debes citar. CC BY-SA exige compartir igual.</p></div>
</div>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cab"><span class="rotulo">Para máquinas</span><h2 class="t2">El catálogo, también en formato abierto</h2></div>
<div class="rejilla r3">
<div class="bloque"><h3 class="t3"><code>GET /v1/herramientas</code></h3><p>Pregunta, familia, fuente, créditos y ruta de cada herramienta. Público y sin costo.</p><a class="enlace" href="/v1/herramientas">Abrir</a></div>
<div class="bloque"><h3 class="t3"><code>GET /v1/fuentes/&#123;id&#125;</code></h3><p>La ficha técnica de una fuente: cobertura, campos, actualización y alertas.</p><a class="enlace" href="/v1/fuentes">Abrir</a></div>
<div class="bloque"><h3 class="t3"><code>/llms.txt</code></h3><p>El catálogo en texto, para que un agente lo lea de una vez.</p><a class="enlace" href="/llms.txt">Abrir</a></div>
</div>
</div></section>
"""
    )
    return pagina(
        "/fuentes",
        "Fuentes y herramientas",
        f"Busca entre {N_HERR} herramientas sobre {N_FUENTES} fuentes oficiales: territorio, contratación, estadísticas, justicia, ambiente, empresas y normativa.",
        c,
        ("escena-cobertura.js",),
    )


def precios() -> str:
    c = (
        portada(
            "Precios",
            "Pagas por consulta, no por el dato",
            "Cada plan trae créditos al mes. Una consulta cuesta de 1 a 20 créditos según el tipo de pregunta, no según cómo se trae el dato.",
            lado=lado_tarifa(),
        )
        + f"""
<section class="seccion"><div class="envoltura">
{planes_html()}
<p class="fuente-dato" style="margin-top:14px">Los precios en pesos de cada plan se confirman al pedirlo. Los servicios se cotizan aparte.</p>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><span class="rotulo">Tarifa</span><h2 class="t2">Créditos por tipo de pregunta</h2>
<p class="entrada">Que una fuente pase a servirse desde una copia no cambia su precio. Cada herramienta dice su costo en el catálogo, y cada respuesta dice cuánto costó.</p></div>
{tarifa_html()}
<div class="rejilla r2" style="margin-top:32px">
<div class="bloque"><h3 class="t3">No descuentan</h3><ul class="lista"><li>Las respuestas desde la caché</li><li><code>fuera_de_cobertura</code></li><li>Los errores, incluido «no se pudo»</li><li>Las rutas del catálogo</li></ul></div>
<div class="bloque"><h3 class="t3">El saldo del mes</h3><p>Se renueva el día 1 de cada mes a las 00:00 UTC y no se acumula. Si subes de plan, el límite nuevo aplica desde la siguiente consulta. <code>GET /v1/uso</code> te dice cuánto te queda.</p></div>
</div>
</div></section>

<section class="seccion" id="empezar"><div class="envoltura">
<div class="rejilla r2" style="gap:48px;align-items:start">
<div class="cab" style="margin:0"><span class="rotulo">Empezar</span><h2 class="t2">Pide tu llave gratis</h2>
<p class="entrada">El plan Gratis trae 1.500 créditos al mes. Escríbenos con tu nombre, tu organización y qué quieres consultar. La llave llega por un canal privado y una sola vez.</p>
<div class="botones" style="margin-top:8px"><a class="boton p" href="mailto:{CORREO}?subject=Llave%20del%20plan%20Gratis">Pedir mi llave</a><a class="boton s" href="/desarrolladores">Ver cómo conectarse</a></div></div>
<div class="bloque"><h3 class="t3">Llaves</h3>
<div class="desliza"><table class="tabla"><thead><tr><th>Prefijo</th><th>Para qué</th></tr></thead><tbody>
<tr><td><code>rt_live_</code></td><td>Producción: las fuentes con licencia abierta verificada y las de dato público reutilizable, con aviso.</td></tr>
<tr><td><code>rt_test_</code></td><td>Evaluación, que puede tener vencimiento: además, las fuentes con licencia por verificar, con aviso.</td></tr></tbody></table></div>
<p>Cada llave tiene sus familias. Si una llave se filtra, avísanos: la revocamos y te enviamos otra, con el mismo saldo y el mismo plan.</p></div>
</div>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><span class="rotulo">Preguntas frecuentes</span><h2 class="t2">Lo que suelen preguntar</h2></div>
<div class="prosa" style="max-width:860px">
<h3>¿Qué pasa si se me acaban los créditos?</h3><p>La puerta responde <code>402 saldo_agotado</code> con la fecha en que se renueva tu saldo. Puedes subir de plan en cualquier momento.</p>
<h3>¿Puedo usar los datos comercialmente?</h3><p>Las llaves de producción no ven fuentes con licencia por verificar. Cada respuesta dice su licencia y, si es un dato público con condiciones propias de la entidad, trae un aviso. Al publicar un dato, cita la atribución que trae la respuesta y respeta su licencia: CC BY-SA exige compartir igual.</p>
<h3>¿Qué hay de los datos personales?</h3><p>No hay búsquedas de personas por cédula ni por nombre, ni perfiles de personas. Los campos que salen de cada fuente están en una lista blanca.</p>
<h3>¿Hay límite de tasa?</h3><p>Cada llave tiene una ráfaga de 20 consultas y repone 60 por minuto. Las cabeceras <code>RateLimit</code> dicen cuánto queda.</p>
<h3>¿Y los servicios?</h3><p>No van en estos planes. Se evalúan, el precio se fija antes de empezar y nunca se cobra por hora. <a href="/servicios">Ver servicios</a>.</p>
</div>
</div></section>
"""
    )
    return pagina(
        "/precios",
        "Precios",
        "Planes por créditos al mes. Una consulta cuesta de 1 a 20 créditos según el tipo de pregunta; los errores y la caché no descuentan.",
        c,
    )


def desarrolladores() -> str:
    perfiles = ", ".join(f"<code>{f}</code>" for f in POR_FAMILIA if f != "meta")
    c = (
        portada(
            "Desarrolladores",
            "Conecta tu agente o tu sistema",
            "MCP por streamable HTTP para agentes, API REST para sistemas. La misma llave y el mismo contrato rt/1 en las dos.",
            lado=lado_puertas(),
        )
        + f"""
<section class="seccion"><div class="envoltura doc">
<nav aria-label="En esta página"><a href="#inicio">Inicio rápido</a><a href="#mcp">MCP</a><a href="#perfiles">Perfiles</a><a href="#rest">API REST</a><a href="#contrato">Contrato rt/1</a><a href="#errores">Errores</a><a href="#recursos">Recursos</a></nav>
<div class="prosa">
<h2 id="inicio" style="margin-top:0">Inicio rápido</h2>
<div class="instruccion">
<p class="et">La forma más corta: dale esta instrucción a tu agente y se configura solo.</p>
<p id="instruccion">{INSTRUCCION}</p>
<button class="boton s chico" type="button" data-copiar="#instruccion">Copiar instrucción</button>
</div>
<ol><li><b>Pide tu llave.</b> <a href="/precios#empezar">El plan Gratis</a> trae 1.500 créditos al mes. Guárdala como un secreto, nunca en el código.</li>
<li><b>Haz la primera consulta.</b> El código DIVIPOLA de un municipio por su nombre cuesta 1 crédito:</li></ol>
<pre class="suelto"><code>export TERRNOVA_LLAVE=rt_live_...
curl -s -X POST https://terrnova.com/v1/co/territorio/dane_divipola_buscar \\
  -H "Authorization: Bearer $TERRNOVA_LLAVE" \\
  -H "Content-Type: application/json" \\
  -d '{{"nombre":"Cali"}}'</code></pre>
<p>La respuesta trae <code>"estado":"encontrado"</code>, los municipios que coinciden en <code>datos.elementos</code> y la fuente (DANE) con su licencia en <code>procedencia</code>. La búsqueda respeta las tildes: «Bogota» no encuentra «Bogotá».</p>
<ol start="3"><li><b>Mira tu saldo</b> con <code>GET /v1/uso</code>.</li></ol>

<h2 id="mcp">MCP</h2>
<p>La puerta habla MCP por <i>streamable HTTP</i>, con la llave en la cabecera <code>Authorization</code>.</p>
<p>Claude Code:</p>
<pre class="suelto"><code>claude mcp add --transport http terrnova https://terrnova.com/mcp \\
  --header "Authorization: Bearer $TERRNOVA_LLAVE"</code></pre>
<p>Cursor y otros clientes que aceptan <code>url</code> y <code>headers</code>:</p>
<pre class="suelto"><code>{{
  "mcpServers": {{
    "terrnova": {{
      "url": "https://terrnova.com/mcp/territorio",
      "headers": {{ "Authorization": "Bearer rt_live_..." }}
    }}
  }}
}}</code></pre>
<p>Claude Desktop y otros clientes que solo hablan por stdio, con el puente <code>mcp-remote</code>:</p>
<pre class="suelto"><code>{{
  "mcpServers": {{
    "terrnova": {{
      "command": "npx",
      "args": ["mcp-remote", "https://terrnova.com/mcp/ambiente",
               "--header", "Authorization: Bearer ${{TERRNOVA_LLAVE}}"],
      "env": {{ "TERRNOVA_LLAVE": "rt_live_..." }}
    }}
  }}
}}</code></pre>

<h2 id="perfiles">Perfiles</h2>
<table class="tabla"><thead><tr><th>Ruta</th><th>Qué expone</th><th>Para</th></tr></thead><tbody>
<tr><td><code>/mcp</code></td><td>Las {N_HERR} herramientas, más <code>ficha_lugar</code> y <code>fuente_describir</code></td><td>Clientes que buscan herramientas por su cuenta, como Claude</td></tr>
<tr><td><code>/mcp/&lt;familia&gt;</code></td><td>Las de una sola familia</td><td>Un caso de uso de un solo tema: lo más preciso y lo más rápido</td></tr>
<tr><td><code>/mcp/catalogo</code></td><td>Pocas herramientas genéricas que buscan en el catálogo</td><td>Clientes con tope de herramientas, como los modelos de OpenAI (128)</td></tr>
</tbody></table>
<p>Familias: {perfiles}. Todos los perfiles traen las herramientas de nombre a código (1 crédito) y <code>fuente_describir</code>, que no gasta créditos.</p>

<h2 id="rest">API REST</h2>
<p>Las herramientas siguen el patrón <code>POST /v1/co/&lt;familia&gt;/&lt;herramienta&gt;</code>, con la entrada en JSON. La ficha de un lugar está en <code>POST /v1/fichas</code>. El esquema completo, con la entrada de cada herramienta, está en <a href="/openapi.json"><code>/openapi.json</code></a> y se navega en <a href="/docs"><code>/docs</code></a>.</p>
<table class="tabla"><thead><tr><th>Para</th><th>Dónde</th></tr></thead><tbody>
<tr><td>Lista de herramientas con su costo</td><td><code>GET /v1/herramientas</code></td></tr>
<tr><td>Ficha técnica de una fuente</td><td><code>GET /v1/fuentes/&#123;fuente_id&#125;</code></td></tr>
<tr><td>Saldo del mes</td><td><code>GET /v1/uso</code></td></tr>
<tr><td>Estado por fuente</td><td><code>GET /v1/estado</code></td></tr>
</tbody></table>
<p>Las rutas de catálogo son públicas y no gastan créditos.</p>

<h2 id="contrato">Contrato rt/1</h2>
<p>Toda consulta que llega a la fuente devuelve el mismo sobre:</p>
<table class="tabla"><thead><tr><th>Campo</th><th>Contenido</th></tr></thead><tbody>
<tr><td><code>estado</code></td><td><code>encontrado</code>, <code>no_encontrado</code>, <code>fuera_de_cobertura</code> o <code>parcial</code></td></tr>
<tr><td><code>datos</code></td><td>El resultado</td></tr>
<tr><td><code>huella</code></td><td><code>sha256</code> de <code>datos</code>, para verificar que no cambió</td></tr>
<tr><td><code>procedencia</code></td><td>Por fuente: entidad, URL, norma (si la hay), licencia, atribución, <code>servido_desde</code>, <code>consultado_en</code> y <code>completitud</code></td></tr>
<tr><td><code>avisos</code></td><td>Lo que debes saber: total desconocido, datos no recientes, copia vencida…</td></tr>
<tr><td><code>geo_result</code></td><td>Las geometrías, en EPSG:4326 salvo que pidas <code>crs_salida: EPSG:9377</code></td></tr>
<tr><td><code>creditos</code></td><td>Lo que costó esa consulta</td></tr>
</tbody></table>
<p><b>«No encontrado» no es «no se pudo».</b> Cuando la fuente no responde llega un error, nunca un sobre vacío. Terrnova nunca inventa un dato ni hace pasar uno viejo por actual: <code>servido_desde: obsoleto</code> siempre llega con aviso.</p>

<h2 id="errores">Errores</h2>
<p>Por REST, en <code>application/problem+json</code> (RFC 9457), con un <code>code</code> estable y el <code>solicitud_id</code> que debes darnos si escribes a soporte.</p>
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
<p>Cada llave tiene una ráfaga de 20 consultas y repone 60 por minuto. Reintenta con espera creciente, nunca en bucle cerrado.</p>

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
            "Aliados",
            "Proyectos hermanos",
            "Terrnova trabaja junto a dos proyectos de la comunidad geoespacial latinoamericana. Son aliados, no clientes.",
        )
        + """
<section class="seccion"><div class="envoltura" style="display:grid;gap:0">
<div class="aliado"><img src="/img/geoai-latam.webp" alt="GeoAI LATAM" width="640" height="144">
<div><h2 class="t3">GeoAI LATAM</h2><p class="suave" style="margin-top:8px">Una comunidad que comparte conocimiento y desarrolla soluciones de inteligencia geoespacial para Latinoamérica: proyectos abiertos, tutoriales y notas de campo.</p>
<p style="margin-top:12px"><a class="enlace" href="https://geoailatam.terrnova.com/">geoailatam.terrnova.com</a></p></div></div>
<div class="aliado"><div class="pendiente">Atalaya Mapas<small>Logo oficial pendiente</small></div>
<div><h2 class="t3">Atalaya Mapas</h2><p class="suave" style="margin-top:8px">Proyecto aliado de cartografía. Mientras llega su logo oficial, aquí va solo su nombre.</p></div></div>
</div></section>
"""
    )
    return pagina(
        "/aliados", "Aliados", "GeoAI LATAM y Atalaya Mapas, proyectos hermanos de Terrnova.", c
    )


def contacto() -> str:
    c = (
        portada(
            "Contacto",
            "Escríbenos",
            "Respondemos de lunes a viernes, de 8:00 a 18:00, hora de Colombia, sin festivos.",
        )
        + f"""
<section class="seccion"><div class="envoltura">
<div class="rejilla r3">
<div class="bloque"><span class="num">servicios</span><h3 class="t3">Cuéntanos tu proyecto</h3><p>Qué decisión quieres tomar, sobre qué lugares y con qué plazo. Respondemos con lo que se puede probar y un precio fijo.</p><a class="boton p" href="mailto:{CORREO}?subject=Proyecto%20territorial" style="margin-top:auto">Escribir</a></div>
<div class="bloque"><span class="num">datos</span><h3 class="t3">Pide tu llave</h3><p>Tu nombre, tu organización y qué quieres consultar. La llave del plan Gratis llega por un canal privado.</p><a class="boton s" href="mailto:{CORREO}?subject=Llave%20del%20plan%20Gratis" style="margin-top:auto">Pedir llave</a></div>
<div class="bloque"><span class="num">soporte</span><h3 class="t3">Algo no funciona</h3><p>Incluye el <code>solicitud_id</code> de la respuesta. Si una fuente está caída, míralo primero en <a class="enlace" href="/estado">el estado</a>.</p><a class="boton s" href="mailto:{CORREO}?subject=Soporte" style="margin-top:auto">Escribir a soporte</a></div>
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
        portada("Legal", titulo, entrada)
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
        "404",
        "Aquí no hay nada",
        "La página no existe o cambió de lugar. «No encontrado» es una respuesta honesta.",
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
