# SECOP II, compromisos presupuestales (`cce.secop2.compromisos`)

Conjunto `skc9-met7` de datos.gov.co. Lo publica Colombia Compra Eficiente. Licencia CC BY-SA 4.0. Se consulta en vivo.

## Qué publica

Una fila por ítem de un compromiso presupuestal ligado a un contrato: tipo de compromiso, código y
valor del ítem, balance, vigencia futura y estado de integración. Son 5,9 M filas (medido el
2026-11-02).

## Cobertura

- Solo las entidades que registran su presupuesto en SECOP II. En una muestra aparecen entidades
  territoriales: Funza y las subredes de salud de Bogotá.
- El PAE de Chía no aparece (medido el 2026-11-02).
- Sin medir: qué parte de las entidades lo hace.

## Trampas medidas

1. **El vacío no es «no tiene compromiso».** El CDP puede estar en `secop_cdp_contrato`.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_compromisos_contrato` | medio | contesta cuando hay datos. Desde el 2026-11-02, el vacío lleva el aviso de cobertura (`cobertura.aviso_vacio`) |

## Decisiones

- **2026-11-02:** `cobertura.aviso_vacio` con la cobertura medida. El motor lo pone en cada «no
  encontrado» de la fuente (patrón A de la revisión de valor).
