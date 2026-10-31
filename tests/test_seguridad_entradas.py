"""Revisión de seguridad de las entradas (auditoría C27, 2026-10-31): lo que llega a la plantilla
de una fuente pasa por su tipo, sin comillas, comodines ni valores imposibles."""

import pytest

from terranova.catalogo import cargar
from terranova.ejecutor import validar_entrada
from terranova.errores import ErrorEntrada

CATALOGO = cargar()


def _con_tipo(tipo: str) -> str:
    return next(h.id for h in CATALOGO.herramientas.values() if tipo in h.entrada.values())


@pytest.mark.parametrize("valor", ["A", "AB", "x' OR '1'='1", "50%", "a_b"])
def test_nombre_corto_o_con_comodines_no_pasa(valor: str) -> None:
    h = CATALOGO.herramientas["aerocivil_aeropuertos_buscar"]
    with pytest.raises(ErrorEntrada):
        validar_entrada(h, {"nombre": valor})
    validar_entrada(h, {"nombre": "Bogota"})


def test_una_fecha_imposible_es_parametro_invalido() -> None:
    h = CATALOGO.herramientas[_con_tipo("fecha")]
    entrada = dict(h.canario.entrada)
    campo = next(k for k, t in h.entrada.items() if t == "fecha")
    entrada[campo] = "2026-13-45"
    with pytest.raises(ErrorEntrada, match="fecha real"):
        validar_entrada(h, entrada)
