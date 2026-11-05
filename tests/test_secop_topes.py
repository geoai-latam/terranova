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
