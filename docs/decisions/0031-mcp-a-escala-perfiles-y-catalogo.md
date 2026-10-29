# ADR-0031 · MCP a escala: herramientas tipadas, perfiles por familia y perfil «catálogo» (enmienda la ADR-0006)

- **Estado:** aceptada (2026-10-28; regla de escala, 2026-10-29). Enmienda la [ADR-0006](0006-una-herramienta-por-pregunta-generada-del-catalogo.md)
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
    - Catálogo gana en estadísticas (7 de 10, el mejor) y pierde en territorio (8 de 22): el agente
      usa `ficha_lugar` en vez de la capa específica en las preguntas de un punto (t11–t15). La
      causa de fondo salió en la segunda corrida (abajo).
    - Las fallas comunes a todos los escenarios no dependen del modelo de exposición:
      - `sinic_predio_en_punto` frente a `igac_predio_en_punto` (descripciones hermanas);
      - el `bbox` de las preguntas de zona (t16, t17);
      - `upra_rangos_precio_municipio` frente a `upra_precio_tierra_rural_municipio`.
- **Curva de tamaño (segunda corrida, 2026-10-29, con los arreglos de #186):**
  - **Método:** el mismo banco y el mismo modelo, con el perfil de cada pregunta rellenado con
    herramientas de otras familias hasta 90 y 140 (orden fijo por hash, `perfil+N`). Se compara con el
    perfil solo (de 14 a 47 herramientas, 35 de media) y con plano (209). t20 queda fuera porque la
    fuente del DANE se agotó en todos los escenarios: quedan 59 preguntas.

  | Herramientas visibles | Éxito | Herramienta correcta | Tokens de entrada por pregunta | Segundos |
  |---|---|---|---|---|
  | perfil (35 de media) | 49 de 59 | 95 % | 22 728 | 8,2 |
  | 90 | 50 de 59 | 97 % | 49 064 | 13,5 |
  | 140 | 50 de 59 | 93 % | 74 321 | 13,5 |
  | 209 (plano) | 49 de 59 | 93 % | 104 813 | 15,6 |
  | catálogo (6) | 44 de 59 | 83 % | 10 558 | 9,4 |

  - **Lectura crítica:**
    - **La precisión no cae con el tamaño** hasta 209 con este modelo y este banco: de 49 a 50
      aciertos en los cuatro tamaños. Entre corridas, la misma configuración varía unas 3 preguntas
      (el perfil dio 87 % en la primera y 82 % en esta), así que esas diferencias son ruido.
    - **Lo que crece es el costo:** unos 470 tokens de entrada por herramienta visible y pregunta, y
      casi el doble de tiempo de 35 a 209.
    - Las fallas que quedan son las mismas en todos los tamaños:
      - t02, entre `igac_registro_predio` y `igac_predio_por_codigo`;
      - el `bbox` de t16 y t17;
      - la entrada de t18 y t19 (sismos y lluvia de una estación);
      - s09.
      Son ambigüedades de la verdad o de la entrada, no del modo de exposición.
    - **El catálogo** sigue en 83 % de herramienta correcta. Su causa de fondo: el mapa de familias
      de `buscar_herramienta` decía que territorio cubre áreas protegidas, pero esas herramientas,
      resguardos, cobertura y sismos son de `ambiente`. El agente filtraba por «territorio» y el
      filtro le ocultaba la herramienta, y respondía «no hay herramienta» (t10, t11, t13) o usaba una
      vecina (t12, t15, t18). Arreglo: el mapa sale corregido y el filtro por familia ya no oculta el
      mejor resultado sin filtro (va primero). El recall del buscador sin filtro ya era 97 % entre
      los 6 primeros.
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
  7. **Regla de escala** (de la curva):
     - **Un perfil se parte por costo y por los topes de los clientes, no por precisión.**
     - Tope: **≤ 90 herramientas** por perfil. Es el tamaño medido sin pérdida, a unos 50 000 tokens
       por pregunta, y queda bajo los topes de Windsurf (100) y VS Code (128).
     - Una familia que pase de 90 se parte en subperfiles por tema (p. ej. `territorio` en catastro y
       ordenamiento), nunca por orden alfabético.
     - Hoy la familia más grande tiene 44 herramientas: hay margen para doblar el catálogo sin
       partir nada.
     - `/mcp` completo no tiene tope: sirve a quien acepta el costo. Su precio crece lineal con el
       catálogo, unos 470 tokens por herramienta y pregunta.
     - El catálogo cuesta lo mismo con cualquier tamaño (~11 000 tokens). Es la salida cuando el
       total ya no cabe en un cliente, siempre que su buscador conserve el recall.
- **Consecuencias:**
  - El banco de escala queda como prueba de regresión del modo de exposición. Se corre con el modelo
    mini al cambiar descripciones, perfiles o el buscador, y se revisa pregunta por pregunta.
  - Arreglos que salieron del banco:
    1. el ranking de `ficha_lugar` en el buscador del catálogo (#186);
    2. la desambiguación SINIC/IGAC (#186); la de UPRA sigue abierta;
    3. el agente rellenaba `codigo` de `ficha_lugar` con ceros junto a `lon`/`lat` (#186);
    4. `fuente_describir` recibía ids con punto o nombres de familia (#186);
    5. el mapa de familias del catálogo y el filtro que ocultaba la mejor herramienta (segunda
       corrida).
  - El catálogo sale de beta cuando una corrida con el arreglo 5 lo lleve a ≥ 85 % de éxito.
  - Si el catálogo crece, la palanca es la regla de escala (§7): partir familias grandes en
    subperfiles, no aplanar.
