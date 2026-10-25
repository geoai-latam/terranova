# ADR-0026 · Cobertura de datos abiertos: conector genérico + buscador de catálogo (G6), no un tool por dataset

- **Estado:** aceptada (2026-10-25). Validación: dirección acordada con el dueño el 2026-10-25, tras
  dimensionar el universo real (ver Confirmación).
- **Contexto:**
  - datos.gov.co (Socrata) publica del orden de **miles** de conjuntos (su Discovery API topa en
    10.000 resultados). La pregunta natural es: ¿hacemos **un MCP por cada dataset del Estado**?
  - F5 hoy cura **a mano, ola por ola** contra [FUENTES_OBJETIVO.md](../FUENTES_OBJETIVO.md): una ficha
    de fuente + herramientas + canario por fuente. Eso da calidad, pero no alcanza la **cola larga**.
  - Un **tool por dataset** no funciona:
    - un router LLM no elige entre miles de herramientas; más tools ≠ mejor (se vio el misrouteo entre
      dos hermanas, geo-copilot #82);
    - la mayoría de esos conjuntos son duplicados municipales, desactualizados, de una fila o **sin
      licencia** — exponerlos como «oficiales» rompe [ADR-0019](0019-licencias-por-item-y-by-sa-por-defecto.md)
      y la honestidad de estado;
    - el acceso crudo a un dataset es **commodity**: cualquiera (Croma, Esri) lo autogenera. La ventaja
      del proyecto es **saber qué fuente responde qué**, no conectar más endpoints.
  - Ya existe el conector genérico `datos-abiertos-mcp` (Socrata) que alcanza **cualquier** dataset por
    su id 4x4; lo que falta es **encontrar** el competente entre miles.
- **Decisión:** la cobertura del Estado se da en **tres capas**, no con un tool por dataset.
  1. **Conector genérico (ya existe).** `datos-abiertos-mcp` (Socrata) alcanza cualquier dataset por su
     id. Es el catch-all de la cola larga. Prerrequisito: `$group` en Socrata (pieza **G1**) para que
     sirva agregados; sin eso, un `count`/`sum` cae en la copia (ADR-0024) o no se ofrece.
  2. **Buscador de catálogo (pieza nueva G6).** Se ingiere el **catálogo DCAT** de datos.gov.co como
     DATO (una pasada de metadatos, no carga) y se expone una herramienta `catalogo_buscar`: dada una
     pregunta o un lugar, devuelve los **datasets candidatos competentes** con su **entidad, licencia,
     vigencia e id**, para que el agente los consulte con el conector genérico. Es el moat —«qué fuente
     responde qué»— hecho herramienta; detalle en [specs/09-descubrimiento.md](../specs/09-descubrimiento.md).
  3. **Promoción curada por valor/uso.** Los datasets de alto valor o más consultados se **promueven**
     a herramientas `rt/1` con canario (lo que hoy son las fichas de F5). F5 deja de ser curaduría a
     mano y pasa a **promover desde el catálogo**, ordenado por valor y por uso real del cliente.
  - **Honestidad (no negociable).** El buscador carga y surte **por candidato** el estado de licencia
    ([ADR-0019](0019-licencias-por-item-y-by-sa-por-defecto.md): sin licencia verificada no sale a
    producción; si no se sabe, BY-SA) y la **frescura** (regla 13 de `rt/1`: «Datos no recientes»).
    «Cobertura total» es cobertura **con su bandera de licencia y de frescura**, nunca a ciegas. Nada
    con datos personales se versiona ni se indexa ([ADR-0014](0014-sin-perfiles-de-personas.md)).
- **Alternativas descartadas:**
  - **Un tool MCP por dataset (~10.000).** Ingobernable para el router, commodity, y rompe la compuerta
    de licencia. Es justo lo que el cliente no quiere mantener (láminas 8 y 11 del deck).
  - **Solo curaduría a mano (F5 tal cual, sin G6).** Da calidad pero no cubre la cola larga ni hace la
    selección data-driven; se queda corto frente a «todo el Estado».
  - **Exponer el catálogo entero sin licencia ni frescura.** Viola ADR-0019 y la honestidad; mentiría
    por omisión.
- **Consecuencias:**
  - F5 gana una **pieza genérica G6** (catálogo descubrible + buscador); se suma a G1–G5 en
    [PLAN_EXPANSION.md](../PLAN_EXPANSION.md). La compuerta de F5 ya no es solo «FUENTES_OBJETIVO al
    100 %», sino «catálogo descubrible ingerido + buscador con canario + olas promovidas desde él».
  - La **selección de olas** pasa a ser medible: se promueve por valor y por uso, no por intuición.
  - El buscador hereda la **lista blanca** y la **licencia** de cada fuente; la geometría y los campos
    personales siguen fuera (ADR-0014).
  - `$group` (G1) se vuelve prerrequisito real de la cola larga, no un lujo.
  - Aparece un almacén de **metadatos sobre fuentes** `descubrimiento.datasets` (su **propio** espacio,
    **no** un `copia.*`: una copia es datos en bulk bajo lista blanca, ADR-0024; el catálogo es metadatos
    y no tiene una sola fuente). Se refresca a diario con su fecha, huella y `obsoleto`. La licencia que
    guarda es la **declarada**; «verificada» (ADR-0019) se pone al **promover**, no al ingerir.
- **Confirmación:**
  - **Ingesta:** una pasada del Discovery API de Socrata deja la tabla con, por dataset: entidad/dueño,
    título, descripción, columnas, licencia, frecuencia, última actualización e id 4x4. Métricas de la
    compuerta: nº de datasets, cuántos con **licencia verificable**, cuántos por **entidad competente**,
    cuántos **vivos** (< N meses). Se espera que «lo que decide» sean **unos pocos cientos**.
  - **Buscador:** canario con una verdad medida —«para la pregunta X en el lugar L, la fuente competente
    es el dataset Y de la entidad Z»— y una prueba de que el agente hace **buscador → conector genérico**
    y responde con procedencia, licencia y frescura.
