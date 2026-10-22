# ADR-0012 · La puerta no usa LLM

- **Estado:** aceptada (2026-10-21).
- **Decisión:** determinista; sin modelos en la ruta de respuesta. El LLM vive en los clientes
  (GEO Copilot, Claude). Las descripciones de herramientas las redacta la fábrica y las aprueba una
  persona.
- **Consecuencias:** costo marginal bajo, reproducible, agnóstico del modelo.
- **Validación (2026-10-21):** Sin conflictos; la puerta del spike es determinista.
