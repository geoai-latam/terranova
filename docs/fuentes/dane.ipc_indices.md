# DANE: índice de precios al consumidor (`dane.ipc_indices`)

El anexo de índices del IPC (`anex-IPC-Indices-<mes><año>.xlsx`, hoja «IndicesIPC»). Términos de
dane.gov.co, verificados el 2026-11-04 (ADR-0039): verde, con la cita textual «Fuente: Departamento
Administrativo Nacional de Estadística: www.dane.gov.co». Terrnova lo **copia** (ADR-0024): el DANE
responde 403 al servidor, y la copia se baja desde Colombia.

| Fuente | Origen | Herramientas |
|---|---|---|
| `dane.ipc_indices` | anexo de índices, serie de empalme | `dane_ipc_indice_anio` |

## Qué publica

El número índice del IPC total nacional (diciembre de 2018 = 100), un mes por fila y un año por
columna, desde enero de 2003. Dos decimales.

La página del IPC enlaza otros tres anexos: variaciones (un .xls con solo la mensual), PAAG (el
porcentaje de ajuste del año gravable, para impuestos) e IPC sin alimentos ni regulados. Ninguno trae
la inflación anual de cada mes en una tabla que sirva.

## Campos que importan

- `Mes`: el nombre en español («Enero»).
- `columna`: el año, tras pasar la tabla ancha a larga.
- `valor`: el índice.
- `variacion_mensual`, `variacion_anual`, `variacion_anio_corrido`: **no vienen en el anexo.** Se
  calculan al copiar, en porcentaje con dos decimales.

## Cobertura

El anexo de septiembre de 2026 se publicó el 7 de octubre. Llega hasta septiembre de 2026.

## Trampas medidas

1. **La pregunta era la inflación y la respuesta, el índice.** La v1 daba 152,27 para diciembre de
   2025 y no se podía sacar la inflación anual: faltaba diciembre de 2024.
2. **Calcular con el índice redondeado puede diferir en una centésima.** Medido el 2026-11-02:
   diciembre de 2021 da 5,62 %, de 2022 13,12 %, de 2023 9,28 % y de 2024 5,20 %, las cifras del
   DANE. Diciembre de 2020 da 1,62 % y el DANE publicó 1,61 %.
3. **2003 no tiene año anterior** en la serie: sus variaciones anuales salen vacías, y la mensual de
   enero también.
4. **Debajo de la tabla vienen notas:** la copia lee hasta la fila 21.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `dane_ipc_indice_anio` | alto | v2: inflación anual, del año corrido y mensual en cada mes; arriba, el último mes |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor:**
  - Las variaciones se calculan al copiar (`copia.variaciones`), no al consultar. La consulta pide
    un año, y la inflación anual necesita el anterior.
  - El almacén de copias publica la vista con `DROP` y `CREATE` en una transacción. `CREATE OR
    REPLACE` no deja sumar columnas, y la primera reconstrucción falló por eso, sin tocar la copia
    vigente.
  - La copia se reconstruyó desde Colombia el 2026-11-02.

## Revisión de valor (2026-11-04)

- 1990 y 2027 volvían `no_encontrado` a secas. Ahora la fuente declara `desde_anio: 2003` y el motor
  dice cuándo un año es futuro, así que los dos salen `fuera_de_cobertura` con su razón.
- El IPM (nacional y departamental) trae el año en número y la nota literal del DANE para los años
  con asterisco (2017*, 2020**, 2021***), leída en los anexos 2025.
