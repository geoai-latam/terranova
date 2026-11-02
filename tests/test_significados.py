"""Un código solo no le dice nada a quien pregunta: su significado va en la misma respuesta."""

from terranova.catalogo import cargar
from terranova.ejecutor import mapear_fila

CATALOGO = cargar()


def _mapear(herramienta: str, fila: dict[str, object]) -> dict[str, object]:
    h = CATALOGO.herramientas[herramienta]
    return mapear_fila(h, CATALOGO.fuentes[h.fuente], fila, None)


def test_el_destino_economico_llega_con_su_significado() -> None:
    fila = _mapear("igac_registro_predio", {"DESTINO_ECONOMICO": "G"})
    assert fila["destino_economico"] == "G"
    assert fila["destino_economico_significado"] == "Recreacional"


def test_una_letra_que_ninguna_norma_define_llega_sin_significado() -> None:
    fila = _mapear("igac_registro_predio", {"DESTINO_ECONOMICO": "Ñ"})
    assert fila["destino_economico_significado"] is None


def test_el_uso_numerico_tambien() -> None:
    fila = _mapear("igac_caracteristicas_predio", {"USO_1": 28})
    assert fila["uso_construccion_significado"] == "Comercio (comercial)"


def test_el_suelo_urbano_explica_por_que_no_hay_clase() -> None:
    urbano = _mapear("igac_capacidad_uso_en_punto", {"UCCapacida": "ZU", "Descripcio": "ZU"})
    assert "Zona urbana" in str(urbano["nota_capacidad"])
    rural = _mapear("igac_capacidad_uso_en_punto", {"UCCapacida": "2c", "Descripcio": "x"})
    assert rural["nota_capacidad"] is None
