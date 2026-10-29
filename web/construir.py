"""Construye el sitio público de Terranova (terrnova.com) en web/publico/.

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
    ("/precios", "Precios"),
    ("/desarrolladores", "Desarrolladores"),
]


def miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def corta(entidad: str) -> str:
    m = re.search(r"\(([^()]{2,24})\)\s*$", entidad)
    return m.group(1) if m else entidad


# ---------------------------------------------------------------- catálogo real
CAT = cargar(RAIZ.parent / "catalogo")
HERR = sorted(CAT.herramientas.values(), key=lambda h: (h.familia, h.id))
N_HERR = len(HERR)
N_FUENTES = len(CAT.fuentes)
N_ENTIDADES = len({f.entidad for f in CAT.fuentes.values()})
POR_FAMILIA = Counter(h.familia for h in HERR)
MODOS = Counter(f.modo for f in CAT.fuentes.values())
LICENCIAS = Counter(f.licencia.spdx or "sin SPDX" for f in CAT.fuentes.values())


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
<a class="marca" href="/" aria-label="Terranova, inicio">{simbolo()}Terranova</a>
<nav class="menu" aria-label="Principal">{menu}</nav>
<div class="der"><a href="/estado">{PULSO}Estado</a><a href="/contacto">Contacto</a><a class="boton p chico" href="/precios#empezar">Probar gratis</a></div>
<button class="abrir" type="button" aria-expanded="false" aria-label="Abrir el menú"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
</div></header>"""


PIE = f"""<footer class="pie-sitio"><div class="envoltura">
<div class="arr">
<div><a class="marca" href="/">{simbolo("#F3EFE4", "#E0A13A", "#0B231C")}Terranova</a>
<p class="desc">Respuestas territoriales con la fuente oficial y su prueba. Licencia verificada por fuente y nunca perfiles de personas.</p></div>
<div><h2>Producto</h2><ul><li><a href="/fuentes">Fuentes y herramientas</a></li><li><a href="/precios">Precios</a></li><li><a href="/estado">Estado del servicio</a></li><li><a href="/servicios">Servicios</a></li></ul></div>
<div><h2>Desarrolladores</h2><ul><li><a href="/desarrolladores">Guía de conexión</a></li><li><a href="/docs">API REST (OpenAPI)</a></li><li><a href="/llms.txt">llms.txt</a></li><li><a href="/desarrolladores#contrato">Contrato rt/1</a></li></ul></div>
<div><h2>Empresa</h2><ul><li><a href="/aliados">Aliados</a></li><li><a href="/contacto">Contacto</a></li><li><a href="mailto:{CORREO}">{CORREO}</a></li><li><a href="/terminos">Términos</a> · <a href="/privacidad">Privacidad</a></li></ul></div>
</div>
<div class="ab"><span>© 2026 Terranova · terrnova.com</span><span>4,6097 N · 74,0817 W · Bogotá</span></div>
</div></footer>"""


def pagina(
    ruta: str, titulo: str, descripcion: str, cuerpo: str, scripts: tuple[str, ...] = ()
) -> str:
    canon = DOMINIO + (ruta if ruta != "/" else "/")
    tit = titulo if ruta == "/" else f"{titulo} · Terranova"
    mods = "".join(f'\n<script type="module" src="/js/{s}"></script>' for s in scripts)
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(tit)}</title>
<meta name="description" content="{escape(descripcion)}">
<link rel="canonical" href="{canon}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Terranova">
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


def lado_capas() -> str:
    capas = [
        ("Analítica", "calcula"),
        ("Desarrollo", "construye"),
        ("Automatización", "opera"),
    ]
    filas = "".join(f'<div class="capa"><b>{n}</b><span>{v}</span></div>' for n, v in capas)
    return f"""<figure class="lado-fig capas"><figcaption>Cuatro capas, una prueba</figcaption>{filas}
<div class="capa base"><b>Datos Terranova</b><span>{N_HERR} herramientas · {N_FUENTES} fuentes</span></div>
<p class="fuente-dato">cada capa se apoya en la de datos</p></figure>"""


def lado_puertas() -> str:
    return """<figure class="lado-fig puertas"><figcaption>Dos puertas, un contrato</figcaption>
<div class="p"><span class="et">agentes</span><code>POST /mcp</code><small>MCP · streamable HTTP · perfiles por familia</small></div>
<div class="p"><span class="et">sistemas</span><code>POST /v1/co/&lt;familia&gt;/&lt;herramienta&gt;</code><small>REST · OpenAPI en /docs</small></div>
<div class="p uno"><span class="et">las dos</span><code>Authorization: Bearer rt_live_…</code><small>misma llave · respuesta rt/1</small></div></figure>"""


TARJETA_GEO = """<div class="tarjeta" data-k="geo">
<div class="top"><span class="herr">sinic_predio_en_punto</span><span class="sello">ejemplo · capturado 2026-10-29</span></div>
<dl><dt>estado</dt><dd class="ok">encontrado</dd><dt>predial</dt><dd>4700101090000025808…</dd>
<dt>destinación</dt><dd>Habitacional · urbano</dd><dt>entidad</dt><dd>IGAC · SINIC</dd>
<dt>licencia</dt><dd>CC-BY-SA-4.0 · comercial: sí</dd><dt>servido</dt><dd>copia del 2026-10-28 · 0,56 s</dd></dl>
<div class="huella"><span>huella</span><b>sha256:7a2cc965…</b></div></div>"""
TARJETA_TRM = """<div class="tarjeta" data-k="nogeo"{oculta}>
<div class="top"><span class="herr">banrep_trm_recientes</span><span class="sello">ejemplo · capturado 2026-10-29</span></div>
<dl><dt>estado</dt><dd class="ok">encontrado</dd><dt>TRM</dt><dd>3.162,35 COP · 2026-10-29</dd>
<dt>serie</dt><dd>diaria · CCSP</dd><dt>entidad</dt><dd>Banco de la República</dd>
<dt>licencia</dt><dd>banrep-aviso-legal · comercial: sí</dd><dt>servido</dt><dd>fuente en vivo · 07:14 UTC</dd></dl>
<div class="huella"><span>huella</span><b>sha256:ac30c9f5…</b></div></div>"""

CODIGO = """<div class="codigo">
<div class="panel">
<div class="pest" role="tablist" aria-label="Formas de conectarse"><button role="tab" aria-selected="true" data-t="cc">Claude Code</button><button role="tab" aria-selected="false" tabindex="-1" data-t="js">mcp.json</button><button role="tab" aria-selected="false" tabindex="-1" data-t="rs">REST</button></div>
<pre data-t="cc"><span class="c"># Una vez: registra la puerta en tu agente</span>
<span class="f">claude mcp add</span> --transport http terranova \\
  <span class="s">https://terrnova.com/mcp</span> \\
  --header <span class="s">"Authorization: Bearer $TERRANOVA_LLAVE"</span>

<span class="c"># Luego pregunta en lenguaje natural</span>
&gt; ¿Cuál es la TRM de hoy?</pre>
<pre data-t="js" hidden>{
  <span class="k">"mcpServers"</span>: {
    <span class="k">"terranova"</span>: {
      <span class="k">"url"</span>: <span class="s">"https://terrnova.com/mcp/territorio"</span>,
      <span class="k">"headers"</span>: { <span class="k">"Authorization"</span>: <span class="s">"Bearer rt_live_..."</span> }
    }
  }
}</pre>
<pre data-t="rs" hidden><span class="f">curl</span> -X POST \\
  <span class="s">https://terrnova.com/v1/co/estadisticas/banrep_trm_recientes</span> \\
  -H <span class="s">"Authorization: Bearer $TERRANOVA_LLAVE"</span> \\
  -H <span class="s">"Content-Type: application/json"</span> \\
  -d <span class="s">'{"ultimas": 1}'</span></pre>
<div class="pie"><span>MCP por HTTP · REST /v1</span><span>2 créditos</span></div>
</div>
<div class="panel">
<div class="pest"><button aria-selected="true" tabindex="-1">Respuesta</button><span class="meta">200 · rt/1</span></div>
<pre>{
  <span class="k">"contrato"</span>: <span class="s">"rt/1"</span>,
  <span class="k">"herramienta"</span>: <span class="s">"banrep_trm_recientes@1"</span>,
  <span class="k">"estado"</span>: <span class="s">"encontrado"</span>,
  <span class="k">"datos"</span>: { <span class="k">"elementos"</span>: [
    { <span class="k">"fecha"</span>: <span class="s">"20261029"</span>, <span class="k">"valor"</span>: <span class="n">3162.35</span>, <span class="k">"unidad"</span>: <span class="s">"COP"</span> }
  ]},
  <span class="k">"procedencia"</span>: [{
    <span class="k">"entidad"</span>: <span class="s">"Banco de la República"</span>,
    <span class="k">"licencia"</span>: { <span class="k">"uso_comercial"</span>: <span class="s">"si"</span> },
    <span class="k">"servido_desde"</span>: <span class="s">"fuente"</span>,
    <span class="k">"consultado_en"</span>: <span class="s">"2026-10-29T07:14:56Z"</span>
  }],
  <span class="k">"huella"</span>: <span class="s">"sha256:ac30c9f5…"</span>,
  <span class="k">"creditos"</span>: <span class="n">2</span>
}</pre>
<div class="pie"><span>ejemplo · capturado 2026-10-29 · recortado</span><span>req_01M6386A…</span></div>
</div>
</div>"""


def planes_html() -> str:
    # Un solo botón primario (Gratis): ningún plan de pago se destaca sin un dato que lo respalde.
    filas = []
    for n, c in PLANES:
        boton = (
            '<a class="boton p" href="/precios#empezar">Empezar gratis</a>'
            if n == "Gratis"
            else f'<a class="boton s" href="/contacto?asunto=plan-{n.lower()}">Pedir este plan</a>'
        )
        filas.append(
            f'<div class="plan"><h3>{n}</h3><b>{miles(c)}</b><span>créditos al mes</span>'
            f'<span class="eq">≈ {miles(c // 10)} consultas de predio por punto</span>{boton}</div>'
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
<section class="heroe"><div class="envoltura">
<div class="izq">
<h1 class="t1">Respuestas territoriales verificables</h1>
<p class="entrada">Agentes que hacen el trabajo territorial sobre la fuente oficial. Cada respuesta llega con su entidad, su licencia y su huella.</p>
<div class="botones"><a class="boton p" href="/precios#empezar">Probar gratis</a><a class="boton s" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a></div>
<div class="cifras"><div><b>{N_HERR}</b><span>herramientas</span></div><div><b>{N_FUENTES}</b><span>fuentes oficiales</span></div><div><b>{N_ENTIDADES}</b><span>entidades</span></div></div>
<p class="fuente-dato">Catálogo de producción · 29-10-2026</p>
</div>
<div class="escena" data-escena="predios" role="img" aria-label="Predios reales de Santa Marta en 3D, con el predio consultado resaltado. Arrastra para girar.">
<img class="respaldo" src="/img/predio-santamarta.webp" alt="" width="900" height="900">
<svg class="guia" aria-hidden="true"><line/><circle r="4"/></svg>
<div class="rotulos" aria-hidden="true"></div>
<p class="gira">Arrastra para girar</p>
{TARJETA_GEO}
<p class="lectura"><b>11,2211 N · 74,1572 W</b> · 11 de Noviembre, Santa Marta · predios IGAC SINIC · calles © OpenStreetMap</p>
<div class="mueble" aria-hidden="true"><div class="escala"><i style="width:80px"></i><span>100 m</span></div><div class="norte"><svg width="18" height="22" viewBox="-9 -11 18 22"><path d="M0 -10 L6 8 L0 4 L-6 8 Z" fill="currentColor"/></svg><span>N</span></div></div>
</div>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cab"><span class="rotulo">Cómo funciona</span><h2 class="t2">De la pregunta a la respuesta con prueba</h2>
<p class="entrada">Una sola puerta, por MCP y por API REST, sobre {N_FUENTES} fuentes oficiales. La puerta no interpreta preguntas: valida la llave, cobra los créditos y llama a la herramienta del catálogo.</p></div>
<ol class="pasos">
<li><span class="n">01</span><h3>Tu agente o tu sistema</h3><p>Pregunta por MCP en <code>/mcp</code> o por REST en <code>/v1</code>. Claude, ChatGPT, n8n o un script de Python: la puerta no distingue.</p><span class="deja"><code>herramienta</code></span></li>
<li class="puerta"><span class="n">02</span><h3>La puerta</h3><p>Valida la llave y descuenta los créditos según la tarifa. No interpreta la pregunta: aquí no hay LLM.</p><span class="deja"><code>creditos</code><code>solicitud_id</code></span></li>
<li><span class="n">03</span><h3>El catálogo</h3><p>{N_HERR} herramientas en {len([f for f in POR_FAMILIA if f != "meta"])} familias. Cada una sabe a qué fuente ir y con qué licencia sale el dato.</p><span class="deja"><code>licencia</code></span></li>
<li><span class="n">04</span><h3>La fuente oficial</h3><p>{N_FUENTES} fuentes de {N_ENTIDADES} entidades: {MODOS["en_vivo"]} se consultan en vivo y {MODOS["copia"]} desde una copia del bulk oficial.</p><span class="deja"><code>procedencia</code><code>servido_desde</code></span></li>
<li><span class="n">05</span><h3>La respuesta</h3><p>El dato con su estado: «no encontrado» y «no se pudo» nunca se confunden. La huella permite comprobar después que no cambió.</p><span class="deja"><code>estado</code><code>huella</code></span></li>
</ol>
<p class="fuente-dato pasos-pie">Columna derecha: el campo de la respuesta <code>rt/1</code> que deja cada paso.</p>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cobertura">
<div style="display:flex;flex-direction:column;gap:20px;padding:8px 0">
<span class="rotulo">Cobertura</span>
<h2 class="t2">Dónde hay predio SINIC hoy</h2>
<p class="suave">Cada columna es una celda de unos 8 km. Su altura cuenta los predios de la muestra que caen en ella; las celdas planas son territorio sin predios en la muestra.</p>
<div class="filas"><div><b>6,1 M</b><span>predios en el SINIC</span></div><div><b>186.988</b><span>en esta muestra (3 %)</span></div><div><b>949</b><span>celdas con predios</span></div></div>
<div class="leyenda"><span>menos</span><i></i><span>más predios por celda</span></div>
<p class="fuente-dato">IGAC SINIC · muestra del 3 % · 28-10-2026</p>
</div>
<div class="escena" data-escena="cobertura" role="img" aria-label="Columnas hexagonales sobre Colombia con los predios SINIC de la muestra. Arrastra para girar.">
<img class="respaldo" src="/img/mapa-colombia.webp" alt="" loading="lazy">
<p class="gira">Arrastra para girar</p>
<p class="lectura">Pasa sobre una columna</p>
</div>
</div>
<div style="margin-top:48px;display:grid;gap:16px">
<h3 class="t3">Qué más puedes consultar</h3>
{chips_familias()}
<p><a class="enlace" href="/fuentes">Ver las {N_HERR} herramientas y sus fuentes →</a></p>
</div>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cab"><span class="rotulo">La respuesta por dentro</span><h2 class="t2">Cada respuesta trae su prueba</h2>
<p class="entrada">El mismo sobre <code>rt/1</code> para las {N_HERR} herramientas. Lo que importa para confiar en el dato viene en la respuesta, no en un documento aparte.</p></div>
<div class="anotada">
<div>{TARJETA_TRM.format(oculta="")}</div>
<div class="notas">
<div><code>estado</code><p>Encontrado, no encontrado, fuera de cobertura o parcial. «No se pudo» nunca es un estado: es un error con su código.</p></div>
<div><code>procedencia</code><p>La entidad, la URL de la consulta y la norma que le da la competencia.</p></div>
<div><code>licencia</code><p>SPDX, enlace y si permite uso comercial, verificada fuente por fuente.</p></div>
<div><code>servido_desde</code><p>En vivo, desde una copia del bulk oficial, curado, caché u obsoleto (siempre con aviso).</p></div>
<div><code>huella</code><p><code>sha256</code> de los datos, para comprobar después que no cambiaron.</p></div>
</div>
</div>
<dl class="estados">
<div class="e1"><dt>encontrado</dt><dd>La fuente respondió y hay datos.</dd></div>
<div class="e2"><dt>no_encontrado</dt><dd>La fuente respondió y no hay datos para esa entrada. Es una respuesta, no una falla.</dd></div>
<div class="e3"><dt>parcial</dt><dd>Una consulta compuesta con partes que fallaron; cada una queda en <code>errores</code>.</dd></div>
<div class="e4"><dt>fuera_de_cobertura</dt><dd>La entrada está fuera de lo que cubre la fuente. No descuenta créditos.</dd></div>
<div class="e5"><dt>502 fuente_no_disponible</dt><dd>La fuente oficial no respondió. Llega un error, nunca un sobre vacío ni un dato viejo disfrazado de actual. No descuenta.</dd></div>
</dl>
</div></section>

<section class="seccion inv"><div class="envoltura">
<div class="cab"><span class="rotulo">Servicios</span><h2 class="t2">Agentes que hacen el trabajo territorial</h2>
<p class="entrada">La capa de datos se vende sola, por consulta. Sobre ella construimos y operamos el trabajo completo con tu equipo.</p></div>
<div class="columnas c4">
<div class="activa"><span class="et">en producción · por consulta</span><h3>Datos</h3><p>La capa Terranova: {N_HERR} herramientas sobre {N_FUENTES} fuentes, por MCP, API REST y archivos.</p></div>
<div><span class="et">por entrega</span><h3>Analítica</h3><p>Reglas por obligación, cruces y modelos calibrados en Colombia. Un expediente con la prueba de cada hallazgo.</p></div>
<div><span class="et">por entrega</span><h3>Desarrollo</h3><p>Agentes y aplicaciones dentro del sistema de tu equipo, sobre la capa de datos.</p></div>
<div><span class="et">por proceso o licencia</span><h3>Automatización</h3><p>Procesos que verifican, vigilan y reportan solos, con registro de cada paso.</p></div>
</div>
</div>
<p class="entrada" style="margin-top:28px;font-size:16px">Un agente hace el trabajo, otro lo evalúa sin ver su razonamiento y una persona aprueba. <a class="enlace" href="/servicios">Cómo trabajamos →</a></p>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cab"><span class="rotulo">Para agentes y desarrolladores</span><h2 class="t2">Conecta en un minuto</h2>
<p class="entrada">Tu agente elige la herramienta y Terranova responde con la prueba. Perfiles MCP por familia para clientes con tope de herramientas.</p></div>
{CODIGO}
<p style="margin-top:20px"><a class="enlace" href="/desarrolladores">Guía de conexión completa →</a></p>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><span class="rotulo">Casos</span><h2 class="t2">Preguntas sobre lugares, no sobre personas</h2>
<p class="entrada">Así se ve el trabajo. Todavía no mostramos clientes: estos casos son ilustrativos y sus cifras son posibles, no medidas.</p></div>
<div class="columnas c3">
<div><span class="sello-i">ilustrativo</span><h3>Debida diligencia EUDR</h3><p>Un exportador de café revisa un lote de parcelas contra áreas protegidas, cobertura del suelo y restricciones antes de embarcar.</p><span class="res">Sin hallazgos en 1.510 de 1.900 parcelas; 390 a revisión humana</span></div>
<div><span class="sello-i">ilustrativo</span><h3>Antes de construir</h3><p>Un desarrollador consulta el predio, su destinación, las áreas protegidas y las amenazas de la zona en una sola ficha de lugar.</p><span class="res">Ficha del lugar con su procedencia</span></div>
<div><span class="sello-i">ilustrativo</span><h3>Contexto para crédito</h3><p>Una entidad financiera agrega al estudio de un crédito rural el contexto del municipio: estadísticas, contratación pública y ambiente.</p><span class="res">Un expediente por solicitud</span></div>
</div></div>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cab"><span class="rotulo">Precios</span><h2 class="t2">Pagas por consulta, no por el dato</h2>
<p class="entrada">Cada plan trae créditos al mes. Una consulta cuesta de 1 a 20 créditos según el tipo de pregunta. Los errores, la caché y lo que está fuera de cobertura no descuentan.</p></div>
{planes_html()}
<p style="margin-top:20px"><a class="enlace" href="/precios">Tarifa por tipo de pregunta y preguntas frecuentes →</a></p>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><span class="rotulo">Confianza</span><h2 class="t2">Reglas que no se negocian</h2></div>
<div class="columnas c4">
<div><h3>Licencia por fuente</h3><p>Sin licencia verificada, una fuente no sale a producción. {LICENCIAS["CC-BY-SA-4.0"]} de las {N_FUENTES} son CC BY-SA 4.0.</p></div>
<div><h3>Sin perfiles de personas</h3><p>No hay búsquedas por cédula ni por nombre. Los campos que salen están en una lista blanca.</p></div>
<div><h3>Estado público</h3><p>Cada fuente tiene un canario diario con una verdad medida en la fuente. <a class="enlace" href="/estado">Ver el estado</a></p></div>
<div><h3>La puerta no usa LLM</h3><p>La lógica de cada fuente vive en el catálogo. La misma entrada da la misma consulta, siempre.</p></div>
</div>
<div style="margin-top:40px;display:flex;align-items:center;gap:28px;flex-wrap:wrap">
<span class="rotulo">Aliados y proyectos</span>
<a href="/aliados"><img src="/img/geoai-latam.webp" alt="GeoAI LATAM" width="200" height="45" loading="lazy" style="height:36px;width:auto"></a>
<a href="/aliados" class="t3" style="text-decoration:none">Atalaya Mapas</a>
</div>
</div></section>

<section class="seccion"><div class="envoltura cierre">
<div class="cab" style="margin:0"><h2 class="t2">Prueba una consulta hoy</h2><p class="entrada">1.500 créditos al mes sin costo. Si tienes un proyecto, cuéntanos y lo evaluamos.</p></div>
<div class="botones"><a class="boton p" href="/precios#empezar">Probar gratis</a><a class="boton s" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a></div>
</div></section>
"""
    return pagina(
        "/",
        "Terranova · Respuestas territoriales verificables",
        f"Una puerta por MCP y API REST a {N_FUENTES} fuentes oficiales de Colombia. Cada respuesta con su entidad, su licencia y su huella.",
        c,
        ("escena-predios.js", "escena-cobertura.js"),
    )


def servicios() -> str:
    capas = [
        (
            "Analítica",
            "calcula",
            "Reglas por obligación, cruces entre fuentes y modelos calibrados en Colombia.",
            [
                "Debida diligencia de lotes de parcelas",
                "Cruces de un predio con restricciones y amenazas",
                "Indicadores territoriales por municipio",
            ],
            "Un expediente con la prueba de cada hallazgo",
            "Por entrega",
        ),
        (
            "Desarrollo",
            "construye",
            "Agentes y aplicaciones dentro del sistema de tu equipo, sobre la capa de datos.",
            [
                "Un agente que responde con las fuentes de tu sector",
                "Integración con tu SIG, tu ERP o tus documentos",
                "Tableros y aplicaciones con datos verificables",
            ],
            "Código y despliegue en tu entorno",
            "Por entrega",
        ),
        (
            "Automatización",
            "opera",
            "Procesos que verifican, vigilan y reportan solos, con registro de cada paso.",
            [
                "Vigilancia de cambios en predios o normas",
                "Alertas cuando una fuente publica algo nuevo",
                "Reportes periódicos con su procedencia",
            ],
            "Un proceso en marcha con su bitácora",
            "Por proceso o licencia",
        ),
        (
            "Datos",
            "respalda y expone",
            f"La capa Terranova: {N_HERR} herramientas sobre {N_FUENTES} fuentes oficiales.",
            ["MCP para agentes", "API REST para sistemas", "Archivos para equipos SIG"],
            "Respuestas rt/1 con su prueba",
            "En producción · por consulta",
        ),
    ]
    bloques = "".join(
        f'<div class="bloque{" vivo" if n == "Datos" else ""}"><span class="num">{n.lower()} · {v}</span><h3 class="t3">{n}</h3><p>{d}</p>'
        f'<ul class="lista">{"".join(f"<li>{x}</li>" for x in ej)}</ul><p style="margin-top:6px"><b style="color:var(--tinta);font-weight:600">Entrega:</b> {e}</p>'
        f'<span class="pie">{cobro}</span></div>'
        for n, v, d, ej, e, cobro in capas
    )
    c = (
        portada(
            "Servicios",
            "El trabajo territorial completo, con prueba en cada paso",
            "Analítica, desarrollo y automatización sobre la capa de datos Terranova. Los agentes hacen el trabajo y tu equipo decide.",
            '<div class="botones" style="margin-top:8px"><a class="boton p" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a></div>',
            lado_capas(),
        )
        + f"""
<section class="seccion"><div class="envoltura">
<div class="cab"><span class="rotulo">Las cuatro capas</span><h2 class="t2">Qué entregamos y cómo se cobra</h2></div>
<div class="rejilla r2">{bloques}</div>
</div></section>

<section class="seccion inv"><div class="envoltura">
<div class="cab"><span class="rotulo">Método</span><h2 class="t2">Un agente hace, otro evalúa, una persona aprueba</h2>
<p class="entrada">En cada capa el trabajo pasa por tres manos. El evaluador no ve el razonamiento del que hizo el trabajo: solo el resultado y su prueba.</p></div>
<div class="rejilla r3">
<div class="bloque oscuro"><span class="num" style="color:var(--ambar-500)">1</span><h3 class="t3">El agente hace</h3><p>Consulta las fuentes oficiales por la capa de datos y arma el resultado con la procedencia de cada dato.</p></div>
<div class="bloque oscuro"><span class="num" style="color:var(--ambar-500)">2</span><h3 class="t3">Otro agente evalúa</h3><p>Revisa el resultado contra las fuentes sin ver cómo se llegó a él. Lo que no cuadra vuelve.</p></div>
<div class="bloque oscuro"><span class="num" style="color:var(--ambar-500)">3</span><h3 class="t3">Una persona aprueba</h3><p>Alguien de tu equipo o del nuestro firma la entrega. Nada sale sin esa aprobación.</p></div>
</div>
<p class="entrada" style="margin-top:28px;font-size:16px">Cada entrega deja una pieza reutilizable: una fuente nueva, una regla, un modelo o una plantilla.</p>
</div></section>

<section class="seccion"><div class="envoltura">
<div class="cab"><span class="rotulo">Cómo empezamos</span><h2 class="t2">Precio fijo antes de empezar, nunca por hora</h2></div>
<div class="rejilla r4">
<div class="bloque"><span class="num">1</span><h3 class="t3">Nos cuentas</h3><p>Qué decisión quieres tomar, sobre qué lugares y con qué plazo.</p></div>
<div class="bloque"><span class="num">2</span><h3 class="t3">Evaluamos</h3><p>Revisamos qué fuentes lo cubren y qué falta. Te decimos qué se puede probar y qué no.</p></div>
<div class="bloque"><span class="num">3</span><h3 class="t3">Fijamos el precio</h3><p>Un precio por entrega, acordado antes de empezar. No cobramos por hora.</p></div>
<div class="bloque"><span class="num">4</span><h3 class="t3">Entregamos</h3><p>Con la prueba de cada dato. Si el trabajo se repite, pasa a precio por lugar verificado o por proceso.</p></div>
</div>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><span class="rotulo">Pruebas</span><h2 class="t2">Lo que ya existe, con su alcance</h2></div>
<div class="rejilla r2">
<div class="bloque"><h3 class="t3">GEO Copilot</h3><p>Un asistente territorial, proyecto del fundador. Hoy es un cliente más de la capa de datos: se conecta por el MCP de Terranova, como cualquier agente.</p><span class="pie">Proyecto propio · cliente de la capa de datos</span></div>
<div class="bloque"><h3 class="t3">Vectorización de ortofotos del IGAC</h3><p>Un modelo de segmentación sobre ortofotos del IGAC, desarrollado como tesis de maestría del fundador (mIoU 0,694).</p><span class="pie">Investigación · no es un modelo de producción</span></div>
</div>
</div></section>

<section class="seccion"><div class="envoltura cierre">
<div class="cab" style="margin:0"><h2 class="t2">¿Tienes un proyecto territorial?</h2><p class="entrada">Escríbenos con la decisión que quieres tomar. Respondemos con lo que se puede probar y un precio fijo.</p></div>
<div class="botones"><a class="boton p" href="/contacto?asunto=proyecto">Cuéntanos tu proyecto</a></div>
</div></section>
"""
    )
    return pagina(
        "/servicios",
        "Servicios",
        "Analítica, desarrollo y automatización territorial sobre fuentes oficiales, con prueba en cada paso y precio fijo antes de empezar.",
        c,
    )


def fuentes() -> str:
    lic = "".join(
        f'<tr><td><code>{escape(k)}</code></td><td class="n">{v}</td></tr>'
        for k, v in LICENCIAS.most_common()
    )
    ent = Counter(corta(f.entidad) for f in CAT.fuentes.values()).most_common(12)
    ent_html = "".join(f'<span class="chip">{escape(e)} <b>{n}</b></span>' for e, n in ent)
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

<section class="seccion sup"><div class="envoltura">
<div class="rejilla r2" style="gap:48px">
<div><span class="rotulo">Entidades</span><h2 class="t2" style="margin:12px 0 20px">Quién publica los datos</h2>
<div class="chips">{ent_html}</div>
<p class="suave" style="margin-top:16px">{MODOS["en_vivo"]} fuentes se consultan en vivo y {MODOS["copia"]} desde una copia del bulk oficial, con su fecha de corte en cada respuesta.</p></div>
<div><span class="rotulo">Licencias</span><h2 class="t2" style="margin:12px 0 20px">Licencia verificada por fuente</h2>
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
<tr><td><code>rt_live_</code></td><td>Producción: las fuentes con licencia verificada para uso comercial.</td></tr>
<tr><td><code>rt_test_</code></td><td>Evaluación, con vencimiento: además, fuentes con licencia por verificar, con aviso.</td></tr></tbody></table></div>
<p>Cada llave tiene sus familias. Si una llave se filtra, avísanos: la revocamos y te enviamos otra, con el mismo saldo y el mismo plan.</p></div>
</div>
</div></section>

<section class="seccion sup"><div class="envoltura">
<div class="cab"><span class="rotulo">Preguntas frecuentes</span><h2 class="t2">Lo que suelen preguntar</h2></div>
<div class="prosa" style="max-width:860px">
<h3>¿Qué pasa si se me acaban los créditos?</h3><p>La puerta responde <code>402 saldo_agotado</code> con la fecha en que se renueva tu saldo. Puedes subir de plan en cualquier momento.</p>
<h3>¿Puedo usar los datos comercialmente?</h3><p>Las llaves de producción solo ven fuentes con licencia verificada para uso comercial. Al publicar un dato, cita la atribución que trae la respuesta y respeta su licencia: CC BY-SA exige compartir igual.</p>
<h3>¿Qué hay de los datos personales?</h3><p>No hay búsquedas por cédula ni por nombre, ni perfiles de personas. Los campos que salen de cada fuente están en una lista blanca.</p>
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
<ol><li><b>Pide tu llave.</b> <a href="/precios#empezar">El plan Gratis</a> trae 1.500 créditos al mes. Guárdala como un secreto, nunca en el código.</li>
<li><b>Haz la primera consulta.</b> El código DIVIPOLA de un municipio por su nombre cuesta 1 crédito:</li></ol>
<pre class="suelto"><code>export TERRANOVA_LLAVE=rt_live_...
curl -s -X POST https://terrnova.com/v1/co/territorio/dane_divipola_buscar \\
  -H "Authorization: Bearer $TERRANOVA_LLAVE" \\
  -H "Content-Type: application/json" \\
  -d '{{"nombre":"Cali"}}'</code></pre>
<p>La respuesta trae <code>"estado":"encontrado"</code>, los municipios que coinciden en <code>datos.elementos</code> y la fuente (DANE) con su licencia en <code>procedencia</code>. La búsqueda respeta las tildes: «Bogota» no encuentra «Bogotá».</p>
<ol start="3"><li><b>Mira tu saldo</b> con <code>GET /v1/uso</code>.</li></ol>

<h2 id="mcp">MCP</h2>
<p>La puerta habla MCP por <i>streamable HTTP</i>, con la llave en la cabecera <code>Authorization</code>.</p>
<p>Claude Code:</p>
<pre class="suelto"><code>claude mcp add --transport http terranova https://terrnova.com/mcp \\
  --header "Authorization: Bearer $TERRANOVA_LLAVE"</code></pre>
<p>Cursor y otros clientes que aceptan <code>url</code> y <code>headers</code>:</p>
<pre class="suelto"><code>{{
  "mcpServers": {{
    "terranova": {{
      "url": "https://terrnova.com/mcp/territorio",
      "headers": {{ "Authorization": "Bearer rt_live_..." }}
    }}
  }}
}}</code></pre>
<p>Claude Desktop y otros clientes que solo hablan por stdio, con el puente <code>mcp-remote</code>:</p>
<pre class="suelto"><code>{{
  "mcpServers": {{
    "terranova": {{
      "command": "npx",
      "args": ["mcp-remote", "https://terrnova.com/mcp/ambiente",
               "--header", "Authorization: Bearer ${{TERRANOVA_LLAVE}}"],
      "env": {{ "TERRANOVA_LLAVE": "rt_live_..." }}
    }}
  }}
}}</code></pre>

<h2 id="perfiles">Perfiles</h2>
<table class="tabla"><thead><tr><th>Ruta</th><th>Qué expone</th><th>Para</th></tr></thead><tbody>
<tr><td><code>/mcp</code></td><td>Las {N_HERR} herramientas</td><td>Clientes que buscan herramientas por su cuenta, como Claude</td></tr>
<tr><td><code>/mcp/&lt;familia&gt;</code></td><td>Las de una sola familia</td><td>Un caso de uso de un solo tema: lo más preciso y lo más rápido</td></tr>
<tr><td><code>/mcp/catalogo</code></td><td>Pocas herramientas genéricas que buscan en el catálogo</td><td>Clientes con tope de herramientas, como los modelos de OpenAI (128)</td></tr>
</tbody></table>
<p>Familias: {perfiles}. Todos los perfiles traen las herramientas de nombre a código y <code>fuente_describir</code>, que no gasta créditos.</p>

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
<tr><td><code>procedencia</code></td><td>Por fuente: entidad, URL, norma, licencia, atribución, <code>servido_desde</code>, <code>consultado_en</code> y <code>completitud</code></td></tr>
<tr><td><code>avisos</code></td><td>Lo que debes saber: total desconocido, datos no recientes, copia vencida…</td></tr>
<tr><td><code>geo_result</code></td><td>Las geometrías, en EPSG:4326 salvo que pidas <code>crs_salida: EPSG:9377</code></td></tr>
<tr><td><code>creditos</code></td><td>Lo que costó esa consulta</td></tr>
</tbody></table>
<p><b>«No encontrado» no es «no se pudo».</b> Cuando la fuente no responde llega un error, nunca un sobre vacío. Terranova nunca inventa un dato ni hace pasar uno viejo por actual: <code>servido_desde: obsoleto</code> siempre llega con aviso.</p>

<h2 id="errores">Errores</h2>
<p>En <code>application/problem+json</code> (RFC 9457), con un <code>code</code> estable y el <code>solicitud_id</code> que debes darnos si escribes a soporte.</p>
<div class="desliza"><table class="tabla"><thead><tr><th>HTTP</th><th><code>code</code></th><th>Qué hacer</th></tr></thead><tbody>
<tr><td class="n">400</td><td><code>parametro_invalido</code>, <code>zona_demasiado_grande</code></td><td>Corregir la entrada; <code>param</code> dice cuál</td></tr>
<tr><td class="n">401</td><td><code>no_autenticado</code></td><td>Falta la llave o no es válida</td></tr>
<tr><td class="n">402</td><td><code>saldo_agotado</code></td><td>Se acabaron los créditos del mes; dice cuándo se renuevan</td></tr>
<tr><td class="n">403</td><td><code>sin_permiso</code>, <code>licencia_no_habilitada</code></td><td>La llave no cubre esa familia o esa fuente</td></tr>
<tr><td class="n">404</td><td><code>no_existe</code></td><td>La herramienta o la fuente no existe; sugiere ids parecidos</td></tr>
<tr><td class="n">429</td><td><code>limite_tasa</code></td><td>Espera lo que dice <code>Retry-After</code></td></tr>
<tr><td class="n">502</td><td><code>fuente_no_disponible</code></td><td><b>No se pudo:</b> la fuente oficial falló; reintenta más tarde</td></tr>
<tr><td class="n">504</td><td><code>fuente_lenta</code></td><td><b>No se pudo:</b> la fuente no respondió a tiempo</td></tr>
<tr><td class="n">500</td><td><code>error_interno</code></td><td>Falla nuestra; escríbenos con el <code>solicitud_id</code></td></tr>
</tbody></table></div>
<p>Cada llave tiene una ráfaga de 20 consultas y repone 60 por minuto. Reintenta con espera creciente, nunca en bucle cerrado.</p>

<h2 id="recursos">Recursos</h2>
<ul><li><a href="/llms.txt"><code>/llms.txt</code></a>: el catálogo en texto para agentes.</li>
<li><a href="/.well-known/mcp/server-card.json"><code>/.well-known/mcp/server-card.json</code></a>: la tarjeta del servidor MCP.</li>
<li><a href="/estado"><code>/estado</code></a>: el estado de la puerta y de cada fuente según su canario diario.</li>
<li>Soporte: <a href="mailto:{CORREO}">{CORREO}</a>, de lunes a viernes de 8:00 a 18:00, hora de Colombia.</li></ul>
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
            "Terranova trabaja junto a dos proyectos de la comunidad geoespacial latinoamericana. Son aliados, no clientes.",
        )
        + """
<section class="seccion"><div class="envoltura" style="display:grid;gap:0">
<div class="aliado"><img src="/img/geoai-latam.webp" alt="GeoAI LATAM" width="640" height="144">
<div><h2 class="t3">GeoAI LATAM</h2><p class="suave" style="margin-top:8px">Una comunidad que comparte conocimiento y desarrolla soluciones de inteligencia geoespacial para Latinoamérica: proyectos abiertos, tutoriales y notas de campo.</p>
<p style="margin-top:12px"><a class="enlace" href="https://geoailatam.terrnova.com/">geoailatam.terrnova.com →</a></p></div></div>
<div class="aliado"><div class="pendiente">Atalaya Mapas<small>Logo oficial pendiente</small></div>
<div><h2 class="t3">Atalaya Mapas</h2><p class="suave" style="margin-top:8px">Proyecto aliado de cartografía. Mientras llega su logo oficial, aquí va solo su nombre.</p></div></div>
</div></section>
"""
    )
    return pagina(
        "/aliados", "Aliados", "GeoAI LATAM y Atalaya Mapas, proyectos hermanos de Terranova.", c
    )


def contacto() -> str:
    c = (
        portada(
            "Contacto",
            "Escríbenos",
            "Respondemos de lunes a viernes, de 8:00 a 18:00, hora de Colombia.",
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
        "Escríbenos para un proyecto territorial, para pedir tu llave o para soporte.",
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
            "Las condiciones de uso de Terranova.",
            [
                "Los datos vienen de fuentes oficiales con su licencia; al reutilizarlos, citas la atribución que trae cada respuesta.",
                "Las llaves de producción solo ven fuentes con licencia verificada para uso comercial.",
                "Los créditos se renuevan el día 1 de cada mes y no se acumulan.",
                "Los errores, la caché y lo que está fuera de cobertura no descuentan créditos.",
            ],
        ),
        "privacidad.html": legal(
            "/privacidad",
            "Privacidad",
            "Qué datos tratamos y cómo.",
            [
                "No hay búsquedas por cédula ni por nombre, ni perfiles de personas.",
                "Los campos que salen de cada fuente están en una lista blanca.",
                "Guardamos de tu llave solo su huella (HMAC), nunca la llave.",
                "Medimos el uso por llave para descontar créditos.",
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
