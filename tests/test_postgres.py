"""El registro de llaves y el outbox sobre Postgres (F3.7, ADR-0015). Corre solo con
`TERRANOVA_PG_PRUEBAS=postgresql://…` (en CI, un servicio Postgres)."""

import os
import uuid

import pytest

from terranova.identidad import RegistroSql
from terranova.medicion import Evento, OutboxSql

URL = os.environ.get("TERRANOVA_PG_PRUEBAS")
pytestmark = pytest.mark.skipif(not URL, reason="sin TERRANOVA_PG_PRUEBAS")


def test_registro_en_postgres() -> None:
    assert URL
    r = RegistroSql(URL, "p" * 40)
    org = "org-" + uuid.uuid4().hex[:8]
    llave = r.crear(org, {"territorio"}, prueba=True, expira=None)
    p = r.verificar(llave)
    assert p is not None and p.org == org and p.plan == "evaluacion" and p.nivel == "con_llave"
    r.fijar_nivel(org, "ampliado")
    r.fijar_nivel(org, "ampliado")  # upsert
    assert (q := r.verificar(llave)) is not None and q.nivel == "ampliado"
    (ll,) = r.listar(org)
    assert ll.ultimo_uso is not None
    assert r.revocar(ll.llave_id) and not r.revocar(ll.llave_id)
    assert r.verificar(llave) is None


def test_dos_replicas_ven_la_misma_revocacion() -> None:
    """Dos puertas con su propia conexión: la revocación en una surte efecto en la otra."""
    assert URL
    a, b = RegistroSql(URL, "p" * 40), RegistroSql(URL, "p" * 40)
    org = "org-" + uuid.uuid4().hex[:8]
    llave = a.crear(org, {"*"}, prueba=False, expira=None)
    assert b.verificar(llave) is not None
    a.revocar(a.listar(org)[0].llave_id)
    assert b.verificar(llave) is None


def test_outbox_en_postgres_sin_duplicados() -> None:
    assert URL
    o = OutboxSql(URL)
    org = "org-" + uuid.uuid4().hex[:8]
    e = Evento(
        "req_" + uuid.uuid4().hex, org, "llv_1", "h", 10, "encontrado", "fuente", "2026-10-22"
    )
    o.registrar(e)
    o.registrar(e)
    assert o.eventos(org) == [e]
