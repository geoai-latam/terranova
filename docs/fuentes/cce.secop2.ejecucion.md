# SECOP II, ejecución de contratos (`cce.secop2.ejecucion`)

Conjunto `mfmm-jqmq` de datos.gov.co. Lo publica Colombia Compra Eficiente. Licencia CC BY-SA 4.0. Se consulta en vivo.

## Qué publica

Una fila por entrega planeada o avance de un contrato: tipo de ejecución, plan, fechas esperada y
real, porcentaje esperado y real, artículos y cantidades.

Tipos medidos el 2026-11-02, sobre 7,7 M filas: «Recepción de artículos» (4,1 M), «Porcentaje»
(3,6 M) y «No Definido» (15 750).

## Cobertura

- Solo los contratos en los que la entidad registra un plan de entregas o un porcentaje de
  avance.
- El PAE de Chía no aparece (medido el 2026-11-02).

## Trampas medidas

1. **El vacío no es «no se está ejecutando».** Los pagos y las facturas están en otros conjuntos
   (`secop_pagos_contrato`).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_ejecucion_contrato` | medio | contesta cuando hay datos. Desde el 2026-11-02, el vacío lleva el aviso de cobertura (`cobertura.aviso_vacio`) |

## Decisiones

- **2026-11-02:** `cobertura.aviso_vacio` con la cobertura medida. El motor lo pone en cada «no
  encontrado» de la fuente (patrón A de la revisión de valor).
