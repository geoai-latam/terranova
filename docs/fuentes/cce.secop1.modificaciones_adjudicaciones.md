# Colombia Compra: SECOP I, modificaciones a adjudicaciones (`cce.secop1.modificaciones_adjudicaciones`)

Los cambios que se hicieron a las adjudicaciones (contratos) de SECOP I. Colombia Compra los publica
en datos.gov.co (`u5b4-ae3s`) con licencia CC BY-SA 4.0. Se consulta en vivo, por el
`id_adjudicacion` que da `secop1_proceso_por_constancia`.

## Qué publica

Una fila por campo cambiado, con:
- adjudicación e identificador de la modificación;
- fecha;
- campo, valor anterior y valor nuevo;
- justificación.

## Cobertura

823 425 filas, del 2013-06-13 al 2026-11-02, medido el 2026-11-03. Los campos más cambiados:

| Campo modificado | Filas |
|---|---|
| Sexo representante legal | 238 066 |
| Destinación del gasto | 116 912 |
| FECHA INICIO EJECUCION | 99 978 |
| Codigo BPIN | 46 096 |
| Valor del rubro presupuestal | 36 057 |
| Valor Definitivo Proceso | 32 799 |

## Trampas medidas

1. **Muchos cambios son correcciones de datos, no del contrato.** El más común es el sexo del
   representante legal. El canario (10878821) corrige el nombre del contratista y un dígito del
   número de contrato.
2. **La justificación casi siempre es texto**: solo 119 filas traen un número interno, al revés que
   en las modificaciones a procesos (`cce.secop1.modificaciones_procesos`).
3. **Trae nombres de contratistas persona natural y de representantes legales**, como los publica la
   fuente. No se busca por persona (ADR-0014): la entrada es el id de la adjudicación.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop1_modificaciones_adjudicacion` | medio | sin cambios: responde bien |

## Decisiones

- **2026-11-03, revisión de valor:** sin cambios. Medido en producción: el canario, 3 cambios, 1,4 s.
