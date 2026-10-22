"""Identidad (ADR-0009, F3.2): organizaciones con llaves, scopes por familia y revocación inmediata.

- La llave (`rt_live_…` o `rt_test_…`) se muestra una sola vez. Se guarda su HMAC-SHA256 con la
  pimienta del servidor (`TERRANOVA_PIMIENTA`), nunca la llave.
- `rt_test_` es plan `evaluacion` (ve fuentes con licencia por verificar, ADR-0007); `rt_live_`,
  plan `normal`.
- Scopes: familias (`territorio`, `ambiente`…) o `*`.
- Se consulta en cada petición: una revocación surte efecto en la siguiente (< 5 s, ADR-0009).
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal, Protocol

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


def _ahora() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class RegistroSqlite:
    """Llaves en SQLite: desarrollo y una sola réplica. Producción usa Postgres (F3.7)."""

    def __init__(self, ruta: str | Path, pimienta: str) -> None:
        if len(pimienta) < 32:
            raise ValueError("TERRANOVA_PIMIENTA debe tener al menos 32 caracteres")
        self._pimienta = pimienta.encode()
        self._candado = threading.Lock()
        if str(ruta) != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self._bd = sqlite3.connect(str(ruta), check_same_thread=False, isolation_level=None)
        self._bd.execute(
            """CREATE TABLE IF NOT EXISTS llaves (
                llave_id TEXT PRIMARY KEY, huella TEXT NOT NULL UNIQUE, org TEXT NOT NULL,
                plan TEXT NOT NULL, scopes TEXT NOT NULL, creada TEXT NOT NULL,
                expira TEXT, revocada TEXT, ultimo_uso TEXT)"""
        )
        self._bd.execute(
            "CREATE TABLE IF NOT EXISTS orgs (org TEXT PRIMARY KEY, nivel TEXT NOT NULL)"
        )

    def fijar_nivel(self, org: str, nivel: str) -> None:
        from terranova.cuota import NIVELES

        if nivel not in NIVELES:
            raise ValueError(f"nivel: uno de {sorted(NIVELES)}")
        with self._candado:
            self._bd.execute(
                "INSERT INTO orgs VALUES (?, ?) "
                "ON CONFLICT(org) DO UPDATE SET nivel = excluded.nivel",
                (org, nivel),
            )

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
        with self._candado:
            self._bd.execute(
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
        with self._candado:
            cur = self._bd.execute(
                "UPDATE llaves SET revocada = ? WHERE llave_id = ? AND revocada IS NULL",
                (_ahora(), llave_id),
            )
        return cur.rowcount == 1

    def listar(self, org: str | None = None) -> list[Llave]:
        consulta = (
            "SELECT llave_id, org, plan, scopes, creada, expira, revocada, ultimo_uso FROM llaves"
        )
        filas = self._bd.execute(
            consulta + (" WHERE org = ?" if org else "") + " ORDER BY creada", (org,) if org else ()
        ).fetchall()
        return [
            Llave(f[0], f[1], f[2], frozenset(f[3].split(",")), f[4], f[5], f[6], f[7])
            for f in filas
        ]

    def verificar(self, llave: str) -> Principal | None:
        """Principal de una llave vigente, o None. La comparación es por HMAC (sin la llave)."""
        if not FORMATO.fullmatch(llave):
            return None
        huella = self._huella(llave)
        with self._candado:
            fila = self._bd.execute(
                "SELECT llave_id, org, plan, scopes, expira, revocada FROM llaves WHERE huella = ?",
                (huella,),
            ).fetchone()
            if fila is None or fila[5] is not None:
                return None
            if fila[4] and date.fromisoformat(fila[4]) < datetime.now(UTC).date():
                return None
            self._bd.execute(
                "UPDATE llaves SET ultimo_uso = ? WHERE llave_id = ?", (_ahora(), fila[0])
            )
            nivel = self._bd.execute("SELECT nivel FROM orgs WHERE org = ?", (fila[1],)).fetchone()
        org_nivel = nivel[0] if nivel else "con_llave"
        return Principal(fila[1], fila[0], fila[2], frozenset(fila[3].split(",")), org_nivel)


def registro_desde_entorno() -> RegistroSqlite:
    pimienta = os.environ.get("TERRANOVA_PIMIENTA", "")
    if not pimienta:
        raise RuntimeError("falta TERRANOVA_PIMIENTA (secreto del servidor, ≥ 32 caracteres)")
    return RegistroSqlite(os.environ.get("TERRANOVA_BD", "datos_locales/terranova.db"), pimienta)


def bearer(cabecera: str | None) -> str | None:
    if not cabecera:
        return None
    partes = cabecera.split(None, 1)
    if len(partes) != 2 or partes[0].lower() != "bearer":
        return None
    return partes[1].strip() or None
