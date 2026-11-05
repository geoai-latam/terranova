"""Topes de las consultas agrupadas de SECOP: que quepan las entidades grandes."""

from terranova.catalogo import cargar

CATALOGO = cargar()


def test_los_contratos_por_nit_caben_para_bogota() -> None:
    """El NIT de Bogotá (899999061) agrupa 369 filas: 34 entidades por 11 años más los sin fecha
    (medido en jbjy-vk9h el 2026-11-04). Con 100 se perdía todo antes de 2026."""
    h = CATALOGO.herramientas["secop_contratos_entidad"]
    assert h.consulta.argumentos["max_filas"] >= 369


def test_los_contratos_de_un_anio_por_nit_caben_para_bogota() -> None:
    """Bogotá en 2025: 554 grupos de entidad, tipo y modalidad, 26 304 contratos (2026-11-04). Con
    200, el total del año daba 25 640 porque se sumaba sobre lo que vino."""
    h = CATALOGO.herramientas["secop_contratos_entidad_anio"]
    assert h.consulta.argumentos["max_filas"] >= 554


def test_el_conteo_de_un_municipio_no_llega_al_tope() -> None:
    """Con `max_filas: 1`, la única fila del conteo llegaba al tope y salía «no se sabe si vino
    todo» en cada respuesta (revisión de valor, 2026-11-04)."""
    h = CATALOGO.herramientas["secop_contratos_municipio"]
    assert h.consulta.argumentos["max_filas"] >= 2


def test_cero_contratos_en_un_municipio_avisa_que_revise_el_nombre() -> None:
    """«Chia» sin tilde da 0 y salía «encontrado» como si Chía no contratara."""
    from terranova.contrato import Sobre
    from terranova.ejecutor import avisos_de_la_ficha

    h = CATALOGO.herramientas["secop_contratos_municipio"]
    cero = Sobre.model_construct(estado="encontrado", datos={"contratos": 0}, avisos=[])
    avisos = avisos_de_la_ficha(h, CATALOGO.fuentes[h.fuente], cero)
    assert len(avisos) == 1 and "tilde" in avisos[0]
    doce_mil = Sobre.model_construct(estado="encontrado", datos={"contratos": 12168}, avisos=[])
    assert avisos_de_la_ficha(h, CATALOGO.fuentes[h.fuente], doce_mil) == []
