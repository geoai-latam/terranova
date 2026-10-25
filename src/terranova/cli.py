"""`terranova`: sin argumentos levanta la puerta; `terranova llaves …` administra llaves (F3.2).

    terranova llaves crear --org geoai --scopes territorio,ambiente [--prueba] [--expira 2027-01-01]
    terranova llaves revocar llv_…
    terranova llaves listar [--org geoai]
    terranova orgs nivel geoai ampliado      (saldo mensual: con_llave 20 000, ampliado 200 000)
    terranova canarios [--cada-horas 24]     (F7.1: canarios en vivo, guardados en TERRANOVA_BD)
    terranova copias actualizar [fuente …] [--cada-horas 24]   (G3: copias en TERRANOVA_COPIAS_URL)
    terranova catalogo-dcat ingerir [--fuente socrata|icde] [--limite-paginas N]   (G6: cosechar)
    terranova catalogo-dcat buscar "<consulta>" [--entidad E] [--limite N]         (G6: buscador)

Cliente del REST /v1 (ADR-0027; TERRANOVA_PUERTA y TERRANOVA_LLAVE):
    terranova consultar <herramienta> --<arg> <valor> [--json]
    terranova herramientas [--familia F] · terranova fuentes · terranova uso

La llave se imprime UNA vez; después solo existe su HMAC (ADR-0009).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from typing import TYPE_CHECKING

from terranova.identidad import registro_desde_entorno

if TYPE_CHECKING:
    import pathlib

    from terranova.descubrimiento import DatasetDescubrible


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
    """G6 (ADR-0026, spec 09): `ingerir` cosecha el catálogo DCAT; `buscar` busca en él."""
    if argumentos[:1] == ["ingerir"]:
        return _catalogo_ingerir(argumentos[1:])
    if argumentos[:1] == ["buscar"]:
        return _catalogo_buscar(argumentos[1:])
    print("uso: terranova catalogo-dcat ingerir|buscar …", file=sys.stderr)
    return 2


def _catalogo_ingerir(argumentos: list[str]) -> int:
    """Cosecha un catálogo DCAT a JSONL y muestra sus métricas. `--fuente socrata` (datos.gov.co,
    tablas) o `--fuente icde` (Hub de la ICDE, capas ArcGIS)."""
    import collections
    import pathlib

    from terranova.descubrimiento import a_jsonl, ingerir, ingerir_dcat_us, metricas

    parser = argparse.ArgumentParser(prog="terranova catalogo-dcat ingerir")
    parser.add_argument("--fuente", choices=["socrata", "icde"], default="socrata")
    parser.add_argument("--limite-paginas", type=int, help="acota la cosecha (solo socrata)")
    parser.add_argument("--por-pagina", type=int, default=1000)
    parser.add_argument("--salida", help="por defecto, datos_locales/catalogo_<fuente>.jsonl")
    parser.add_argument(
        "--embeddings",
        action="store_true",
        help="re-embebe todo el catálogo (ADR-0028) y deja el índice de vectores al lado",
    )
    a = parser.parse_args(argumentos)

    if a.fuente == "icde":
        datasets = ingerir_dcat_us()
    else:
        datasets = ingerir(limite_paginas=a.limite_paginas, por_pagina=a.por_pagina)
    ruta = a.salida or f"datos_locales/catalogo_{a.fuente}.jsonl"
    salida = pathlib.Path(ruta)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(a_jsonl(datasets) + "\n", encoding="utf-8")
    if a.embeddings:
        try:
            from terranova.descubrimiento import (
                FastEmbedder,
                embeber_catalogo,
                vectores_a_jsonl,
            )

            vectores = embeber_catalogo(datasets, FastEmbedder())
        except ImportError:
            print(
                "faltan los embeddings; instala el extra: pip install 'terranova[descubrimiento]'",
                file=sys.stderr,
            )
            return 2
        ruta_vec = salida.with_suffix(".vec.jsonl")
        ruta_vec.write_text(vectores_a_jsonl(vectores) + "\n", encoding="utf-8")
        print(f"embeddings: {len(vectores)} vectores → {ruta_vec}")
    m = metricas(datasets)

    def pct(x: int) -> str:
        return f"{100 * x // m.total}%" if m.total else "-"

    print(f"catálogo ({a.fuente}): {m.total} datasets → {ruta}")
    print(f"  con licencia declarada: {m.con_licencia} ({pct(m.con_licencia)})")
    print(f"  vivos (< 12 meses):     {m.vivos} ({pct(m.vivos)})")
    print(f"  entidades distintas:    {m.entidades}")
    if a.fuente == "icde":
        # la entidad es casi toda IGAC; lo que decide es la CLASE (base vs temático), spec 09
        clases = collections.Counter(d.categoria or "(sin)" for d in datasets)
        print("  por clase:")
        for clase, n in clases.most_common():
            print(f"    {n:>5}  {clase}")
    print("  top entidades:")
    for ent, n in m.top_entidades:
        print(f"    {n:>5}  {ent[:70]}")
    return 0


def _buscar_mejor(
    datasets: list[DatasetDescubrible],
    rutas: list[pathlib.Path],
    consulta: str,
    *,
    entidad: str | None,
    limite: int,
) -> list[DatasetDescubrible]:
    """Si hay índice de vectores (`*.vec.jsonl`) y el modelo está, busca por **embeddings**
    (ADR-0028); si no, cae al buscador **léxico**. Mismo tipo de candidatos. El filtro por
    `--entidad` solo lo hace el léxico, así que fuerza esa vía."""
    from terranova.descubrimiento import buscar, cargar_vectores

    vec_rutas = [r.with_suffix(".vec.jsonl") for r in rutas]
    if entidad or not any(r.exists() for r in vec_rutas):
        return buscar(datasets, consulta, entidad=entidad, limite=limite)
    try:
        from terranova.descubrimiento import FastEmbedder, buscar_vectorial

        vectores: dict[str, tuple[float, ...]] = {}
        for r in vec_rutas:
            if r.exists():
                vectores.update(cargar_vectores(r.read_text(encoding="utf-8")))
        vq = FastEmbedder().consulta(consulta)
        return buscar_vectorial(datasets, vq, vectores, limite=limite)
    except ImportError:
        return buscar(datasets, consulta, entidad=entidad, limite=limite)


def _catalogo_buscar(argumentos: list[str]) -> int:
    """Busca en los catálogos ingeridos (socrata + icde): qué fuente responde una pregunta, con su
    licencia. Usa embeddings si hay índice de vectores; si no, el buscador léxico. Con `--catalogo`,
    busca solo en ese archivo."""
    import pathlib

    from terranova.descubrimiento import cargar_jsonl

    parser = argparse.ArgumentParser(prog="terranova catalogo-dcat buscar")
    parser.add_argument("consulta")
    parser.add_argument("--entidad", help="acota a una entidad")
    parser.add_argument("--limite", type=int, default=20)
    parser.add_argument("--catalogo", help="un archivo concreto; por defecto, todos los catálogos")
    a = parser.parse_args(argumentos)

    if a.catalogo:
        rutas = [pathlib.Path(a.catalogo)]
    else:
        base = pathlib.Path("datos_locales")
        rutas = sorted(base.glob("catalogo_*.jsonl"))
    rutas = [r for r in rutas if r.exists()]
    if not rutas:
        print("no hay catálogos; corre antes 'catalogo-dcat ingerir'", file=sys.stderr)
        return 2
    datasets = []
    for r in rutas:
        datasets.extend(cargar_jsonl(r.read_text(encoding="utf-8")))
    hallados = _buscar_mejor(datasets, rutas, a.consulta, entidad=a.entidad, limite=a.limite)
    for d in hallados:
        lic = (d.licencia or "")[:30] if d.con_licencia() else "sin licencia"
        proto = "" if d.protocolo == "socrata" else f" ({d.protocolo})"
        print(f"{d.id_socrata}  {d.entidad[:30]:30}  [{lic}]  {d.titulo[:45]}{proto}")
    if not hallados:
        print("(sin candidatos para esa consulta)", file=sys.stderr)
    return 0


def main() -> None:
    argumentos = sys.argv[1:]
    if argumentos[:2] == ["copias", "actualizar"]:
        sys.exit(copias(argumentos[2:]))
    if argumentos[:1] == ["catalogo-dcat"]:
        sys.exit(catalogo_dcat(argumentos[1:]))
    if argumentos[:1] == ["canarios"]:
        sys.exit(canarios(argumentos[1:]))
    if argumentos[:1] == ["llaves"]:
        sys.exit(llaves(argumentos[1:]))
    if argumentos[:2] == ["orgs", "nivel"] and len(argumentos) == 4:
        registro_desde_entorno().fijar_nivel(argumentos[2], argumentos[3])
        print(f"{argumentos[2]}: nivel {argumentos[3]}")
        sys.exit(0)
    if argumentos and argumentos[0] in ("consultar", "herramientas", "fuentes", "uso"):
        from terranova import cliente  # cliente delgado del REST (ADR-0027); no carga el núcleo

        sys.exit(getattr(cliente, argumentos[0])(argumentos[1:]))
    if argumentos and not argumentos[0].startswith("-"):
        # antes, un subcomando mal escrito (`terranova orgs --help`) levantaba el servidor
        print(f"subcomando desconocido: {' '.join(argumentos)}", file=sys.stderr)
        print(__doc__ or "", file=sys.stderr)
        sys.exit(2)
    from terranova.app import main as servir

    servir()
