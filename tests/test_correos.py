"""Los correos de Terrnova: HTML y texto, la marca, una sola acción, nunca una llave, y lo que
escribe la persona siempre escapado."""

from datetime import date

import pytest

from terranova import correos
from terranova.correos import Mensaje

SOPORTE = "soporte@terrnova.com"
ENLACE = "https://terrnova.com/v1/alta/confirmar?t=abcdefghijklmnopqrstuvwxyz012345"


def _todos() -> list[Mensaje]:
    return [
        correos.enlace_llave("sebastian", ENLACE, creditos=300, dias=15, soporte=SOPORTE),
        correos.ya_tiene_llave("Ana María", soporte=SOPORTE),
        correos.bienvenida("ana", creditos=300, vence=date(2026, 11, 16), soporte=SOPORTE),
        correos.acuse_contacto(
            "ana", "Tablero o informe", "Hola,\nquiero un tablero.", soporte=SOPORTE
        ),
        correos.aviso_contacto("ana", "ana@ejemplo.co", "Ejemplo SAS", "Soporte", "Ayuda"),
    ]


@pytest.mark.parametrize("m", _todos(), ids=lambda m: m.asunto[:30])
def test_cada_correo_tiene_html_texto_y_marca(m: Mensaje) -> None:
    assert m.asunto and m.texto.strip() and m.html.startswith("<!doctype html>")
    assert "terrnova-correo.png" in m.html and 'lang="es"' in m.html
    assert "rt_live_" not in m.texto + m.html and "rt_test_" not in m.texto + m.html
    assert m.responder_a  # siempre hay a quién responder
    for href in __import__("re").findall(r'href="([^"]+)"', m.html):
        assert href.startswith("https://terrnova.com"), href


def test_el_nombre_va_con_mayuscula_y_se_trata_de_tu() -> None:
    m = correos.enlace_llave("sebastian forero", ENLACE, creditos=300, dias=15, soporte=SOPORTE)
    assert "Hola, Sebastian Forero:" in m.texto and "Hola, Sebastian Forero:" in m.html
    assert "El equipo de Terrnova" in m.texto and "Confirmar correo" in m.html
    assert correos.nombre_visible("María de la Paz") == "María de la Paz"


def test_lo_que_escribe_la_persona_se_escapa() -> None:
    m = correos.acuse_contacto("<b>x</b>", "Otro", "<script>alert(1)</script>", soporte=SOPORTE)
    assert "<script>" not in m.html and "&lt;script&gt;" in m.html
    a = correos.aviso_contacto("x", "a@b.co", "<img src=x>", "Otro", "hola")
    assert "<img src=x>" not in a.html


def test_el_aviso_interno_se_responde_a_quien_escribio() -> None:
    a = correos.aviso_contacto("ana", "ana@ejemplo.co", "", "Soporte", "Ayuda")
    assert a.responder_a == "ana@ejemplo.co" and "sin organización" in a.texto


def test_la_fecha_va_en_palabras() -> None:
    assert correos.fecha_larga(date(2026, 11, 16)) == "16 de noviembre de 2026"
    m = correos.bienvenida("ana", creditos=300, vence=date(2026, 11, 16), soporte=SOPORTE)
    assert "16 de noviembre de 2026" in m.texto
