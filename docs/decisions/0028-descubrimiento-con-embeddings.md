# ADR-0028 · Descubrimiento del catálogo con embeddings (buscador semántico), reconciliado con ADR-0012

- **Estado:** aceptada (2026-10-25). Validación: dirección del dueño («de cabeza con los embeddings, no
  incremental; me ha funcionado en otros proyectos») + lógica probada sin red (ver Confirmación).
- **Contexto:**
  - El buscador de G6 ([spec 09](../specs/09-descubrimiento.md), [ADR-0026](0026-cobertura-datos-abiertos-buscador-no-tool-por-dataset.md))
    casaba **texto** (subcadena de todas las palabras). Es determinista pero tiene **desajuste de
    vocabulario**: «contaminación del agua» **no** encuentra un dataset de «vertimientos» o «calidad
    hídrica» si no comparten palabras. El agente pregunta en muchas formas; el léxico se queda corto.
  - Los propios portales DCAT traen **API de búsqueda** (`q=` de la Discovery API de Socrata; `q=` /
    `/api/search/v1` del ArcGIS Hub). Son útiles, pero **léxicas**, **globales** (la del Hub indexa todo
    ArcGIS del mundo —ruido—) y **no llevan nuestras reglas** (licencia, frescura, clase, sin personas).
    Sirven de complemento para la cola larga, **no** como el recuperador del moat.
  - Tensión real: un embedding es un **modelo**. [ADR-0012](0012-la-puerta-no-usa-llm.md) dice que la
    puerta **no usa LLM** y que la lógica sale del catálogo, no de código suelto. Hay que reconciliarlo
    sin traicionar la honestidad ni el **canario reproducible**.
- **Decisión:** `catalogo_buscar` recupera por **embeddings** (buscador **semántico**), con estas reglas:
  1. **Modelo local y fijado.** `paraphrase-multilingual-MiniLM-L12-v2` (multilingüe, español; ONNX en CPU vía
     `fastembed`, sin torch; local, offline y **gratis** —coherente con el proyecto y con la poca
     memoria del equipo). La **versión se fija** (`MODELO_EMBEDDING`): el canario es reproducible.
     Instalable con el extra `terranova[descubrimiento]`; el núcleo no lo arrastra.
  2. **Re-embed COMPLETO por pasada** (no incremental). En cada cosecha diaria se re-embebe **todo** el
     catálogo. Es más simple y robusto que llevar diffs por huella; a la escala del catálogo (decenas de
     miles de textos cortos) una pasada con el modelo pequeño es barata. Cambiar de modelo = re-embeder
     todo (deliberado, canariado).
  3. **Orden:** por **parecido semántico** (coseno) con un **piso de similitud** (lo poco parecido no se
     muestra); dentro de un mismo nivel de parecido, **desempata por valor** (licencia > vivo). Así la
     relevancia manda pero la honestidad no se pisa.
  4. **Reconciliación con ADR-0012 (no negociable).** Los embeddings viven **solo en el descubrimiento**
     —sugerir *qué fuente* mirar—, **nunca en la ruta del dato**. El ejecutor, los conectores y el sobre
     `rt/1` siguen **sin modelo** y deterministas: la **respuesta** sale de la fuente, no de un vector.
     Un modelo ordena *sugerencias*; jamás *decide el dato*. Se preserva el fin de ADR-0012 (dato
     auditable, sin LLM generando respuestas).
  5. **APIs de los portales = complemento**, no núcleo: para la cola larga aún no ingerida, como
     generación de candidatos de respaldo, siempre pasando por nuestras reglas de licencia/frescura.
- **Alternativas descartadas:**
  - **Solo léxico (buscador actual).** Determinista y simple, pero el desajuste de vocabulario deja
    fuera la fuente competente. Queda como **respaldo** (sin el extra, o con `--entidad`).
  - **Las API de búsqueda de los portales como recuperador principal.** Léxicas, globales y sin nuestras
    reglas; la del Hub es ruido mundial. No son el moat.
  - **Embeddings por API hosted (OpenAI u otro).** Costo por consulta, dependencia externa y privacidad;
    rompe «offline y gratis». El modelo local pequeño basta.
  - **Re-embed incremental por huella.** Más eficiente en teoría, pero añade contabilidad de diffs y
    estado; el dueño pidió explícitamente la pasada completa, que ya es barata a esta escala.
  - **Embeddings en la ruta del dato (RAG que redacta la respuesta).** Rompe ADR-0012 y la honestidad:
    el dato debe salir de la fuente, no de un modelo.
- **Runtime (decidido con el dueño, 2026-10-25):**
  - **Almacén: PostGIS + `pgvector`** (Q1). El catálogo y los vectores viven en `descubrimiento.datasets`
    (columna `vector(384)`), compartido entre las dos réplicas y refrescado por el job de ingesta. La
    imagen Postgres (hoy `postgis`) necesita la extensión `pgvector` (se añade en su Dockerfile).
  - **El modelo corre en un MICROSERVICIO aparte** (Q2), no dentro de la puerta: un contenedor
    `embeddings` (`fastembed`, modelo horneado en la imagen) en la red interna, que la puerta y el job
    llaman por HTTP (`EmbedderRemoto`). Así el modelo no se duplica en cada réplica (memoria) y la
    puerta no carga onnxruntime. `terranova embeddings-servicio` lo sirve.
  - **Yo construyo el código y la config; el dueño despliega** (Q3): no se baja el modelo ni se
    levantan contenedores en esta máquina (prioridad de memoria a sus procesos de video).
- **Modelo (medido el 2026-10-25):** el nombre que se fijó primero (`intfloat/multilingual-e5-small`)
  **no está en el registro de `fastembed`** (solo el `-large`). Se usa
  **`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`**: multilingüe, **dim 384**, ~0,22 GB,
  ONNX. Es **simétrico** (no e5): la consulta y los documentos se embeben igual, **sin** prefijos
  `query:`/`passage:`. El `PISO_SIMILITUD` quedó en **0,30** (la escala de coseno de este modelo, no la
  de e5); se afina con el banco de verdades. La reproducibilidad exacta de los scores depende de la
  versión de `fastembed` (una versión nueva cambió el pooling a *mean*); el canario, al ser un mínimo
  (≥1 candidato), es robusto a ese cambio.
- **Consecuencias:**
  - Extra nuevo `descubrimiento` (`fastembed` + `uvicorn`). El buscador: embeddings si hay índice de
    vectores y el servicio responde; si no, cae al **léxico** (nada se rompe sin el extra/servicio).
  - Aparece un **índice de vectores** por catálogo: en desarrollo, un `*.vec.jsonl` al lado del JSONL
    (`catalogo-dcat ingerir --embeddings`); en producción, una columna `vector` en
    `descubrimiento.datasets` (pgvector) —parte del mismo aterrizaje en PostGIS que ya bloquea el
    runtime del catálogo—. El coseno en memoria es la **lógica de referencia** (dev y pruebas); la
    corrida grande va en pgvector, misma cuenta.
  - El **canario de G6** fija la versión del modelo y afirma una verdad medida (una pregunta devuelve el
    dataset esperado en el top-K). Reproducible mientras el modelo no cambie.
  - El **piso de similitud** se afina con el banco de verdades (no se clava a ciegas).
- **Confirmación:**
  - **Lógica pura sin red** (`texto_para_embedding`, `_coseno`, `buscar_vectorial`, `embeber_catalogo`,
    `vectores_a_jsonl`/`cargar_vectores`), probada con un **embebedor falso** determinista: la consulta
    sobre «agua» trae el dataset de agua y no los ortogonales; el empate lo rompe la licencia; el índice
    redondea por JSONL.
  - **Corrida real con `fastembed`** ✅ (2026-10-25, en la máquina de desarrollo): se instaló el extra,
    se cosechó una muestra de 300 datasets de datos.gov.co y se embebió con el modelo real;
    `catalogo-dcat buscar "contaminación del agua"` trajo —por significado, sin compartir palabras—
    datasets de hidrología, inundación, humedales y corredores ambientales (IDEAM, POT). Destapó el
    nombre de modelo inválido, los prefijos e5 de más, el piso en escala e5, y dos bugs del CLI en
    Windows (consola cp1252 y el glob que agarraba el índice de vectores), ya corregidos. No se corre
    en CI por memoria/descarga del modelo.
  - **Canario** con verdad medida y modelo fijado, y la prueba de que el agente hace **buscar →
    conector genérico** con procedencia, licencia y frescura (va con la exposición `rt/1`, spec 09 §9.6).
