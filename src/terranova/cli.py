"""`terranova`: sin argumentos levanta la puerta; `terranova llaves …` administra llaves (F3.2).

    terranova llaves crear --org geoai --scopes territorio,ambiente [--prueba] [--expira 2027-01-01]
    terranova llaves revocar llv_…
    terranova llaves listar [--org geoai]
    terranova orgs nivel geoai ampliado      (saldo mensual: con_llave 20 000, ampliado 200 000)
    terranova canarios [--cada-horas 24]     (F7.1: canarios en vivo, guardados en TERRANOVA_BD)
    terranova copias actualizar [fuente …] [--cada-horas 24]   (G3: copias en TERRANOVA_COPIAS_URL)
    terranova catalogo-dcat ingerir [--limite-paginas N] [--salida f.jsonl]   (G6: catálogo DCAT)

La llave se imprime UNA vez; después solo existe su HMAC (ADR-0009).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from terranova.identidad import registro_desde_entorno


def llaves(argumentos: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="terranova llaves")
    sub = parser.add_subparsers(dest="accion", required=True)
    crear = sub.add_parser("crear")
    crear.add_argument("--org", required=True)
    crear.add_argument("--scopes", required=True, help="familias separadas por coma, o *")
    crear.add_argument("--prueba", action="store_true", help="rt_test_: plan evaluación")
    crear.add_argument("--expira", type=date.fromisoformat)
    revocar = sub.add_parser("revocar")
    revocar.add_argument("llave_id")
    listar = sub.add_parser("listar")
    listar.add_argument("--org")
    a = parser.parse_args(argumentos)

    registro = registro_desde_entorno()
    if a.accion == "crear":
        scopes = {s.strip() for s in a.scopes.split(",") if s.strip()}
        llave = registro.crear(a.org, scopes, prueba=a.prueba, expira=a.expira)
        print(llave)
        print("Guárdala ahora: no se vuelve a mostrar.", file=sys.stderr)
        return 0
    if a.accion == "revocar":
        if registro.revocar(a.llave_id):
            print(f"revocada {a.llave_id}")
            return 0
        print(f"no hay una llave vigente {a.llave_id}", file=sys.stderr)
        return 1
    for ll in registro.listar(a.org):
        estado = "revocada" if ll.revocada else "vigente"
        print(
            f"{ll.llave_id}  {ll.org}  {ll.plan}  {','.join(sorted(ll.scopes))}  {estado}  "
            f"creada {ll.creada}  último uso {ll.ultimo_uso or '-'}"
        )
    return 0


def canarios(argumentos: list[str]) -> int:
    """Una corrida (o una cada N horas) de todos los canarios; sale 1 si alguno quedó rojo."""
    import asyncio
    import os
    import time

    from terranova.catalogo import cargar
    from terranova.conector import ConectorMCP, conectores_desde_entorno
    from terranova.ejecutor import Ejecutor
    from terranova.vigilancia import RegistroCanarios, alertar, correr

    parser = argparse.ArgumentParser(prog="terranova canarios")
    parser.add_argument("--cada-horas", type=float, help="repetir (servicio del compose)")
    a = parser.parse_args(argumentos)
    registro = RegistroCanarios(os.environ.get("TERRANOVA_BD", "datos_locales/terranova.db"))

    async def una_vez() -> bool:
        catalogo = cargar()
        conectores = conectores_desde_entorno(catalogo)
        try:
            for c in conectores.values():
                if isinstance(c, ConectorMCP):
                    try:
                        await c.abrir()
                    except Exception:  # noqa: BLE001 (su canario lo dirá: fuente_no_disponible)
                        pass
            resultados = await correr(catalogo, Ejecutor(catalogo, conectores))
        finally:
            for c in conectores.values():
                if isinstance(c, ConectorMCP):
                    await c.cerrar()
        for r in resultados:
            registro.registrar(r)
            marca = "verde" if r.ok else "ROJO "
            print(f"{marca} {r.herramienta:42} {r.latencia_ms:>6} ms  {r.codigo}  {r.detalle[:80]}")
        alertar(resultados, os.environ.get("TERRANOVA_ALERTA_URL"))
        return all(r.ok for r in resultados)

    while True:
        verde = asyncio.run(una_vez())
        if not a.cada_horas:
            return 0 if verde else 1
        time.sleep(a.cada_horas * 3600)


def copias(argumentos: list[str]) -> int:
    """Construye una versión nueva de cada copia (ADR-0024); sale 1 si alguna falló."""
    import os
    import time
    from datetime import date

    from terranova.catalogo import cargar
    from terranova.copias import AlmacenCopias, descargar_socrata

    parser = argparse.ArgumentParser(prog="terranova copias actualizar")
    parser.add_argument("fuentes", nargs="*", help="ids de fuente (por defecto, todas las copias)")
    parser.add_argument("--cada-horas", type=float, help="repetir (servicio del compose)")
    a = parser.parse_args(argumentos)
    url = os.environ.get("TERRANOVA_COPIAS_URL") or os.environ.get("TERRANOVA_CURADO_URL")
    if not url:
        print("falta TERRANOVA_COPIAS_URL (postgresql://…)", file=sys.stderr)
        return 2
    # en el equipo de desarrollo se acota la ventana (memoria); en la VM va la de la ficha
    desde_local = os.environ.get("TERRANOVA_COPIA_DESDE")

    def una_vez() -> bool:
        catalogo = cargar()
        elegidas = [
            f for f in catalogo.fuentes.values() if f.copia and (not a.fuentes or f.id in a.fuentes)
        ]
        almacen = AlmacenCopias(url)
        bien = True
        for fuente in elegidas:
            assert fuente.copia is not None
            ventana = fuente.copia.ventana.desde if fuente.copia.ventana else None
            desde = (
                max(ventana, date.fromisoformat(desde_local))
                if ventana and desde_local
                else ventana
            )
            inicio = time.monotonic()
            try:
                v = almacen.construir(fuente, descargar_socrata(fuente, desde), desde)
                almacen.podar(fuente.copia.tabla)
                segundos = time.monotonic() - inicio
                print(
                    f"ok    {fuente.id}: {v.filas} filas desde {desde}, "
                    f"{v.repetidas} repetidas en la fuente ({segundos:.0f} s)"
                )
            except Exception as exc:  # noqa: BLE001 — una copia rota no detiene las demás
                bien = False
                print(f"FALLO {fuente.id}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return bien

    while True:
        bien = una_vez()
        if not a.cada_horas:
            return 0 if bien else 1
        time.sleep(a.cada_horas * 3600)


def catalogo_dcat(argumentos: list[str]) -> int:
    """Ingiere el catálogo DCAT de datos.gov.co (G6, ADR-0026) a JSONL y muestra sus métricas."""
    import pathlib

    from terranova.descubrimiento import a_jsonl, ingerir, metricas

    parser = argparse.ArgumentParser(prog="terranova catalogo-dcat ingerir")
    parser.add_argument("--limite-paginas", type=int, help="acota la cosecha (desarrollo)")
    parser.add_argument("--por-pagina", type=int, default=1000)
    parser.add_argument("--salida", default="datos_locales/catalogo_dcat.jsonl")
    a = parser.parse_args(argumentos)

    datasets = ingerir(limite_paginas=a.limite_paginas, por_pagina=a.por_pagina)
    salida = pathlib.Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(a_jsonl(datasets) + "\n", encoding="utf-8")
    m = metricas(datasets)

    def pct(x: int) -> str:
        return f"{100 * x // m.total}%" if m.total else "-"

    print(f"catálogo: {m.total} datasets → {a.salida}")
    print(f"  con licencia declarada: {m.con_licencia} ({pct(m.con_licencia)})")
    print(f"  vivos (< 12 meses):     {m.vivos} ({pct(m.vivos)})")
    print(f"  entidades distintas:    {m.entidades}")
    print("  top entidades:")
    for ent, n in m.top_entidades:
        print(f"    {n:>5}  {ent[:70]}")
    return 0


def main() -> None:
    argumentos = sys.argv[1:]
    if argumentos[:2] == ["copias", "actualizar"]:
        sys.exit(copias(argumentos[2:]))
    if argumentos[:2] == ["catalogo-dcat", "ingerir"]:
        sys.exit(catalogo_dcat(argumentos[2:]))
    if argumentos[:1] == ["canarios"]:
        sys.exit(canarios(argumentos[1:]))
    if argumentos[:1] == ["llaves"]:
        sys.exit(llaves(argumentos[1:]))
    if argumentos[:2] == ["orgs", "nivel"] and len(argumentos) == 4:
        registro_desde_entorno().fijar_nivel(argumentos[2], argumentos[3])
        print(f"{argumentos[2]}: nivel {argumentos[3]}")
        sys.exit(0)
    if argumentos and not argumentos[0].startswith("-"):
        # antes, un subcomando mal escrito (`terranova orgs --help`) levantaba el servidor
        print(f"subcomando desconocido: {' '.join(argumentos)}", file=sys.stderr)
        print(__doc__ or "", file=sys.stderr)
        sys.exit(2)
    from terranova.app import main as servir

    servir()
