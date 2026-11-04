# Colombia Compra: SECOP I, modificaciones a procesos (`cce.secop1.modificaciones_procesos`)

Los cambios que se hicieron a los procesos de SECOP I: qué campo cambió, el valor anterior y el
nuevo, la fecha y la justificación. Colombia Compra los publica en datos.gov.co (`36vw-pbq2`) con
licencia CC BY-SA 4.0. Se consulta en vivo, por la constancia del proceso.

## Qué publica

Una fila por campo cambiado, con:
- constancia del proceso e identificador de la modificación;
- fecha;
- campo, valor anterior y valor nuevo;
- justificación.

## Cobertura

22 057 filas, del 2014-02-12 al 2026-10-30, medido el 2026-11-03. Es poco para todo SECOP I.

| Campo modificado | Filas |
|---|---|
| Cambio Estado al proceso | 13 609 |
| Numero Proceso | 4 840 |
| Cuantia | 1 257 |
| Detalle Objeto | 547 |
| ID CAUSAL CONTRATACION DIRECTA | 461 |

## Trampas medidas

1. **La justificación a veces es un número.** En 3 383 filas (15 %) es un número interno de SECOP I,
   como el 373278 del canario, y no hay un conjunto publicado que lo traduzca. Las demás son texto,
   con mayúsculas y minúsculas revueltas y sin tildes: «CaMBio De eSTaDo en (PRoCeSo y/o ConTRaTo)
   De aCueRDo Con La SoLiCiTuD De La enTiDaD nuMeRo De CaSo 313».
2. **Son cambios al proceso, no al contrato.** Los del contrato adjudicado (valor, plazo,
   contratista) están en otro conjunto, `u5b4-ae3s`, con 823 425 filas: lo consulta
   `secop1_modificaciones_adjudicacion`, por el `id_adjudicacion` que da
   `secop1_proceso_por_constancia`.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop1_modificaciones_proceso` (v2) | medio | avisa de la justificación numérica; vacío que remite a la adjudicación |

## Decisiones

- **2026-11-03, revisión de valor (v2):**
  - La justificación sale como la publica la fuente. Un aviso, con datos, dice que a veces es un
    número interno sin traducción.
  - La descripción y el aviso de vacío remiten a `secop1_modificaciones_adjudicacion` y
    `secop1_adiciones_adjudicacion` para los cambios al contrato.
  - Medido en producción: el canario (3 cambios, 5,6 s en frío) y una constancia que no existe
    (vacío con aviso, 1,1 s).
