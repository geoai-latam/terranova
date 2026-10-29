# ADR-0033 · Las listas largas salen por páginas de 50; los totales cuentan la lista completa

- **Estado:** aceptada (2026-10-29). Sigue a la [ADR-0032](0032-geometria-completa-bajo-pedido.md)
  y no cambia el contrato `rt/1` ([ADR-0005](0005-contrato-rt-1.md)).
- **Contexto:**
  - Tras la ADR-0032, el banco con un cliente real (`scripts/banco_claude_code.py`, Opus 5.5 desde
    Claude Code) dejó una sola pregunta sobre el tope de Claude Code: t11, con 169 áreas protegidas.
    - El sobre pesaba unos 56 000 caracteres: 37 000 de `datos` y 20 000 de envolventes.
    - Claude Code lo guardó en un archivo y Opus respondió «no pude obtener la cifra».
  - t17 (141 sismos) tropezó igual en su primera llamada, y Opus partió el año en trimestres para
    poder verlos.
    - Los puntos salían con sus atributos repetidos en `properties`: 35 000 caracteres de capa.
  - Lo que el agente necesita casi siempre es el total o el agregado (cuántas, la mayor). Eso ya va
    en `datos`, calculado sobre la lista completa. La lista entera solo hace falta para recorrerla.
- **Decisión:**
  1. **Parámetro común `pagina` (entero desde 1, opcional)** en las herramientas que devuelven una
     lista. Las de un solo elemento no lo tienen, y si llega, se rechaza como cualquier parámetro que
     sobra.
  2. **Si `datos.elementos` pasa de 50**, el sobre lleva solo la página pedida (la primera, si no se
     pide), con sus rasgos en `geo_result`. También lleva un aviso: «van los elementos 1-50 de 169
     (página 1 de 4). Pida `pagina: 2` para los siguientes».
     - Los totales y agregados de `datos` (p. ej. `total`, `total_en_catalogo`, `magnitud_maxima`)
       no cambian: cuentan la lista completa.
     - La `huella` pasa a ser la de lo servido (regla 7), y `entrada.pagina` dice qué página es.
     - Una página que no existe no es un error: llega vacía, con un aviso que dice cuántas hay.
  3. **La fuente, la caché y la idempotencia ven la consulta sin la página**: pedir la página 2 no
     vuelve a la fuente si la lista está en caché.
  4. **Igual en MCP y en REST** (ADR-0004): se pagina en `puerta.ejecutar`, antes de resumir la
     geometría.
  5. **Los puntos también apuntan a su elemento:** la ADR-0032 dejaba las `properties` completas en
     los puntos. Ahora van como `{"elemento": i}` (su posición en la página de `datos`), con la
     geometría entera. Con `geometria: true` todo va como antes.
- **Resultado medido:** ver `docs/ESTADO.md` (banco con cliente real tras el despliegue).
- **Consecuencias:**
  - **Cambio visible para REST:** quien leía la lista entera de una vez debe seguir las páginas.
    Hoy no hay clientes de pago (ADR-0020). Queda en la guía para clientes.
  - El tamaño de una respuesta de lista queda acotado: 50 elementos y sus envolventes, unos 15 000 a
    20 000 caracteres, bajo el tope de los clientes MCP.
  - 50 es un compromiso: cabe en el tope con elementos de 20 atributos, y la mayoría de las listas
    del catálogo (por municipio, por entidad) ya son más cortas y no cambian.
