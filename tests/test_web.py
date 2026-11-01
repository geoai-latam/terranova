"""El sitio público (web/): páginas al día, enlaces internos que existen y reglas de marca."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PUBLICO = RAIZ / "web" / "publico"
PAGINAS = sorted(PUBLICO.glob("*.html"))
# rutas que sirve la puerta, no el sitio (Caddyfile: todo lo que no es @sitio va a la puerta)
DE_LA_PUERTA = ("/v1/", "/mcp", "/estado", "/docs", "/openapi.json", "/llms.txt", "/.well-known/")


def test_paginas_al_dia_con_el_catalogo() -> None:
    r = subprocess.run(
        [sys.executable, str(RAIZ / "web" / "construir.py"), "--revisar"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_estan_todas_las_paginas() -> None:
    nombres = {p.name for p in PAGINAS}
    for n in (
        "index",
        "servicios",
        "fuentes",
        "precios",
        "desarrolladores",
        "aliados",
        "contacto",
        "terminos",
        "privacidad",
        "404",
    ):
        assert f"{n}.html" in nombres


def test_enlaces_internos_existen() -> None:
    caddy = (RAIZ / "docker" / "Caddyfile").read_text(encoding="utf-8")
    for p in PAGINAS:
        html = p.read_text(encoding="utf-8")
        for ruta in re.findall(r'(?:href|src)="(/[^"#?]*)', html):
            if ruta.startswith(DE_LA_PUERTA):
                continue
            destino = PUBLICO / ruta.lstrip("/")
            existe = destino.is_file() or destino.with_suffix(".html").is_file() or (ruta == "/")
            assert existe, f"{p.name}: {ruta} no existe en web/publico"
            primero = "/" + ruta.strip("/").split("/")[0]
            if ruta != "/" and not ruta.startswith(("/js/", "/datos/", "/img/")):
                assert f" {primero}" in caddy, f"{ruta} no está en @sitio del Caddyfile"


def test_reglas_de_marca_y_secretos() -> None:
    for p in PAGINAS:
        html = p.read_text(encoding="utf-8")
        assert "arcgis" not in html.lower(), f"{p.name} nombra ArcGIS"
        # solo marcadores de llave, nunca una llave real
        for llave in re.findall(r"rt_(?:live|test)_[A-Za-z0-9_-]*", html):
            assert llave in ("rt_live_", "rt_test_"), f"{p.name}: posible llave {llave[:12]}…"
        assert '<html lang="es">' in html
        assert "<title>" in html and 'name="description"' in html


def test_ejemplos_van_sellados() -> None:
    # La landing muestra respuestas reales capturadas (la consola del héroe), cada una con su
    # fecha en DD-MM-AAAA; si vuelve un caso ilustrativo, también va sellado.
    html = (PUBLICO / "index.html").read_text(encoding="utf-8")
    assert len(re.findall(r"capturado el \d{2}-\d{2}-\d{4}", html)) >= 3
    assert not re.search(r"capturado el \d{4}-", html)
    assert "ejemplo" not in html.lower()
    # (las figuras lo dicen además en su aria-label, en plural: «… son ilustrativos»)
    sellos = html.count('class="sello-i">ilustrativo<')
    assert len(re.findall(r"(?<![a-z])ilustrativo(?![a-z])", html)) == sellos


def test_soluciones_por_sector_salen_de_herramientas_reales() -> None:
    sys.path.insert(0, str(RAIZ / "web"))
    import construir  # type: ignore[import-not-found]  # web/ no es un paquete

    vendibles = {h.id for h in construir.HERR}
    html = (PUBLICO / "index.html").read_text(encoding="utf-8")
    sector = html[html.index('class="sectores"') :]
    paneles = re.findall(r'data-herramientas="([a-z0-9_ ]+)"', sector)
    assert len(paneles) == 6
    citadas = {h for p in paneles for h in p.split()}
    assert citadas <= vendibles
    for h in citadas:  # sin el DANE en lo que se vende como servicio (decisión del 01-11-2026)
        fuente = construir.CAT.fuentes[construir.CAT.herramientas[h].fuente]
        assert "DANE" not in construir.nombre_entidad(fuente.entidad), h


def test_el_sitio_ofrece_solo_la_prueba_y_los_precios_decididos() -> None:
    # Decisiones del dueño (01-11-2026): solo la llave de prueba (el plan Gratis no se anuncia),
    # precios de lanzamiento en pesos y quién está detrás, sin nombre de persona.
    sys.path.insert(0, str(RAIZ / "web"))
    import construir  # web/ no es un paquete

    for p in PAGINAS:
        texto = re.sub(r"<[^>]+>", " ", p.read_text(encoding="utf-8"))
        assert not re.search(r"plan gratis|empieza gratis|1\.500 créditos", texto, re.I), p.name
        assert "plan-gratis" not in p.read_text(encoding="utf-8"), p.name
    precios = (PUBLICO / "precios.html").read_text(encoding="utf-8")
    for _, nombre, mes, anual in construir.PLANES:
        assert nombre in precios and construir.miles(mes) in precios
        assert construir.miles(anual) in precios
    prueba = f"{construir.miles(construir.CREDITOS_PRUEBA)} créditos"
    assert prueba in precios and f"{construir.DIAS_PRUEBA} días" in precios
    assert construir.QUIEN in (PUBLICO / "index.html").read_text(encoding="utf-8")


def test_cada_pagina_tiene_imagen_para_compartir() -> None:
    for p in PAGINAS:
        html = p.read_text(encoding="utf-8")
        m = re.search(
            r'property="og:image" content="https://terrnova\.com(/img/og/[a-z]+\.png)"', html
        )
        assert m, f"{p.name} sin og:image"
        assert (PUBLICO / m.group(1).lstrip("/")).is_file(), m.group(1)
        assert '<meta name="twitter:card" content="summary_large_image">' in html


def test_el_sitio_no_anuncia_fuentes_sin_uso_comercial() -> None:
    # DISENO.md: una fuente «sin fines de lucro» no se anuncia en el sitio (auditoría 2026-10-31).
    import json

    datos = json.loads((PUBLICO / "datos" / "catalogo.json").read_text(encoding="utf-8"))
    assert all(f["uso_comercial"] == "si" for f in datos["fuentes"].values())
    ids = set(datos["fuentes"])
    assert all(h["fuente"] in ids for h in datos["herramientas"])


def test_indice_de_entidades_solo_con_fuentes_vendibles() -> None:
    # El índice de /fuentes nombra solo entidades con al menos una fuente publicada y con uso
    # comercial «si»; la fuente «sin fines de lucro» de la DIAN (usuarios aduaneros) no aparece.
    sys.path.insert(0, str(RAIZ / "web"))
    import construir  # web/ no es un paquete

    html = (PUBLICO / "fuentes.html").read_text(encoding="utf-8")
    indice = html[html.index('class="indice"') :]
    nombradas = set(re.findall(r"<h3>([^<]+)<span", indice))
    vendibles = {
        construir.nombre_entidad(f.entidad)
        for f in construir.CAT.fuentes.values()
        if f.estado == "publicada" and f.uso_comercial == "si"
    }
    assert nombradas and nombradas <= vendibles
    sin_lucro = [f for f in construir.CAT.fuentes.values() if f.uso_comercial != "si"]
    textos = "".join(p.read_text(encoding="utf-8") for p in PAGINAS).casefold()
    for f in sin_lucro:
        assert f.titulo.casefold() not in textos, f"{f.id} no tiene uso comercial y aparece"
    assert "usuarios aduaneros" not in textos


def test_figuras_isometricas_al_dia_y_verdaderas() -> None:
    # Las figuras del sitio (web/figuras, kit de Anatomy) llevan la huella de sus datos, sus
    # scripts y el kit; los datos salen del catálogo y no nombran entidades fuera de los turnos.
    sys.path.insert(0, str(RAIZ / "web"))
    import construir  # web/ no es un paquete

    datos = construir.datos_figuras()
    huella = construir.huella_figuras()
    html = "".join(p.read_text(encoding="utf-8") for p in PAGINAS)
    for nombre in construir.NOMBRES_FIGURAS:
        for capa in ("", "-viva"):  # la capa fija (<img>) y la viva (en línea)
            svg = (PUBLICO / "img" / "figuras" / f"{nombre}{capa}.svg").read_text(encoding="utf-8")
            assert f'data-datos="{huella}"' in svg, f"{nombre}{capa}.svg no está al día"
        assert f'data-figura="{nombre}"' in html, f"ninguna página usa la figura {nombre}"
    ids = {h.id for h in construir.HERR}
    turnos = datos["ruta"]["turnos"]
    assert {t["herramienta"] for t in turnos} <= ids
    assert len(turnos) + len(datos["ruta"]["otras"]) == construir.N_ENTIDADES
    assert sum(n for _, n in datos["capas"]["familias"]) + construir.POR_FAMILIA["meta"] == (
        construir.N_HERR
    )
    # Las entidades sin nombre en la figura van solo como conteos: nada de nombres sueltos.
    assert all(isinstance(n, int) for n in datos["ruta"]["otras"])
    assert "DIAN" not in (PUBLICO / "index.html").read_text(encoding="utf-8")


def test_figuras_respetan_movimiento_reducido_y_marca() -> None:
    css = (PUBLICO / "estilo.css").read_text(encoding="utf-8")
    js = (PUBLICO / "js" / "figuras.js").read_text(encoding="utf-8")
    bloque = css[css.index("figuras isométricas de la portada") :]
    assert "prefers-reduced-motion: reduce" in bloque
    assert "prefers-reduced-motion: reduce" in js
    html = (PUBLICO / "index.html").read_text(encoding="utf-8")
    texto = re.sub(r"<[^>]+>", " ", html)
    assert "Terranova" not in texto, "la marca se escribe Terrnova"
    assert "Terrnova" in (PUBLICO / "img" / "figuras" / "ruta-viva.svg").read_text(encoding="utf-8")


def test_figuras_solo_nombran_herramientas_vendibles_y_sin_dane() -> None:
    # Las figuras solo nombran herramientas publicadas y con uso comercial, y ninguna nombra el DANE
    # (sin base legal para venderlo en servicios, decisión del dueño del 01-11-2026).
    import html
    import json

    sys.path.insert(0, str(RAIZ / "web"))
    import construir  # web/ no es un paquete

    datos = construir.datos_figuras()
    vendibles = {h.id for h in construir.HERR}
    for fig, ids in datos["usadas"].items():
        assert ids and set(ids) <= vendibles, (
            f"{fig} nombra herramientas no vendibles: {set(ids) - vendibles}"
        )
        for i in ids:
            fuente = construir.CAT.fuentes[construir.CAT.herramientas[i].fuente]
            assert "DANE" not in construir.nombre_entidad(fuente.entidad), (
                f"{fig} usa {i}, del DANE"
            )
    sin_mapa = {k: v for k, v in datos.items() if k != "cobertura"}
    assert not re.search(r"\bDANE\b", json.dumps(sin_mapa, ensure_ascii=False))
    for nombre in construir.NOMBRES_FIGURAS:
        svg = html.unescape(
            "".join(
                (PUBLICO / "img" / "figuras" / f"{nombre}{capa}.svg").read_text(encoding="utf-8")
                for capa in ("", "-viva")
            )
        )
        for hid in construir.SIN_CANARIO_VERDE:
            assert hid not in svg, f"{nombre} usa de ejemplo {hid}, sin canario en verde"
        assert not re.search(r"\bDANE\b", svg), f"{nombre}.svg nombra el DANE"
        for hid in re.findall(r"\b[a-z0-9]+(?:_[a-z0-9]+){2,}\b", svg):
            assert hid in vendibles, f"{nombre}.svg nombra {hid}, que no se vende"
    # y la lectura bajo cada figura en las páginas
    for p in PAGINAS:
        for lectura in re.findall(
            r"<span data-lectura[^>]*>(.*?)</span>", p.read_text(encoding="utf-8")
        ):
            assert "DANE" not in lectura, f"{p.name}: una figura lee {lectura}"
            for hid in re.findall(r"<code>([a-z0-9_]+)</code>", lectura):
                assert hid in vendibles


def test_ninguna_pagina_usa_de_ejemplo_una_herramienta_sin_canario_verde() -> None:
    # Las herramientas cuyo canario no está en verde siguen en el catálogo (/fuentes las lista desde
    # datos/catalogo.json), pero ninguna página ni figura las usa de ejemplo.
    sys.path.insert(0, str(RAIZ / "web"))
    import construir  # web/ no es un paquete

    html = "".join(p.read_text(encoding="utf-8") for p in PAGINAS)
    for hid in construir.SIN_CANARIO_VERDE:
        assert hid not in html, f"una página usa de ejemplo {hid}"
    for pagina in ("index.html", "servicios.html", "precios.html", "desarrolladores.html"):
        texto = re.sub(r"<[^>]+>", " ", (PUBLICO / pagina).read_text(encoding="utf-8"))
        for ejemplo in ("TRM", "Saber 11", "dólar", "BanRep"):
            assert ejemplo not in texto, f"{pagina} usa de ejemplo {ejemplo}"
