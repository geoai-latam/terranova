# SIC: sanciones en firme (`sic.sanciones`)

Un conjunto de datos.gov.co, publicado por la Superintendencia de Industria y Comercio con licencia
CC BY-SA 4.0. Se consulta en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `sic.sanciones` | `73dx-n59j` | `sic_sanciones_por_sector` |

## Qué publica

Las sanciones en firme de protección al consumidor: una fila por sancionado en cada resolución, con
radicado, multado, valor en pesos, conducta, sector y fecha de la resolución.

Medido el 2026-11-02: 3 938 filas, del 31 de enero de 2013 al 29 de mayo de 2026.

## Campos que importan

- `fecha_emitida`: la fecha de la resolución. Define el año.
- `radicado`: una resolución puede tener varias filas, una por sancionado, y a veces con fechas
  distintas (el 24 111054 trae filas del 23 y del 26 de enero de 2026).
- `valor`: número, en pesos.
- `sector`: texto libre, con mayúsculas que cambian entre filas.
- `multado`: puede ser una persona natural, así que no sale (ADR-0014).

## Cobertura

Medido el 2026-11-02, último mes con sanciones en cada año:

- **de 2013 a 2025, todos los años llegan a diciembre**. 2020 tiene 10 meses con sanciones;
- **2026 llega a mayo** (93 sancionados).

## Trampas medidas

1. **El mismo sector con dos grafías.** En toda la fuente pasa con «Turismo»/«TURISMO»,
   «Muebles»/«muebles», «Productos Milagro»/«Productos milagro» y «Venta En Almacenes»/«Venta en
   almacenes». En 2024 Turismo salía partido en dos.
2. **Contar filas cuenta sancionados, no resoluciones.** En 2024 hay 327 sancionados en 312
   resoluciones. Una resolución con sancionados de dos sectores cuenta en los dos.
3. **El año en curso parece bajo.** 2026 suma $11 483 913 000 en cinco meses.
4. **Coincidencia que parece error.** En 2026, Muebles y Turismo suman lo mismo ($998 784 360).
   Muebles son tres filas de una resolución; Turismo, 46 sanciones: es casualidad.
5. **SoQL no deja agrupar por `upper(sector)` y llamar `sector` a la columna de salida.** Por eso
   sale como `nombre_sector`, con `min(sector)`, y se renombra.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `sic_sanciones_por_sector` | medio | agrupa sin mayúsculas, de la mayor suma a la menor, con `hasta_mes` y aviso |
| `sic_sanciones_por_empresa` | alto | nueva: sanciones de una empresa por su nombre, solo personas jurídicas |

## Decisiones

- **2026-10-22 (spec 07):** se dan resoluciones (distintas) y sanciones (sancionados) por separado.
- **2026-11-02, error 9 de la revisión de valor (v2):**
  - Se agrupa por `upper(sector)`. 2024 queda en 32 sectores, y Turismo en 73 resoluciones.
  - El orden pasa de alfabético a valor de mayor a menor: la pregunta es dónde se sanciona más.
  - Cada sector dice su último mes; el resultado da `hasta_mes`, `valor_total_anio` y `sectores`,
    y avisa si `hasta_mes` es menor que 12.
  - Aquí no hace falta el `complemento`: el último mes sale del propio agregado.
- **2026-11-03, `sic_sanciones_por_empresa`:**
  - La fuente no trae NIT: se busca por el nombre del sancionado (`multado`), que es texto libre.
  - `multado` puede ser una persona natural (ADR-0014). La consulta exige que el nombre lleve una
    forma jurídica: S.A., S A al final, SAS, LTDA, LIMITADA, E.S.P., Y CIA, S EN C, sociedad,
    corporación, fundación, asociación, cooperativa, compañía, banco o universidad. Así una
    persona natural no sale nunca, aunque se busque su nombre.
  - Medido el 2026-11-03:
    - De 3 254 sancionados distintos, 2 255 llevan forma jurídica y suman 2 885 de las 3 938
      filas. En una muestra de 25 del resto, todos son nombres de 3 a 5 palabras.
    - «GARCIA» y «MARIA» solo dan empresas (una agencia S.A.S. y un centro de estética S.A.S.).
  - Da `resoluciones` (radicados distintos), `valor_total` y `por_sancionado`. Este último hace
    falta porque el texto encuentra a varias: «Falabella» da FALABELLA DE COLOMBIA S A (11),
    FALABELLA.COM S.A.S. (2) y una agencia de viajes (1).
  - Canario: ALMACENES EXITO S.A., 35 sanciones por 5 005 844 444 pesos.
- **Pendiente:** las empresas inscritas sin forma jurídica en el nombre no salen; avisa el vacío.
