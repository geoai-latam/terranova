"""CLI de cliente (ADR-0027, spec 10): un cliente delgado del REST `/v1`.

No agrega lógica de negocio — hace la petición con la llave, interpreta el sobre `rt/1`, y decide el
código de salida: `0` si la fuente respondió (`encontrado`/`no_encontrado`), `≠0` solo cuando «no se
pudo» (fuente caída/lenta, 4xx/5xx, red). Las funciones puras (`codigo_salida`, `formatear`,
`familia_de`, `pares`) se prueban sin red; `Cliente` hace la llamada.

MVP de la lámina: `consultar / fuentes / herramientas / uso`. `catalogo buscar`, `exportar` y
`verificar` llegan después (dependen de G6, de GDAL y de las reglas de la obligación; ver spec 10).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

#: El sobre `rt/1` con estos estados SÍ es una respuesta de la fuente (exit 0).
RESPONDIO = {"encontrado", "no_encontrado"}


def _cliente_http(timeout: float = 60) -> Any:
    import httpx

    return httpx.Client(timeout=timeout, headers={"User-Agent": "terranova-cli/1"})


class Cliente:
    """Un cliente del REST `/v1` con la llave del usuario. `http` se inyecta en las pruebas."""

    def __init__(self, puerta: str, llave: str, http: Any = None) -> None:
        self.puerta = puerta.rstrip("/")
        self._http = http or _cliente_http()
        self._auth = {"Authorization": f"Bearer {llave}"}

    def _get(self, ruta: str) -> Any:
        return self._http.get(f"{self.puerta}{ruta}", headers=self._auth)

    def herramientas(self) -> list[dict[str, Any]]:
        r = self._get("/v1/herramientas")
        r.raise_for_status()
        datos = r.json()
        return datos if isinstance(datos, list) else datos.get("herramientas", [])

    def fuentes(self) -> list[dict[str, Any]]:
        r = self._get("/v1/fuentes")
        r.raise_for_status()
        datos = r.json()
        return datos if isinstance(datos, list) else datos.get("fuentes", [])

    def uso(self) -> dict[str, Any]:
        r = self._get("/v1/uso")
        r.raise_for_status()
        return dict(r.json())

    def consultar(self, familia: str, herramienta: str, args: dict[str, str]) -> dict[str, Any]:
        r = self._http.post(
            f"{self.puerta}/v1/co/{familia}/{herramienta}", json=args, headers=self._auth
        )
        # un 4xx/5xx trae un problem+json; se devuelve como sobre para que `codigo_salida` lo trate
        try:
            return dict(r.json())
        except ValueError:
            return {"estado": "error_interno", "detalle": f"HTTP {r.status_code}"}


def pares(extras: list[str]) -> dict[str, str]:
    """`['--lon', '-74.0', '--lat', '4.8']` → `{'lon': '-74.0', 'lat': '4.8'}`."""
    salida: dict[str, str] = {}
    i = 0
    while i < len(extras):
        clave = extras[i]
        if clave.startswith("--") and i + 1 < len(extras):
            salida[clave[2:]] = extras[i + 1]
            i += 2
        else:
            i += 1
    return salida


def familia_de(herramientas: list[dict[str, Any]], nombre: str) -> str | None:
    """La familia de una herramienta, de la lista que devuelve `/v1/herramientas`."""
    for h in herramientas:
        if h.get("id") == nombre or h.get("herramienta") == nombre:
            fam = h.get("familia")
            return str(fam) if fam else None
    return None


def codigo_salida(sobre: dict[str, Any]) -> int:
    """`0` si la fuente respondió (encontrado/no_encontrado), `≠0` si «no se pudo»."""
    return 0 if sobre.get("estado") in RESPONDIO else 1


def formatear(sobre: dict[str, Any]) -> str:
    """El sobre `rt/1` en texto legible: estado, dato, procedencia y licencia."""
    partes = [f"estado: {sobre.get('estado', '?')}"]
    datos = sobre.get("datos")
    if datos:
        partes.append(json.dumps(datos, ensure_ascii=False)[:800])
    proc = sobre.get("procedencia") or {}
    if proc:
        fuente = proc.get("fuente") or proc.get("entidad") or ""
        lic = proc.get("licencia") or ""
        partes.append(f"fuente: {fuente}  ·  licencia: {lic}")
    return "\n".join(partes)


def _avisos_a_stderr(sobre: dict[str, Any]) -> None:
    for aviso in sobre.get("avisos") or []:
        print(f"aviso: {aviso}", file=sys.stderr)
    if sobre.get("estado") not in RESPONDIO:
        print(
            f"no se pudo: {sobre.get('estado')} {sobre.get('detalle', '')}".strip(), file=sys.stderr
        )


def _conectar(a: argparse.Namespace) -> Cliente:
    puerta = os.environ.get("TERRANOVA_PUERTA") or getattr(a, "puerta", None)
    llave = os.environ.get("TERRANOVA_LLAVE")
    if not puerta:
        raise SystemExit("falta TERRANOVA_PUERTA (o --puerta)")
    if not llave:
        raise SystemExit("falta TERRANOVA_LLAVE (rt_live_… o rt_test_…)")
    return Cliente(puerta, llave)


def _salida(sobre: dict[str, Any], crudo: bool) -> int:
    print(json.dumps(sobre, ensure_ascii=False) if crudo else formatear(sobre))
    _avisos_a_stderr(sobre)
    return codigo_salida(sobre)


def consultar(argumentos: list[str]) -> int:
    """`terranova consultar <herramienta> --<arg> <valor> [--json]`."""
    import httpx

    parser = argparse.ArgumentParser(prog="terranova consultar")
    parser.add_argument("herramienta")
    parser.add_argument("--puerta")
    parser.add_argument("--json", action="store_true", dest="crudo")
    a, extras = parser.parse_known_args(argumentos)
    try:
        cli = _conectar(a)
        fam = familia_de(cli.herramientas(), a.herramienta)
        if fam is None:
            print(f"herramienta desconocida: {a.herramienta}", file=sys.stderr)
            return 2
        sobre = cli.consultar(fam, a.herramienta, pares(extras))
    except httpx.HTTPError as exc:
        print(f"no se pudo: {type(exc).__name__}", file=sys.stderr)
        return 1
    return _salida(sobre, a.crudo)


def _listar(argumentos: list[str], que: str) -> int:
    import httpx

    parser = argparse.ArgumentParser(prog=f"terranova {que}")
    parser.add_argument("--puerta")
    parser.add_argument("--familia")
    a = parser.parse_args(argumentos)
    try:
        cli = _conectar(a)
        filas = cli.herramientas() if que == "herramientas" else cli.fuentes()
    except httpx.HTTPError as exc:
        print(f"no se pudo: {type(exc).__name__}", file=sys.stderr)
        return 1
    for f in filas:
        if a.familia and f.get("familia") != a.familia:
            continue
        ident = f.get("id") or f.get("herramienta") or f.get("fuente") or "?"
        print(f"{ident}  {f.get('familia', '')}")
    return 0


def herramientas(argumentos: list[str]) -> int:
    return _listar(argumentos, "herramientas")


def fuentes(argumentos: list[str]) -> int:
    return _listar(argumentos, "fuentes")


def uso(argumentos: list[str]) -> int:
    import httpx

    parser = argparse.ArgumentParser(prog="terranova uso")
    parser.add_argument("--puerta")
    a = parser.parse_args(argumentos)
    try:
        datos = _conectar(a).uso()
    except httpx.HTTPError as exc:
        print(f"no se pudo: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(datos, ensure_ascii=False))
    return 0
