"""CLI de cliente (ADR-0027, spec 10): las funciones puras y la petición al REST, sin red."""

import json

import httpx

from terranova.cliente import (
    Cliente,
    codigo_salida,
    familia_de,
    formatear,
    pares,
)


def test_codigo_salida_distingue_no_encontrado_de_no_se_pudo() -> None:
    assert codigo_salida({"estado": "encontrado"}) == 0
    assert codigo_salida({"estado": "no_encontrado"}) == 0  # «no hay» no es «no se pudo»
    assert codigo_salida({"estado": "fuente_no_disponible"}) == 1
    assert codigo_salida({"estado": "fuente_lenta"}) == 1
    assert codigo_salida({"estado": "error_interno"}) == 1
    assert codigo_salida({}) == 1


def test_familia_de() -> None:
    hs = [{"id": "igac_predio_en_punto", "familia": "territorio"}]
    assert familia_de(hs, "igac_predio_en_punto") == "territorio"
    assert familia_de(hs, "desconocida") is None


def test_pares_arma_el_cuerpo() -> None:
    assert pares(["--lon", "-74.0", "--lat", "4.8"]) == {"lon": "-74.0", "lat": "4.8"}
    assert pares(["--solo"]) == {}  # una bandera sin valor se ignora


def test_formatear_incluye_estado_dato_y_procedencia() -> None:
    sobre = {
        "estado": "encontrado",
        "datos": [{"codigo_predial": "251750000000000050067000000000"}],
        "procedencia": {"fuente": "IGAC", "licencia": "CC BY 4.0"},
    }
    t = formatear(sobre)
    assert "encontrado" in t and "IGAC" in t and "CC BY 4.0" in t


def test_cliente_consultar_hace_post_al_v1_con_la_llave() -> None:
    capturado: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        capturado["url"] = str(req.url)
        capturado["auth"] = req.headers.get("authorization")
        capturado["body"] = json.loads(req.content)
        return httpx.Response(200, json={"estado": "encontrado", "datos": [{"codigo": "x"}]})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    cli = Cliente("https://puerta.test", "rt_test_abc", http=http)
    sobre = cli.consultar("territorio", "igac_predio_en_punto", {"lon": "-74.0", "lat": "4.8"})

    assert sobre["estado"] == "encontrado"
    assert capturado["url"] == "https://puerta.test/v1/co/territorio/igac_predio_en_punto"
    assert capturado["auth"] == "Bearer rt_test_abc"
    assert capturado["body"] == {"lon": "-74.0", "lat": "4.8"}
