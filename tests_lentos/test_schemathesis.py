"""F3.5: Schemathesis sobre el OpenAPI publicado. Sin 5xx y sin violar el esquema de respuesta
(`Sobre` o `Problema`), con entradas válidas e inválidas generadas. Sin red: el conector falso
responde vacío."""

from typing import Any

import pytest
import schemathesis
from hypothesis import HealthCheck, settings
from schemathesis.specs.openapi.checks import positive_data_acceptance

from terranova import puerta
from terranova.app import crear_api


class Vacio:
    async def llamar(self, herramienta: str, argumentos: dict[str, Any]) -> dict[str, Any]:
        return {"geo_result": "1", "artifacts": [], "facts": {}}


VACIOS = {
    n: Vacio()
    for n in ("arcgis-mcp", "datos-abiertos-mcp", "dane-mcp", "amenazas-mcp", "imagery-mcp")
}
schema = schemathesis.openapi.from_asgi("/openapi.json", crear_api())


@pytest.fixture(autouse=True)
def sin_red(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("TERRANOVA_PLAN", "evaluacion")
    puerta.usar_conectores(dict(VACIOS))
    yield
    puerta.usar_conectores(None)


@schema.parametrize()
@settings(max_examples=25, deadline=None, suppress_health_check=list(HealthCheck))
def test_api(case: Any) -> None:
    # Un bbox con min ≥ max cumple el esquema (4 números) pero no es un rectángulo: «mín < máx» no
    # se puede decir en JSON Schema y la puerta lo rechaza con 400, como debe. Solo para esas
    # herramientas se omite la comprobación de «dato válido aceptado»; las demás siguen.
    excluidas = (
        [positive_data_acceptance] if isinstance(case.body, dict) and "bbox" in case.body else []
    )
    case.call_and_validate(excluded_checks=excluidas)
