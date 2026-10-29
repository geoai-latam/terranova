"""Captura secciones del sitio local (web/servir.py) para revisarlas a ojo.

Uso: uv run --with playwright python web/capturar.py <ancho> <ruta> "<sel>|<sel>" [espera_ms]
Deja capturas/v-<ancho>-<i>.png. Usa Edge con GPU: sin ella las escenas WebGL no pintan.
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

SALIDA = pathlib.Path("capturas")


def main() -> None:
    ancho, ruta, selectores = int(sys.argv[1]), sys.argv[2], sys.argv[3].split("|")
    espera = int(sys.argv[4]) if len(sys.argv) > 4 else 2500
    SALIDA.mkdir(exist_ok=True)
    with sync_playwright() as p:
        nav = p.chromium.launch(
            channel="msedge", args=["--enable-gpu", "--use-angle=d3d11", "--ignore-gpu-blocklist"]
        )
        pag = nav.new_page(viewport={"width": ancho, "height": 900}, device_scale_factor=1)
        pag.on("pageerror", lambda e: print("error:", str(e)[:300]))
        pag.on(
            "console", lambda m: m.type in ("warning", "error") and print("consola:", m.text[:300])
        )
        pag.goto("http://localhost:8080" + ruta)
        pag.wait_for_timeout(1500)
        for i, sel in enumerate(selectores):
            el = pag.locator(sel).first
            el.scroll_into_view_if_needed()
            pag.wait_for_timeout(espera)
            el.screenshot(path=SALIDA / f"v-{ancho}-{i}.png")
            print(SALIDA / f"v-{ancho}-{i}.png")
        nav.close()


if __name__ == "__main__":
    main()
