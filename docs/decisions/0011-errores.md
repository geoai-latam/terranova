# ADR-0011 · Errores

- **Estado:** aceptada (2026-10-21).
- **Decisión:** REST `application/problem+json` (RFC 9457) con extensiones `code`, `fuente_id`,
  `reintentar_en_s`, `solicitud_id`; MCP `isError: true` con el mismo objeto en `structuredContent`.
  Catálogo de códigos en [specs/01-contrato-rt1.md](../specs/01-contrato-rt1.md). Error de una parte de la ficha ≠ error de la ficha (estado `parcial`).
- **Validación (2026-10-21):** Sin conflictos; el spike ya distingue el fallo (error) del no encontrado (sobre). Los códigos estables se implementan en F1.3 y F2.
