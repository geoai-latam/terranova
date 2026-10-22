# ADR-0003 · Versión del protocolo y librerías

- **Estado:** propuesta.
- **Decisión:** la puerta usa **FastMCP 4.1.x fijado** (negocia 2025-11-25 y 2026-07-28, para que
  funcione con clientes viejos y nuevos). Los conectores siguen en `mcp` 1.28 mientras sean internos;
  su migración es un trabajo aparte después de M1.
- **Confirmación (spike F0):** (1) Claude Code y MCP Inspector se conectan a la puerta y listan y
  llaman herramientas; (2) el cliente FastMCP 4 de la puerta llama a un conector en 1.28 sin error;
  (3) `outputSchema` + `structuredContent` se validan en el cliente.
