"""El registro de llaves y el outbox sobre Postgres (F3.7, ADR-0015). Corre solo con
`TERRANOVA_PG_PRUEBAS=postgresql://…` (en CI, un servicio Postgres)."""

import asyncio
import os
import uuid
from pathlib import Path

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
    assert (org, "ampliado", 1) in r.listar_orgs()
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
    assert o.consumo("2026-10", org) == [(org, "h", 10, 1)]  # SUM/COUNT de Postgres → int


def test_restricciones_curadas_en_postgis(tmp_path: Path) -> None:
    """F4.1 → ficha: lo que carga `cargar_postgis` es lo que lee la puerta (`curado.versiones`)."""
    assert URL
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box

    from terranova.curado import RestriccionesPostgis
    from terranova.datasets import restricciones as r

    filas = gpd.GeoDataFrame(
        {
            "id": ["runap:1", "ant.resguardos_indigenas:R-1"],
            "tipo": ["area_protegida", "resguardo_indigena"],
            "nombre": ["Chingaza", "Uno"],
            "categoria": ["Parque Nacional Natural", "Nasa"],
            "acto": [None, "Resolución 12"],
            "fecha": ["2011-06-30", "1990-01-15"],
            "fuente_id": ["pnn.runap", "ant.resguardos_indigenas"],
            "url": [None, None],
        },
        geometry=[box(-74.0, 4.4, -73.5, 4.8), box(-70.6, 0.7, -70.4, 0.9)],
        crs=r.CRS,
    )
    origenes = [r.Origen("pnn.runap", "https://x", "2026-10-09", 1)]
    m = r.publicar([filas], origenes, tmp_path)
    parquet = tmp_path / f"restricciones_{m.version}.parquet"
    r.cargar_postgis(parquet, URL, m)
    r.cargar_postgis(parquet, URL, m)  # la misma versión otra vez: nada cambia

    c = asyncio.run(RestriccionesPostgis(URL).en_punto(-73.75, 4.55))
    assert [f["nombre"] for f in c.filas] == ["Chingaza"]
    assert c.manifiesto["version"] == m.version and c.manifiesto["huella"] == m.huella
    assert asyncio.run(RestriccionesPostgis(URL).en_punto(-60.0, 10.0)).filas == []


def test_el_pool_se_cierra_al_salir_del_proceso(monkeypatch: pytest.MonkeyPatch) -> None:
    """La CLI (`terranova orgs uso`) no deja el pool para el recolector del apagado, donde sus
    hilos fallan con «cannot join current thread»."""
    import atexit

    from terranova.bd import Conexion

    assert URL
    al_salir: list[object] = []
    monkeypatch.setattr(atexit, "register", al_salir.append)
    c = Conexion(URL)
    assert c.ejecutar("SELECT 1")[0] == [(1,)]
    assert al_salir == [c._pool.close]
    c._pool.close()


def test_saldo_en_postgres_sin_sobreconsumo_entre_replicas() -> None:
    """Dos réplicas con su propia conexión reservan a la vez: el UPDATE condicional no deja pasar ni
    un crédito de más (auditoría integral, 2026-10-31: el saldo pasó de Redis a la base)."""
    assert URL
    from terranova.cuota import NIVELES, SaldoSql

    a, b = SaldoSql(URL), SaldoSql(URL)
    org = "org-" + uuid.uuid4().hex[:8]
    limite = NIVELES["con_llave"]

    async def todas() -> list[tuple[bool, int]]:
        return await asyncio.gather(
            *(r.reservar(org, "con_llave", 50) for r in [a, b] * (limite // 50))
        )

    resultados = asyncio.run(todas())
    assert sum(ok for ok, _ in resultados) == limite // 50
    assert asyncio.run(b.usados(org)) == limite
    asyncio.run(a.devolver(org, limite + 10))
    assert asyncio.run(b.usados(org)) == 0
