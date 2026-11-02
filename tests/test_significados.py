"""Un código solo no le dice nada a quien pregunta: su significado va en la misma respuesta."""

from collections.abc import Mapping

from terranova.catalogo import cargar
from terranova.ejecutor import aviso_de_anio_incompleto, convertir, mapear_fila

CATALOGO = cargar()


def _mapear(herramienta: str, fila: Mapping[str, object]) -> dict[str, object]:
    h = CATALOGO.herramientas[herramienta]
    return mapear_fila(h, CATALOGO.fuentes[h.fuente], dict(fila), None)


def test_el_destino_economico_llega_con_su_significado() -> None:
    fila = _mapear("igac_registro_predio", {"DESTINO_ECONOMICO": "G"})
    assert fila["destino_economico"] == "G"
    assert fila["destino_economico_significado"] == "Recreacional"


def test_una_letra_que_ninguna_norma_define_llega_sin_significado() -> None:
    fila = _mapear("igac_registro_predio", {"DESTINO_ECONOMICO": "Ñ"})
    assert fila["destino_economico_significado"] is None


def _zona(fila: Mapping[str, object], capa: str) -> dict[str, object]:
    h = CATALOGO.herramientas["igac_zona_fisica_en_punto"]
    return mapear_fila(h, CATALOGO.fuentes[h.fuente], dict(fila), capa)


def test_el_mismo_codigo_dice_otra_cosa_en_lo_rural_y_en_lo_urbano() -> None:
    # dominio publicado por el IGAC en las capas 15 y 16 (medido el 2026-11-02)
    rural = _zona({"USO_ACTUAL_SUELO": 1, "INFLUENCIA_VIAL": 1, "DISPONIBILIDAD_AGUA": 2}, "15")
    assert rural["uso_actual_suelo_significado"] == "Edificios"
    assert rural["influencia_vial_significado"] == "Buenas 1 - Pavimentada, dos o más vías"
    assert rural["disponibilidad_agua_significado"] == "Suficientes"
    urbano = _zona({"USO_ACTUAL_SUELO": 1, "INFLUENCIA_VIAL": 1, "SERVICIO_PUBLICO": 3}, "16")
    assert urbano["uso_actual_suelo_significado"] == "Residencial"
    assert urbano["influencia_vial_significado"] == "Pavimentadas"
    assert urbano["servicios_publicos_significado"] == "Servicios básicos completos"


def test_un_codigo_que_el_igac_no_define_queda_sin_significado() -> None:
    fila = _zona({"USO_ACTUAL_SUELO": 20, "DISPONIBILIDAD_AGUA": 0}, "15")
    assert fila["uso_actual_suelo"] == 20
    assert fila["uso_actual_suelo_significado"] is None
    assert fila["disponibilidad_agua_significado"] is None


def test_el_uso_numerico_tambien() -> None:
    fila = _mapear("igac_caracteristicas_predio", {"USO_1": 28})
    assert fila["uso_construccion_significado"] == "Comercio (comercial)"


def test_el_suelo_urbano_explica_por_que_no_hay_clase() -> None:
    urbano = _mapear("igac_capacidad_uso_en_punto", {"UCCapacida": "ZU", "Descripcio": "ZU"})
    assert "Zona urbana" in str(urbano["nota_capacidad"])
    rural = _mapear("igac_capacidad_uso_en_punto", {"UCCapacida": "2c", "Descripcio": "x"})
    assert rural["nota_capacidad"] is None


def test_un_codigo_guardado_como_numero_recupera_sus_ceros() -> None:
    fila = _mapear("ungrd_emergencias_municipio", {"codificaci_n_segun_divipola": "5001"})
    assert fila["municipio_divipola"] == "05001"


def test_un_dato_danado_en_la_fuente_sale_vacio() -> None:
    dañada = {"tasa_matriculacion_5_16": "109000000000000.00", "ano": "2012"}
    assert _mapear("men_educacion_etc", dañada)["tasa_matriculacion_5_16"] is None
    sana = {"tasa_matriculacion_5_16": "97.12", "ano": "2021"}
    assert _mapear("men_educacion_etc", sana)["tasa_matriculacion_5_16"] == 97.12


def test_un_entero_con_separador_de_miles_no_se_pierde() -> None:
    assert convertir("379,616", "int") == 379616
    assert convertir("1,5", "int") is None


def test_el_texto_en_blanco_es_vacio() -> None:
    assert convertir(" ", "str") is None


def test_la_fecha_del_banrep_sale_con_formato() -> None:
    assert _mapear("banrep_trm_recientes", {"TIME_PERIOD": "20261103"})["fecha"] == "2026-11-03"


def test_el_ancho_quita_los_decimales_y_rellena_el_cero() -> None:
    fila = _mapear("supersociedades_empresa_grande_por_nit", {"nit": "899999068.00", "ciiu": "610"})
    assert (fila["nit"], fila["ciiu"]) == ("899999068", "0610")


def test_los_anios_sin_residencias_lo_dicen() -> None:
    fuente = CATALOGO.fuentes["policia.hurto_comercio_residencias"]
    assert "residencias" in (aviso_de_anio_incompleto(fuente, {"anio": 2023}) or "")
    assert aviso_de_anio_incompleto(fuente, {"anio": 2024}) is None
    assert aviso_de_anio_incompleto(CATALOGO.fuentes["policia.lesiones"], {"anio": 2023}) is None
