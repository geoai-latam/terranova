# SECOP II, modificaciones a contratos (`cce.secop2.modificaciones`)

Conjunto `u8cx-r425` de datos.gov.co. Lo publica Colombia Compra Eficiente. Licencia CC BY-SA 4.0,
verificada el 2026-10-22. Se consulta en vivo y se actualiza a diario.

## Qué publica

Una fila por cada modificación de un contrato de SECOP II (`CO1.CTRMOD.…`), cualquiera sea su
estado: adiciones, prórrogas, suspensiones, reinicios, cesiones y cambios de estado del contrato.
La fila trae la versión del contrato que deja la modificación: valor, fechas de inicio y fin,
dirección y BPIN.

## Campos que importan

- `valor_modificacion`: **no es lo que cambió**. Es el valor total del contrato en la versión que
  deja la modificación. Medido el 2026-11-02:
  - En CO1.PCCNTR.7143094 (la Subred Centro Oriente, prestación de servicios) sube así:
    24 476 320, 32 446 432, 40 574 368 … 52 983 280. El último es igual al
    `valor_del_contrato` de `jbjy-vk9h`.
  - En CO1.PCCNTR.7180851 (el PAE de Chía) vale 64 938 000 000 en las 9 filas, aunque ninguna
    añadió nada.
  - Quien suma esa columna multiplica el contrato (el PAE daría 9 veces su valor).
- `estado_modificacion`: solo algunas cuentan. Medido en todo el conjunto el 2026-11-02:

  | Estado | Filas | ¿Cuenta? |
  |---|---|---|
  | Publicado | 7 381 349 | sí |
  | Aprobado | 56 859 | sí |
  | Aceptado por el Proveedor | 24 969 | sí |
  | Cancelado | 654 043 | no |
  | En Proceso de Aprobación | 128 690 | no |
  | En Edición | 103 976 | no |
  | Enviado al Proveedor | 47 497 | no |
  | Rechazado por el Proveedor | 31 008 | no |
  | Rechazado | 22 984 | no |
  | No definido | 222 | no |

- `dias_extendidos`: los días de prórroga de esa modificación. Es por modificación, no
  acumulado. En el contrato de Pitalito, las prórrogas vigentes suman 178, 92 y 94 días.
- `fecha_de_aprobacion`: falta en las que no se aprobaron. Para ordenar se usa `fecha_creacion`.
- `descripcion`: es el objeto del contrato repetido en cada fila, no la descripción del cambio.
  Lo que explica el cambio va en `proposito_modificacion`.
- `proposito_modificacion`: texto libre, con tildes rotas en la fuente («f�sico»).

## Cobertura

- Todo SECOP II.
- **No publica el valor con que se firmó el contrato.** Lo que cambió la primera modificación no se
  puede calcular con este conjunto. El `precio_base` del proceso (`p6dx-8zbt`) no sirve como valor
  inicial: es el del proceso, no el firmado (en CO1.PCCNTR.7143094 dice 15 940 224).

## Trampas medidas

1. **El valor es el total tras el cambio, no el cambio** (ver arriba).
2. **Las canceladas siguen en la lista, con valor.** En el PAE de Chía son 3 de 9 y en Pitalito
   8 de 16 (cancelados y uno «Rechazado por el Proveedor»).
3. **Copias exactas.** Hasta el 2026-10-28 la fuente traía filas repetidas: Pitalito tenía 33 filas
   y solo 21 distintas. Ese día se republicó sin ellas (16). Se conserva el `distinct`.
4. **La fuente borra.** Ese mismo republicado bajó de 21 a 16 modificaciones en Pitalito.

## El conjunto hermano: `cb9c-h8sn` («adiciones»)

- Trae los mismos `CO1.CTRMOD`, con un `tipo`.
- No son solo adiciones. Medido en todo el conjunto el 2026-11-02:

  | Tipo | Filas |
  |---|---|
  | Modificacion General | 4,1 M |
  | Conclusion | 2,0 M |
  | No definido | 1,7 M |
  | Adicion en el valor | 258 109 |
  | Reactivación | 141 535 |
  | Suspensión | 128 301 |
  | Cesion | 107 582 |
  | Extension | 380 |
  | Reduccion en el valor | 143 |

- El `tipo` no sirve para saber el valor. En CO1.PCCNTR.7143094 las «Modificacion General» también
  suben el valor.
- Algunos `tipo` vienen cruzados con su texto: en el PAE de Chía, la «Reactivación» trae el motivo de
  la suspensión y la «Suspensión» trae el acta de reinicio.
- Por eso la fuente quedó en borrador y su herramienta se retiró.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_modificaciones_contrato` (v2) | alto | todas las modificaciones, cada una con `vigente`. Da `valor_contrato_tras_cambio` y `cambio_valor` (la diferencia con la vigente anterior). Arriba van `valor_tras_primera`, `valor_actual`, `cambio_valor_desde_primera` y `dias_extendidos_total`, solo con las vigentes |
| ~~`secop_adiciones_contrato`~~ | retirada | daba los mismos eventos que la de modificaciones, con un `tipo` que engaña |

## Decisiones

- **2026-11-02:**
  - `valor_modificacion` sale como `valor_contrato_tras_cambio`.
  - El motor suma `diferencia_anterior`, `ultimo` y `solo_si`, para calcular lo añadido solo
    entre las vigentes.
  - Se retiró `secop_adiciones_contrato` y `cce.secop2.adiciones` pasó a borrador.
- **Pendiente:**
  - Un aviso dentro de la respuesta (no solo en la descripción) que diga que la primera
    modificación no tiene cambio calculable. Va con el patrón A del motor.
  - Revisar si `cb9c-h8sn` publica la fecha del cambio de tipo o algo que no tenga `u8cx-r425`.
