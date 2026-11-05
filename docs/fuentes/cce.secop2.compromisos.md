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

1. **El vacío no es «no tiene compromiso».** El CDP puede estar en `secop_cdp_contrato`. Un
   contrato del SENA (CO1.PCCNTR.6893653) tiene su CDP «Con compromiso», pero aquí sale vacío
   (2026-11-04).
2. **El tipo es un código.** La fuente usa 0 para «ingresos» y 1 para «vigencias futuras»; lo
   dice el diccionario del conjunto (`skc9-met7`). El código del ítem es interno de la
   integración con el SIIF y no tiene tabla publicada.
3. **Dos estados distintos.** `estado_integraci_n` es el resultado de la última consulta al
   SIIF (Exito, Fallido…). `estado_integraci_n_item` es el estado del compromiso (Generado, Con
   Obligación, Cancelado…), y es el que dice si el contrato está respaldado.
4. **Lento.** El canario (CO1.PCCNTR.100201) tardó 13,3 s el 2026-11-04, por encima del tope de
   10 s. No se relaja el tope; si se repite, es candidato a copia.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_compromisos_contrato` | medio | v2: estado del compromiso, saldo de vigencias futuras y significado del tipo |

## Decisiones

- **2026-11-02:** `cobertura.aviso_vacio` con la cobertura medida. El motor lo pone en cada «no
  encontrado» de la fuente (patrón A de la revisión de valor).
- **2026-11-03, revisión de valor:** verificado en producción con el PAE de Chía
  (CO1.PCCNTR.7180851): el vacío sale con el aviso de cobertura. Sin más cambios.
- **2026-11-04, revisión de valor (v2):** la herramienta no pedía el estado del compromiso, que
  es lo que contesta la pregunta. Ahora lo pide, junto con el saldo de vigencias futuras y el
  significado del tipo, tomado del diccionario del conjunto.
