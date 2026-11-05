"""Pruebas doradas (F2.1): cada herramienta del catálogo contra la respuesta real grabada de
su conector (`scripts/grabar_doradas.py`). Sin red: si cambia el mapeo, el contrato o el catálogo,
falla aquí; si cambia la fuente, falla al regrabar (spec 04, §11.3)."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from terranova.canario import campos_presentes, comprobar
from terranova.catalogo import cargar
from terranova.contrato import Sobre, fuera_de_lista_blanca
from terranova.ejecutor import Ejecutor, licencia_de

DORADAS = Path(__file__).parent / "doradas"
CATALOGO = cargar()


class ConectorGrabado:
    """Responde lo grabado para esa misma llamada; una llamada distinta es un error de la prueba."""

    def __init__(self, nombre: str, llamadas: list[dict[str, Any]]) -> None:
        self.grabadas = [ll for ll in llamadas if ll["conector"] == nombre]

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        for ll in self.grabadas:
            if ll["tool"] == herramienta and ll["argumentos"] == argumentos:
                copia: dict[str, Any] = json.loads(json.dumps(ll["respuesta"]))
                return copia
        raise AssertionError(f"llamada no grabada: {herramienta} {argumentos}")


def _ejecutor(llamadas: list[dict[str, Any]]) -> Ejecutor:
    nombres = {ll["conector"] for ll in llamadas}
    return Ejecutor(CATALOGO, {n: ConectorGrabado(n, llamadas) for n in nombres})


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_cada_herramienta_tiene_su_dorada() -> None:
    assert {p.stem for p in DORADAS.glob("*.json")} == set(CATALOGO.herramientas)


@pytest.mark.anyio
@pytest.mark.parametrize("herramienta", sorted(CATALOGO.herramientas))
async def test_dorada(herramienta: str) -> None:
    h = CATALOGO.herramientas[herramienta]
    fuente = CATALOGO.fuentes[h.fuente]
    grabado = json.loads((DORADAS / f"{herramienta}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(
        herramienta, h.canario.entrada, plan="evaluacion"
    )

    Sobre.model_validate(sobre.model_dump(mode="json"))  # reglas 1-9, ida y vuelta por JSON
    assert comprobar(h, sobre) == [], "la verdad medida del canario no coincide"
    assert sorted(campos_presentes(sobre)) == h.canario.campos, "corre scripts/campos_canario.py"
    permitidos = fuente.nombres_rt | set(h.derivados) | {"elementos"}
    if (comp := h.consulta.complemento) is not None:  # sus hechos salen arriba, con su nombre
        cf = CATALOGO.fuentes[comp.fuente]
        for col, x in comp.hechos.items():
            permitidos.add(x.nombre)
            if col in cf.campos and cf.campos[col].codigos is not None:
                permitidos.add(x.nombre + "_significado")  # el código va con su significado
    assert fuera_de_lista_blanca(sobre, permitidos) == set(), "regla 10: campo fuera de la lista"
    for elemento in sobre.datos.get("elementos", []):
        assert set(elemento) <= permitidos
    assert {p.fuente_id for p in sobre.procedencia} >= {fuente.id}
    for p in sobre.procedencia:
        if p.fuente_id == fuente.id:
            assert p.licencia.spdx == licencia_de(fuente).spdx
            assert p.atribucion == fuente.atribucion
    assert sobre.creditos == h.creditos


def _filas_crudas(respuesta: dict[str, Any]) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for art in respuesta.get("artifacts") or []:
        filas += [r for r in art.get("rows") or [] if isinstance(r, dict)]
        filas += [f.get("properties") or {} for f in (art.get("data") or {}).get("features") or []]
    return filas


DE_SOCRATA = sorted(
    h for h, f in CATALOGO.herramientas.items() if CATALOGO.fuentes[f.fuente].protocolo == "socrata"
)


@pytest.mark.parametrize("herramienta", DE_SOCRATA)
def test_la_dorada_de_socrata_solo_guarda_la_lista_blanca(herramienta: str) -> None:
    """El repo es público: la respuesta grabada no puede traer columnas fuera de la lista blanca
    (cédulas, supervisores, contactos). Por eso las fichas de Socrata piden `select`."""
    h = CATALOGO.herramientas[herramienta]
    permitidas = set(CATALOGO.fuentes[h.fuente].campos) | {
        d.campo for d in h.derivados.values() if d.de == "columna" and d.campo
    }
    if h.consulta.previa:  # la consulta previa va a otra fuente, con su propia lista blanca
        permitidas |= set(CATALOGO.fuentes[h.consulta.previa.fuente].campos)
    if h.consulta.complemento:  # el complemento solo trae las columnas que declara
        permitidas |= set(h.consulta.complemento.hechos)
    grabado = json.loads((DORADAS / f"{herramienta}.json").read_text(encoding="utf-8"))
    filas = [fila for ll in grabado["llamadas"] for fila in _filas_crudas(ll["respuesta"])]
    vistas = {k for fila in filas for k in fila}
    assert vistas <= permitidas, f"columnas fuera de la lista blanca: {sorted(vistas - permitidas)}"


# (columna del tipo de documento, columna del número) en los conjuntos de SECOP (ADR-0025)
DOCUMENTOS_SECOP = [
    ("tipodocproveedor", "documento_proveedor"),
    ("tipo_identifi_del_contratista", "identificacion_del_contratista"),
    ("tipo_doc_proponente", "num_doc_proponente"),
]


# columnas de documento sin columna de tipo al lado: en una dorada, solo NIT de empresa
DOCUMENTOS_SIN_TIPO = ["documento_contratista"]
NIT_DE_EMPRESA = re.compile(r"^[89][0-9]{8,9}$")


def test_un_documento_sin_tipo_en_una_dorada_es_un_nit_de_empresa() -> None:
    """Las multas de SECOP I no dicen el tipo de documento: el canario se eligió con empresas, y una
    cédula (p. ej. 80123456, que también empieza por 8) rompe esta prueba."""
    for ruta in DORADAS.glob("*.json"):
        grabado = json.loads(ruta.read_text(encoding="utf-8"))
        for ll in grabado["llamadas"]:
            for fila in _filas_crudas(ll["respuesta"]):
                for columna in DOCUMENTOS_SIN_TIPO:
                    if valor := fila.get(columna):
                        assert NIT_DE_EMPRESA.match(str(valor)), f"{ruta.name}: {columna}"


def test_ninguna_dorada_guarda_una_cedula() -> None:
    """ADR-0025: SECOP muestra el documento del contratista, pero el repo es público: las doradas
    se graban con registros de personas jurídicas."""
    for ruta in DORADAS.glob("*.json"):
        grabado = json.loads(ruta.read_text(encoding="utf-8"))
        for ll in grabado["llamadas"]:
            for fila in _filas_crudas(ll["respuesta"]):
                for tipo, numero in DOCUMENTOS_SECOP:
                    es_cedula = "dula" in str(fila.get(tipo) or "")
                    assert not (es_cedula and fila.get(numero)), f"{ruta.name}: cédula grabada"


@pytest.mark.anyio
async def test_una_lista_que_llega_al_tope_lo_dice_en_el_sobre() -> None:
    """Con un tope de 200, Chapinero trajo una parte de 948 tratamientos y solo la procedencia lo
    decía (GEO Copilot, 2026-11-03). La ANCP graba 20 de más de 1 200 conceptos."""
    from terranova.contrato import paginar

    h = CATALOGO.herramientas["ancp_conceptos_buscar"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    total = sobre.datos["coincidencias"]
    assert total > 1000
    assert any(
        a.startswith(f"Vinieron 20 de {total}: la consulta trae como máximo 20")
        for a in sobre.avisos
    )
    pagina = paginar(
        sobre.model_copy(
            update={"datos": {**sobre.datos, "elementos": sobre.datos["elementos"] * 3}}
        ),
        1,
    )
    assert "cuentan los elementos que vinieron" in pagina.avisos[-1]


@pytest.mark.anyio
async def test_el_inicio_de_un_texto_largo_no_lleva_el_aviso_del_tope() -> None:
    h = CATALOGO.herramientas["corte_constitucional_texto_inicio"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    assert not any(a.startswith("Vinieron") for a in sobre.avisos)


@pytest.mark.anyio
async def test_la_infraestructura_energetica_sale_en_una_capa_con_su_tipo() -> None:
    """Cuatro capas de la UPME en una: cada elemento dice su tipo, lo que no aplica sale vacío (la
    tensión de una central) y arriba van el total y cuántos hay de cada tipo."""
    h = CATALOGO.herramientas["upme_infraestructura_energetica_en_zona"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    datos = sobre.model_dump(mode="json")["datos"]
    assert datos["total"] == 256
    assert set(datos["por_tipo"]) == {
        "subestación eléctrica",
        "línea de transmisión eléctrica",
        "central de generación eléctrica",
        "ducto de hidrocarburos",
    }
    centrales = [e for e in datos["elementos"] if e["tipo"].startswith("central")]
    assert centrales and all(e["tension_kv"] is None for e in centrales)
    assert datos["capacidad_mw_total"] == sum(e["capacidad_mw"] for e in centrales)


@pytest.mark.anyio
async def test_un_proyecto_sgr_por_bpin_no_dice_que_falte_algo() -> None:
    """Con `max_filas: 1`, el grupo único del BPIN llegaba al tope y cada proyecto decía «no se
    sabe si vino todo» (revisión de valor, 2026-11-04)."""
    h = CATALOGO.herramientas["dnp_proyecto_sgr_por_bpin"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    assert sobre.estado == "encontrado"
    assert not any("no se sabe si vino todo" in a for a in sobre.avisos)


def test_el_vacio_de_regalias_del_municipio_no_es_no_recibir() -> None:
    """Medellín sale vacío: su alcaldía no ejecuta proyectos del SGR (los ejecutan Ruta N y la
    Universidad de Medellín, medido el 2026-11-04), y eso no es «no recibe regalías»."""
    from terranova.contrato import Sobre
    from terranova.ejecutor import avisos_de_la_ficha

    h = CATALOGO.herramientas["dnp_proyectos_sgr_municipio"]
    vacio = Sobre.model_construct(estado="no_encontrado", datos={}, avisos=[])
    avisos = avisos_de_la_ficha(h, CATALOGO.fuentes[h.fuente], vacio)
    assert len(avisos) == 1 and "no quiere decir que no reciba" in avisos[0]


@pytest.mark.anyio
async def test_el_bpin_de_un_proceso_sale_resumido_arriba() -> None:
    """El CO1.REQ.11194762 trae 41 filas (una por contrato), todas del mismo BPIN (2026-11-04)."""
    h = CATALOGO.herramientas["secop_bpin_proceso"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    por_bpin = sobre.datos["contratos_por_bpin"]
    assert list(por_bpin) == ["2024080010085"] and por_bpin["2024080010085"] >= 41


@pytest.mark.anyio
async def test_un_cdp_con_dos_bpin_cuenta_un_cdp_y_avisa_no_sumar() -> None:
    """Revisión de valor: el CDP de Támesis sale en dos filas (una por BPIN) con el mismo saldo;
    sumarlas lo doblaba."""
    h = CATALOGO.herramientas["secop_cdp_contrato"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    datos = sobre.model_dump(mode="json")["datos"]
    assert (datos["numero_registros"], datos["cdps"]) == (2, 1)
    assert any("no se" in a and "suman" in a for a in sobre.avisos)


@pytest.mark.anyio
async def test_un_compromiso_de_secop2_dice_su_estado_y_que_es_su_tipo() -> None:
    """Revisión de valor: el compromiso salía con «tipo: 0» y sin su estado (Generado, Con
    Obligación…), que es lo que dice si el contrato está respaldado."""
    h = CATALOGO.herramientas["secop_compromisos_contrato"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    (fila,) = sobre.model_dump(mode="json")["datos"]["elementos"]
    assert (fila["tipo"], fila["tipo_significado"]) == ("0", "ingresos")
    assert fila["estado_compromiso"] == "Con Obligación"
    assert fila["balance_vigencias_futuras"] == 0.0


@pytest.mark.anyio
async def test_un_contrato_de_secop2_dice_cuanto_falta_por_pagar_y_de_que_bolsa_sale() -> None:
    """Revisión de valor: el predio de Chía salía con `valor_pagado: 0` y nada más. La fuente dice
    que nada se facturó, que falta pagarlo entero y que lo pone la alcaldía (2026-11-04)."""
    h = CATALOGO.herramientas["secop_contrato_por_id"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    datos = sobre.model_dump(mode="json")["datos"]
    assert datos["valor_pendiente_pago"] == datos["valor"] == 2602628368
    assert datos["recursos_propios_territoriales"] == datos["valor"]
    assert (datos["destino_gasto"], datos["dias_adicionados"]) == ("Inversión", 0)


@pytest.mark.anyio
async def test_buscar_en_una_entidad_trae_todo_sin_tope() -> None:
    """Revisión de valor: en todo el país, «mantenimiento de vías terciarias» da 1 308, se ven 50
    y el aviso pide acotar sin dar cómo. En Pitalito, «mantenimiento vías» da 31, todos
    (2026-11-04)."""
    h = CATALOGO.herramientas["secop_contratos_buscar_entidad"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    assert sobre.datos["coincidencias"] == 31
    assert {e["nit_entidad"] for e in sobre.datos["elementos"]} == {"891180077"}
    assert not any(a.startswith("Vinieron") for a in sobre.avisos)


@pytest.mark.anyio
async def test_el_cronograma_trae_las_fechas_que_la_fuente_si_llena() -> None:
    """Revisión de valor: el concurso de méritos del canario salía con una fecha; la fuente trae
    también presentación de ofertas y la entrega y aprobación de garantías, en columnas de otra
    plantilla (2026-11-04)."""
    h = CATALOGO.herramientas["secop_cronograma_proceso"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    primera = sobre.model_dump(mode="json")["datos"]["elementos"][0]
    assert primera["fecha_entrega_garantia_b"] == "2022-05-09"
    assert primera["fecha_aprobacion_garantias_b"] == "2022-05-10"


@pytest.mark.anyio
async def test_transmilenio_dice_tipo_y_etapa_de_cada_estacion() -> None:
    """Estaciones troncales y trazados en una capa. Los códigos de tipo y etapa salen con su
    significado (diccionario del ítem). Calle 45 y Calle 63 estaban cerradas por obras en la
    medición del 2026-11-04."""
    h = CATALOGO.herramientas["transmilenio_troncal_en_zona"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    datos = sobre.model_dump(mode="json")["datos"]
    assert datos["total"] == 40
    assert datos["por_tipo"] == {"estación troncal": 32, "trazado troncal": 8}
    por_nombre = {e["nombre"]: e for e in datos["elementos"]}
    assert por_nombre["Calle 63"]["etapa_operacion_significado"] == "cierre temporal por obras"
    assert por_nombre["CAN"]["tipo_estacion_significado"] == "sencilla"
    assert por_nombre["Suba"]["letra_troncal"] == "C"


@pytest.mark.anyio
async def test_transmilenio_rutas_y_paraderos_con_horario_y_localidad() -> None:
    """Rutas del SITP por zona y por código, y paraderos zonales. Conteos medidos en el servicio de
    TransMilenio el 2026-11-04: 95 servicios y 87 paraderos en el rectángulo del canario; la línea
    GA503 tiene dos sentidos."""

    async def correr(herramienta: str) -> dict[str, object]:
        h = CATALOGO.herramientas[herramienta]
        grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
        sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
        return dict(sobre.model_dump(mode="json")["datos"])

    rutas = await correr("transmilenio_rutas_en_zona")
    assert rutas["total"] == 95
    ruta = await correr("transmilenio_ruta_buscar")
    sentidos = {e["codigo_ruta"]: e for e in ruta["elementos"]}  # type: ignore[attr-defined]
    assert set(sentidos) == {"A503-1", "G503-2"}
    assert sentidos["A503-1"]["origen"] == "San Bernardino"
    assert sentidos["A503-1"]["localidad_origen_significado"] == "Bosa"
    assert sentidos["A503-1"]["horario_habil"].startswith("3:00")
    paraderos = await correr("transmilenio_paraderos_en_zona")
    assert paraderos["total"] == 87
    assert paraderos["por_localidad"] == {"Chapinero": 76, "Barrios Unidos": 11}


@pytest.mark.anyio
async def test_ani_puertos_aeropuertos_y_red_ferrea_con_su_ubicacion() -> None:
    """Capas 0, 1 y 2 de ModosANI, medidas el 2026-11-05: 23 puertos en la bahía de Cartagena,
    El Dorado en Bogotá y la Red férrea del Atlántico por Santa Marta."""

    async def correr(herramienta: str) -> dict[str, object]:
        h = CATALOGO.herramientas[herramienta]
        grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
        sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
        return dict(sobre.model_dump(mode="json")["datos"])

    puertos = await correr("ani_puertos_en_zona")
    assert puertos["numero_registros"] == 23
    dexton = next(e for e in puertos["elementos"] if "DEXTON" in e["sociedad_portuaria"])  # type: ignore[attr-defined]
    assert dexton["fecha_fin_concesion"] == "2031-09-29"
    aeropuertos = await correr("ani_aeropuertos_en_zona")
    assert [e["aeropuerto"] for e in aeropuertos["elementos"]] == ["El Dorado (Bogotá)"]  # type: ignore[attr-defined]
    ferreo = await correr("ani_red_ferrea_en_zona")
    assert [e["corredor"] for e in ferreo["elementos"]] == ["Red férrea del Atlántico"]  # type: ignore[attr-defined]


@pytest.mark.anyio
async def test_sedes_educativas_del_dane_con_punto_zona_y_sector() -> None:
    """SISE del DANE: 6 sedes en el rectángulo del canario (centro de Bogotá) y 7 en Cubarral
    (50223), medidas en el servicio y en la copia el 2026-11-05; «Divino Niño Cubarral» da la sede
    250223000114."""

    async def correr(herramienta: str) -> dict[str, object]:
        h = CATALOGO.herramientas[herramienta]
        grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
        sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
        return dict(sobre.model_dump(mode="json")["datos"])

    zona = await correr("dane_sedes_educativas_en_zona")
    assert zona["total"] == 6
    municipio = await correr("dane_sedes_educativas_municipio")
    assert municipio["total"] == 7
    assert sum(municipio["por_sector"].values()) == 7  # type: ignore[attr-defined]
    sede = await correr("dane_sedes_educativas_buscar")
    assert [e["codigo_dane"] for e in sede["elementos"]] == ["250223000114"]  # type: ignore[attr-defined]


@pytest.mark.anyio
async def test_sedes_de_salud_del_sispro_con_punto_naturaleza_y_ese() -> None:
    """Capa 2 del visor de Protección Social del SISPRO, medida en la copia el 2026-11-05: 183
    sedes en el rectángulo del canario (centro de Bogotá), 2 en Cubarral (50223, una de ellas la ESE
    del hospital local) y 68 con «Hospital San Vicente»."""

    async def correr(herramienta: str) -> dict[str, object]:
        h = CATALOGO.herramientas[herramienta]
        grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
        sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
        return dict(sobre.model_dump(mode="json")["datos"])

    zona = await correr("minsalud_sedes_salud_en_zona")
    assert zona["total"] == 183
    municipio = await correr("minsalud_sedes_salud_municipio")
    assert municipio["total"] == 2 and municipio["por_ese"] == {"sí": 1, "sin dato": 1}
    ese = next(e for e in municipio["elementos"] if e["es_ese"] == "1")  # type: ignore[attr-defined]
    assert ese["prestador"] == "EMPRESA SOCIAL DEL ESTADO HOSPITAL LOCAL DE CUBARRAL"
    assert ese["naturaleza_juridica_significado"] == "pública"
    buscar = await correr("minsalud_sedes_salud_buscar")
    assert buscar["total"] == 68
    assert all(e["tipo_persona"] != "1" for e in buscar["elementos"])  # type: ignore[attr-defined]


@pytest.mark.anyio
async def test_infraestructura_igac_100k_por_tipo() -> None:
    """Cartografía 1:100 000 del IGAC: 4 embalses en el oriente antioqueño (El Peñol en dos
    polígonos), medidos en la copia el 2026-11-05."""
    h = CATALOGO.herramientas["igac_infraestructura_en_zona"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    datos = sobre.model_dump(mode="json")["datos"]
    assert datos["total"] == 4 and datos["por_tipo"] == {"embalse": 4}
    assert "Embalse El Peñol (Guatape)" in {e["nombre"] for e in datos["elementos"]}


@pytest.mark.anyio
async def test_firms_da_los_focos_del_producto_estandar_con_su_significado() -> None:
    """NASA FIRMS por periodo (API por área con MAP_KEY): 182 focos de VIIRS S-NPP en la Orinoquía
    el 2024-02-01, del producto estándar, que no cambia (medido el 2026-11-05)."""
    h = CATALOGO.herramientas["nasa_firms_focos_en_zona"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    datos = sobre.model_dump(mode="json")["datos"]
    assert datos["total"] == 182 and datos["por_fecha"] == {"2024-02-01": 182}
    assert {e["producto"] for e in datos["elementos"]} == {"VIIRS_SNPP_SP"}
    assert {e["confianza_significado"] for e in datos["elementos"]} <= {"baja", "nominal", "alta"}


@pytest.mark.anyio
async def test_captaciones_del_ideam_con_el_punto_de_grados_minutos_y_segundos() -> None:
    """SIRH del IDEAM (4q6d-6s7b), medido en la copia el 2026-11-05: 12 captaciones de la CAR en
    el rectángulo de Chía, 2 de CORMACARENA en Cubarral (50223) y 1 en el caño Arenas Blancas.
    El punto sale de grados, minutos y segundos (4°52'58" N, 74°0'40" O)."""

    async def correr(herramienta: str) -> dict[str, object]:
        h = CATALOGO.herramientas[herramienta]
        grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
        sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
        return dict(sobre.model_dump(mode="json")["datos"])

    zona = await correr("ideam_captaciones_en_zona")
    assert zona["total"] == 12 and zona["por_autoridad"] == {"CAR": 12}
    municipio = await correr("ideam_captaciones_municipio")
    assert municipio["total"] == 2 and municipio["por_autoridad"] == {"CORMACARENA": 2}
    arenas = await correr("ideam_captaciones_buscar")
    assert [e["fuente_hidrica"] for e in arenas["elementos"]] == ["ARENAS BLANCAS"]  # type: ignore[attr-defined]


@pytest.mark.anyio
async def test_emergencias_de_bogota_por_tipo() -> None:
    """Bomberos, policía, CAI y red pública de salud de Bogotá, medidos en la copia el 2026-11-05:
    16 sedes en el centro (10 CAI, 3 estaciones de policía, 2 de salud y la de bomberos Central).
    El nombre de la policía sale de EPODESCRIP, sin la «í» rota de EPONOMBRE."""
    h = CATALOGO.herramientas["bogota_emergencias_en_zona"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    datos = sobre.model_dump(mode="json")["datos"]
    assert datos["total"] == 16
    assert datos["por_tipo"] == {
        "CAI": 10,
        "estación de policía": 3,
        "sede de la red pública de salud": 2,
        "estación de bomberos": 1,
    }
    nombres = {e["nombre"] for e in datos["elementos"]}
    assert "Estación de Policía Teusaquillo" in nombres
    assert "Estación de Bomberos Central - Carlos Julio Rico Cuellar" in nombres


def test_ninguna_dorada_guarda_un_correo() -> None:
    """Un correo es un dato personal y las doradas se versionan: grabar_doradas los enmascara."""
    correo = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
    for archivo in sorted(DORADAS.glob("*.json")):
        hallados = set(correo.findall(archivo.read_text(encoding="utf-8")))
        assert hallados <= {"correo@enmascarado.invalid"}, f"{archivo.name}: {sorted(hallados)}"


@pytest.mark.anyio
async def test_siniestralidad_critica_de_bogota_por_actor_vial() -> None:
    """Sitios críticos 2022-2025 de la SDM, medidos el 2026-11-05 en la descarga de sus veinte
    capas: en Kennedy y Puente Aranda hay 49. Las sumas por actor vial son solo de los puntos."""
    h = CATALOGO.herramientas["sdm_siniestralidad_critica_en_zona"]
    grabado = json.loads((DORADAS / f"{h.id}.json").read_text(encoding="utf-8"))
    sobre = await _ejecutor(grabado["llamadas"]).ejecutar(h.id, h.canario.entrada)
    datos = sobre.model_dump(mode="json")["datos"]
    assert datos["total"] == 49
    assert datos["sitios_por_actor_vial"] == {
        "vulnerables": 17,
        "motociclistas": 14,
        "peatones": 10,
        "ciclistas": 8,
    }
    assert datos["fallecidos_en_puntos_por_actor_vial"] == {
        "peatones": 6,
        "vulnerables": 2,
        "motociclistas": 0,
    }
    assert datos["lesionados_en_puntos_por_actor_vial"] == {
        "vulnerables": 93,
        "peatones": 54,
        "motociclistas": 45,
    }
    assert {e["elemento"] for e in datos["elementos"]} == {"punto", "tramo", "zona"}
