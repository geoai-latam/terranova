"""Métricas del embudo (spec 11, F8.5): salen de la base, no se cuentan a mano."""

from datetime import UTC, datetime, timedelta

from terranova.bd import Conexion
from terranova.embudo import informe, medir
from terranova.medicion import Evento, OutboxSql

AHORA = datetime(2026, 11, 20, 12, 0, tzinfo=UTC)


def _base() -> Conexion:
    bd = Conexion(":memory:")
    bd.ejecutar(
        "CREATE TABLE llaves (llave_id TEXT, huella TEXT, org TEXT, plan TEXT, scopes TEXT, "
        "creada TEXT, expira TEXT, revocada TEXT, ultimo_uso TEXT)"
    )
    bd.ejecutar(
        "CREATE TABLE altas (correo TEXT, org TEXT, nombre TEXT, organizacion TEXT, uso TEXT, "
        "creada TEXT, confirmada TEXT, ip TEXT)"
    )
    return bd


def _llave(bd: Conexion, llave_id: str, hace: timedelta) -> datetime:
    creada = AHORA - hace
    bd.ejecutar(
        "INSERT INTO llaves VALUES (?, '', 'o', 'normal', '*', ?, NULL, NULL, NULL)",
        (llave_id, creada.isoformat()),
    )
    return creada


def _eventos(bd: Conexion, llave_id: str, desde: datetime, n: int, resultado: str) -> None:
    for i in range(n):
        momento = (desde + timedelta(hours=1 + i)).isoformat()
        bd.ejecutar(
            "INSERT INTO eventos VALUES (?,?,?,?,?,?,?,?,0)",
            (
                f"req_{llave_id}_{i}_{resultado}",
                "o",
                llave_id,
                "h",
                2,
                resultado,
                "fuente",
                momento,
            ),
        )


def test_activacion_primera_llamada_y_activas() -> None:
    bd = _base()
    bd.ejecutar(
        "CREATE TABLE eventos (solicitud_id TEXT PRIMARY KEY, org TEXT, llave_id TEXT, "
        "herramienta TEXT, creditos INTEGER, resultado TEXT, servido_desde TEXT, momento TEXT, "
        "enviado INTEGER)"
    )
    activa = _llave(bd, "llv_a", timedelta(days=10))
    _eventos(bd, "llv_a", activa, 12, "encontrado")  # 12 exitosas en su primer día: se activa
    floja = _llave(bd, "llv_b", timedelta(days=9))
    _eventos(bd, "llv_b", floja, 3, "encontrado")
    _eventos(bd, "llv_b", floja + timedelta(hours=5), 20, "fuente_no_disponible")  # errores
    _llave(bd, "llv_c", timedelta(days=2))  # aún no se sabe si se activa; no ha llamado
    bd.ejecutar(
        "INSERT INTO altas VALUES ('a@x.co','o','A','','',?,?,'ip')",
        ((AHORA - timedelta(days=10)).isoformat(), (AHORA - timedelta(days=10)).isoformat()),
    )
    e = medir(bd, semanas=4, ahora=AHORA)
    assert e.llaves_nuevas == 3
    assert (e.activadas, e.activables) == (1, 2)
    assert e.horas_hasta_primera_llamada == 1.0
    assert e.activas_7 == 0 and e.activas_28 == 2
    assert sum(p for _, p, _, _ in e.semanas) == 1 and sum(c for _, _, c, _ in e.semanas) == 1
    texto = informe(e)
    assert "1 de 2 (50 %)" in texto and "1.0 h" in texto


def test_una_base_sin_altas_ni_contactos_no_falla() -> None:
    bd = _base()
    bd.ejecutar("DROP TABLE altas")
    e = medir(bd, ahora=AHORA)
    assert e.llaves_nuevas == 0 and e.horas_hasta_primera_llamada is None
    assert "sin datos" in informe(e)


def test_el_outbox_crea_sus_indices(tmp_path: object) -> None:
    o = OutboxSql(":memory:")
    o.registrar(Evento("req_1", "o", "llv_1", "h", 2, "encontrado", "fuente", AHORA.isoformat()))
    filas, _ = o._bd.ejecutar("SELECT name FROM sqlite_master WHERE type = 'index'")
    nombres = {f[0] for f in filas}
    assert {"eventos_momento", "eventos_org_momento", "eventos_llave_momento"} <= nombres
