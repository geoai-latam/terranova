# Catálogo DCAT de datos.gov.co y de la ICDE (`descubrimiento.catalogo_dcat`)

Los metadatos de los conjuntos de datos.gov.co y de las capas del Hub de la ICDE, cosechados a
diario en el servidor y embebidos con e5-large (ADR-0028). No es una fuente de datos: es el índice
para encontrar una. La herramienta es `catalogo_buscar`.

## Qué publica

Por conjunto: id, título, descripción, entidad, categoría, columnas, licencia, fecha de
actualización, vistas, descargas, URL y protocolo (`socrata` o `icde`). Medido el 2026-11-03:
43 732 conjuntos en `descubrimiento.datasets`, todos con vector.

## Cómo busca

- Híbrida: fusiona por rango recíproco (RRF) el parecido de significado (coseno de pgvector, desde
  el piso de 0,84) y la coincidencia de palabras (FTS en español, que exige todas las palabras).
- `parecido` es solo el coseno. Por eso el orden no lo sigue: en «áreas protegidas de un predio»
  el censo de Restrepo (0,861) va antes que «Predios en Sector de Interés Urbanístico» (0,874),
  porque nombra lo que se busca. Ordenar solo por parecido pondría primero el segundo, que no
  responde.
- Antes que los conjuntos, hasta 3 herramientas de Terrnova (`protocolo: terrnova`, sin
  `parecido`) que casen con fuerza por palabras con la pregunta (BM25 desde 7,0).

## Trampas medidas

1. **El índice HNSW perdía resultados.** Con el `ef_search` de 40 por defecto, «buses de
   TransMilenio» contaba 6 conjuntos sobre el piso y devolvía 2. Con 400 devuelve los 6 en ~1 s
   (2026-11-03). La conexión lo fija.
2. **Muchas licencias vacías.** En «áreas protegidas de un predio», 14 de los 20 primeros no
   declaran licencia. Salen como «no declarada: se trata como CC BY-SA 4.0 (ADR-0019)».
3. **La entidad no siempre es la dueña.** Los conjuntos de Bogotá (avalúos por manzana, POT,
   TransMilenio) salen con entidad «Ministerio de Tecnologías de la Información y las
   Comunicaciones»: así los registra el catálogo.
4. **No filtra por lugar.** «Calidad del agua de los ríos de Antioquia» da Corporinoquia, Bogotá y
   Cali: no hay un conjunto de Antioquia sobre el piso. La descripción pide mirar `titulo` y
   `entidad`.
5. **Títulos que no son datos.** Un conjunto de la Gobernación de Boyacá se titula con el nombre de
   una persona (salió en «precio de la vivienda en Bogotá»). Es lo que publica el catálogo.

## Herramientas que lo usan

| Herramienta | Valor | Estado |
|---|---|---|
| `catalogo_buscar` | medio | remite a las herramientas propias, avisa la licencia, no pierde resultados |

## Decisiones

- **2026-11-03, revisión de valor (v2):**
  - Las herramientas propias van primero. El umbral de BM25 se midió en 12 preguntas reales:
    - Aciertos, de 7,8 a 14,1: áreas protegidas, calidad del agua, vuelos, accidentes,
      temperatura, matrícula.
    - Errores, de 4,2 a 6,7: vivienda → población, TransMilenio → peajes, aves, empresas.
    - Dos aciertos quedan por debajo y no se remiten: contratos de Cali (6,9) y población de
      Yopal (5,8).
  - No se usó un umbral por coseno: no se ha medido.
  - El orden de los conjuntos sigue siendo el de RRF. La descripción explica por qué el
    parecido no manda.
  - `hnsw.ef_search = 400` en cada conexión.
  - `coincidencias` cuenta los conjuntos y las herramientas remitidas.
- **Pendiente:**
  - filtrar o avisar por lugar cuando la pregunta nombra uno;
  - un umbral por coseno, medido con el índice vectorizado de la puerta.
