"""El catálogo real valida, y cada regla de la spec 02 y de las ADR rompe con una ficha mala."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from terranova.catalogo import RAIZ, CatalogoInvalido, cargar

FUENTE = "fuentes/igac.catastro.terreno.yaml"
HERRAMIENTA = "herramientas/igac_predio_en_punto.yaml"


def test_el_catalogo_versionado_es_valido() -> None:
    catalogo = cargar()
    assert "igac_predio_en_punto" in catalogo.herramientas


def _catalogo_con(tmp_path: Path, ruta: str, cambio: Callable[[dict[str, Any]], None]) -> Path:
    raiz = tmp_path / "catalogo"
    for carpeta in ("fuentes", "herramientas", "cobertura"):
        shutil.copytree(RAIZ / carpeta, raiz / carpeta)
    archivo = raiz / ruta
    ficha = yaml.safe_load(archivo.read_text(encoding="utf-8"))
    cambio(ficha)
    archivo.write_text(yaml.safe_dump(ficha, allow_unicode=True), encoding="utf-8")
    return raiz


def _set(**valores: Any) -> Callable[[dict[str, Any]], None]:
    def cambio(ficha: dict[str, Any]) -> None:
        for ruta, valor in valores.items():
            *padres, hoja = ruta.split("__")
            destino = ficha
            for p in padres:
                destino = destino[p]
            if valor is _BORRAR:
                del destino[hoja]
            else:
                destino[hoja] = valor

    return cambio


_BORRAR = object()

CASOS = [
    # (archivo, cambio, mensaje esperado)
    (FUENTE, _set(licencia__spdx=None), "ADR-0019"),
    (FUENTE, _set(licencia__verificada=None), "ADR-0007"),
    (FUENTE, _set(licencia__evidencia=None), "evidencia"),
    (FUENTE, _set(clase_acceso="interno_con_permiso"), "ADR-0018"),
    (FUENTE, _set(datos_personales="presentes"), "ADR-0014"),
    # Enmienda ADR-0019: una fuente roja no se publica (queda en borrador).
    (FUENTE, _set(clasificacion_licencia="rojo"), "borrador"),
    # Enmienda ADR-0019: ámbar es dato público reutilizable → uso_comercial «si».
    (FUENTE, _set(clasificacion_licencia="ambar", uso_comercial="no"), "uso_comercial"),
    # Enmienda ADR-0019: datos personales presentes no caben en ámbar (son rojo).
    (
        FUENTE,
        _set(clasificacion_licencia="ambar", uso_comercial="si", datos_personales="presentes"),
        "ADR-0014",
    ),
    # WS3: una cédula de persona natural como campo de la lista blanca rompe el catálogo (ADR-0014)
    (
        FUENTE,
        _set(campos__ced={"nombre": "cedula", "tipo": "str", "desc": "x"}),
        "cédula de persona",
    ),
    (FUENTE, _set(url="http://inseguro.gov.co"), "url"),
    (FUENTE, _set(campos={}), "campos"),
    (
        FUENTE,
        _set(campos__CODIGO_ANTERIOR={"nombre": "codigo_predial", "tipo": "str", "desc": "x"}),
        "mismo nombre",
    ),
    (FUENTE, _set(frescura__sla_actualizacion="mensual"), "sla_actualizacion"),
    (FUENTE, _set(campo_inventado=1), "campo_inventado"),
    (FUENTE, _set(id="igac.otra"), "debe llamarse"),
    (FUENTE, _set(cobertura__indice="cobertura_inventada"), "no existe en catalogo/cobertura"),
    (HERRAMIENTA, _set(fuente="igac.no_existe"), "no existe"),
    (HERRAMIENTA, _set(consulta__campos=["CODIGO", "GLOBALID"]), "lista blanca"),
    (
        HERRAMIENTA,
        _set(consulta__argumentos={"where": "MUNICIPIO = '{municipio}'"}),
        "marcadores sin entrada",
    ),
    (HERRAMIENTA, _set(consulta__capas=[]), "no declara capas"),
    (HERRAMIENTA, _set(consulta__tool="Arcgis Query"), "tool"),
    (HERRAMIENTA, _set(canario__verdad={"propietario": "x"}), "no salen"),
    (HERRAMIENTA, _set(descripcion="Predio en un punto."), "cerrar con"),
    (
        HERRAMIENTA,
        _set(descripcion="Predio. (Fuente: IGAC; licencia: CC BY 4.0.)"),
        "fuente es «CC BY-SA 4.0»",
    ),
    (HERRAMIENTA, _set(canario__entrada={"lon": -74.0}), "entrada del canario"),
    (HERRAMIENTA, _set(familia="deportes"), "familia"),
    (HERRAMIENTA, _set(canario__verdad={}), "verdad o minimos"),
    (HERRAMIENTA, _set(canario__minimos={"codigo_predial": 1}), "a la vez en verdad y minimos"),
    (HERRAMIENTA, _set(canario__minimos={"inventado": 1}), "no salen"),
    (HERRAMIENTA, _set(entrada={"lon": "texto_libre", "lat": "float"}), "entrada"),
    (FUENTE, _set(cobertura__pais="Colombia"), "pais"),
    (
        FUENTE,
        _set(
            campos__CODIGO={"nombre": "codigo_predial", "tipo": "str", "desc": "x", "codigos": {}}
        ),
        "la norma que los define",
    ),
    (FUENTE, _set(cobertura__columna_tiempo="NO_ESTA"), "columna_tiempo"),
    (
        FUENTE,
        _set(
            campos__CODIGO={"nombre": "codigo_predial", "tipo": "str", "desc": "x", "origen": "x"}
        ),
        "origen",
    ),
]


@pytest.mark.parametrize(("ruta", "cambio", "mensaje"), CASOS)
def test_regla_rota_rompe_el_catalogo(
    tmp_path: Path, ruta: str, cambio: Callable[[dict[str, Any]], None], mensaje: str
) -> None:
    raiz = _catalogo_con(tmp_path, ruta, cambio)
    with pytest.raises(CatalogoInvalido, match=mensaje):
        cargar(raiz)


def test_junta_todos_los_errores(tmp_path: Path) -> None:
    raiz = _catalogo_con(
        tmp_path, HERRAMIENTA, _set(consulta__campos=["X"], canario__verdad={"y": 1})
    )
    with pytest.raises(CatalogoInvalido) as exc:
        cargar(raiz)
    assert len(exc.value.errores) == 2


def test_permiso_escrito_habilita_backend_interno(tmp_path: Path) -> None:
    permiso = {"fecha": "2026-11-01", "evidencia": "radicado 2026-000123"}
    raiz = _catalogo_con(
        tmp_path, FUENTE, _set(clase_acceso="interno_con_permiso", permiso=permiso)
    )
    assert cargar(raiz).fuentes["igac.catastro.terreno"].permiso is not None


POR_CODIGO = "herramientas/igac_predio_por_codigo.yaml"


def test_un_str_libre_dentro_de_un_where_es_inyeccion(tmp_path: Path) -> None:
    """`CODIGO = '{codigo}'` con `codigo: str` dejaría pasar `' OR 1=1 --`."""
    raiz = _catalogo_con(
        tmp_path, POR_CODIGO, _set(entrada={"codigo": "str"}, canario__entrada={"codigo": "x"})
    )
    with pytest.raises(CatalogoInvalido, match="inyección"):
        cargar(raiz)


def test_un_marcador_que_es_el_valor_entero_no_es_inyeccion(tmp_path: Path) -> None:
    """`"{lon}"` se reemplaza por el número tal cual: no se arma texto, no hay inyección."""
    assert cargar().herramientas["igac_predio_en_punto"].entrada["lon"] == "float"


def test_los_patrones_de_entrada_rechazan_lo_que_inyectaria() -> None:
    import re

    from terranova.catalogo import PATRONES_ENTRADA

    malos = [
        "' OR 1=1 --",
        "2517500000000000500670000000; DROP",
        "Chía' --",
        "CO1.PCCNTR.1' or '1'='1",
    ]
    for tipo, patron in PATRONES_ENTRADA.items():
        for malo in malos:
            assert re.fullmatch(patron, malo) is None, (tipo, malo)
    assert re.fullmatch(PATRONES_ENTRADA["codigo_predial"], "251750000000000050067000000000")
    assert re.fullmatch(PATRONES_ENTRADA["nombre"], "Chía")
    assert re.fullmatch(PATRONES_ENTRADA["id_secop"], "CO1.PCCNTR.5141215")
    assert re.fullmatch(PATRONES_ENTRADA["documento_normativo"], "resolucion_creg_101-131_2026")
    assert re.fullmatch(PATRONES_ENTRADA["documento_normativo"], "../etc/passwd_2026") is None
    assert re.fullmatch(PATRONES_ENTRADA["sentencia_relatoria"], "T-760-08")


def test_cada_tipo_con_patron_dice_su_forma_con_un_ejemplo_valido() -> None:
    import re

    from terranova.catalogo import FORMAS_ENTRADA, PATRONES_ENTRADA

    assert set(FORMAS_ENTRADA) == set(PATRONES_ENTRADA)
    for tipo, (_, ejemplo) in FORMAS_ENTRADA.items():
        assert re.fullmatch(PATRONES_ENTRADA[tipo], ejemplo), tipo


def test_licencias_legibles() -> None:
    catalogo = cargar()
    assert (
        "licencia: dominio público de Estados Unidos.)"
        in catalogo.herramientas["usgs_sismos_en_zona"].descripcion
    )


def test_corte_igac_se_lee_de_la_descripcion_no_del_nombre() -> None:
    """G2: `…_IGAC_de_octubre` es el corte de octubre de 2025, aunque parezca el más nuevo."""
    import importlib.util
    from datetime import date
    from pathlib import Path

    ruta = Path(__file__).resolve().parents[1] / "scripts" / "corte_igac.py"
    spec = importlib.util.spec_from_file_location("corte_igac", ruta)
    assert spec is not None and spec.loader is not None
    corte_igac = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(corte_igac)
    leer = corte_igac.fecha_de_corte
    assert leer("Información catastral a corte de 31 de octubre de 2025") == date(2025, 10, 31)
    assert leer("… a corte de 30 de junio de 2026") == date(2026, 6, 30)
    assert leer("sin fecha") is None and leer("corte de 3 de brumario de 2026") is None
    fichas = corte_igac.fichas_catastrales()
    assert len(fichas) >= 8 and len(set(fichas.values())) == 1  # todas en el mismo corte


def test_toda_fuente_tiene_perfil() -> None:
    """Spec 07: las 77 fuentes quedaron perfiladas el 2026-10-22; una nueva entra con perfil."""
    sin_perfil = sorted(f.id for f in cargar().fuentes.values() if f.perfil is None)
    assert not sin_perfil, f"fuentes sin perfil (spec 07): {sin_perfil}"


def test_toda_fuente_tiene_ficha_tecnica() -> None:
    """Spec 08: cosechada de la fuente o, si no publica metadatos, escrita a mano."""
    catalogo = cargar()
    sin_ficha = sorted(set(catalogo.fuentes) - set(catalogo.metadatos))
    assert not sin_ficha, f"fuentes sin catalogo/metadatos/<id>.yaml (spec 08): {sin_ficha}"
    for fid, m in catalogo.metadatos.items():
        protocolo = catalogo.fuentes[fid].protocolo
        if protocolo in ("socrata", "arcgis_rest"):
            assert m.metodo == "cosechado", f"{fid}: {protocolo} se cosecha, no se escribe a mano"


def test_la_ficha_tecnica_no_guarda_valores_de_personas() -> None:
    """El repo es público (ADR-0014): de una columna que puede traer personas no sale nada."""
    from terranova.cosecha import _PERSONAS

    for fid, m in cargar().metadatos.items():
        for columna, campo in m.campos.items():
            if _PERSONAS.search(columna):
                assert campo.minimo is None and campo.maximo is None and campo.valores is None, (
                    f"{fid}.{columna}"
                )


def test_metadatos_fuera_de_la_lista_blanca_rompen_el_catalogo(tmp_path: Path) -> None:
    raiz = _catalogo_con(tmp_path, FUENTE, lambda _: None)
    (raiz / "metadatos").mkdir()
    (raiz / "metadatos" / "igac.catastro.terreno.yaml").write_text(
        "fuente: igac.catastro.terreno\nmetodo: cosechado\ncosechado: 2026-10-22\n"
        "origen: https://x.gov.co\ncampos:\n  PROPIETARIO: {tipo_fuente: text}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogoInvalido, match="fuera de la lista blanca"):
        cargar(raiz)


def test_la_ficha_tecnica_no_guarda_correos_ni_telefonos() -> None:
    """Un campo de texto libre puede traer contactos de personas (spec 08): ningún valor guardado
    parece un correo ni anuncia un teléfono."""
    import re

    # sin patrón de dígitos: un BPIN (3603130014) parece un celular; las cédulas las cubre la
    # prueba de columnas de personas
    # y sin palabras sueltas: «Correo Contacto» es el nombre de un campo modificado (una categoría)
    contacto = re.compile(r"@|(TEL[EÉ]FONO|CELULAR|M[OÓ]VIL)\W{0,3}\d{7}", re.IGNORECASE)
    for fid, m in cargar().metadatos.items():
        for columna, campo in m.campos.items():
            vistos = [campo.minimo or "", campo.maximo or "", *(campo.valores or {})]
            assert not any(contacto.search(v) for v in vistos), f"{fid}.{columna}"


def test_ids_parecidos_para_un_error_accionable() -> None:
    from terranova.catalogo import cargar, ids_parecidos

    catalogo = cargar()
    assert ids_parecidos(catalogo, "open-meteo")[:2] == [
        "open_meteo.era5",
        "open_meteo_clima_serie",
    ]
    assert "medicinalegal.homicidios" in ids_parecidos(catalogo, "Medicina Legal")
    assert ids_parecidos(catalogo, "xyzzy") == [] and ids_parecidos(catalogo, "--") == []


def test_la_licencia_dice_si_no_hay_uso_comercial() -> None:
    """Con «licencia: CC BY 4.0» a secas, un agente dijo que Open-Meteo se podía usar
    comercialmente; su API gratuita es solo no comercial (GEO Copilot, plan de fiabilidad)."""
    h = cargar().herramientas["open_meteo_clima_serie"]
    assert h.descripcion.rstrip().endswith("licencia: CC BY 4.0, sin uso comercial.)")


def test_toda_herramienta_que_pide_nit_dice_como_buscarlo() -> None:
    """Fiabilidad: si el agente no tiene el NIT, la descripción debe mandarlo a una herramienta
    de búsqueda por nombre; si no, lo supone (GEO Copilot supuso el de la Alcaldía de Chía)."""
    c = cargar()
    busquedas = {
        h.id
        for h in c.herramientas.values()
        if "buscar" in h.id or h.id == "secop_entidades_municipio"
    }

    def pide_nit(h: object) -> bool:
        return any(
            "nit" in n.lower() and t in ("int", "nit_empresa")
            for n, t in h.entrada.items()  # type: ignore[attr-defined]
        )

    sin_guia = [
        h.id
        for h in c.herramientas.values()
        if pide_nit(h) and not any(b in h.descripcion for b in busquedas)
    ]
    assert not sin_guia, f"piden NIT y no dicen cómo buscarlo: {sorted(sin_guia)}"
