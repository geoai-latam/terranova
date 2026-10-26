# Descubrimiento de datos abiertos y buscador de catálogo (G6)

Pieza genérica de F5 que decide [ADR-0026](../decisions/0026-cobertura-datos-abiertos-buscador-no-tool-por-dataset.md):
la cobertura del Estado se da con **conector genérico + buscador de catálogo + promoción curada**, no
con un tool por dataset. Este spec detalla la ingesta del catálogo, la herramienta `catalogo_buscar`
y la promoción. No cambia el contrato `rt/1` ni el ejecutor; agrega una fuente interna y una
herramienta.

> **Validación al implementar (2026-10-25).** La ingesta (primer código, `descubrimiento.py`) afinó tres
> cosas de este spec: (a) el catálogo es **metadatos sobre fuentes**, no un `copia` de datos (ADR-0024
> es para datos en bulk bajo lista blanca); vive en su **propio almacén** `descubrimiento.datasets`, no
> en `copia.*`. (b) La ingesta solo obtiene la licencia **declarada**; «verificada» (ADR-0019) es un paso
> manual en la **promoción**, no en la ingesta. (c) La pasada completa necesita `scroll` (el offset de
> la Discovery API topa en ~10.000). Medido en una muestra de 2.000: 36 % con licencia declarada, un
> publicador (MinTIC) con ~63 % de la cuenta.

> **Segundo catálogo DCAT (2026-10-25): las capas, no solo las tablas.** El descubrimiento tiene **dos**
> catálogos DCAT, con la **misma** `DatasetDescubrible` y el **mismo** buscador: (1) datos.gov.co
> (Socrata, **tablas**, `protocolo=socrata`) y (2) el **Hub de la ICDE** `datos.icde.gov.co` (ArcGIS Hub,
> **DCAT-US 1.1**, **capas**, `protocolo=arcgis_rest`). `de_dcat_us` interpreta el segundo a la misma
> fila, con la `url` del endpoint **ArcGIS REST** (lo que consume el conector). Es la «G6 para
> geoportales», y **ya es código**, no hipótesis (`ingerir_dcat_us`). Medido: el feed de la ICDE topa en
> ~10.000, **100 % CC BY 4.0 declarada**, ~99 % IGAC, y **~89 % es restitución cartográfica** (mapa base
> troceado), solo ~11 % «Dato temático» — por eso `de_dcat_us` marca la **clase** (`_clase_icde`) y la
> promoción se centra en el resto, no en las 9k primitivas. Detalle y cifras en
> [FUENTES_OBJETIVO.md](../FUENTES_OBJETIVO.md).

## 9.1 Alcance

- **Sí:** ingerir los catálogos DCAT (datos.gov.co de Socrata **y** el Hub DCAT-US de la ICDE) como
  **metadatos**; exponer `catalogo_buscar` que, dada una pregunta o un lugar, devuelve los datasets o
  capas candidatos competentes con entidad, licencia, vigencia e id; un criterio para **promover** a
  herramienta `rt/1`.
- **No:** un tool por dataset; indexar datos personales o geometría de predios (ADR-0014); sacar a
  producción un dataset sin licencia verificada (ADR-0019); reemplazar las fichas curadas de F5 —el
  buscador las **complementa** (la cola larga) y las **alimenta** (qué promover).

## 9.2 La ingesta (metadatos sobre fuentes, no carga)

El catálogo descubrible es **metadatos sobre fuentes** en su **propio almacén** `descubrimiento.datasets`
(no un `copia.*`, que es para datos en bulk bajo lista blanca, ADR-0024): una pasada del Discovery API
de Socrata de datos.gov.co (`https://api.us.socrata.com/api/catalog/v1?domains=www.datos.gov.co`),
paginada, en serie, con `User-Agent` propio, **una vez al día**, nunca por pregunta — con `scroll`
(no solo `offset`, que topa en ~10.000) para la pasada completa. Es el mismo espíritu del canario:
metadatos, no bulk de datos.

Por cada dataset se guarda (lo que ya lee `de_socrata_catalog`):

```yaml
# fila de descubrimiento.datasets, una por dataset
id_socrata: "jbjy-vk9h"                 # el 4x4
titulo: "SECOP II - Contratos Electrónicos"
descripcion: "..."                       # resumen de la fuente
entidad: "Colombia Compra Eficiente"     # attribution / dueño (competencia a confirmar al promover)
categoria: "Gastos Gubernamentales"
columnas: [nombre_entidad, valor_del_contrato, ciudad, ...]   # para casar preguntas con campos
licencia_declarada: "Creative Commons Attribution 4.0"   # lo que DECLARA la fuente; verificar es manual
verificada: false                        # ADR-0019: se pone al promover, no en la ingesta
actualizado_en: "2026-10-24"             # última actualización declarada por la fuente
vistas: 1234                             # señal de uso, para ordenar la promoción
descargas: 56
protocolo: socrata
url: "https://www.datos.gov.co/resource/jbjy-vk9h.json"
promovido_a: "secop_*"                   # herramienta(s) rt/1 si ya está curado; null si no
```

El almacén lleva su fecha, huella y conteos (como una copia, aunque no lo sea). Si pasa su SLA de
refresco, el buscador responde con `obsoleto` y su `consultado_en` original (ADR-0008).

**Métricas de la ingesta (compuerta):** nº total de datasets; cuántos con **licencia declarada**;
cuántos por **entidad**; cuántos **vivos** (`actualizado_en` < N meses); cuántos ya **promovidos**. Se
espera que «lo que decide» sea de unos **pocos cientos** (medido: MinTIC solo acapara ~63 % de la
cuenta; las entidades que deciden tienen decenas cada una).

## 9.3 La herramienta `catalogo_buscar`

Una herramienta `rt/1` de la familia `meta`, con conector interno propio sobre `descubrimiento.datasets`.

```yaml
id: catalogo_buscar
version: 1
familia: meta
fuente: datos_abiertos.catalogo_dcat
pregunta: "¿Qué fuente oficial responde esta pregunta sobre un lugar, y con qué licencia?"
entrada: {consulta: texto, entidad: texto?, lugar: punto?}   # texto libre tipado con patrón (ADR-0012)
consulta:
  operacion: buscar_texto
  resultado: lista
  # casa la consulta contra titulo + descripcion + columnas + entidad (texto completo en español);
  # ordena por señal de valor: ya promovido > con licencia declarada > vivo > uso (vistas/descargas)
salida: CandidatosCatalogo
campos: [id_socrata, titulo, entidad, licencia, actualizado_en, promovido_a, url]
```

**Salida (cada candidato):** `id_socrata`, `titulo`, `entidad`, `licencia` (con su estado), vigencia
(`actualizado_en` + si es `obsoleto`), si está `promovido_a` una herramienta curada, y la `url`. El
agente usa un candidato para consultar con el **conector genérico** `datos-abiertos-mcp` (o salta a la
herramienta curada si `promovido_a` no es null).

**Honestidad por candidato (regla de oro):**

- **Licencia (ADR-0019):** se surte el estado de licencia; un candidato `por_verificar` se marca y
  **no** se presenta como apto para producción (si no se sabe, BY-SA).
- **Frescura (regla 13):** «Datos no recientes» cuando la ficha lo muestre.
- **Personas (ADR-0014):** un dataset con datos personales no entra al índice; nunca se busca por
  cédula ni por nombre de persona.

**El recuperador: híbrido (semántico + léxico), [ADR-0028](../decisions/0028-descubrimiento-con-embeddings.md).**
El buscador recupera por **parecido semántico** (embeddings), así «contaminación del agua» encuentra un
dataset de «vertimientos» aunque no compartan términos; y lo **fusiona por RRF con el léxico** (el FTS en
español del almacén, `ts_rank`, que pondera por IDF). Medido en vivo (2026-10-25, 2000 datasets): el
puro-vectorial mete ruido en el top y falla algunos tipeos; el híbrido mejora la precisión, y el FTS por
IDF evita que las palabras comunes inflen un falso positivo (lo que sí pasó con una frecuencia de
términos cruda). Modelo multilingüe **local y fijado** (`paraphrase-multilingual-MiniLM-L12-v2`, ONNX vía
`fastembed`, extra `terranova[descubrimiento]`); la versión se fija para que el **canario sea
reproducible**. Hay un **piso de similitud** (lo poco parecido no se muestra) y **desempate por valor**
(licencia > vivo), para que la relevancia mande sin pisar la honestidad. **Límite conocido:** los
embeddings devuelven *lo más parecido*, no *«no lo tengo»*; para una pregunta cuya fuente no está en el
catálogo pueden dar un candidato tangencial con confianza media —se mitiga con el piso y surtiendo el
score, pero conviene tenerlo presente. Y cuando **ambas señales coinciden** en un falso positivo (medido:
«contratos del estado» trae un registro cuya descripción habla del «Estado» y de «cumplimiento ordenado
por la Corte»), el híbrido no lo arregla: es **calidad del modelo** (el pequeño `MiniLM` confunde «estado»
el Estado con contenido de gobierno). El modelo es **intercambiable** (`MODELO_EMBEDDING`/`DIM_EMBEDDING`):
en un host con más RAM que el equipo de desarrollo, `intfloat/multilingual-e5-large` (1024-dim, ~2,2 GB)
rankea mejor; se decide al desplegar, midiendo con el banco de verdades. **El piso no distingue el
gibberish con pinta de palabras:** medido con pruebas de usuario humano, «asdkjfh qwerty» puntúa 0,47
(cae en páginas municipales genéricas) y una consulta buena como «cuanto cuesta un remedio» puntúa 0,469
—el coseno absoluto de este modelo no está calibrado, así que ningún piso fijo los separa (subirlo mata
buenas). Mitiga: el **cliente LLM juzga** los candidatos (Terranova es recuperación honesta, no el juez),
y un modelo grande calibra mejor. El gibberish claro sin palabras («xzxzxz 12345», 0,37) sí cae bajo el
piso. **Reconciliación con [ADR-0012](../decisions/0012-la-puerta-no-usa-llm.md):**
los embeddings viven **solo aquí** (sugerir *qué fuente* mirar), **nunca en la ruta del dato** —el
ejecutor, los conectores y el sobre `rt/1` siguen sin modelo y deterministas—. Sin el extra, el buscador
cae al **léxico** (nada se rompe). Las **API de búsqueda de los portales** (Socrata `q=`, ArcGIS Hub
`q=`) son **complemento** de la cola larga, no el recuperador: léxicas, globales y sin nuestras reglas.

**Mantenimiento del índice (ADR-0028): re-embed COMPLETO por pasada**, no incremental. En cada cosecha
diaria se re-embebe **todo** el catálogo (a esta escala —decenas de miles de textos cortos— una pasada
con el modelo pequeño es barata); cambiar de modelo obliga a re-embeder todo (deliberado, canariado). En
desarrollo el índice es un `*.vec.jsonl` al lado del catálogo (`catalogo-dcat ingerir --embeddings`); en
producción, una columna `vector` en `descubrimiento.datasets` (pgvector), parte del mismo aterrizaje en
PostGIS que bloquea el runtime del catálogo. El coseno en memoria es la **lógica de referencia** (dev y
pruebas); la corrida grande va en pgvector, misma cuenta.

## 9.3b Flujo de consumo y economía de contexto (por qué no un tool por dataset)

El argumento central de [ADR-0026](../decisions/0026-cobertura-datos-abiertos-buscador-no-tool-por-dataset.md):
decenas de miles de datasets **no pueden** ser decenas de miles de herramientas. Ya las ~153 curadas
pasan el **tope de 128 de OpenAI** (por eso GEO Copilot usa perfiles por familia). Un tool por dataset
reventaría el contexto del LLM antes de empezar. La puerta **no tiene LLM** (ADR-0012): el catálogo
(los ~20k de Socrata + los ~10k de la ICDE) vive en el almacén `descubrimiento.datasets`, se consulta
por **SQL/texto** y **nunca entra a un prompt**.

Lo que el MCP expone es un conjunto **pequeño y fijo**: (1) las **herramientas curadas** (las fuentes
promovidas, en perfiles ≤128), (2) **una** herramienta de descubrimiento `catalogo_buscar` (familia
`meta`), y (3) **un conector genérico por protocolo** (`datos-abiertos-mcp` para Socrata; el consumo
`arcgis_rest` para las capas de la ICDE). Tres tipos de pieza, no treinta mil.

El consumo es en **dos pasos, como un buscador**:

```
pregunta del usuario
   │  "¿qué me restringe este polígono ambientalmente?"
   ▼
① catalogo_buscar(consulta, lugar?)       ← la puerta casa texto en el ALMACÉN (SQL, vocabulario
   │                                          cerrado, ADR-0012) y devuelve SOLO el top-N (≤20):
   │                                          id · entidad · licencia · vigencia · url · promovido_a
   ▼
② el agente elige UN candidato y:
     ├─ promovido_a ≠ null  → llama la herramienta CURADA (ficha + canario)
     └─ promovido_a = null  → llama el conector GENÉRICO con ese id + params
            · Socrata  → datos-abiertos-mcp(id, $where/$select…)
            · ICDE     → arcgis_rest(url, punto/bbox → features)
   ▼
sobre rt/1 (estado · dato · procedencia · licencia · completitud)
```

El contexto del LLM en todo momento = **la lista fija de herramientas** + **los ≤20 resultados de la
pregunta actual**, nunca el corpus. Es *retrieval*, no *stuffing*: RAG en espíritu pero **determinista**
(coincidencia de texto + orden por valor), sin embeddings y sin LLM en la puerta. Ahí vive la
«libertad» de consultar cualquiera de las miles de fuentes, no en miles de tools ni en SQL libre
escrito por un modelo.

## 9.4 Promoción a herramienta curada

Un dataset del catálogo se **promueve** a una ficha `rt/1` (F5) cuando cumple el umbral de valor:

1. **Licencia verificada** (ADR-0019) — sin esto no sale a producción.
2. **Valor de decisión o uso** — está en FUENTES_OBJETIVO, o lo piden los clientes (señal de uso del
   buscador), o cruza con un lugar (territorio).
3. **Factible** — en vivo, o por copia (ADR-0024) si el agregado/texto no se puede en vivo, o por
   scrape con estado (G4) si es HTML con estado.

La promoción es la **unidad de trabajo de F5** de siempre (ficha + herramientas + mapeo + canario),
pero **ordenada por el buscador**: se promueve por valor y uso medidos, no por intuición. El campo
`promovido_a` cierra el lazo (el buscador deja de ofrecer el crudo cuando ya hay curado).

**La cola de promoción está mecanizada** (`candidatos_a_promover`, `terranova catalogo-dcat promover`):
corre las preguntas del **banco de verdades** sin herramienta (`herramienta: null`, las fuentes
objetivo) por el buscador del almacén y ordena los datasets por **cobertura medida** (en cuántas
preguntas aparecen), luego por licencia y frescura. Así la siguiente ola sale de datos, no de
intuición. La corrida real va contra el almacén desplegado (pgvector + embeddings).

## 9.5 Qué queda fuera y qué comparte

- **Agregados en la cola larga:** dependen de `$group` en Socrata (pieza **G1**). Hasta tenerlo, un
  `count`/`sum` sobre un dataset no promovido cae en copia (ADR-0024) o no se ofrece.
- **Contrato y ejecutor:** sin cambios. `catalogo_buscar` es una herramienta más; su conector interno es
  propio (sobre `descubrimiento.datasets`), con SQL parametrizado y vocabulario cerrado (ADR-0012), como
  el de copia pero sin ser una copia.
- **Superficie:** `catalogo_buscar` sale por REST, MCP y OGC como cualquier herramienta (spec 03).

## 9.6 Compuerta de G6

- **Ingesta** ✅ (#84 Socrata, #91 ICDE, #94 microservicio de embeddings, #95 aterrizaje): la cosecha
  con sus métricas (9.2); funciones puras (`de_socrata_catalog`, `de_dcat_us`) probadas sin red y
  validadas en vivo. El **aterrizaje en PostGIS/pgvector** (`AlmacenDescubrimiento`,
  `descubrimiento.datasets` con columna `vector`, `catalogo-dcat ingerir --a-postgis`) y el
  **microservicio de embeddings** ya están; el job `descubrimiento` del compose refresca los dos
  catálogos a diario. La **pasada completa** también: Socrata con `scroll_id` (no `offset`, que topa
  en ~10.000) e ICDE con `?page=N` hasta que una página no trae ítems nuevos (#98).
- **Buscador (lógica)** ✅ (#86 léxico, #93 embeddings): `buscar` (léxico) casa la pregunta y ordena por
  valor; **`buscar_vectorial`** (semántico, ADR-0028) ordena por coseno con piso y desempate por valor,
  re-embed completo (`embeber_catalogo`), modelo local fijado (`FastEmbedder`); `catalogo-dcat buscar`
  usa vectores si hay índice, si no cae al léxico. Lógica pura probada sin red (embebedor falso). Falta
  la **corrida real con `fastembed`** (extra; modelo se baja una vez) y exponerlo como herramienta
  **`rt/1`** por REST/MCP (conector interno + `modo` en el ejecutor + ficha con **canario reproducible**
  + almacén en runtime con pgvector): es una decisión de **deploy** del catálogo, no solo código.
- **Honestidad:** la lógica ya marca «sin licencia» y no indexa personas; la prueba como herramienta
  `rt/1` va con la exposición.
- **Promoción:** la **cola está mecanizada** (`catalogo-dcat promover`, #99): ordena por cobertura
  medida del banco de verdades. Falta la **primera fuente promovida desde ella** (ficha + canario en
  verde), que va contra el almacén desplegado — la unidad de trabajo de F5, ya data-driven.
