# Descubrimiento de datos abiertos y buscador de catálogo (G6)

Pieza genérica de F5 que decide [ADR-0026](../decisions/0026-cobertura-datos-abiertos-buscador-no-tool-por-dataset.md):
la cobertura del Estado se da con **conector genérico + buscador de catálogo + promoción curada**, no
con un tool por dataset. Este spec detalla la ingesta del catálogo, la herramienta `catalogo_buscar`
y la promoción. No cambia el contrato `rt/1` ni el ejecutor; agrega una fuente interna y una
herramienta.

## 9.1 Alcance

- **Sí:** ingerir el catálogo DCAT de datos.gov.co como dato; exponer `catalogo_buscar` que, dada una
  pregunta o un lugar, devuelve los datasets candidatos competentes con entidad, licencia, vigencia e
  id; un criterio para **promover** un dataset a herramienta `rt/1`.
- **No:** un tool por dataset; indexar datos personales o geometría de predios (ADR-0014); sacar a
  producción un dataset sin licencia verificada (ADR-0019); reemplazar las fichas curadas de F5 —el
  buscador las **complementa** (la cola larga) y las **alimenta** (qué promover).

## 9.2 La ingesta (una copia de metadatos, no carga)

El catálogo descubrible es una **copia** (ADR-0024) de **metadatos**, no de datos: una pasada del
Discovery API de Socrata de datos.gov.co (`/api/catalog/v1`), paginada, en serie, con `User-Agent`
propio, **una vez al día**, nunca por pregunta. Es el mismo espíritu del canario: metadatos, no bulk
de datos.

Por cada dataset se guarda:

```yaml
# fila de copia.catalogo_dcat (o catalogo/descubribles), una por dataset
id_socrata: "jbjy-vk9h"                 # el 4x4
titulo: "SECOP II - Contratos Electrónicos"
descripcion: "..."                       # resumen de la fuente
entidad: "Colombia Compra Eficiente"     # dueño/publisher (competencia a confirmar)
categoria: "Gastos Gubernamentales"
columnas: [nombre_entidad, valor_del_contrato, ciudad, ...]   # para casar preguntas con campos
licencia: {spdx: CC-BY-SA-4.0, verificada: null}   # por ítem (ADR-0019); null = por verificar
frecuencia: "diaria"                     # accrualPeriodicity declarada
actualizado_en: "2026-10-25"             # última actualización declarada por la fuente
filas: 30500694                          # tamaño declarado, si lo expone
protocolo: socrata
url: "https://www.datos.gov.co/resource/jbjy-vk9h.json"
promovido_a: "secop_*"                   # herramienta(s) rt/1 si ya está curado; null si no
```

El manifiesto de la copia (`copia.versiones`) lleva fecha, huella y conteos. Si la copia pasa su
`sla_actualizacion`, el buscador responde con `obsoleto` y su `consultado_en` original (ADR-0008).

**Métricas de la ingesta (compuerta de la ingesta):** nº total de datasets; cuántos con **licencia
verificable**; cuántos por **entidad**; cuántos **vivos** (`actualizado_en` < N meses); cuántos ya
**promovidos**. Se espera que «lo que decide» sea de unos **pocos cientos**.

## 9.3 La herramienta `catalogo_buscar`

Una herramienta `rt/1` de la familia `meta` (o `territorio`), con conector interno sobre la copia.

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
  # ordena por señal de valor: ya promovido > licencia verificada > vivo > tamaño/uso
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

## 9.5 Qué queda fuera y qué comparte

- **Agregados en la cola larga:** dependen de `$group` en Socrata (pieza **G1**). Hasta tenerlo, un
  `count`/`sum` sobre un dataset no promovido cae en copia (ADR-0024) o no se ofrece.
- **Contrato y ejecutor:** sin cambios. `catalogo_buscar` es una herramienta más; su conector interno
  es análogo al de copia (ADR-0024), con SQL parametrizado y vocabulario cerrado (ADR-0012).
- **Superficie:** `catalogo_buscar` sale por REST, MCP y OGC como cualquier herramienta (spec 03).

## 9.6 Compuerta de G6

- **Ingesta:** el catálogo DCAT ingerido con sus métricas (9.2), refrescado a diario como una copia,
  con huella y `obsoleto`.
- **Buscador:** `catalogo_buscar` con **canario de verdad medida** —«para la pregunta X en el lugar L,
  la fuente competente es el dataset Y de la entidad Z»— y prueba de que el agente hace **buscador →
  conector genérico** y responde con procedencia, licencia y frescura.
- **Honestidad:** una prueba de que un candidato sin licencia verificada sale marcado y no como apto, y
  de que ningún dataset con datos personales entra al índice.
- **Promoción:** al menos una fuente de la cola larga **promovida desde el buscador** (no desde
  FUENTES_OBJETIVO a mano), con su ficha y canario en verde.
