"""`terranova`: sin argumentos levanta la puerta; `terranova llaves …` administra llaves (F3.2).

    terranova llaves crear --org geoai --scopes territorio,ambiente [--prueba] [--expira 2027-01-01]
    terranova llaves revocar llv_…
    terranova llaves listar [--org geoai]
    terranova orgs nivel geoai ampliado      (saldo mensual: con_llave 20 000, ampliado 200 000)

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


def main() -> None:
    argumentos = sys.argv[1:]
    if argumentos[:1] == ["llaves"]:
        sys.exit(llaves(argumentos[1:]))
    if argumentos[:2] == ["orgs", "nivel"] and len(argumentos) == 4:
        registro_desde_entorno().fijar_nivel(argumentos[2], argumentos[3])
        print(f"{argumentos[2]}: nivel {argumentos[3]}")
        sys.exit(0)
    from terranova.app import main as servir

    servir()
