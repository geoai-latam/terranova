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
    # La landing muestra respuestas reales capturadas (consola y respuesta anotada), cada una con su
    # sello; si vuelve un caso ilustrativo, también va sellado.
    html = (PUBLICO / "index.html").read_text(encoding="utf-8")
    assert html.count("capturado el ") >= 3
    assert "ejemplo" not in html.lower()
    assert html.count("ilustrativo") == html.count('class="sello-i">ilustrativo<')


def test_preguntas_por_sector_son_herramientas_reales() -> None:
    sys.path.insert(0, str(RAIZ / "src"))
    from terranova.catalogo import cargar

    ids = set(cargar(RAIZ / "catalogo").herramientas)
    html = (PUBLICO / "index.html").read_text(encoding="utf-8")
    sector = html[html.index('class="sectores"') :]
    citadas = re.findall(r'<span class="id"><code>([a-z0-9_]+)</code>', sector)
    assert len(citadas) == 30
    assert set(citadas) <= ids


def test_el_sitio_no_anuncia_fuentes_sin_uso_comercial() -> None:
    # DISENO.md: una fuente «sin fines de lucro» no se anuncia en el sitio (auditoría 2026-10-31).
    import json

    datos = json.loads((PUBLICO / "datos" / "catalogo.json").read_text(encoding="utf-8"))
    assert all(f["uso_comercial"] == "si" for f in datos["fuentes"].values())
    ids = set(datos["fuentes"])
    assert all(h["fuente"] in ids for h in datos["herramientas"])
