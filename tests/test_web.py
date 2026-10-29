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


def test_casos_ilustrativos_van_sellados() -> None:
    html = (PUBLICO / "index.html").read_text(encoding="utf-8")
    assert html.count('class="sello-i">ilustrativo<') == 3
    assert html.count("ejemplo · capturado") >= 2
