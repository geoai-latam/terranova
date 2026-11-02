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

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_rubros_contrato` | medio | contesta cuando hay datos. Desde el 2026-11-02, el vacío lleva el aviso de cobertura (`cobertura.aviso_vacio`) |

## Decisiones

- **2026-11-02:** `cobertura.aviso_vacio` con la cobertura medida. El motor lo pone en cada «no
  encontrado» de la fuente (patrón A de la revisión de valor).
