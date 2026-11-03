# Colombia Compra: multas y sanciones de SECOP I y SECOP II (`cce.secop1.multas`, `cce.secop2.sanciones`)

Las multas, cláusulas penales y otras sanciones que las entidades imponen a sus contratistas. Colombia
Compra las publica en dos conjuntos de datos.gov.co, uno por sistema, con licencia CC BY-SA 4.0. Se
consultan en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `cce.secop1.multas` | `4n4q-k399` | `secop1_multas_municipio` |
| `cce.secop2.sanciones` | `it5q-hg94` | `secop_multas_entidad`, `secop_sanciones_contrato` |

## Qué publica

- **SECOP I:** entidad con su NIT, municipio, resolución, contrato, contratista con su documento,
  valor, y las fechas de firmeza y de publicación. Tiene 1 716 multas; la más reciente es de
  septiembre de 2026.
- **SECOP II:** contrato (CO1.PCCNTR.…), entidad que la impuso, contratista, tipo de sanción,
  valor, valor pagado, estado, fecha del evento y número del acto. **No trae municipio ni NIT de la
  entidad**, así que se busca por el nombre de la entidad. Tiene 588 filas el 2026-11-03 (554 el
  2026-10-22).

## Estados de SECOP II (medido el 2026-11-03, 588 filas)

| Estado | Filas | Qué es |
|---|---|---|
| A la espera de aprobación | 378 | la plataforma aún no la aprueba |
| Publicado por el administrador de la plataforma | 146 | publicada |
| Rechazado por el administrador de la plataforma | 33 | no es sanción |
| Borrador | 31 | no es sanción |

Tipos de sanción: Cláusula Penal (412), Multa (95), No Definido (55), Otro (25), Vencimiento (1).

## Trampas medidas

1. **SECOP I y SECOP II no se cruzan.** En Chía, SECOP I tiene una multa, de 2016 (del SENA), y
   SECOP II ninguna entidad con «Chía» en el nombre. Una herramienta sola no contesta «¿qué multas
   hay en este municipio?».
2. **La mayoría no está en firme.** El 64 % está «A la espera de aprobación». Sumar todo el valor
   suma sanciones que aún no se aprueban o que se rechazaron.
3. **La misma sanción en varias filas.** 15 grupos tienen el mismo acto y el mismo valor, y en 7
   el contratista es distinto: un consorcio y sus integrantes. En Palmira, la Resolución 071 de
   2022 (11 424 millones) sale para CONSORCIO PTAR PW (publicada) y para JLX PROYECTOS SAS (a la
   espera), y el acto viene escrito de dos formas.
4. **Fechas imposibles.** Hay un evento de 2027, uno de 2028 y 55 sin fecha. Las sin fecha son
   también las de acto «No definido» y valor 0.
5. **Nombres con y sin tilde.** Están «ICBF REGIONAL BOGOTA» y «UNIDAD PRESTADORA DE SALUD
   BOGOTÁ». Con `{entidad:sin_tildes}`, la vocal con tilde de la pregunta se vuelve comodín:
   «Bogotá» encuentra las dos. «Bogota», sin tilde, no encuentra la segunda.
6. **El aviso «no cambian desde» se medía en la cosecha.** Con los metadatos del 2026-10-22, la
   puerta decía «sus datos no cambian desde 2026-10-08», y la fuente se había actualizado ese mismo
   día (`rowsUpdatedAt` 2026-11-03). Se volvió a cosechar.
7. **SECOP I trae personas naturales.** Saca nombre y cédula de un contratista persona natural,
   como lo publica la fuente. No se quitan campos, y no se busca por persona (ADR-0014).

Medido el 2026-11-03 con `secop_multas_entidad`:

| Entidad buscada | Filas | Publicadas | Valor publicado |
|---|---|---|---|
| INVIAS | 42 | 3 | 19 880 619 |
| Bogotá (6 entidades) | 56 | 9 | 116 113 968 |
| ICBF REGIONAL NARIÑO | 33 | 17 | 1 429 283 161 |
| Palmira (2 entidades) | 9 | 1 | 11 424 010 667 |
| Chía | 0 | | |

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_multas_entidad` | alto | nueva: multas de SECOP II por nombre de entidad, con totales por estado |
| `secop1_multas_municipio` (v2) | medio | dice que es solo SECOP I y remite a SECOP II |
| `secop_sanciones_contrato` | medio | por contrato |

## Decisiones

- **2026-11-03, revisión de valor (SECOP I, multas):**
  - `secop_multas_entidad` busca por nombre de entidad, porque la fuente no trae municipio.
  - Da `por_estado` y `por_entidad`. `publicadas` y `valor_publicadas` cuentan solo «Publicado por
    el administrador»; se muestran todas las filas, como las publica la fuente.
  - Ordena de la más reciente a la más antigua, con las que no tienen fecha al final.
  - Un aviso dice qué estado es firme y que la misma sanción puede repetirse. El aviso de vacío
    remite a SECOP I.
  - `secop1_multas_municipio` v2 avisa, con datos y sin ellos, que es solo SECOP I.
  - Se recosecharon los metadatos de `cce.secop2.sanciones`.
- **Pendiente:** que el aviso de atraso diga a qué fecha se midió (PR aparte: afecta a todas las
  fuentes).
