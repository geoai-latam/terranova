"""Dibuja las imágenes para compartir (og:image, 1200 x 630) en web/publico/img/og/.

Cada una lleva el logo, el titular (h1) de su página tal como está publicado y una figura del sitio
(las de web/publico/img/figuras, en su reposo): nada de texto escrito aparte. Se corre a mano cuando
cambia un titular o una figura; necesita Playwright y Edge, como capturar.py.

    uv run python web/construir.py
    uv run --with playwright python web/og.py
"""

from __future__ import annotations

import re
import sys
import tempfile
from html import unescape
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent
PUBLICO = RAIZ / "publico"
sys.path.insert(0, str(RAIZ))
import construir  # noqa: E402

FIGURA = {
    "portada": "prueba",
    "servicios": "revision",
    "fuentes": "cobertura",
    "precios": "capas",
    "desarrolladores": "ruta",
}
ARCHIVO = {"portada": "index.html"}


def titular(nombre: str) -> str:
    html = (PUBLICO / ARCHIVO.get(nombre, f"{nombre}.html")).read_text(encoding="utf-8")
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    assert m, nombre
    return unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


def lamina(nombre: str) -> str:
    svg = (PUBLICO / "img" / "figuras" / f"{FIGURA[nombre]}.svg").read_text(encoding="utf-8")
    css = (PUBLICO / "estilo.css").as_uri()
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<link rel="stylesheet" href="{css}">
<style>
html, body {{ margin: 0; width: 1200px; height: 630px; overflow: hidden; background: var(--fondo); }}
.og {{ position: relative; width: 1200px; height: 630px; display: grid; grid-template-columns: 500px 1fr;
  gap: 24px; padding: 56px 56px 48px 64px; box-sizing: border-box; border-top: 6px solid var(--bosque-800); }}
.og .izq {{ display: flex; flex-direction: column; justify-content: space-between; }}
.og .marca {{ font-size: 28px; gap: 14px; }} .og .marca svg {{ width: 38px; height: 38px; }}
.og h1 {{ font: 700 54px/1.04 var(--font-sans); letter-spacing: -0.035em; color: var(--tinta); text-wrap: balance; }}
.og .dom {{ font: 400 18px/1 var(--font-mono); color: var(--tinta-tenue); }}
.og .fig-iso {{ align-self: center; width: 100%; }}
</style></head><body><div class="og">
<div class="izq"><span class="marca">{construir.simbolo()}Terrnova</span><h1>{titular(nombre)}</h1><span class="dom">terrnova.com</span></div>
<figure class="fig-iso" data-figura="{FIGURA[nombre]}"><div class="lienzo">{svg}</div></figure>
</div></body></html>"""


def main() -> None:
    destino = PUBLICO / "img" / "og"
    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pag = b.new_page(viewport={"width": 1200, "height": 630})
        for nombre in FIGURA:
            html = Path(tmp) / f"{nombre}.html"
            html.write_text(lamina(nombre), encoding="utf-8")
            pag.goto(html.as_uri())
            pag.wait_for_timeout(600)
            pag.screenshot(path=str(destino / f"{nombre}.png"))
            print("og:", nombre)
        b.close()


if __name__ == "__main__":
    main()
