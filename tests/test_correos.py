"""Los correos de Terrnova: HTML y texto, la marca, una sola acción, nunca una llave, lo que
escribe la persona siempre escapado y el dato de ejemplo igual al de producción."""

import json
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from terranova import correos
from terranova.correos import Mensaje

SOPORTE = "soporte@terrnova.com"
ENLACE = "https://terrnova.com/v1/alta/confirmar?t=abcdefghijklmnopqrstuvwxyz012345"
AHORA = datetime(2026, 11, 1, 2, 40, tzinfo=UTC)  # 31-10-2026, 21:40 en Colombia
MANANA = datetime(2026, 11, 2, 2, 40, tzinfo=UTC)


def _enlace(nombre: str = "sebastian") -> Mensaje:
    return correos.enlace_llave(
        nombre, ENLACE, creditos=300, dias=15, pedida=AHORA, vence=MANANA, soporte=SOPORTE
    )


def _acuse(nombre: str = "ana", mensaje: str = "Hola,\nquiero un tablero.") -> Mensaje:
    return correos.acuse_contacto(
        nombre,
        "tablero",
        "Tablero o informe",
        mensaje,
        ref="TN-7F3A2C",
        recibido=AHORA,
        soporte=SOPORTE,
    )


def _aviso(organizacion: str = "Ejemplo SAS") -> Mensaje:
    return correos.aviso_contacto(
        "ana", "ana@ejemplo.co", organizacion, "Soporte", "Ayuda", ref="TN-1", recibido=AHORA
    )


def _todos() -> list[Mensaje]:
    return [
        _enlace(),
        correos.ya_tiene_llave(
            "Ana María",
            desde=date(2026, 10, 30),
            vence=date(2026, 11, 14),
            pedida=AHORA,
            soporte=SOPORTE,
        ),
        correos.bienvenida("ana", creditos=300, vence=date(2026, 11, 16), soporte=SOPORTE),
        _acuse(),
        _aviso(),
    ]


@pytest.mark.parametrize("m", _todos(), ids=lambda m: m.asunto[:30])
def test_cada_correo_tiene_html_texto_y_marca(m: Mensaje) -> None:
    assert m.asunto and m.texto.strip() and m.html.startswith("<!doctype html>")
    assert "terrnova-correo.png" in m.html and 'lang="es"' in m.html
    assert "prefers-color-scheme: dark" in m.html  # modo oscuro decidido, no a la suerte
    assert "rt_live_" not in m.texto + m.html and "rt_test_" not in m.texto + m.html
    assert m.responder_a  # siempre hay a quién responder
    for href in re.findall(r'<a [^>]*href="([^"]+)"', m.html):
        assert href.startswith("https://terrnova.com"), href
    assert len(m.html.encode()) < 102_000  # Gmail recorta los correos más pesados


def test_el_nombre_va_con_mayuscula_y_se_trata_de_tu() -> None:
    m = _enlace("sebastian forero")
    assert "Hola, Sebastian Forero." in m.texto and "Hola, Sebastian Forero." in m.html
    assert "El equipo de Terrnova" in m.texto and "Confirmar y ver mi llave" in m.html
    assert correos.nombre_visible("María de la Paz") == "María de la Paz"


def test_las_horas_van_en_hora_de_colombia() -> None:
    assert correos.hora_colombia(AHORA) == "31-10-2026, 21:40 (hora de Colombia)"
    assert correos.fecha(date(2026, 11, 16)) == "16-11-2026"
    m = _enlace()
    assert "31-10-2026, 21:40" in m.texto and "01-11-2026, 21:40" in m.texto


def test_lo_que_escribe_la_persona_se_escapa() -> None:
    m = _acuse("<b>x</b>", "<script>alert(1)</script>")
    assert "<script>" not in m.html and "&lt;script&gt;" in m.html
    assert "<img src=x>" not in _aviso("<img src=x>").html


def test_el_contacto_lleva_referencia_en_los_dos_correos() -> None:
    acuse, aviso = _acuse(), _aviso()
    assert "[TN-7F3A2C]" in acuse.asunto and "TN-7F3A2C" in acuse.texto
    assert "/servicios" in acuse.html  # lo relacionado con el tema
    assert aviso.responder_a == "ana@ejemplo.co" and "TN-1" in aviso.asunto
    assert "sin organización" in _aviso("").texto
    assert correos.referencia("7f3a2c9e") == "TN-7F3A2C"


def test_el_ejemplo_de_la_bienvenida_es_el_predio_del_heroe() -> None:
    """La respuesta de ejemplo es real, y la imagen dibuja ese mismo predio."""
    sm = json.loads(Path("web/publico/datos/sm.json").read_text(encoding="utf-8"))
    assert sm["codes"][sm["obj"]] == correos.EJEMPLO["predio"]
    assert Path("web/publico/img/correo-predio.png").exists()
    m = correos.bienvenida("ana", creditos=300, vence=date(2026, 11, 16), soporte=SOPORTE)
    assert correos.EJEMPLO["predio"] in m.html and correos.PRIMERA_PREGUNTA in m.texto
    assert "16-11-2026" in m.texto and "correo-predio.png" in m.html
