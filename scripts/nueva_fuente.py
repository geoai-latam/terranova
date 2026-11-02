"""Arranca una fuente nueva de datos.gov.co y lleva sus horas (modelo operativo, PLAN_EXPANSION).

    uv run scripts/nueva_fuente.py crear policia.hurto_nuevo abcd-1234
    uv run scripts/nueva_fuente.py horas policia.hurto_nuevo 1.5 "perfil y canario"

`crear` lee los metadatos publicados y escribe `catalogo/fuentes/<id>.yaml` en borrador. La ficha no
sale sola: licencia y datos personales quedan sin decidir porque los decide una persona (ADR-0014,
ADR-0019). `horas` suma a `interno/horas_fuentes.csv`, que no se versiona.
"""

import argparse
import csv
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from terranova.catalogo import ID_FUENTE, Fuente

RAIZ = Path(__file__).resolve().parents[1]
CONJUNTO = re.compile(r"[a-z0-9]{4}-[a-z0-9]{4}")
TIPOS = {"number": "float", "text": "str", "calendar_date": "date", "checkbox": "bool"}
# Se quedan fuera de la lista blanca hasta que una persona las revise (ADR-0014).
DE_PERSONA = re.compile(r"cedula|c_dula|documento|nombre|apellido|correo|email|telefono|tel_fono")
PASOS = """Sigue, en orden:
  1. Revisa la licencia en {evidencia} y decide `uso_comercial` y `verificada`.
  2. Decide `datos_personales` y recorta la lista blanca.
  3. uv run scripts/perfilar_fuente.py {id} --donde "…": mide la clave y los tiempos.
  4. Escribe la herramienta en `catalogo/herramientas/`, con su canario y una verdad medida.
  5. uv run scripts/grabar_doradas.py <herramienta>
  6. uv run scripts/validar_catalogo.py y `make check`.
  7. Pasa la ficha a `estado: publicada`.
"""


def _campos(vista: dict[str, Any]) -> tuple[dict[str, dict[str, str]], list[str]]:
    """La lista blanca inicial y las columnas apartadas por parecer de una persona."""
    campos: dict[str, dict[str, str]] = {}
    apartadas: list[str] = []
    for col in vista.get("columns") or []:
        nombre = col["fieldName"]
        tipo = TIPOS.get(col.get("dataTypeName", ""))
        if tipo is None or nombre.startswith(":"):
            continue
        if DE_PERSONA.search(nombre):
            apartadas.append(nombre)
            continue
        campos[nombre] = {
            "nombre": nombre,
            "tipo": tipo,
            "desc": (col.get("description") or col.get("name") or nombre).strip(),
        }
    return campos, apartadas


def ficha_socrata(fuente_id: str, conjunto: str, vista: dict[str, Any]) -> dict[str, Any]:
    """La ficha en borrador. Lo que no se sabe queda sin decidir, nunca supuesto."""
    campos, _ = _campos(vista)
    if not campos:
        raise ValueError("el conjunto no trae columnas utilizables")
    entidad = (vista.get("attribution") or "por_verificar").strip()
    evidencia = f"https://www.datos.gov.co/api/views/{conjunto}.json"
    licencia = (vista.get("license") or {}).get("name") or "sin licencia declarada"
    return {
        "id": fuente_id,
        "titulo": vista["name"].strip(),
        "entidad": entidad,
        "competencia": None,
        "acto": None,
        "licencia": {
            "spdx": None,
            "url": f"https://www.datos.gov.co/d/{conjunto}",
            "verificada": None,
            "evidencia": evidencia,
            "cita": licencia,
        },
        "uso_comercial": "por_verificar",
        "clase_acceso": "api",
        "atribucion": f"Fuente: {entidad}. Portal de Datos Abiertos www.datos.gov.co",
        "protocolo": "socrata",
        "conector": "datos-abiertos-mcp",
        "url": f"https://www.datos.gov.co/resource/{conjunto}.json",
        "modo": "en_vivo",
        "frescura": {"ttl_cache_s": 86400, "sla_actualizacion": "P1M"},
        "cobertura": {"pais": "CO"},
        "datos_personales": "presentes",
        "estado": "borrador",
        "campos": campos,
    }


def crear(fuente_id: str, conjunto: str, *, destino: Path | None = None) -> Path:
    if not re.fullmatch(ID_FUENTE, fuente_id):
        raise ValueError(f"id: debe seguir {ID_FUENTE}")
    if not CONJUNTO.fullmatch(conjunto):
        raise ValueError("conjunto: un id de datos.gov.co, como abcd-1234")
    ruta = destino or RAIZ / "catalogo" / "fuentes" / f"{fuente_id}.yaml"
    if ruta.exists():
        raise ValueError(f"ya existe {ruta.name}: una ficha no se pisa")
    respuesta = httpx.get(f"https://www.datos.gov.co/api/views/{conjunto}.json", timeout=30)
    respuesta.raise_for_status()
    vista = respuesta.json()
    ficha = ficha_socrata(fuente_id, conjunto, vista)
    Fuente.model_validate(ficha)
    ruta.write_text(
        yaml.safe_dump(ficha, allow_unicode=True, sort_keys=False, width=120),
        encoding="utf-8",
        newline="\n",
    )
    _, apartadas = _campos(vista)
    if apartadas:
        print(f"Apartadas por parecer de una persona: {', '.join(apartadas)}")
    print(f"Escrita {ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta}, en borrador.")
    print(PASOS.format(id=fuente_id, evidencia=ficha["licencia"]["evidencia"]))
    return ruta


def horas(fuente_id: str, cantidad: float, nota: str, archivo: Path | None = None) -> Path:
    if cantidad <= 0:
        raise ValueError("horas: debe ser mayor que cero")
    ruta = archivo or RAIZ / "interno" / "horas_fuentes.csv"
    nuevo = not ruta.exists()
    with ruta.open("a", encoding="utf-8", newline="") as salida:
        escritor = csv.writer(salida)
        if nuevo:
            escritor.writerow(["fecha", "fuente", "horas", "nota"])
        hoy = datetime.now(UTC).date().isoformat()
        escritor.writerow([hoy, fuente_id, cantidad, nota])
    return ruta


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nueva_fuente")
    sub = parser.add_subparsers(dest="accion", required=True)
    alta = sub.add_parser("crear", help="escribe la ficha en borrador")
    alta.add_argument("id")
    alta.add_argument("conjunto")
    tiempo = sub.add_parser("horas", help="registra horas de alta o de mantenimiento")
    tiempo.add_argument("id")
    tiempo.add_argument("horas", type=float)
    tiempo.add_argument("nota", nargs="?", default="")
    a = parser.parse_args(argumentos)
    try:
        if a.accion == "crear":
            crear(a.id, a.conjunto)
        else:
            horas(a.id, a.horas, a.nota)
            print(f"{a.id}: {a.horas} h")
    except (ValueError, httpx.HTTPError) as exc:
        print(f"No se pudo: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
