# Colombia Compra: SECOP II, fechas del cronograma (`cce.secop2.cronograma`)

Las fechas del cronograma de cada fase de un proceso de SECOP II. Colombia Compra las publica en
datos.gov.co (`f3ev-294c`) con licencia CC BY-SA 4.0. Se consulta en vivo, por el proceso de compra
(CO1.BDOS.…) o por la fase (CO1.REQ.…).

## Qué publica

Una fila por fase de un proceso, con:
- fase y proceso de compra;
- modalidad;
- fechas de presentación y apertura de ofertas, audiencia de adjudicación, entrega de la garantía y
  creación del cronograma.

## Cobertura

9 184 138 filas, medido el 2026-11-03.

## Trampas medidas

1. **Casi todas las fechas vienen vacías.** De 9 184 138 filas faltan:

   | Fecha | Vacía en |
   |---|---|
   | presentación de ofertas | 8 801 534 |
   | apertura de ofertas | 8 917 895 |
   | audiencia de adjudicación | 9 155 185 |
   | entrega de la garantía | 8 566 243 |
   | creación | 8 976 160 |

2. **Depende de la modalidad.** La apertura de ofertas viene vacía en todas las filas de
   contratación directa (4 323 183), régimen especial (3 717 773), solicitud de información a los
   proveedores (197 550) y contratación directa con ofertas (109 076). En mínima cuantía falta en
   385 207 de 387 803. En selección abreviada de menor cuantía, solo en 6 288 de 204 956.
3. **Un proceso tiene varias fases.** El PAE de Chía (CO1.BDOS.7088717) tiene dos, CO1.REQ.7226140 y
   CO1.REQ.7304794, con fechas que difieren en un día.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop_cronograma_proceso` (v2) | medio | avisa que una fecha vacía depende de la modalidad |

## Decisiones

- **2026-11-03, revisión de valor (v2):**
  - Un aviso, con datos, dice que una fecha vacía no quiere decir que el paso no ocurrió, y remite a
    `secop_contrato_por_id` para la firma y el estado.
  - Las fechas salen como las publica la fuente.
  - Medido en producción: el canario (concurso de méritos, 2 fases, 2,1 s) y el PAE de Chía
    (licitación: apertura el 18 y 19 de diciembre de 2024, adjudicación el 27 y 28, garantía el 30;
    1,6 s).
