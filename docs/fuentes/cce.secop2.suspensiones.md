# Colombia Compra: SECOP II, suspensiones de contratos (`cce.secop2.suspensiones`)

Las suspensiones y reanudaciones de los contratos de SECOP II. Colombia Compra las publica en
datos.gov.co (`u99c-7mfm`) con licencia CC BY-SA 4.0. Se consulta en vivo, por contrato
(CO1.PCCNTR.…).

## Qué publica

Una fila por suspensión o reanudación, con:
- contrato;
- tipo (suspensión o reanudación);
- motivo, en texto libre;
- fechas de creación y de aprobación.

## Cobertura

Medido el 2026-11-03: 485 557 filas de suspensión y 422 796 de reanudación, del 2016-05-11 al
2026-11-02.

## Trampas medidas

1. **Cada evento sale dos veces** (spec 07, medido el 2026-10-22 en CO1.PCCNTR.3712964: 20 filas,
   10 distintas). La herramienta usa `distinct`.
2. **El motivo llega sin tildes y con la vocal en minúscula donde iba la tilde** desde la fuente
   («SUSPENSIoN»), y con punto y coma donde iban comas.
3. **Hay más suspensiones que reanudaciones** (62 761 de diferencia). Sin medir cuántas son
   contratos todavía suspendidos y cuántas reanudaciones no registradas.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_suspensiones_contrato` | medio | sin cambios: responde bien |

## Decisiones

- **2026-11-03, revisión de valor:** sin cambios. Medido en producción con el PAE de Chía
  (CO1.PCCNTR.7180851): 3 filas, dos suspensiones por el receso escolar y una reanudación. El texto
  sale como lo publica la fuente.
