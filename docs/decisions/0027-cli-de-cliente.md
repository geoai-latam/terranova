# ADR-0027 · CLI de cliente: un cliente delgado del REST `/v1`, con `catalogo buscar` y `verificar <archivo>`

- **Estado:** aceptada (2026-10-25). Validación: las seis decisiones de abajo se confirmaron con el
  dueño el 2026-10-25, sobre el informe de investigación del CLI.
- **Contexto:**
  - El `terranova` CLI de hoy es **100 % admin/ops** (`llaves`, `orgs`, `canarios`, `copias`, y
    levantar la puerta). **Quien pregunta no tiene terminal:** solo MCP, o REST a mano.
  - El deck vende el acceso por «MCP, API, OGC API o archivos» (lámina 6) y el caso EUDR (láminas
    15–18) es, literalmente, **un batch sobre un archivo de lugares**. Un CLI de cliente es el canal
    que falta para el **script, el cron y el CI del cliente**.
  - La puerta **ya expone el REST `/v1`** que un CLI necesita (`POST /v1/co/{familia}/{herramienta}`,
    `/v1/herramientas`, `/v1/fuentes`, `/v1/uso`, con llave `Bearer`). El CLI es un **cliente** de eso,
    no lógica nueva.
- **Decisión:** un CLI de **cliente**, delgado sobre el REST, con seis decisiones zanjadas.
  1. **Un binario, dos mundos separados por import.** Mismo nombre `terranova`:
     `consultar / catalogo / exportar / verificar / uso / fuentes / herramientas` son **cliente** (solo
     hablan REST); `llaves / orgs / canarios / copias / serve` son **admin** (cargan el núcleo). Extras
     de instalación: `terranova[cliente]` **no** arrastra FastAPI ni PostGIS.
  2. **Lenguaje: Typer (Python) ahora.** Reusa `contrato.py` (modelos `rt/1`) y es consistente con el
     repo. Un binario único en Go es más vendible (cero deps), pero es un segundo lenguaje: se deja
     **para cuando el canal CLI tenga tracción o un cliente lo pida** (igual que ArcGIS/QGIS).
  3. **Dónde vive:** mismo repo, módulo `src/terranova/cliente/`; instalación aparte por extra.
  4. **Cómo habla: cliente delgado del REST `/v1` con la llave.** Nunca embebido — el cliente no tiene
     las fuentes ni la base, y así respeta **cuota, scopes y auditoría** como cualquier cliente. El CLI
     es, de hecho, la **prueba viva de que el REST basta**: si un comando no se puede hacer solo con
     REST, el hueco está en el REST, no en el CLI.
  5. **Alcance de `verificar <archivo>` (el batch EUDR):** «**cruza y entrega expediente**» —GeoJSON
     validado + Excel por lugar + expediente firmado (láminas 15–18)—, **sin** revisión humana ni
     campo; eso es la capa de Automatización. Acotarlo evita que `verificar` se trague medio producto.
  6. **Exit codes (para `set -e` en CI):** `0` si `encontrado`; `0` si `no_encontrado` (el aviso va a
     stderr); **≠0 solo cuando «no se pudo»** (fuente caída, 4xx/5xx, error). Coherente con la regla del
     proyecto «no encontrado ≠ no se pudo».
  - **Honestidad.** Salida por defecto legible con **estado `rt/1`, procedencia y licencia**; `--json`
    para el sobre crudo; `catalogo buscar` es el **front de terminal de G6** (ADR-0026).
- **Alternativas descartadas:**
  - **Dos binarios separados desde el inicio.** Sobre-ingeniería; basta separar por import y por extra.
  - **CLI embebido (con las fuentes/BD dentro).** El cliente no las tiene; saltaría cuota, scopes y
    auditoría, y duplicaría la puerta.
  - **Go desde el MVP.** Segundo lenguaje sin tracción que lo justifique.
  - **Lógica de negocio en el CLI.** Duplicaría el REST y abriría superficie de bug; el CLI formatea,
    no decide.
- **Consecuencias:**
  - El CLI **valida la completitud del REST**: cada comando = una ruta `/v1` + formateo.
  - **Depende de G6** (ADR-0026) para `catalogo buscar`; del REST `/v1` (ya existe) para el resto.
  - Se suma el extra `terranova[cliente]` y el módulo `cliente/`; `03-superficie.md` gana la sección
    **8.4 CLI** (hoy solo documenta REST, MCP y ficha). Detalle en [spec 10](../specs/10-cli.md).
  - Es un **canal de cliente** (junto con la API con cuota, OGC API y archivos que el deck promete a
    «60 d»), apoyado en G6 y en el REST; no abre una fase nueva por sí solo.
- **Confirmación:**
  - Prueba **sin red**: cada comando contra un REST mockeado (ruta correcta, formateo del sobre,
    `--json`), y los **exit codes** en un `set -e`.
  - `verificar` sobre un CSV pequeño de lugares (el caso EUDR acotado) deja GeoJSON validado + Excel +
    expediente.
  - `catalogo buscar "<pregunta>"` llama a G6 y devuelve candidatos con entidad, licencia e id.
