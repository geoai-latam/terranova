"""Spec 08: la ficha técnica junta lo curado, lo cosechado y lo medido, y dice sus alertas."""

from datetime import date

import httpx
import pytest

from terranova import puerta
from terranova.catalogo import cargar
from terranova.ficha_tecnica import alertas, ficha_tecnica

CATALOGO = cargar()
HOY = date(2026, 10, 22)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_el_icfes_dice_sus_anios_y_que_esta_atrasado() -> None:
    """Medido el 2026-10-22: declara actualización semestral; sus filas no cambian desde 2023."""
    f = ficha_tecnica(CATALOGO, "icfes.saber11", HOY)
    assert f["cobertura"]["periodo"].startswith("20101 a 20224")
    assert f["frescura"]["datos_actualizados"] == "2023-08-23"
    assert any("semestral" in a and "2023-08-23" in a for a in f["alertas"])
    assert any("llegan hasta 2022:" in a for a in f["alertas"])  # «20224»: año y semestre
    assert any("registro único" in a for a in f["alertas"])  # el perfil: estudiantes repetidos
    assert f["es_geografica"] is False


def test_el_catastro_dice_su_geometria_capas_y_corte() -> None:
    f = ficha_tecnica(CATALOGO, "igac.catastro.terreno", HOY)
    assert f["es_geografica"] and f["geografia"]["geometria"] == "poligono"
    assert set(f["geografia"]["capas"]) == {"7", "14"}  # JSON: las claves son texto
    assert f["frescura"]["corte"] == "30 de junio de 2026"
    nombres = {c["nombre"] for c in f["campos"]}
    assert "codigo_predial" in nombres
    assert {h["id"] for h in f["herramientas"]} == {
        "igac_predio_en_punto",
        "igac_predio_por_codigo",
    }


def test_una_fuente_al_dia_no_tiene_alerta_de_atraso() -> None:
    f = CATALOGO.fuentes["cce.secop2.contratos"]
    m = CATALOGO.metadatos["cce.secop2.contratos"]
    assert not any("no cambian desde" in a for a in alertas(f, m, m.datos_actualizados or HOY))


@pytest.mark.anyio
async def test_fuente_describir_por_mcp_acepta_la_herramienta() -> None:
    r = await puerta.puerta.call_tool("fuente_describir", {"fuente": "icfes_saber11_municipio"})
    assert r.structured_content is not None and r.structured_content["id"] == "icfes.saber11"
    with pytest.raises(Exception, match="no_existe"):
        await puerta.puerta.call_tool("fuente_describir", {"fuente": "no.existe"})
    # error accionable: un agente pidió «open-meteo» y se rindió sin saber el id
    with pytest.raises(Exception, match=r"¿quiso decir dian\.usuarios_aduaneros"):
        await puerta.puerta.call_tool("fuente_describir", {"fuente": "dian-usuarios"})


@pytest.mark.anyio
async def test_rest_sirve_la_ficha_tecnica() -> None:
    from terranova.app import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://t"
    ) as rest:
        f = (await rest.get("/v1/fuentes/igac.catastro.terreno")).json()
        lista = (await rest.get("/v1/fuentes")).json()
    assert f["geografia"]["geometria"] == "poligono" and f["alertas"]
    assert next(x for x in lista if x["id"] == "icfes.saber11")["periodo"].startswith("20101")


def test_los_codigos_dicen_su_norma_y_los_que_nadie_define() -> None:
    """Res. IGAC 070 de 2011 define A a T; los datos traen U a Z y 0, que nadie define."""
    destino = next(
        c
        for c in ficha_tecnica(CATALOGO, "igac.catastro.registro1", HOY)["campos"]
        if c["columna_fuente"] == "DESTINO_ECONOMICO"
    )
    assert destino["codigos"]["A"] == "Habitacional" and "070 de 2011" in destino["codigos_norma"]
    assert {"U", "Z", "0"} <= set(destino["sin_definir"]) and "A" not in destino["sin_definir"]
    agua = next(
        c
        for c in ficha_tecnica(CATALOGO, "igac.catastro.zona_fisica", HOY)["campos"]
        if c["columna_fuente"] == "DISPONIBILIDAD_AGUA"
    )
    assert agua["codigos_norma"] == "dominio publicado por la fuente"


def test_el_atraso_se_mide_a_la_fecha_de_la_cosecha() -> None:
    """Una fuente diaria cosechada hace un mes no queda «atrasada» por eso, y tres días de atraso
    de una diaria no son «datos no recientes»."""
    from datetime import timedelta

    from terranova.ficha_tecnica import atraso

    f = CATALOGO.fuentes["cce.secop2.contratos"]
    m = CATALOGO.metadatos["cce.secop2.contratos"]
    assert atraso(f, m, m.cosechado + timedelta(days=30)) == []
    tres = m.model_copy(update={"datos_actualizados": m.cosechado - timedelta(days=3)})
    assert atraso(f, tres, m.cosechado) == []
    viejo = m.model_copy(update={"datos_actualizados": m.cosechado - timedelta(days=30)})
    assert atraso(f, viejo, m.cosechado)
