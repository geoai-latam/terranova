# ADR-0004 · Un núcleo, dos adaptadores

- **Estado:** aceptada (2026-10-21).
- **Decisión:** cada herramienta es una función del núcleo con entrada y salida Pydantic. El
  adaptador REST (FastAPI) y el MCP (FastMCP) se **generan** a partir del catálogo y llaman a la
  misma función; el esquema OpenAPI de la respuesta y el `outputSchema` MCP salen del mismo modelo.
- **Alternativas:** generar MCP desde FastAPI (las herramientas quedan con forma de endpoint, peor
  para agentes según la propia documentación de FastMCP); dos códigos (deriva segura).
- **Confirmación:** prueba de paridad en CI: cada herramienta MCP tiene su `operationId`, los
  esquemas son iguales y la misma entrada da el mismo sobre por las dos puertas.
- **Validación (2026-10-21):** Acorde con F0.3: `outputSchema` ya sale del modelo Pydantic de retorno. La paridad REST ≡ MCP se mide en F3.
