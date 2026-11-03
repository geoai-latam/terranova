# Colombia Compra: SECOP I, proponentes (`cce.secop1.proponentes`)

Los que se presentaron a cada proceso de SECOP I y si les adjudicaron. Colombia Compra los publica en
datos.gov.co (`tauh-5jvn`) con licencia CC BY-SA 4.0. Se consulta en vivo, por constancia
(aa-n-nnnnnn).

## Qué publica

Una fila por proponente y evaluación, con:
- constancia;
- nombre o razón social;
- tipo y número de documento (ADR-0025: como lo publica la fuente);
- calificación;
- adjudicado («Si»/«No»);
- id de adjudicación;
- número de contrato;
- fecha de publicación del proceso.

## Trampas medidas (2026-11-03)

1. **El mismo proponente en varias filas.** En 21-15-11667083, GONSEGUROS sale tres veces; en
   21-11-11918076, un solo proponente sale tres veces, con el nombre en dos órdenes («CARPINTERO
   FARFAN JAVIER ANTONIO» y «Javier Antonio Carpintero Farfan»). Contar filas no es contar
   proponentes.
2. **Solo la fila adjudicada trae documento y contrato.** En las demás, documento y contrato dicen
   «No Definido».
3. **Calificación sin escala.** Trae «100000», «99600», «10000», «9800», «4600» y «000». No hay
   escala documentada.
4. **Tildes perdidas** en el tipo de documento: «Nit de Persona Jurdica», «Cdula de Ciudadana».
   Es la fuente.
5. **El canario no adjudica.** 09-1-47723 (2009) tiene tres filas de dos proponentes y ninguna
   adjudicada.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `secop1_proponentes_proceso` (v2) | medio → alto | dice quién ganó y su contrato; avisa las filas repetidas |

## Decisiones

- **2026-11-03, revisión de valor:**
  - Orden `adjudicado DESC, proponente`, para que la fila adjudicada vaya primero.
  - `adjudicado_a` y `contrato_adjudicado` (`primero` con `solo_si` adjudicado = «Si»).
  - Un aviso dice que las filas se repiten y que la calificación no tiene escala. Otro, cuando no
    hay fila adjudicada, remite a `secop1_proceso_por_constancia`.
  - No se deduplica: el nombre del mismo proponente cambia de forma, y juntarlo sería adivinar.
