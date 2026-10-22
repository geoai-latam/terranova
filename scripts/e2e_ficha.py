"""E2E-07 y E2E-08 (spec 04, §11.5) y la medición de F4.3, con los conectores en vivo.

E2E-07: la ficha del predio de Chía tiene todas sus partes, cada una con procedencia, y coincide
con las verdades: el predio (canario medido en el IGAC) y las restricciones, medidas aparte sobre
el GeoParquet curado de F4.1 (RUNAP y ANT descargados en bloque, no por la puerta).
E2E-08: con un conector apuntando a un puerto muerto, la ficha sale `parcial`, con el error de
esas partes y las demás completas.
F4.3: p95 de la ficha en vivo (< 15 s) y con caché (< 2 s). Pocas corridas, en serie: no es carga.

Uso: `TERRANOVA_CONECTOR_LLAVE=… uv run --extra datasets scripts/e2e_ficha.py [--corridas 5]`
"""

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import date
from pathlib import Path

from terranova import ficha as f
from terranova.cache import AlmacenMemoria
from terranova.catalogo import cargar
from terranova.conector import (
    CONECTORES_POR_DEFECTO,
    Conector,
    ConectorMCP,
    conectores_desde_entorno,
)
from terranova.contrato import Sobre
from terranova.curado import restricciones_desde_entorno
from terranova.ejecutor import Ejecutor

CHIA = {"lon": -74.0262, "lat": 4.8619}
# con TERRANOVA_CURADO_URL, las restricciones salen del dataset curado (PostGIS)
BASE_CURADA = restricciones_desde_entorno()
CODIGO = "251750000000000050067000000000"
CURADO = Path(__file__).resolve().parents[1] / "datos_locales" / "datasets"
PARTE_DE_TIPO = {
    "area_protegida": "areas_protegidas",
    "resguardo_indigena": "resguardos",
    "zona_reserva_campesina": "reservas_campesinas",
}


def _ok(condicion: bool, texto: str, fallas: list[str]) -> None:
    print(("  ✓ " if condicion else "  ✗ ") + texto)
    if not condicion:
        fallas.append(texto)


def restricciones_medidas(lon: float, lat: float) -> dict[str, set[str]]:
    """Nombres de cada tipo de restricción que contienen el punto, según el dataset curado."""
    import geopandas as gpd
    from shapely.geometry import Point

    (archivo,) = sorted(CURADO.glob("restricciones_*.parquet"))[-1:]
    g = gpd.read_parquet(archivo)
    dentro = g[g.geometry.contains(Point(lon, lat))]
    return {
        parte: set(dentro[dentro["tipo"] == tipo]["nombre"])
        for tipo, parte in PARTE_DE_TIPO.items()
    }


async def _abiertos(conectores: dict[str, Conector]) -> dict[str, Conector]:
    for c in conectores.values():
        if isinstance(c, ConectorMCP):
            try:
                await c.abrir()
            except Exception as exc:  # noqa: BLE001 (el conector caído es parte de la prueba)
                print(f"  (conector sin sesión al abrir: {exc.__class__.__name__})")
    return conectores


async def _cerrar(conectores: dict[str, Conector]) -> None:
    for c in conectores.values():
        if isinstance(c, ConectorMCP):
            await c.cerrar()


async def e2e_07(ej: Ejecutor, fallas: list[str]) -> Sobre:
    print("E2E-07 · ficha del predio de Chía")
    t = time.monotonic()
    s = await f.ficha(ej, CHIA, plan="normal", hoy=date.today(), curado=BASE_CURADA)
    print(f"  ({time.monotonic() - t:.1f} s, {s.creditos} créditos, estado {s.estado})")
    Sobre.model_validate(s.model_dump(mode="json"))
    esperadas = {p.nombre for p in (f.PREDIO_EN_PUNTO, *f.PARTES_PUNTO, *f.PARTES_PREDIO)}
    # plan normal: población (DANE, licencia por verificar) no se consulta y lo dice
    esperadas.discard("poblacion_municipio")
    if BASE_CURADA is not None:
        esperadas = (esperadas - set(f.PARTES_RESTRICCIONES.values())) | {"restricciones"}
    _ok(
        s.estado == "encontrado",
        f"encontrado, sin errores ({[e.codigo for e in s.errores]})",
        fallas,
    )
    _ok(
        set(s.datos) == esperadas,
        f"todas las partes ({sorted(esperadas - set(s.datos))} faltan)",
        fallas,
    )
    _ok(
        any("poblacion_municipio" in a and "licencia" in a for a in s.avisos),
        "DANE omitido con aviso",
        fallas,
    )
    fuentes = {p.fuente_id for p in s.procedencia}
    todas = (f.PREDIO_EN_PUNTO, *f.PARTES_PUNTO, *f.PARTES_PREDIO)
    por_parte = {ej.catalogo.herramientas[p.herramienta].fuente for p in todas}
    por_parte.discard("dane.cnpv2018.municipio")
    _ok(
        por_parte <= fuentes,
        f"cada parte con procedencia ({sorted(por_parte - fuentes)} faltan)",
        fallas,
    )
    predio = s.datos.get("predio", {})
    _ok(predio.get("codigo_predial") == CODIGO, f"predio = {CODIGO} (canario IGAC)", fallas)
    _ok(
        predio.get("municipio_divipola") == "25175" and predio.get("zona") == "rural",
        "Chía, rural",
        fallas,
    )
    medidas = restricciones_medidas(CHIA["lon"], CHIA["lat"])
    for parte, nombres in medidas.items():
        if "restricciones" in s.datos:  # desde el curado: una lista por tipo
            obtenido = {x["nombre"] for x in s.datos["restricciones"].get(parte, [])}
        else:
            d = s.datos.get(parte, {})
            encontrado = d.get("estado") == "encontrado" and d.get("nombre")
            obtenido = {d["nombre"]} if encontrado else set()
        _ok(
            obtenido == nombres,
            f"{parte}: {sorted(obtenido) or 'ninguna'} = curado {sorted(nombres) or 'ninguna'}",
            fallas,
        )
    # medidas aparte en la fuente el 2026-10-22: USGS `count` M≥3 en ±0,5° el último año = 0; UPRA
    # (datos.gov.co rttb-pk7n) no tiene filas de Chía (25175)
    sismos = s.datos.get("sismos_cercanos", {})
    _ok(sismos.get("total_en_catalogo") == 0, "sismos M≥3 cerca de Chía = 0 (USGS count)", fallas)
    precio = s.datos.get("precio_tierra", {}).get("estado")
    _ok(precio == "no_encontrado", f"UPRA sin Chía: no_encontrado ({precio})", fallas)
    for parte in ("construcciones", "vereda", "cobertura_suelo", "vocacion_uso"):
        print(f"    {parte}: {json.dumps(s.datos.get(parte), ensure_ascii=False)[:160]}")
    return s


async def e2e_08(almacen: AlmacenMemoria, fallas: list[str]) -> None:
    print("E2E-08 · ficha con una parte caída (amenazas-mcp en un puerto muerto)")
    urls = {**CONECTORES_POR_DEFECTO, "amenazas-mcp": "http://127.0.0.1:9/mcp"}
    os.environ["TERRANOVA_CONECTORES"] = json.dumps(urls)
    try:
        conectores = await _abiertos(conectores_desde_entorno())
    finally:
        del os.environ["TERRANOVA_CONECTORES"]
    try:
        # con la caché del calentamiento: lo que no es la parte caída sale completo aunque la
        # agrología del IGAC esté fría; sin la copia de sismos, que es la parte que se prueba
        sin_sismos = AlmacenMemoria()
        sin_sismos._datos = {
            k: v
            for k, v in almacen._datos.items()
            if "usgs_sismos_en_zona@" not in json.dumps(v[1])
        }
        ej = Ejecutor(cargar(), conectores, sin_sismos)
        s = await f.ficha(ej, CHIA, plan="normal", hoy=date.today(), curado=BASE_CURADA)
    finally:
        await _cerrar(conectores)
    Sobre.model_validate(s.model_dump(mode="json"))
    _ok(s.estado == "parcial", f"parcial ({s.estado})", fallas)
    _ok(
        [(e.codigo, e.fuente_id) for e in s.errores] == [("fuente_no_disponible", "usgs.sismos")],
        f"solo el error de sismos ({[(e.codigo, e.fuente_id) for e in s.errores]})",
        fallas,
    )
    _ok(
        "sismos_cercanos" not in s.datos
        and s.datos.get("predio", {}).get("codigo_predial") == CODIGO,
        "las demás partes completas",
        fallas,
    )
    _ok(
        "usgs.sismos" in {p.fuente_id for p in s.procedencia},
        "la fuente caída está en procedencia (regla 3)",
        fallas,
    )


def p95(xs: list[float]) -> float:
    return statistics.quantiles(xs, n=20, method="inclusive")[-1] if len(xs) > 1 else xs[0]


async def f4_3(almacen: AlmacenMemoria, corridas: int, fallas: list[str]) -> None:
    print(f"F4.3 · {corridas} fichas en serie, sin caché y con caché")
    conectores = await _abiertos(conectores_desde_entorno())
    try:
        sin, con = [], []
        catalogo = cargar()
        for _ in range(corridas):
            t = time.monotonic()
            await f.ficha(Ejecutor(catalogo, conectores), CHIA, plan="normal", curado=BASE_CURADA)
            sin.append(time.monotonic() - t)
            t = time.monotonic()
            s = await f.ficha(
                Ejecutor(catalogo, conectores, almacen), CHIA, plan="normal", curado=BASE_CURADA
            )
            con.append(time.monotonic() - t)
        desde = {p.servido_desde for p in s.procedencia}
    finally:
        await _cerrar(conectores)
    print(f"  en vivo: {[round(x, 1) for x in sin]} s · con caché: {[round(x, 2) for x in con]} s")
    _ok(p95(sin) < 15, f"p95 en vivo {p95(sin):.1f} s < 15 s", fallas)
    _ok(
        p95(con) < 2,
        f"p95 con caché {p95(con):.2f} s < 2 s (servido_desde {sorted(desde)})",
        fallas,
    )


async def calentar(almacen: AlmacenMemoria) -> None:
    """Una ficha que llena la caché, esperando a las partes que siguen en segundo plano (la
    agrología del IGAC tiene arranque en frío de ~45 s)."""
    print("calentamiento")
    conectores = await _abiertos(conectores_desde_entorno())
    try:
        t = time.monotonic()
        s = await f.ficha(
            Ejecutor(cargar(), conectores, almacen), CHIA, plan="normal", curado=BASE_CURADA
        )
        lentas = [e.fuente_id for e in s.errores]
        await asyncio.gather(*list(f._EN_SEGUNDO_PLANO), return_exceptions=True)
        print(f"  ({time.monotonic() - t:.1f} s; lentas al tope: {lentas or 'ninguna'})")
    finally:
        await _cerrar(conectores)


async def main(corridas: int) -> int:
    fallas: list[str] = []
    almacen = AlmacenMemoria()
    await calentar(almacen)
    conectores = await _abiertos(conectores_desde_entorno())
    try:
        await e2e_07(Ejecutor(cargar(), conectores), fallas)  # en vivo, sin caché
    finally:
        await _cerrar(conectores)
    await e2e_08(almacen, fallas)
    if corridas:
        await f4_3(almacen, corridas, fallas)
    print("\nverde" if not fallas else f"\n{len(fallas)} fallas")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    parser = argparse.ArgumentParser()
    parser.add_argument("--corridas", type=int, default=5)
    sys.exit(asyncio.run(main(parser.parse_args().corridas)))
