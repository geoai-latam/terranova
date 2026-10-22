"""Copias de fuentes abiertas en PostGIS (G3, ADR-0024).

Tres piezas, de la más pura a la que toca la red y la base:

- `plan_de_consulta`: arma el SQL parametrizado de `consultar_copia` con un vocabulario cerrado.
  Los nombres de columna salen del catálogo (la lista blanca) y los valores de la entrada van como
  parámetros, nunca dentro del texto (ADR-0012).
- `descargar_socrata` y `AlmacenCopias`: el job diario. Baja la ventana de la fuente (solo la lista
  blanca, ordenada por la clave), la guarda en una tabla nueva `copia.<tabla>_<version>` y mueve la
  vista `copia.<tabla>` a esa versión de una vez. El manifiesto queda en `copia.versiones`.
- `ConectorCopia`: el conector interno `copia` que usa la puerta. Responde como un conector MCP,
  con `servido_desde` y `consultado_en` de la copia, y `obsoleto` si pasó su SLA (ADR-0008).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from terranova.catalogo import Catalogo, Fuente

ESQUEMA = "copia"
PAGINA = 50_000
MAX_LIMITE = 1_000
AGREGADOS = {"count", "sum", "avg", "median", "min", "max"}
_ALIAS = re.compile(r"^[a-z][a-z0-9_]{0,40}$")
_TIPO_SQL = {
    "str": "text",
    "int": "bigint",
    "float": "double precision",
    "bool": "boolean",
    "date": "date",
    "datetime": "timestamptz",
}


class ErrorCopia(ValueError):
    """La consulta pide algo fuera del vocabulario o de la lista blanca: error de la ficha."""


# --- plan de consulta (sin red ni base) ------------------------------------------------------


@dataclass(frozen=True)
class Plan:
    sql: str
    parametros: tuple[Any, ...]
    sql_total: str | None  # cuántas filas cumplen, para la completitud (None con agregados)
    parametros_total: tuple[Any, ...]
    limite: int


def _columna(nombre: str, permitidas: set[str]) -> str:
    if nombre not in permitidas:
        raise ErrorCopia(f"«{nombre}» no está en la lista blanca de la copia")
    return f'"{nombre}"'


def _agregado(alias: str, expresion: str, permitidas: set[str]) -> str:
    if not _ALIAS.match(alias):
        raise ErrorCopia(f"alias inválido: «{alias}»")
    funcion, _, columna = expresion.partition(":")
    if funcion not in AGREGADOS:
        raise ErrorCopia(f"agregado desconocido: «{funcion}» (se puede {sorted(AGREGADOS)})")
    if funcion == "count" and not columna:
        return f'count(*) AS "{alias}"'
    col = _columna(columna, permitidas)
    if funcion == "median":
        return f'percentile_cont(0.5) WITHIN GROUP (ORDER BY {col}) AS "{alias}"'
    return f'{funcion}({col}) AS "{alias}"'


def plan_de_consulta(fuente: Fuente, argumentos: dict[str, Any]) -> Plan:
    """El SQL de `consultar_copia`.

    `argumentos` (de la ficha, ya con la entrada puesta): `select` (columnas), `filtros`
    ({columna: valor}, igualdad), `texto` (búsqueda en las columnas `copia.texto`), `agregados`
    ({alias: "count" | "sum:col" | "median:col" …}), `group` (columnas), `order` (columnas; con
    `-` delante, descendente) y `limite`.
    """
    if fuente.copia is None:
        raise ErrorCopia(f"{fuente.id} no tiene copia")
    permitidas = set(fuente.campos)
    vista = f'{ESQUEMA}."{fuente.copia.tabla}"'
    group = [_columna(c, permitidas) for c in argumentos.get("group") or []]
    agregados = [
        _agregado(a, e, permitidas) for a, e in (argumentos.get("agregados") or {}).items()
    ]
    columnas = [_columna(c, permitidas) for c in argumentos.get("select") or []]
    if agregados and (sueltas := set(columnas) - set(group)):
        raise ErrorCopia(f"con agregados, las columnas van en `group`: {sorted(sueltas)}")
    seleccion = ", ".join([*(columnas or ([] if agregados else ["*"])), *agregados])

    condiciones, parametros = [], []
    for columna, valor in (argumentos.get("filtros") or {}).items():
        condiciones.append(f"{_columna(columna, permitidas)} = %s")
        parametros.append(valor)
    if (texto := argumentos.get("texto")) is not None:
        if not fuente.copia.texto:
            raise ErrorCopia(f"{fuente.id} no tiene columnas de texto en su copia")
        condiciones.append("_texto @@ plainto_tsquery('spanish', %s)")
        parametros.append(str(texto))
    donde = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""

    orden = []
    for c in argumentos.get("order") or []:
        desc = c.startswith("-")
        nombre = c.lstrip("-")
        expr = f'"{nombre}"' if agregados and _ALIAS.match(nombre) else _columna(nombre, permitidas)
        orden.append(f"{expr} {'DESC' if desc else 'ASC'} NULLS LAST")
    limite = max(1, min(int(argumentos.get("limite") or MAX_LIMITE), MAX_LIMITE))

    sql = f"SELECT {seleccion} FROM {vista}{donde}"
    if group:
        sql += f" GROUP BY {', '.join(group)}"
    if orden:
        sql += f" ORDER BY {', '.join(orden)}"
    sql += " LIMIT %s"
    sql_total = None if agregados else f"SELECT count(*) FROM {vista}{donde}"
    return Plan(sql, (*parametros, limite), sql_total, tuple(parametros), limite)


# --- el job: descarga y almacén --------------------------------------------------------------


def _valor_socrata(valor: Any) -> Any:
    if isinstance(valor, dict) and "url" in valor:  # las URL vienen como {url: …}
        return valor["url"]
    return valor


def descargar_socrata(
    fuente: Fuente, desde: date | None = None, *, cliente: Any = None
) -> Iterator[list[dict[str, Any]]]:
    """Páginas de la ventana de la fuente: solo la lista blanca, ordenadas por la clave."""
    import httpx

    assert fuente.copia is not None
    copia = fuente.copia
    columnas = list(fuente.campos)
    params: dict[str, Any] = {"$select": ", ".join(columnas), "$order": f"{copia.clave}"}
    inicio = desde or (copia.ventana.desde if copia.ventana else None)
    if copia.ventana and inicio:
        params["$where"] = f"{copia.ventana.columna} >= '{inicio.isoformat()}'"
    url = f"https://www.datos.gov.co/resource/{copia.conjunto}.json"
    propio = cliente is None
    http = cliente or httpx.Client(timeout=180, headers={"User-Agent": "terranova-copias/1"})
    try:
        desplazamiento = 0
        while True:
            pagina = _pedir(http, url, {**params, "$limit": PAGINA, "$offset": desplazamiento})
            if not pagina:
                return
            yield [{c: _valor_socrata(f.get(c)) for c in columnas} for f in pagina]
            if len(pagina) < PAGINA:
                return
            desplazamiento += len(pagina)
    finally:
        if propio:
            http.close()


def _pedir(http: Any, url: str, params: dict[str, Any], intentos: int = 3) -> list[dict[str, Any]]:
    import time

    for intento in range(1, intentos + 1):
        try:
            r = http.get(url, params=params)
            r.raise_for_status()
            datos: list[dict[str, Any]] = r.json()
            return datos
        except Exception:
            if intento == intentos:
                raise
            time.sleep(10 * intento)  # cortesía con la fuente: no se insiste de inmediato
    return []


def _convertir(valor: Any, tipo: str) -> Any:
    if valor in (None, ""):
        return None
    try:
        if tipo == "int":
            return int(float(valor))
        if tipo == "float":
            return float(valor)
        if tipo == "bool":
            return str(valor).strip().lower() in ("true", "1", "si", "sí")
        if tipo in ("date", "datetime"):
            texto = str(valor)
            return texto[:10] if tipo == "date" else texto
    except (TypeError, ValueError):
        return None
    return str(valor)


@dataclass(frozen=True)
class Version:
    fuente_id: str
    tabla: str
    version: str
    filas: int
    huella: str
    ventana_desde: date | None
    actualizada_en: datetime
    repetidas: int = 0  # filas con una clave ya vista: la fuente no garantiza claves únicas


class AlmacenCopias:
    """Versiones de las copias en PostGIS: tabla nueva por corrida, vista vigente y manifiesto."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._conexion: Any = None

    @property
    def _c(self) -> Any:
        """La conexión, abierta al primer uso: la puerta arranca aunque la base no esté."""
        if self._conexion is None:
            import importlib

            psycopg: Any = importlib.import_module("psycopg")  # extra opcional `postgres`
            self._conexion = psycopg.connect(self._url, autocommit=True)
        return self._conexion

    def _asegurar_esquema(self) -> None:
        self._c.execute(f"CREATE SCHEMA IF NOT EXISTS {ESQUEMA}")
        self._c.execute(
            f"""CREATE TABLE IF NOT EXISTS {ESQUEMA}.versiones (
                fuente_id text NOT NULL, tabla text NOT NULL, version text NOT NULL,
                filas bigint NOT NULL, huella text NOT NULL, ventana_desde date,
                actualizada_en timestamptz NOT NULL, vigente boolean NOT NULL DEFAULT false,
                repetidas bigint NOT NULL DEFAULT 0, PRIMARY KEY (tabla, version))"""
        )

    def construir(
        self, fuente: Fuente, paginas: Iterator[list[dict[str, Any]]], desde: date | None
    ) -> Version:
        """Carga las páginas en una tabla nueva y, si todo salió bien, la vuelve la vigente."""
        assert fuente.copia is not None
        self._asegurar_esquema()
        copia = fuente.copia
        ahora = datetime.now(UTC)
        version = ahora.strftime("%Y%m%d%H%M%S%f")  # dos corridas en el mismo segundo no chocan
        fisica = f'{ESQUEMA}."{copia.tabla}_{version}"'
        tipos = {c: _TIPO_SQL[campo.tipo] for c, campo in fuente.campos.items()}
        definicion = ", ".join(f'"{c}" {t}' for c, t in tipos.items())
        texto = " || ' ' || ".join(f"coalesce(\"{c}\", '')" for c in copia.texto)
        generada = (
            f", _texto tsvector GENERATED ALWAYS AS (to_tsvector('spanish', {texto})) STORED"
            if copia.texto
            else ""
        )
        self._c.execute(f"CREATE TABLE {fisica} ({definicion}{generada})")
        resumen = hashlib.sha256()
        filas = repetidas = 0
        anterior: Any = object()
        columnas = list(tipos)
        lista = ", ".join(f'"{c}"' for c in columnas)
        with self._c.cursor() as cur, cur.copy(f"COPY {fisica} ({lista}) FROM STDIN") as cp:
            for pagina in paginas:
                for fila in pagina:
                    if fila.get(copia.clave) == anterior:  # ordenadas: la repetida es contigua
                        repetidas += 1
                        continue
                    anterior = fila.get(copia.clave)
                    valores = [_convertir(fila.get(c), fuente.campos[c].tipo) for c in columnas]
                    cp.write_row(valores)
                    resumen.update(json.dumps(valores, default=str).encode())
                    filas += 1
        self._c.execute(f'ALTER TABLE {fisica} ADD PRIMARY KEY ("{copia.clave}")')
        for col in copia.indices:
            self._c.execute(f'CREATE INDEX ON {fisica} ("{col}")')
        if copia.texto:
            self._c.execute(f"CREATE INDEX ON {fisica} USING gin (_texto)")
        v = Version(
            fuente.id,
            copia.tabla,
            version,
            filas,
            f"sha256:{resumen.hexdigest()}",
            desde,
            ahora,
            repetidas,
        )
        self._publicar(v, fisica)
        return v

    def _publicar(self, v: Version, fisica: str) -> None:
        """La vista pasa a la versión nueva y el manifiesto la marca vigente, en una transacción."""
        with self._c.transaction():
            self._c.execute(
                f'CREATE OR REPLACE VIEW {ESQUEMA}."{v.tabla}" AS SELECT * FROM {fisica}'
            )
            self._c.execute(
                f"UPDATE {ESQUEMA}.versiones SET vigente = false WHERE tabla = %s", (v.tabla,)
            )
            self._c.execute(
                f"""INSERT INTO {ESQUEMA}.versiones (fuente_id, tabla, version, filas, huella,
                    ventana_desde, actualizada_en, repetidas, vigente)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, true)""",
                (
                    v.fuente_id,
                    v.tabla,
                    v.version,
                    v.filas,
                    v.huella,
                    v.ventana_desde,
                    v.actualizada_en,
                    v.repetidas,
                ),
            )

    def podar(self, tabla: str, conservar: int = 2) -> list[str]:
        """Borra las versiones viejas (se conservan la vigente y la anterior, para volver atrás)."""
        filas = self._c.execute(
            f"SELECT version FROM {ESQUEMA}.versiones WHERE tabla = %s ORDER BY version DESC",
            (tabla,),
        ).fetchall()
        borradas = []
        for (version,) in filas[conservar:]:
            self._c.execute(f'DROP TABLE IF EXISTS {ESQUEMA}."{tabla}_{version}"')
            self._c.execute(
                f"DELETE FROM {ESQUEMA}.versiones WHERE tabla = %s AND version = %s",
                (tabla, version),
            )
            borradas.append(version)
        return borradas

    def vigente(self, tabla: str) -> Version | None:
        existe = self._c.execute(f"SELECT to_regclass('{ESQUEMA}.versiones')").fetchone()
        if not existe or existe[0] is None:
            return None
        fila = self._c.execute(
            f"""SELECT fuente_id, tabla, version, filas, huella, ventana_desde, actualizada_en,
                repetidas FROM {ESQUEMA}.versiones WHERE tabla = %s AND vigente""",
            (tabla,),
        ).fetchone()
        return Version(*fila) if fila else None

    def consultar(self, plan: Plan) -> tuple[list[dict[str, Any]], int | None]:
        cur = self._c.execute(plan.sql, plan.parametros)
        nombres = [d.name for d in cur.description or []]
        filas = [dict(zip(nombres, f, strict=True)) for f in cur.fetchall()]
        total = None
        if plan.sql_total is not None:
            conteo = self._c.execute(plan.sql_total, plan.parametros_total).fetchone()
            total = int(conteo[0]) if conteo else None
        return filas, total


# --- el conector `copia` -----------------------------------------------------------------------


def _completitud(vistos: int, total: int | None, limite: int) -> dict[str, Any]:
    """Cuántas vinieron de cuántas cumplen. Con agregados no hay total aparte: si los grupos
    llegaron al límite, puede haber más."""
    if total is not None:
        return {"vistos": vistos, "total": total, "truncado": vistos < total}
    cortado = vistos >= limite
    return {"vistos": vistos, "total": None if cortado else vistos, "truncado": cortado}


def duracion(iso: str) -> timedelta:
    """Una duración ISO 8601 sencilla (P1D, PT6H, P1M ≈ 31 días, P1Y ≈ 366 días)."""
    m = re.fullmatch(
        r"P(?:(\d+)Y)?(?:(\d+)M)?(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?", iso
    )
    if not m:
        raise ValueError(f"duración no soportada: {iso}")
    y, mes, sem, d, h, minutos = (int(x or 0) for x in m.groups())
    return timedelta(days=366 * y + 31 * mes + 7 * sem + d, hours=h, minutes=minutos)


def _a_json(valor: Any) -> Any:
    if isinstance(valor, datetime | date):
        return valor.isoformat()
    return valor


class ConectorCopia:
    """El conector interno `copia` (ADR-0024): misma interfaz que los conectores MCP."""

    def __init__(self, catalogo: Catalogo, almacen: AlmacenCopias) -> None:
        self._por_tabla = {f.copia.tabla: f for f in catalogo.fuentes.values() if f.copia}
        self._almacen = almacen

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        from terranova.conector import ErrorConector

        if herramienta != "consultar_copia":
            raise ErrorConector(f"el conector copia no tiene «{herramienta}»", "error_interno")
        fuente = self._por_tabla.get(str(argumentos.get("tabla")))
        if fuente is None:
            raise ErrorConector(f"no hay copia «{argumentos.get('tabla')}»", "error_interno")
        try:
            plan = plan_de_consulta(fuente, argumentos)
        except ErrorCopia as exc:
            raise ErrorConector(str(exc), "error_interno") from exc
        try:
            version, (filas, total) = await asyncio.to_thread(self._leer, fuente, plan)
        except Exception as exc:  # la base de las copias caída es una fuente caída
            raise ErrorConector(f"copia: {type(exc).__name__}", "fuente_no_disponible") from exc
        if version is None:
            raise ErrorConector(
                f"la copia de {fuente.id} no está construida", "fuente_no_disponible"
            )
        vencida = datetime.now(UTC) - version.actualizada_en > duracion(
            fuente.frescura.sla_actualizacion
        )
        hechos = {
            "servido_desde": "obsoleto" if vencida else "copia",
            "consultado_en": version.actualizada_en.isoformat(),
            "copia": {
                "version": version.version,
                "huella": version.huella,
                "filas": version.filas,
                "repetidas_en_la_fuente": version.repetidas,
                "ventana_desde": _a_json(version.ventana_desde),
            },
            "completitud": _completitud(len(filas), total, plan.limite),
        }
        filas_json = [{k: _a_json(v) for k, v in f.items()} for f in filas]
        columnas = sorted({k for f in filas_json for k in f})
        return {
            "artifacts": [{"kind": "table", "columns": columnas, "rows": filas_json}],
            "facts": hechos,
        }

    def _leer(
        self, fuente: Fuente, plan: Plan
    ) -> tuple[Version | None, tuple[list[dict[str, Any]], int | None]]:
        assert fuente.copia is not None
        version = self._almacen.vigente(fuente.copia.tabla)
        if version is None:
            return None, ([], None)
        return version, self._almacen.consultar(plan)


def conector_desde_entorno(catalogo: Catalogo) -> ConectorCopia | None:
    """El conector `copia` si hay base (`TERRANOVA_COPIAS_URL` o, si no, la del curado)."""
    import os

    url = os.environ.get("TERRANOVA_COPIAS_URL") or os.environ.get("TERRANOVA_CURADO_URL")
    return ConectorCopia(catalogo, AlmacenCopias(url)) if url else None
