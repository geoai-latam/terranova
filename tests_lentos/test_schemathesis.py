"""F3.5: Schemathesis sobre el OpenAPI publicado por la aplicación completa (con identidad).

Sin 5xx, sin respuestas fuera de esquema (`Sobre` o `Problema`), y sin llave → 401. Entradas válidas
e inválidas generadas. Sin red: el conector falso responde vacío."""

from typing import Any

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.specs.openapi.checks import positive_data_acceptance

from terranova import puerta
from terranova.app import crear_aplicacion
from terranova.identidad import RegistroSql


class Vacio:
    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        return {"geo_result": "1", "artifacts": [], "facts": {}}


class CopiaVacia:
    """El conector interno `copia` (ADR-0024) sin filas, pero con la fecha de la copia."""

    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        hechos = {"servido_desde": "copia", "consultado_en": "2026-10-22T00:00:00+00:00"}
        return {"artifacts": [{"kind": "table", "rows": []}], "facts": hechos}


# un conector falso por cada conector del catálogo: uno nuevo (web-mcp) no puede quedar sin el suyo
VACIOS: dict[str, Any] = {
    f.conector: Vacio() for f in puerta.CATALOGO.fuentes.values() if f.conector != "copia"
} | {"copia": CopiaVacia()}
REGISTRO = RegistroSql(":memory:", "p" * 40)
LLAVE = REGISTRO.crear("schemathesis", {"*"}, prueba=True, expira=None)
# antes de cargar el esquema: el arranque de la app ve conectores inyectados y no busca secretos
puerta.usar_conectores(dict(VACIOS))
puerta.registro = REGISTRO
schema = schemathesis.openapi.from_asgi("/openapi.json", crear_aplicacion())


@schema.auth()
class Llave:
    def get(self, case: Any, ctx: Any) -> str:
        return LLAVE

    def set(self, case: Any, data: str, ctx: Any) -> None:
        case.headers = {**(case.headers or {}), "Authorization": f"Bearer {data}"}


@pytest.fixture(autouse=True)
def sin_red() -> Any:
    puerta.usar_conectores(dict(VACIOS))
    puerta.registro = REGISTRO
    yield
    puerta.registro = None
    puerta.usar_conectores(None)


# las entradas `divipola`: aceptan el código o el nombre (regla 12 de rt/1)
DIVIPOLA = {
    n
    for h in puerta.CATALOGO.herramientas.values()
    for n, t in h.entrada.items()
    if t == "divipola"
}


@schema.parametrize()
@settings(max_examples=25, deadline=None, suppress_health_check=list(HealthCheck))
def test_api(case: Any) -> None:
    # Un bbox con min ≥ max cumple el esquema (4 números) pero no es un rectángulo: «mín < máx» no
    # se puede decir en JSON Schema y la puerta lo rechaza con 400, como debe. Solo para esas
    # herramientas se omite la comprobación de «dato válido aceptado»; las demás siguen.
    # Igual con un municipio por nombre: «uno» cumple el patrón, pero no hay un municipio con ese
    # nombre (o hay varios) y la puerta responde 400 con los candidatos. Con el código no se omite.
    cuerpo = case.body if isinstance(case.body, dict) else {}
    con_bbox = "bbox" in cuerpo
    por_nombre = any(
        k in DIVIPOLA and isinstance(v, str) and not v.isdigit() for k, v in cuerpo.items()
    )
    omitir = con_bbox or por_nombre
    case.call_and_validate(excluded_checks=[positive_data_acceptance] if omitir else [])
