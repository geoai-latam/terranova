# ADR-0017 · Lotes y trabajos lentos (M2)

- **Estado:** aceptada (2026-10-21).
- **Decisión:** `_lote` para las herramientas por código (≤ 50 ítems, resultado y error por ítem,
  descuento por ítem); `Prefer: wait=N` → 200 si termina, si no 202 con `status_url`; consultar el estado
  no descuenta. En MCP, la herramienta devuelve el identificador del trabajo y una herramienta
  `estado_trabajo`.
- **Validación (2026-10-21):** Aceptada para M2; no afecta a M1.
