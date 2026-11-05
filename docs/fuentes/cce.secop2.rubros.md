# SECOP II, rubros presupuestales (`cce.secop2.rubros`)

Conjunto `cwhv-7fnp` de datos.gov.co. Lo publica Colombia Compra Eficiente. Licencia CC BY-SA 4.0. Se consulta en vivo.

## Qué publica

Una fila por rubro de un compromiso de un contrato: código, nombre, valor actual y año. Son 5,9 M
filas (medido el 2026-11-02).

## Cobertura

- Las mismas entidades que compromisos (los rubros cuelgan de los compromisos).
- El PAE de Chía no aparece.
- La fuente dice que se actualiza a diario, pero sus datos no cambian desde el 2026-10-09: la
  respuesta lo avisa («Datos no recientes»).

## Trampas medidas

1. **El vacío no es «no tiene rubro».**
2. **La fuente está quieta** desde el 2026-10-09.
3. **«No Definido» no es un rubro.** Cuando la entidad no registró el rubro, la fuente publica una
   fila con código «No Definido», nombre «NO DEFINIDO», valor 0 y año 0. Medido el 2026-11-05: son
   así las 7 del contrato de Pitalito (CO1.PCCNTR.3712964) y las de uno de INVIAS
   (CO1.PCCNTR.2064143). El SENA y el ICBF sí registran código y nombre
   (C-3603-1300-14-0-3603025-02 en CO1.PCCNTR.1322739).
4. **El año viene en 0**, también en los rubros definidos. Sale vacío (`vacios: ["0"]`).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_rubros_contrato` | medio | contesta cuando hay datos. El vacío lleva el aviso de cobertura; arriba va `rubros_sin_definir`, con un aviso de qué es «No Definido» |

## Decisiones

- **2026-11-02:** `cobertura.aviso_vacio` con la cobertura medida. El motor lo pone en cada «no
  encontrado» de la fuente (patrón A de la revisión de valor).
- **2026-11-03, revisión de valor:** verificado en producción con el PAE de Chía
  (CO1.PCCNTR.7180851): el vacío sale con el aviso de cobertura. Sin más cambios.
  La fuente está atrasada de verdad: datos.gov.co la actualizó por última vez el 2026-10-09.
- **2026-11-05, revisión de valor:** `rubros_sin_definir` y un aviso de que «No Definido» con
  valor 0 no es un rubro. La vigencia 0 sale vacía.
