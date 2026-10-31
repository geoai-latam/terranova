"""Identidad (ADR-0009, F3.2): organizaciones con llaves, scopes por familia y revocación inmediata.

- La llave (`rt_live_…` o `rt_test_…`) se muestra una sola vez. Se guarda su HMAC-SHA256 con la
  pimienta del servidor (`TERRANOVA_PIMIENTA`), nunca la llave.
- `rt_test_` es plan `evaluacion` (ve fuentes con licencia por verificar, ADR-0007); `rt_live_`,
  plan `normal`.
- Scopes: familias (`territorio`, `ambiente`…) o `*`.
- Se consulta en cada petición: una revocación surte efecto en la siguiente (< 5 s, ADR-0009).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, Protocol

from terranova.bd import Conexion

Plan = Literal["evaluacion", "normal"]
PREFIJOS: dict[str, Plan] = {"rt_live_": "normal", "rt_test_": "evaluacion"}
FORMATO = re.compile(r"^rt_(live|test)_([A-Za-z0-9_-]{43})$")


@dataclass(frozen=True)
class Principal:
    org: str
    llave_id: str
    plan: Plan
    scopes: frozenset[str]
    nivel: str = "con_llave"  # saldo mensual (ADR-0010): con_llave o ampliado

    def puede(self, familia: str) -> bool:
        return "*" in self.scopes or familia in self.scopes


@dataclass(frozen=True)
class Llave:
    llave_id: str
    org: str
    plan: Plan
    scopes: frozenset[str]
    creada: str
    expira: str | None
    revocada: str | None
    ultimo_uso: str | None


class Registro(Protocol):
    def crear(self, org: str, scopes: set[str], *, prueba: bool, expira: date | None) -> str: ...
    def revocar(self, llave_id: str) -> bool: ...
    def listar(self, org: str | None = None) -> list[Llave]: ...
    def verificar(self, llave: str) -> Principal | None: ...
    def fijar_nivel(self, org: str, nivel: str) -> None: ...
    def listar_orgs(self) -> list[tuple[str, str, int]]: ...


def _ahora() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class RegistroSql:
    """Llaves en SQLite (desarrollo, una réplica) o Postgres (varias réplicas, ADR-0015)."""

    async def ping(self) -> None:
        """Para `/listo`: la base de llaves responde."""
        await asyncio.to_thread(self._bd.ejecutar, "SELECT 1")

    def __init__(self, destino: str | Path, pimienta: str) -> None:
        if len(pimienta) < 32:
            raise ValueError("TERRANOVA_PIMIENTA debe tener al menos 32 caracteres")
        self._pimienta = pimienta.encode()
        self._bd = Conexion(destino)
        self._bd.ejecutar(
            """CREATE TABLE IF NOT EXISTS llaves (
                llave_id TEXT PRIMARY KEY, huella TEXT NOT NULL UNIQUE, org TEXT NOT NULL,
                plan TEXT NOT NULL, scopes TEXT NOT NULL, creada TEXT NOT NULL,
                expira TEXT, revocada TEXT, ultimo_uso TEXT)"""
        )
        self._bd.ejecutar(
            "CREATE TABLE IF NOT EXISTS orgs (org TEXT PRIMARY KEY, nivel TEXT NOT NULL)"
        )

    def fijar_nivel(self, org: str, nivel: str) -> None:
        from terranova.cuota import NIVELES

        if nivel not in NIVELES:
            raise ValueError(f"nivel: uno de {sorted(NIVELES)}")
        self._bd.ejecutar(
            "INSERT INTO orgs VALUES (?, ?) ON CONFLICT(org) DO UPDATE SET nivel = excluded.nivel",
            (org, nivel),
        )

    def listar_orgs(self) -> list[tuple[str, str, int]]:
        """(org, nivel, llaves vigentes) de toda org con nivel fijado o con llaves. Sin fila en
        `orgs`, el nivel es `con_llave`: así se ve quién quedaría en el gratis."""
        filas, _ = self._bd.ejecutar(
            "SELECT t.org, COALESCE(o.nivel, 'con_llave'), "
            "(SELECT COUNT(*) FROM llaves l WHERE l.org = t.org AND l.revocada IS NULL) "
            "FROM (SELECT org FROM orgs UNION SELECT org FROM llaves) t "
            "LEFT JOIN orgs o ON o.org = t.org ORDER BY t.org"
        )
        return [(f[0], f[1], int(f[2])) for f in filas]

    def _huella(self, llave: str) -> str:
        return hmac.new(self._pimienta, llave.encode(), hashlib.sha256).hexdigest()

    def crear(self, org: str, scopes: set[str], *, prueba: bool, expira: date | None) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,62}", org):
            raise ValueError("org: minúsculas, dígitos, _ y -")
        if not scopes:
            raise ValueError("una llave necesita al menos un scope")
        prefijo = "rt_test_" if prueba else "rt_live_"
        llave = prefijo + secrets.token_urlsafe(32)
        llave_id = "llv_" + secrets.token_hex(6)
        self._bd.ejecutar(
            "INSERT INTO llaves VALUES (?,?,?,?,?,?,?,NULL,NULL)",
            (
                llave_id,
                self._huella(llave),
                org,
                PREFIJOS[prefijo],
                ",".join(sorted(scopes)),
                _ahora(),
                expira.isoformat() if expira else None,
            ),
        )
        return llave

    def revocar(self, llave_id: str) -> bool:
        _, afectadas = self._bd.ejecutar(
            "UPDATE llaves SET revocada = ? WHERE llave_id = ? AND revocada IS NULL",
            (_ahora(), llave_id),
        )
        return afectadas == 1

    def listar(self, org: str | None = None) -> list[Llave]:
        consulta = (
            "SELECT llave_id, org, plan, scopes, creada, expira, revocada, ultimo_uso FROM llaves"
        )
        filas, _ = self._bd.ejecutar(
            consulta + (" WHERE org = ?" if org else "") + " ORDER BY creada", (org,) if org else ()
        )
        return [
            Llave(f[0], f[1], f[2], frozenset(f[3].split(",")), f[4], f[5], f[6], f[7])
            for f in filas
        ]

    def verificar(self, llave: str) -> Principal | None:
        """Principal de una llave vigente, o None. La comparación es por HMAC (sin la llave)."""
        if not FORMATO.fullmatch(llave):
            return None
        filas, _ = self._bd.ejecutar(
            "SELECT l.llave_id, l.org, l.plan, l.scopes, l.expira, l.revocada, o.nivel "
            "FROM llaves l LEFT JOIN orgs o ON o.org = l.org WHERE l.huella = ?",
            (self._huella(llave),),
        )
        if not filas or filas[0][5] is not None:
            return None
        f = filas[0]
        if f[4] and date.fromisoformat(f[4]) < datetime.now(UTC).date():
            return None
        self._bd.ejecutar("UPDATE llaves SET ultimo_uso = ? WHERE llave_id = ?", (_ahora(), f[0]))
        return Principal(f[1], f[0], f[2], frozenset(f[3].split(",")), f[6] or "con_llave")


RegistroSqlite = RegistroSql  # nombre de F3.2


def registro_desde_entorno() -> RegistroSql:
    pimienta = os.environ.get("TERRANOVA_PIMIENTA", "")
    if not pimienta:
        raise RuntimeError("falta TERRANOVA_PIMIENTA (secreto del servidor, ≥ 32 caracteres)")
    return RegistroSql(os.environ.get("TERRANOVA_BD", "datos_locales/terranova.db"), pimienta)


def bearer(cabecera: str | None) -> str | None:
    if not cabecera:
        return None
    partes = cabecera.split(None, 1)
    if len(partes) != 2 or partes[0].lower() != "bearer":
        return None
    return partes[1].strip() or None
