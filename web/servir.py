"""Sirve web/publico en local como lo hace Caddy: /ruta -> ruta.html y 404.html.

/estado se genera con el código local (catálogo real, sin canarios en esta máquina).
Uso: uv run python web/servir.py [puerto]
"""

import http.server
import pathlib
import sys
from datetime import UTC, datetime

from terranova.catalogo import cargar
from terranova.pagina_estado import pagina_estado

CATALOGO = cargar()
RAIZ = pathlib.Path(__file__).parent / "publico"
PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8080


class Manejador(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(RAIZ), **k)

    def _html(self, codigo: int, cuerpo: bytes) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = self.path.split("?")[0].split("#")[0]
        if ruta == "/estado":
            self._html(200, pagina_estado([], CATALOGO, datetime.now(UTC)).encode("utf-8"))
            return
        destino = RAIZ / ruta.lstrip("/")
        if ruta != "/" and not destino.exists():
            if destino.with_suffix(".html").is_file():
                self.path = ruta + ".html"
            else:
                self._html(404, (RAIZ / "404.html").read_bytes())
                return
        super().do_GET()


if __name__ == "__main__":
    print(f"Terranova en local: http://localhost:{PUERTO}", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()
