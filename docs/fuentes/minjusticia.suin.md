# MinJusticia: SUIN-Juriscol (`minjusticia.suin`)

Las normas cargadas en el Sistema Único de Información Normativa (SUIN-Juriscol) del Ministerio de
Justicia. Están en datos.gov.co (`fiev-nid6`), con licencia CC BY-SA 4.0, y se consultan en vivo.

## Qué publica

Una fila por norma:

- tipo, en mayúsculas y sin tildes (LEY, DECRETO, RESOLUCION…);
- número, año y subtipo;
- vigencia según SUIN;
- entidad, sector y materias separadas por «|»;
- número de artículos, como texto.

No trae el epígrafe ni el texto.

## Campos que importan

- `vigencia` viene como «NULL» cuando SUIN no ha estudiado la norma. Medido el 2026-11-03 en toda
  la fuente:

  | Vigencia | Normas |
  |---|---|
  | Vigente | 72 214 |
  | Derogado | 7 777 |
  | NULL | 7 529 |
  | Compilado | 1 279 |

- `materia` es «NULL» en la mayoría de las leyes recientes: 85 de las 120 de 2025.
- `subtipo` es «NULL» si no tiene.
- Medido el 2026-11-03 en las 89 366 normas, el texto «NULL» aparece en:

  | Campo | Normas con «NULL» |
  |---|---|
  | `materia` | 73 311 |
  | `subtipo` | 11 878 |
  | `sector` | 5 239 |
  | `entidad` | 2 404 |
  | `art_culos` | 2 173 (el único valor no numérico) |

  La Ley 2294 de 2023 (Plan Nacional de Desarrollo) sale sin entidad.

## Cobertura

Es lo que SUIN tiene cargado, no todo lo que se expidió. De los decretos y las resoluciones carga
una parte. SUIN sigue cargando, así que los conteos de un año crecen.

## Trampas medidas

1. **«Vigentes» se queda corto en los años recientes.** En 2025, 954 de 1 320 normas no tienen dato
   de vigencia, y solo 313 dicen «Vigente».
2. **El conteo no explicaba nada.** Iba en orden alfabético por tipo, sin decir cuántas siguen
   vigentes.
3. **El tipo va sin tildes** (medido el 2026-11-05). Ninguno de los 21 valores de `tipo` lleva
   tilde: RESOLUCION (8 491), CONSTITUCION POLITICA, INSTRUCCION ADMINISTRATIVA CONJUNTA… Quien
   pedía «Resolución» 142 de 1991 recibía «no encontrado», aunque SUIN la tiene (Superintendencia
   de Industria y Comercio, 14 artículos).
4. **El número es texto y no siempre es un número** (2026-11-05). La Constitución de 1991 tiene
   `n_mero` «CP», y hay resoluciones de 1991 con «3-1766» y «mar-20». `suin_norma` pide el número
   como entero: esas no se pueden pedir. Sin medir cuántas son.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `suin_norma` | alto | v2: `articulos` como número, los «NULL» vacíos y aviso de vacío; el tipo con tilde o sin ella |
| `suin_normas_anio` | bajo → medio | v2: del tipo con más normas al de menos, con `vigentes` y `sin_dato_vigencia` por tipo y en total |

## Decisiones

- **2026-11-03, patrón F de la revisión de valor:**
  - `suin_normas_anio` no se retira: la verdad de producto n06 pide ese conteo.
  - No se convierte en una lista de normas: sin epígrafe, la lista dice poco. Para una norma
    concreta está `suin_norma`.
  - La v2 cuenta `vigencia = 'Vigente'` y `vigencia = 'NULL'` con `sum(case(...))`.
- **2026-11-03, `suin_norma` v2 (revisión de valor):**
  - **Artículos:** `articulos` sale como número y se quita `articulos_n`, que lo repetía como
    texto.
  - **Vacíos:** los «NULL» de `subtipo`, `vigencia`, `entidad`, `sector`, `materia` y `art_culos`
    salen vacíos (`vacios`). La descripción dice que una vigencia vacía es que SUIN no la ha
    estudiado.
  - **Aviso:** el vacío avisa que SUIN carga solo una parte de los decretos y las resoluciones.
  - **Latencia:** la fuente respondía en menos de 1 s en frío. En producción, la herramienta tardó
    de 1,5 a 2,5 s con cinco normas, no los 6-14 s de la revisión.
- **2026-11-05, el tipo con tilde (revisión de valor):** la consulta compara con `{tipo:ascii}`:
  «Resolución» llega a la fuente como «Resolucion» y la comparación ya no distingue mayúsculas.
  Medido con el conector desplegado: «Resolución» 142 de 1991 da la de la SIC; antes, «no
  encontrado». La descripción y el aviso de vacío ya no piden escribir sin tildes.
