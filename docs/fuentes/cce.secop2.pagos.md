# Colombia Compra: SECOP II, pagos y facturas (`cce.secop2.pagos`, `cce.secop2.facturas`)

Son los pagos de los contratos de SECOP II. Colombia Compra los publica en dos conjuntos de
datos.gov.co, con licencia CC BY-SA 4.0. Se consultan en vivo, por contrato.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `cce.secop2.pagos` | `uymx-8p3j` | `secop_pagos_contrato` |
| `cce.secop2.facturas` | `ibyt-yi2f` | ninguna (borrador desde el 2026-11-03) |

## Qué publica

Una fila por pago o factura del contrato con:

- `id_de_pago`: consecutivo 1, 2, 3…; es texto;
- número de factura;
- fecha de emisión;
- valor total y valor a pagar;
- estado;
- fecha real de pago (`fecha_real_de_pago`).

El de facturas trae lo mismo con `valor_neto`, `pago_confirmado` y la fecha **estimada** de pago
(`fecha_estiamda_de_pago`, así, con la errata).

## Estados medidos

- «Pagado»: tiene fecha real de pago.
- «Bajo Aprobación» y «Aprobado»: sin fecha de pago.
- En el conjunto de facturas, el mismo pago que aquí sale «Bajo Aprobación» sale como «En Gestión».

## Trampas medidas

1. **Los dos conjuntos son la misma lista.** El PAE de Chía (CO1.PCCNTR.7180851) da las mismas 19
   facturas en los dos, con los mismos valores. Por eso había dos herramientas para la misma
   pregunta.
2. **Lo más viejo primero.** Con el orden por emisión ascendente, el pago pendiente de octubre de
   2026 quedaba al final de la lista.
3. **No hay total.** Para saber cuánto se ha pagado de un contrato había que sumar a mano.

Medido el 2026-11-03:

| Contrato | Valor | Facturado | Pagado | Último pago |
|---|---|---|---|---|
| PAE de Chía | 64 938 millones | 39 059 millones en 19 facturas | 34 829 millones en 17 pagos | 2026-08-18 |
| Pitalito (CO1.PCCNTR.3712964) | 1 173 577 000 | 1 173 577 000 | 1 173 577 000 en 3 pagos | 2023-09-27 |

En el PAE, las dos facturas de agosto y octubre siguen «Bajo Aprobación».

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_pagos_contrato` | alto | v2: del más reciente al más viejo; arriba lo facturado, lo pagado, los pagos hechos, el último pago y el valor del contrato |
| `secop_facturas_contrato` | — | retirada el 2026-11-03 |

## Decisiones

- **2026-11-03, patrón F de la revisión de valor:**
  - Queda solo `secop_pagos_contrato`, porque trae la fecha real de pago. `cce.secop2.facturas`
    pasa a borrador.
  - Los totales usan `solo_si` sobre `estado = Pagado`.
  - El valor del contrato sale de `jbjy-vk9h` con un complemento.
