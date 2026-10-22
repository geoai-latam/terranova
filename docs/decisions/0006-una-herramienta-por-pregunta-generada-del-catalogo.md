# ADR-0006 · Una herramienta por pregunta, generada del catálogo

- **Estado:** aceptada (2026-10-21).
- **Contexto:** los servicios comerciales de datos de gobierno exponen una herramienta por pregunta y les funciona; el diseño previo
  (7 operaciones genéricas con `fuente=`) obliga al agente a conocer los identificadores. Con 150
  herramientas, cargar todas en un cliente cuesta contexto.
- **Decisión:** (1) herramientas por pregunta con nombre `fuente_objeto[_en_punto|_buscar|_lote]` y
  descripción con cobertura y cierre «(Fuente: X; licencia: Y.)», **generadas desde el catálogo**;
  (2) rutas REST 1:1 `/v1/co/<fuente>/<pregunta>`; (3) **perfiles MCP** montados por familia
  (`/mcp/territorio`, `/mcp/contratacion`, `/mcp/empresas`, `/mcp/normativa`, `/mcp/justicia`,
  `/mcp/estadisticas`, `/mcp/ambiente`) y `/mcp` con todo; (4) además, operaciones geográficas
  genéricas para cualquier capa del catálogo (`capa_en_punto`, `capa_en_zona`) y `ficha_lugar`;
  (5) `buscar_herramientas` para descubrir sin cargar todo.
- **Confirmación:** banco de agente ([specs/04-pruebas.md](../specs/04-pruebas.md)): tasa de herramienta correcta ≥ 90 % con `/mcp` completo y
  con un perfil.
- **Validación (2026-10-21):** Sin alternativa mejor medida. La confirmación (≥ 90 % de herramienta correcta) queda para el banco de agente, antes de M1.
