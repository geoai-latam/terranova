# ADR-0031 · MCP a escala: herramientas tipadas, perfiles por familia y perfil «catálogo» (enmienda la ADR-0006)

- **Estado:** aceptada (2026-10-28). Enmienda la [ADR-0006](0006-una-herramienta-por-pregunta-generada-del-catalogo.md)
  y cierra su confirmación. Validación: banco de escala medido (abajo), con LLM real.
- **Contexto:**
  - `/mcp` completo ya expone 209 herramientas. Su `tools/list` pesa 1,4 MB (el 83 % es
    `outputSchema`), y nombre, descripción y entrada suman ~64 000 tokens. Un perfil por familia pesa
    entre ~5 000 y ~16 000 tokens.
  - Lo publicado y lo que hacen otros proveedores (2026):
    - Con una lista plana, la elección de herramienta empeora a partir de unas decenas de
      herramientas, y antes en los modelos chicos.
    - Buscar herramientas recorta del 85 al 99 % de los tokens. Los enrutadores genéricos tienen
      evidencia mixta: GitHub quitó sus *toolsets* dinámicos, y Stainless y Pipedream volvieron atrás.
    - Los proveedores de estadística (Data Commons, World Bank Data360, US Census) convergen en 4 a 6
      herramientas guiadas por catálogo.
  - Los clientes no se comportan igual:
    - Buscan herramientas por su cuenta: Claude, VS Code ≥ 1.118, Cursor y la Responses API de
      OpenAI (`tool_search`).
    - No buscan, o tienen tope: ChatGPT, Windsurf (100), n8n, Zapier, LangChain y Copilot Studio.
  - La spec MCP 2026-07-28 es sin estado: `tools/list` no puede variar por conexión, así que un perfil
    se elige por URL.
  - La ADR-0006 dejó pendiente su confirmación: ≥ 90 % de herramienta correcta con `/mcp` completo y
    con un perfil.
- **Experimento (banco de escala, `scripts/banco_mcp_escala.py`, 2026-10-28):**
  - **Método:**
    - Las 60 preguntas del banco de verdades (`catalogo/verdades_producto.yaml`), en seis familias.
    - Modelo `gpt-5.4-mini` en la Responses API, contra el MCP desplegado en `terrnova.com`, una
      pregunta a la vez.
    - Cinco escenarios:
      - **plano:** las 209 herramientas como funciones;
      - **búsqueda:** `tool_search` alojado, con todas diferidas en un *namespace*;
      - **búsqueda por familias:** un *namespace* por familia;
      - **perfil:** `/mcp/<familia>` de la familia de la pregunta;
      - **catálogo:** `/mcp/catalogo`, que es `buscar_herramienta` → `consultar` más los resolvedores
        de códigos.
  - **Corrección del evaluador:** el banco comparaba la entrada al pie de la letra. Contaba como falla
    pasar `municipio_divipola: "Chía, Cundinamarca"`, aunque la puerta lo resuelve a 25175 y
    responde. Las 53 llamadas así respondieron bien, salvo 3 al geoportal caído del DANE. El evaluador
    ahora resuelve el nombre como la puerta (`_entrada_comparable`). La tabla da las dos cifras.

  | Escenario | Éxito (corregido) | Éxito (literal) | Herramienta correcta | Tokens por pregunta | Segundos |
  |---|---|---|---|---|---|
  | plano (209) | 82 % | 60 % | 93 % | 94 923 | 19,9 |
  | búsqueda (`tool_search`) | 70 % | 53 % | 82 % | 8 996 | 11,8 |
  | búsqueda por familias | 72 % | 53 % | 82 % | 8 872 | 12,4 |
  | **perfil por familia** | **87 %** | 75 % | **98 %** | 22 488 | **9,8** |
  | catálogo | 72 % | 65 % | 77 % | 11 004 | 11,0 |

  - **Lectura crítica:**
    - El perfil supone que el cliente eligió bien la familia, porque el banco le dio la de la
      pregunta. Mide el techo de un cliente configurado para su dominio, no el de un agente generalista.
    - Con n = 60, una diferencia de 5 puntos son 3 preguntas: la ventaja del perfil sobre búsqueda y
      catálogo (15 puntos) es real; la de plano sobre búsqueda, también.
    - Búsqueda gasta 10 veces menos tokens que plano, pero el mini carga la herramienta equivocada más
      a menudo: elige mal la hermana o no carga la específica.
    - Catálogo gana en estadísticas (7 de 10, el mejor) y pierde en territorio (8 de 22). Su buscador
      pone `ficha_lugar` arriba en preguntas de un punto (t11–t15), y el agente la usa en vez de la
      capa específica. El fallo es del buscador, no del patrón, y tiene arreglo.
    - Las fallas comunes a todos los escenarios no dependen del modelo de exposición:
      - `sinic_predio_en_punto` frente a `igac_predio_en_punto` (descripciones hermanas);
      - el `bbox` de las preguntas de zona (t16, t17);
      - `upra_rangos_precio_municipio` frente a `upra_precio_tierra_rural_municipio`.
- **Decisión:**
  1. **Se mantienen las herramientas tipadas por pregunta, generadas del catálogo** (ADR-0006 §1–2).
     Todos los escenarios las usan por debajo; el catálogo solo cambia cómo se descubren.
  2. **Los perfiles por familia son la vía recomendada** cuando el caso de uso tiene dominio conocido
     (`/mcp/contratacion`, `/mcp/territorio`…). Son el mejor escenario en éxito, herramienta correcta
     y tiempo, con un cuarto de los tokens de `/mcp`.
  3. **`/mcp` completo sigue** para los clientes que buscan herramientas por su cuenta y para quien
     quiere todo en una URL. Funciona (93 % de herramienta correcta) pero es caro en contexto. La guía
     para clientes lo dice.
  4. **`/mcp/catalogo` queda como perfil beta** para los clientes con tope o sin búsqueda (ChatGPT,
     Windsurf, n8n…) y para preguntas que cruzan familias. Sale de beta cuando el banco lo lleve
     a ≥ 85 % de éxito; antes hay que corregir el ranking de `ficha_lugar`.
  5. **No se adopta:** modo código, `tools/list_changed`, *toolsets* dinámicos por sesión ni un
     enrutador con LLM en la puerta (ADR-0012).
  6. **Confirmación de la ADR-0006: cumplida.** La herramienta correcta da 93 % con `/mcp` completo y
     98 % con un perfil (≥ 90 %).
- **Consecuencias:**
  - El banco de escala queda como prueba de regresión del modo de exposición. Se corre con el modelo
    mini al cambiar descripciones, perfiles o el buscador, y se revisa pregunta por pregunta.
  - Arreglos que salen del banco (en `docs/ESTADO.md`, hallazgos abiertos):
    1. el ranking de `ficha_lugar` en el buscador del catálogo;
    2. la desambiguación de las descripciones hermanas (SINIC/IGAC, UPRA);
    3. el agente rellena `codigo` de `ficha_lugar` con ceros junto a `lon`/`lat`;
    4. `fuente_describir` recibe ids con punto (`dane.poblacion_municipio`) o nombres de familia.
  - Si el catálogo crece mucho más, la siguiente palanca es partir familias grandes en subperfiles,
    no aplanar.
