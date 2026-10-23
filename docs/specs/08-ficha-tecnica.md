# Spec 08 · Ficha técnica de la fuente

*2026-10-22.* Antes de usar una fuente, un agente o una persona debe poder saber en segundos:

- qué años cubre;
- si es geográfica y cómo (geometría, CRS, extensión, capas);
- qué significa cada campo y qué valores trae;
- qué es una fila;
- cuándo se actualizó y en qué se equivoca.

La ficha técnica lo junta en un solo lugar. Se cosecha de la propia fuente, no se escribe a mano.
Responder bien depende de conocer la fuente, no de un modelo más grande.

## Por qué

Hoy cada cosa está en un lugar distinto: la licencia en la ficha de la fuente, la capa en la
herramienta, el año en un comentario y el corte en la descripción del servicio. El agente solo ve la
descripción de cada herramienta. Lo medido al cosechar las 77 fuentes el 2026-10-22:

| Fuente | Lo que la ficha técnica deja ver |
|---|---|
| ICFES Saber 11 | declara actualización «semestral», pero sus filas no cambian desde el 2023-08-23 y `periodo` llega a 20224 |
| SUIT, trámites | el «histórico» cubre 2018 a 2021; declara actualización mensual y no cambia desde mayo de 2025 |
| UPRA, precio de la tierra | declara actualización anual; sin cambios desde junio de 2022 |
| SECOP II, cronograma y ejecución | fechas en 2108, 3025 y en el año 0018 |
| IGAC, zonas homogéneas | `VIGENCIA` 1899-12-30, la «fecha cero» de Excel: un vacío disfrazado de fecha |
| IGAC, zonas homogéneas | `VALOR_HECTAREA` viene como texto |
| ICFES | `punt_global` es texto: su «máximo» en la fuente es «99», porque en texto «99» > «500» |
| IDEAM, CUM | fechas como texto (dd/mm/aaaa, mm/dd/aaaa): su mínimo y máximo no son fechas |

## Qué se investigó

- **DCAT 3 / DCAT-AP 3:** título y descripción son obligatorios. Se recomiendan cobertura espacial y
  temporal, publicador, palabras clave, tema y distribución. Son opcionales la frecuencia, las
  fechas de emisión y de modificación, la procedencia y la resolución espacial y temporal.
- **ISO 19115-1, anexo F (NTC 4611 en Colombia):** título, resumen, fecha, contacto, extensión
  geográfica, idioma, categoría, resolución espacial, extensión temporal y linaje.
- **MinTIC, guía de calidad e interoperabilidad (2022):** diccionario de datos, definición de los
  valores codificados, licencia, contacto, frecuencia y fecha de actualización. Su criterio de
  «actualidad» compara las dos últimas.
- **ISO 19157, calidad:** completitud, consistencia lógica, exactitud posicional, temática y temporal.
- **Croissant (MLCommons):** describe los conjuntos para ML por registros (`recordSet`) y campos
  (`field`, `dataType`, `references`). Es la idea de «qué es una fila» del perfil (spec 07).
- **Lo que publican las fuentes:**
  - `/api/views/<id>.json` de datos.gov.co: fechas, frecuencia, cobertura e idioma declarados, y
    columnas con descripción, tipo y estadísticas (nulos, mínimo, máximo y los 20 valores más
    frecuentes).
  - ArcGIS: la capa (geometría, CRS, extensión, campos, dominios, última edición), el servicio (el
    corte suele estar en su descripción) y el ítem de ArcGIS Online (descripción, licencia, fechas).

Lo que no publica ninguna fuente lo pone una persona, en la ficha de la fuente o en el perfil:
contacto, linaje, qué es una fila, los años cuando no hay columna que los diga, y el significado de
los códigos sin dominio.

## Tres capas, sin mezclarlas

| Capa | Dónde | Quién la escribe |
|---|---|---|
| curada | `catalogo/fuentes/<id>.yaml` | una persona: entidad, licencia, lista blanca, cobertura |
| medida | `perfil:` de la misma ficha (spec 07) | una persona con `scripts/perfilar_fuente.py` |
| cosechada | `catalogo/metadatos/<id>.yaml` | `scripts/cosechar_metadatos.py`; no se edita a mano |

Las fuentes sin API de metadatos (BanRep SDMX, relatoría de la ANCP, USGS, Open-Meteo, WorldCover,
FIRMS) llevan su archivo escrito a mano, con `metodo: manual`, y solo con lo medido o documentado.

La **ficha técnica** (`src/terranova/ficha_tecnica.py`) junta las tres y calcula sus alertas:

- **atrasada:** la fuente declara una frecuencia y sus datos no cambian hace más del doble de ese
  plazo (el criterio de «actualidad» de MinTIC);
- **vieja:** el máximo de su columna de tiempo es de hace más de dos años;
- **filas no únicas** (del perfil), **licencia por verificar**, **sin uso comercial** y **datos de
  personas**.

## Qué trae

| Bloque | Contenido | Equivale en DCAT / ISO |
|---|---|---|
| `entidad`, `licencia`, `atribucion` | curado | `dct:publisher`, `dct:license` |
| `acceso` | protocolo, URL, clase, modo (en vivo o copia) | `dcat:accessURL`, `dcat:accessService` |
| `cobertura.periodo` | años que cubre: mínimo y máximo de `cobertura.columna_tiempo`, o texto | `dct:temporal`, extensión temporal |
| `frescura` | caché, actualización esperada y declarada, `datos_actualizados`, `corte` | `dct:accrualPeriodicity`, `dct:modified` |
| `geografia` | geometría, CRS, extensión EPSG:4326, capas, resolución en m | `dct:spatial`, `dcat:spatialResolutionInMeters`, sistema de referencia |
| `campos` | por campo: nombre rt/1, columna, tipo y lo cosechado (tipo en la fuente, descripción, nulos, mínimo, máximo, cómo se comparan, valores frecuentes, códigos) | diccionario de datos, Croissant `field` |
| `perfil` | qué es una fila, clave, operaciones, hallazgos, decisión (spec 07) | linaje, calidad (ISO 19157) |
| `herramientas` | las que la usan | — |
| `alertas` | calculadas | calidad: actualidad, unicidad |
| `metadatos` | origen, página, fechas, idioma, categoría, etiquetas | `dcat:landingPage`, `dct:issued`, `dct:language`, `dcat:keyword` |

## Dónde se sirve

- `GET /v1/fuentes/{id}`: la ficha técnica completa. `GET /v1/fuentes` trae un resumen por fuente,
  con `periodo`, `es_geografica` y `datos_actualizados`.
- MCP `fuente_describir(fuente)`: la misma ficha. Acepta el id de la fuente o de una de sus
  herramientas, y cada herramienta lleva su `fuente` en `meta`.
  - No llama a la fuente, no gasta créditos y no usa LLM (ADR-0012).
  - Las instrucciones del servidor piden usarla antes de responder sobre años, cobertura, unidades
    o códigos.
- `/llms.txt` y `docs/HERRAMIENTAS.md` la describen.

## Reglas

- **Toda fuente tiene ficha técnica**, y las de datos.gov.co y ArcGIS la tienen cosechada
  (`tests/test_catalogo.py`).
- **La ficha técnica solo describe columnas de la lista blanca.** Un campo de fuera rompe el catálogo.
- **No guarda valores de personas.** De una columna que puede traer personas (`documento`, `nit`,
  `nombre`, `proveedor`, `titular`…) no sale ni el mínimo, ni el máximo, ni los valores frecuentes:
  el mínimo de `documento_proveedor` es una cédula y el repo es público (ADR-0014). Una prueba
  revisa todos los archivos.
- **Los valores frecuentes solo describen categorías:** se guardan si los 20 más frecuentes cubren el
  95 % de las filas.
- **Mínimo y máximo dicen cómo se comparan** (`numero`, `fecha` o `texto`). En texto no son rangos:
  la ficha lo dice en vez de esconderlo.
- **El canario de deriva:** `scripts/cosechar_metadatos.py --comprobar` vuelve a cosechar y sale con 1
  si una fuente perdió columnas, cambió un tipo, el corte, las capas o la geometría, o si su fecha de
  actualización retrocedió. Entra al canario diario cuando arranque F7.1. Lo que cambie se revisa y se vuelve
  a perfilar antes de regrabar (spec 07).

## Pendiente

- DANE (CNPV 2018): su conector no consulta por capa numerada; la ficha técnica no trae geometría.
- SECOP: fechas imposibles (2099, 3025, 0018). Se miden en el perfil y se decide si las herramientas
  las filtran.
- Códigos sin dominio en la fuente (usos del suelo, destino económico, clases agrológicas): se
  escriben a mano con su fuente normativa (resoluciones del IGAC).
- Contacto de cada fuente (DCAT `contactPoint`): ninguna lo publica en su API.
