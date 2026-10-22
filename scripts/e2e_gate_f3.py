"""E2E-03 a E2E-06 (spec 04, §11.5) contra el compose de `docker/compose.yml`, para el gate F3.

Nunca hace carga contra el Estado (CLAUDE.md): las 50 llamadas simultáneas de E2E-04 van contra la
caché (la primera la llena). E2E-05 detiene el conector local, no la fuente.

Uso: `uv run scripts/e2e_gate_f3.py --env docker/.env`
"""

import argparse
import asyncio
import subprocess
import sys
import time

import httpx

BASE = "http://127.0.0.1:8180"
PREDIO = "/v1/co/territorio/igac_predio_en_punto"
CHIA = {"lon": -74.0262, "lat": 4.8619}
DANE = "/v1/co/estadisticas/dane_poblacion_municipio"


class Compose:
    def __init__(self, env: str) -> None:
        self.base = ["docker", "compose", "-f", "docker/compose.yml", "--env-file", env]

    def __call__(self, *args: str) -> str:
        r = subprocess.run([*self.base, *args], capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def llave(self, org: str, scopes: str, *, prueba: bool = False) -> str:
        extra = ["--prueba"] if prueba else []
        return self(
            "exec",
            "-T",
            "puerta-a",
            "terranova",
            "llaves",
            "crear",
            "--org",
            org,
            "--scopes",
            scopes,
            *extra,
        ).splitlines()[-1]


def _ok(condicion: bool, texto: str, fallas: list[str]) -> None:
    print(("  ✓ " if condicion else "  ✗ ") + texto)
    if not condicion:
        fallas.append(texto)


def _cab(llave: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {llave}"}


async def _mcp_estado(llave: str) -> int:
    """HTTP del primer contacto MCP con esa llave (401 si no vale)."""
    async with httpx.AsyncClient(timeout=30) as http:
        r = await http.post(
            f"{BASE}/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            headers={**_cab(llave), "Accept": "application/json, text/event-stream"},
        )
        return r.status_code


async def e2e03(c: Compose, http: httpx.AsyncClient, fallas: list[str]) -> None:
    print("E2E-03 · llave revocada")
    org = f"e2e03-{int(time.time())}"
    llave = c.llave(org, "territorio")
    _ok(
        (await http.post(PREDIO, json=CHIA, headers=_cab(llave))).status_code == 200,
        "antes: 200",
        fallas,
    )
    llave_id = c("exec", "-T", "puerta-a", "terranova", "llaves", "listar", "--org", org).split()[0]
    t0 = time.monotonic()
    c("exec", "-T", "puerta-b", "terranova", "llaves", "revocar", llave_id)
    rest = (await http.post(PREDIO, json=CHIA, headers=_cab(llave))).status_code
    mcp = await _mcp_estado(llave)
    dt = time.monotonic() - t0
    _ok(rest == 401 and mcp == 401, f"después: REST {rest}, MCP {mcp}", fallas)
    _ok(dt < 5, f"surte efecto en {dt:.1f} s (< 5 s)", fallas)


async def e2e04(c: Compose, http: httpx.AsyncClient, fallas: list[str]) -> None:
    print("E2E-04 · tasa y sin sobreconsumo")
    llave = c.llave(f"e2e04-{int(time.time())}", "territorio")
    cab = _cab(llave)
    assert (await http.post(PREDIO, json=CHIA, headers=cab)).status_code == 200  # llena la caché
    usados = (await http.get("/v1/uso", headers=cab)).json()["usados"]
    respuestas = await asyncio.gather(
        *(http.post(PREDIO, json=CHIA, headers=cab) for _ in range(50))
    )
    codigos = [r.status_code for r in respuestas]
    limitadas = [r for r in respuestas if r.status_code == 429]
    _ok(
        set(codigos) <= {200, 429} and bool(limitadas),
        f"50 simultáneas: {codigos.count(200)} x 200, {len(limitadas)} x 429",
        fallas,
    )
    _ok(
        all(
            r.json()["code"] == "limite_tasa" and int(r.headers["retry-after"]) >= 1
            for r in limitadas
        ),
        "429 limite_tasa con Retry-After",
        fallas,
    )
    _ok(
        all(r.json()["creditos"] == 0 for r in respuestas if r.status_code == 200),
        "desde caché: 0 créditos",
        fallas,
    )
    await asyncio.sleep(2)  # la cubeta quedó vacía: que se repongan fichas para leer el uso
    _ok(
        (await http.get("/v1/uso", headers=cab)).json()["usados"] == usados,
        f"sin sobreconsumo: usados sigue en {usados}",
        fallas,
    )


async def e2e05(c: Compose, http: httpx.AsyncClient, fallas: list[str]) -> None:
    print("E2E-05 · fuente caída")
    llave = c.llave(f"e2e05-{int(time.time())}", "territorio")
    cab = _cab(llave)
    assert (await http.post(PREDIO, json=CHIA, headers=cab)).status_code == 200
    c("stop", "arcgis-mcp")
    try:
        usados = (await http.get("/v1/uso", headers=cab)).json()["usados"]
        otro = {"lon": -74.0301, "lat": 4.8655}  # no está en caché
        t0 = time.monotonic()
        r = await http.post(PREDIO, json=otro, headers=cab)
        dt = time.monotonic() - t0
        _ok(
            r.status_code == 502 and r.json()["code"] == "fuente_no_disponible",
            f"sin caché: {r.status_code} {r.json().get('code')} en {dt:.1f} s",
            fallas,
        )
        _ok(
            (await http.get("/v1/uso", headers=cab)).json()["usados"] == usados,
            "no descuenta",
            fallas,
        )
        cache = await http.post(PREDIO, json=CHIA, headers=cab)
        _ok(
            cache.status_code == 200
            and cache.json()["procedencia"][0]["servido_desde"] in ("cache", "obsoleto"),
            "con caché previa: responde y lo dice",
            fallas,
        )
    finally:
        c("start", "arcgis-mcp")


async def e2e06(c: Compose, http: httpx.AsyncClient, fallas: list[str]) -> None:
    print("E2E-06 · licencia por verificar")
    org = f"e2e06-{int(time.time())}"
    viva = (
        await http.post(
            DANE, json={"municipio_divipola": "11001"}, headers=_cab(c.llave(org, "estadisticas"))
        )
    ).json()
    _ok(viva.get("code") == "licencia_no_habilitada", f"llave normal: {viva.get('code')}", fallas)
    prueba = await http.post(
        DANE,
        json={"municipio_divipola": "11001"},
        headers=_cab(c.llave(org, "estadisticas", prueba=True)),
    )
    # el compose no trae dane-mcp: pasar la compuerta se ve en que el error ya es de la fuente
    _ok(
        prueba.json().get("code") != "licencia_no_habilitada",
        f"llave de evaluación pasa la compuerta ({prueba.json().get('code', 'ok')})",
        fallas,
    )


async def main(env: str) -> int:
    c, fallas = Compose(env), list[str]()
    async with httpx.AsyncClient(base_url=BASE, timeout=120) as http:
        for prueba in (e2e03, e2e04, e2e05, e2e06):
            await prueba(c, http, fallas)
    print("verde" if not fallas else f"{len(fallas)} fallas: {fallas}")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # consola cp1252
    p = argparse.ArgumentParser()
    p.add_argument("--env", default="docker/.env")
    sys.exit(asyncio.run(main(p.parse_args().env)))
