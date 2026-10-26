"""G6 (ADR-0026, spec 09): la ingesta del catálogo DCAT lee bien la Discovery API, sin red."""

import json
from datetime import date
from typing import Any

import pytest

from terranova.descubrimiento import (
    DatasetDescubrible,
    a_jsonl,
    buscar,
    buscar_vectorial,
    cargar_jsonl,
    cargar_vectores,
    de_dcat_us,
    de_socrata_catalog,
    embeber_catalogo,
    metricas,
    texto_para_embedding,
    vectores_a_jsonl,
)

HOY = date(2026, 10, 25)


def _resultado(**over: object) -> dict[str, object]:
    base = {
        "resource": {
            "id": "jbjy-vk9h",
            "name": "SECOP II - Contratos Electrónicos",
            "description": "Contratos del SECOP II.",
            "attribution": "Colombia Compra Eficiente",
            "columns_field_name": ["nombre_entidad", "valor_del_contrato", "ciudad"],
            "data_updated_at": "2026-10-24T05:48:00.000Z",
            "page_views": {"page_views_total": 1234},
            "download_count": 56,
        },
        "classification": {"domain_category": "Gastos Gubernamentales"},
        "metadata": {"domain": "www.datos.gov.co", "license": "Creative Commons Attribution 4.0"},
        "owner": {"display_name": "SECOP"},
    }
    base.update(over)
    return base


def test_de_socrata_catalog_mapea_los_campos() -> None:
    d = de_socrata_catalog(_resultado())
    assert d.id_socrata == "jbjy-vk9h"
    assert d.titulo == "SECOP II - Contratos Electrónicos"
    assert d.entidad == "Colombia Compra Eficiente"  # attribution gana al owner
    assert d.categoria == "Gastos Gubernamentales"
    assert d.columnas == ("nombre_entidad", "valor_del_contrato", "ciudad")
    assert d.licencia == "Creative Commons Attribution 4.0"
    assert d.vistas == 1234 and d.descargas == 56
    assert d.url == "https://www.datos.gov.co/resource/jbjy-vk9h.json"
    assert d.protocolo == "socrata"


def test_entidad_cae_al_owner_y_luego_al_dominio() -> None:
    sin_attr = _resultado(resource={"id": "aaaa-bbbb"}, owner={"display_name": "DANE"})
    assert de_socrata_catalog(sin_attr).entidad == "DANE"
    solo_dominio = _resultado(
        resource={"id": "cccc-dddd"}, owner={}, metadata={"domain": "www.datos.gov.co"}
    )
    assert de_socrata_catalog(solo_dominio).entidad == "www.datos.gov.co"


def test_resultado_sin_id_se_rechaza() -> None:
    with pytest.raises(KeyError):
        de_socrata_catalog(_resultado(resource={"name": "sin id"}))


def test_con_licencia_y_vivo() -> None:
    con = de_socrata_catalog(_resultado())
    assert con.con_licencia() is True
    assert con.vivo(HOY) is True  # actualizado ayer

    sin_lic = de_socrata_catalog(_resultado(metadata={"domain": "x", "license": None}))
    assert sin_lic.con_licencia() is False

    viejo = de_socrata_catalog(
        _resultado(resource={"id": "ee-ff", "data_updated_at": "2023-01-01T00:00:00Z"})
    )
    assert viejo.vivo(HOY) is False

    sin_fecha = de_socrata_catalog(_resultado(resource={"id": "gg-hh"}))
    assert sin_fecha.vivo(HOY) is False  # sin fecha no cuenta como vivo


def _ds(entidad: str, licencia: str | None, fecha: str | None) -> DatasetDescubrible:
    return DatasetDescubrible(
        id_socrata="x",
        titulo="t",
        descripcion="",
        entidad=entidad,
        categoria=None,
        columnas=(),
        licencia=licencia,
        actualizado_en=fecha,
        vistas=0,
        descargas=0,
        url="https://www.datos.gov.co/resource/x.json",
    )


def test_metricas_resume_la_compuerta() -> None:
    datasets = [
        _ds("IGAC", "CC BY 4.0", "2026-10-01T00:00:00Z"),
        _ds("IGAC", None, "2026-09-01T00:00:00Z"),
        _ds("DANE", "CC BY-SA 4.0", "2020-01-01T00:00:00Z"),  # con licencia pero no vivo
    ]
    m = metricas(datasets, hoy=HOY)
    assert m.total == 3
    assert m.con_licencia == 2
    assert m.vivos == 2  # los dos de 2026
    assert m.entidades == 2
    assert m.top_entidades[0] == ("IGAC", 2)


def test_a_jsonl_una_linea_por_dataset_con_sus_campos() -> None:
    datasets = [_ds("IGAC", "CC BY 4.0", "2026-10-01T00:00:00Z")]
    lineas = a_jsonl(datasets).splitlines()
    assert len(lineas) == 1
    fila = json.loads(lineas[0])
    assert fila["entidad"] == "IGAC" and fila["licencia"] == "CC BY 4.0"
    assert fila["url"].endswith("/resource/x.json")


# --------------------------------------------------------------------------- buscador (spec 09)
def _reg(
    id_: str,
    *,
    licencia: str | None = None,
    fecha: str | None = None,
    vistas: int = 0,
    titulo: str = "dato catastro",
    entidad: str = "IGAC",
) -> DatasetDescubrible:
    return DatasetDescubrible(
        id_socrata=id_,
        titulo=titulo,
        descripcion="",
        entidad=entidad,
        categoria=None,
        columnas=(),
        licencia=licencia,
        actualizado_en=fecha,
        vistas=vistas,
        descargas=0,
        url=f"https://www.datos.gov.co/resource/{id_}.json",
    )


def test_buscar_casa_todas_las_palabras_sin_tildes() -> None:
    a = _reg("a", titulo="Contratos de farmacia", entidad="SECOP", vistas=10)
    b = _reg("b", titulo="Áreas protegidas")  # no casa «farmacia»
    hallados = buscar([a, b], "CONTRATOS farmacia", hoy=HOY)  # sin tildes ni mayúsculas
    assert [d.id_socrata for d in hallados] == ["a"]


def test_buscar_ordena_con_licencia_luego_vivo_luego_uso() -> None:
    sin = _reg("sin", licencia=None, fecha=None, vistas=100)  # sin licencia: último
    lic_viejo = _reg("licviejo", licencia="CC BY", fecha="2020-01-01T00:00:00Z")
    vivo_poco = _reg("vivo1", licencia="CC BY", fecha="2026-10-01T00:00:00Z", vistas=1)
    vivo_mucho = _reg("vivo2", licencia="CC BY", fecha="2026-10-01T00:00:00Z", vistas=999)
    orden = buscar([sin, lic_viejo, vivo_poco, vivo_mucho], "catastro", hoy=HOY)
    assert [d.id_socrata for d in orden] == ["vivo2", "vivo1", "licviejo", "sin"]


def test_buscar_filtra_por_entidad() -> None:
    igac = _reg("i", licencia="CC BY", fecha="2026-10-01T00:00:00Z", entidad="IGAC")
    dane = _reg("d", licencia="CC BY", fecha="2026-10-01T00:00:00Z", entidad="DANE")
    hallados = buscar([igac, dane], "catastro", entidad="igac", hoy=HOY)
    assert [d.id_socrata for d in hallados] == ["i"]


def test_cargar_jsonl_redondea_lo_que_dejo_a_jsonl() -> None:
    orig = [_reg("a", licencia="CC BY", fecha="2026-10-01T00:00:00Z", vistas=5)]
    assert cargar_jsonl(a_jsonl(orig)) == orig  # frozen dataclass: igualdad por campos


# --------------------------------------------------------- DCAT-US del Hub de la ICDE (ArcGIS)
def _dcat(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "identifier": "https://www.arcgis.com/home/item.html?id="
        + "4a673b3d51c146abab5fd462992dd2c0&sublayer=0",
        "title": "Dato Fundamental - Cuerpos de Agua 500k",
        "description": "Cuerpos de agua a escala 1:500.000.",
        "publisher": {"name": "Instituto Geográfico Agustín Codazzi"},
        "keyword": ["Cartografía", "Cuerpos de agua", "Hidrografía"],
        "theme": ["geospatial"],
        "license": "http://creativecommons.org/licenses/by/4.0/",
        "modified": "2026-09-30T00:00:00.000Z",
        "landingPage": "https://datos.icde.gov.co/datasets/IGAC::cuerpos-de-agua",
        "distribution": [
            {"title": "ArcGIS Hub Dataset", "format": "Web Page", "accessURL": "https://hub/x"},
            {
                "title": "ArcGIS GeoService",
                "format": "ArcGIS GeoServices REST API",
                "accessURL": "https://mapas.igac.gov.co/server/rest/services/Dato_Fundamental/x",
            },
        ],
    }
    base.update(over)
    return base


def test_de_dcat_us_mapea_capa_arcgis() -> None:
    d = de_dcat_us(_dcat())
    assert d.id_socrata == "4a673b3d51c146abab5fd462992dd2c0:0"  # item + sublayer
    assert d.titulo == "Dato Fundamental - Cuerpos de Agua 500k"
    assert d.entidad == "Instituto Geográfico Agustín Codazzi"
    assert d.columnas == ("Cartografía", "Cuerpos de agua", "Hidrografía")
    assert d.licencia == "http://creativecommons.org/licenses/by/4.0/"
    assert d.actualizado_en == "2026-09-30T00:00:00.000Z"
    assert d.protocolo == "arcgis_rest"
    # la url es el endpoint REST, no la página del Hub
    assert d.url == "https://mapas.igac.gov.co/server/rest/services/Dato_Fundamental/x"


def test_de_dcat_us_clasifica_base_vs_tematico() -> None:
    assert de_dcat_us(_dcat()).categoria == "Dato temático"  # cuerpos de agua
    base = de_dcat_us(_dcat(keyword=["Restitución", "Fotogrametría", "Planimetría", "Altimetría"]))
    assert base.categoria == "Cartografía base"  # restitución del IGAC (la cola larga)


def test_de_dcat_us_sin_rest_cae_a_la_pagina_del_hub() -> None:
    d = de_dcat_us(_dcat(distribution=[{"title": "web", "format": "Web Page"}]))
    assert d.url == "https://datos.icde.gov.co/datasets/IGAC::cuerpos-de-agua"


def test_de_dcat_us_sin_identifier_se_rechaza() -> None:
    with pytest.raises(KeyError):
        de_dcat_us(_dcat(identifier=""))


def test_dcat_us_entra_al_mismo_buscador_y_jsonl() -> None:
    d = de_dcat_us(_dcat())
    # el buscador es el mismo (un solo buscador, dos catálogos)
    assert buscar([d], "cuerpos de agua", hoy=HOY) == [d]
    # y redondea por JSONL conservando el protocolo
    assert cargar_jsonl(a_jsonl([d])) == [d]


# ------------------------------------------------------------ embeddings del catálogo (ADR-0028)
class _EmbedderFalso:
    """Embebedor determinista para probar la lógica sin modelo ni red: cada texto → un vector 3D
    según palabras clave, así el coseno es predecible."""

    def _vec(self, texto: str) -> tuple[float, ...]:
        t = texto.lower()
        return (
            1.0 if "agua" in t or "hidr" in t else 0.0,
            1.0 if "bosque" in t or "arbol" in t else 0.0,
            1.0 if "contrato" in t or "secop" in t else 0.0,
        )

    def consulta(self, texto: str) -> tuple[float, ...]:
        return self._vec(texto)

    def documentos(self, textos: list[str]) -> list[tuple[float, ...]]:
        return [self._vec(t) for t in textos]


def test_texto_para_embedding_junta_los_campos() -> None:
    d = de_dcat_us(_dcat())
    t = texto_para_embedding(d)
    assert "Cuerpos de Agua" in t and "Instituto Geográfico" in t and "Hidrografía" in t


def test_embeber_catalogo_y_buscar_vectorial() -> None:
    agua = _reg("agua", titulo="Cuerpos de agua e hidrografía", licencia="CC BY")
    bosque = _reg("bosque", titulo="Cobertura de bosque y árboles", licencia="CC BY")
    contrato = _reg("contrato", titulo="Contratos del SECOP", licencia="CC BY")
    datasets = [agua, bosque, contrato]
    emb = _EmbedderFalso()
    vectores = embeber_catalogo(datasets, emb)
    assert set(vectores) == {"agua", "bosque", "contrato"}
    # una consulta sobre agua trae el de agua, no los otros (piso filtra lo ortogonal)
    vq = emb.consulta("dónde hay agua")
    hallados = buscar_vectorial(datasets, vq, vectores, piso=0.5, hoy=HOY)
    assert [d.id_socrata for d in hallados] == ["agua"]


def test_buscar_vectorial_rompe_empate_por_licencia() -> None:
    con = _reg("con", titulo="agua potable", licencia="CC BY", fecha="2026-10-01T00:00:00Z")
    sin = _reg("sin", titulo="agua potable", licencia=None)
    emb = _EmbedderFalso()
    vectores = embeber_catalogo([con, sin], emb)
    vq = emb.consulta("agua")
    # mismo parecido (ambos «agua») → el que tiene licencia va primero
    orden = buscar_vectorial([con, sin], vq, vectores, piso=0.5, hoy=HOY)
    assert [d.id_socrata for d in orden] == ["con", "sin"]


def test_vectores_redondean_por_jsonl() -> None:
    vectores: dict[str, tuple[float, ...]] = {"a": (0.1, 0.2, 0.3), "b": (1.0, 0.0, 0.5)}
    assert cargar_vectores(vectores_a_jsonl(vectores)) == vectores


# --------------------------------------------------------- paginación de la ingesta (pieza 5)
class _Resp:
    def __init__(self, cuerpo: dict[str, Any]) -> None:
        self._cuerpo = cuerpo

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return self._cuerpo


class _HTTPFalso:
    """Devuelve páginas en secuencia y guarda los params de cada GET (sin red)."""

    def __init__(self, paginas: list[dict[str, Any]]) -> None:
        self._paginas = paginas
        self.params: list[dict[str, Any]] = []
        self._i = 0

    def get(self, url: str, params: dict[str, Any] | None = None) -> _Resp:
        self.params.append(params or {})
        cuerpo = self._paginas[self._i] if self._i < len(self._paginas) else {}
        self._i += 1
        return _Resp(cuerpo)


def _result(id_: str) -> dict[str, Any]:
    return {"resource": {"id": id_, "name": f"ds {id_}"}, "metadata": {"domain": "d"}}


def test_ingerir_socrata_pagina_con_scroll_id() -> None:
    from terranova.descubrimiento import ingerir

    http = _HTTPFalso(
        [
            {"results": [_result("a-aaaa"), _result("b-bbbb")]},  # página llena (por_pagina=2)
            {"results": [_result("c-cccc")]},  # página corta → última
        ]
    )
    ds = ingerir(http, por_pagina=2)
    assert [d.id_socrata for d in ds] == ["a-aaaa", "b-bbbb", "c-cccc"]
    assert http.params[0]["scroll_id"] == ""  # primera página: scroll_id vacío, sin `order`
    assert "order" not in http.params[0]  # `scroll_id` + `order` da 400 en la API real
    assert http.params[1]["scroll_id"] == "b-bbbb"  # la segunda pide los mayores al último


def test_ingerir_icde_pagina_y_deduplica() -> None:
    from terranova.descubrimiento import ingerir_dcat_us

    p1 = {"dataset": [_dcat(identifier="https://x/item.html?id=" + "a" * 32)]}
    p2 = {"dataset": [_dcat(identifier="https://x/item.html?id=" + "b" * 32)]}
    p3 = {"dataset": [_dcat(identifier="https://x/item.html?id=" + "b" * 32)]}  # repetido → corta
    http = _HTTPFalso([p1, p2, p3])
    ds = ingerir_dcat_us(http)
    assert sorted(d.id_socrata for d in ds) == ["a" * 32, "b" * 32]
    assert http.params[1] == {"page": 2}  # la segunda página pide ?page=2


# ---------------------------------------------------------- promoción data-driven (pieza 6)
def test_candidatos_a_promover_ordena_por_cobertura_medida() -> None:
    from terranova.descubrimiento import candidatos_a_promover

    agua = _reg("agua", titulo="cuerpos de agua", licencia="CC BY")
    bosque = _reg("bosque", titulo="cobertura de bosque", licencia="CC BY")
    raro = _reg("raro", titulo="dataset raro", licencia=None)

    def buscar_fn(pregunta: str) -> list[DatasetDescubrible]:
        if "agua" in pregunta:
            return [agua, raro]
        if "bosque" in pregunta:
            return [agua, bosque]  # agua aparece también aquí
        return [raro]

    preguntas = ["¿dónde hay agua?", "¿cobertura de bosque?", "algo raro"]
    cola = candidatos_a_promover(preguntas, buscar_fn, hoy=HOY)
    # agua y raro salen en 2 preguntas; a igual cobertura, la licencia desempata (agua > raro);
    # bosque sale en 1. → [agua, raro, bosque]
    assert cola[0].dataset.id_socrata == "agua" and cola[0].preguntas == 2
    assert cola[1].dataset.id_socrata == "raro" and cola[1].preguntas == 2
    assert cola[2].dataset.id_socrata == "bosque" and cola[2].preguntas == 1
