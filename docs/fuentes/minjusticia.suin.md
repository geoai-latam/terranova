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

## Cobertura

Es lo que SUIN tiene cargado, no todo lo que se expidió. De los decretos y las resoluciones carga
una parte. SUIN sigue cargando, así que los conteos de un año crecen.

## Trampas medidas

1. **«Vigentes» se queda corto en los años recientes.** En 2025, 954 de 1 320 normas no tienen dato
   de vigencia, y solo 313 dicen «Vigente».
2. **El conteo no explicaba nada.** Iba en orden alfabético por tipo, sin decir cuántas siguen
   vigentes.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `suin_norma` | alto | pendiente: `articulos` repite `articulos_n` como texto; lenta (6-14 s) |
| `suin_normas_anio` | bajo → medio | v2: del tipo con más normas al de menos, con `vigentes` y `sin_dato_vigencia` por tipo y en total |

## Decisiones

- **2026-11-03, patrón F de la revisión de valor:**
  - `suin_normas_anio` no se retira: la verdad de producto n06 pide ese conteo.
  - No se convierte en una lista de normas: sin epígrafe, la lista dice poco. Para una norma
    concreta está `suin_norma`.
  - La v2 cuenta `vigencia = 'Vigente'` y `vigencia = 'NULL'` con `sum(case(...))`.
