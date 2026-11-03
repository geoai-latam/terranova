# Corte Constitucional: índice de sentencias (`corteconstitucional.sentencias`)

El índice de las sentencias de la Corte Constitucional desde 1992. Está en datos.gov.co
(`v2k4-2t8s`), con licencia CC BY-SA 4.0, y se consulta en vivo.

## Qué publica

Una fila por sentencia:

- número (T-760/08);
- tipo: C (constitucionalidad), T (tutela) o SU (unificación);
- fecha y proceso;
- expediente;
- magistrado ponente y sala;
- salvamento y aclaración de voto («s.d.» es sin dato).

No trae el texto ni el tema: para eso están `corte_constitucional_texto_*`.

## Cobertura

De 1992 a la última sentencia indexada. Medido el 2026-11-03: 2026 llega hasta el 30 de septiembre.

## Trampas medidas

1. **El año en curso parece completo.** Medido en la fuente: 584, 530, 520 y 313 sentencias en
   2023-2026. La cifra de 2026, 313, va solo hasta el 30 de septiembre, y nada lo decía.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `corte_constitucional_sentencia` | alto | pendiente: el enlace a la relatoría |
| `corte_constitucional_sentencias_anio` | bajo → medio | v2: con `total_sentencias` y `hasta_fecha` (la última sentencia del año en el índice) |

## Decisiones

- **2026-11-03, patrón F de la revisión de valor:** `corte_constitucional_sentencias_anio` suma un
  complemento con `max(fecha_sentencia)` del año. Si el año no ha terminado, la cifra se lee hasta
  esa fecha. Medido: 2008 suma 1 257 sentencias hasta el 2008-12-19; 2026, 313 hasta el 2026-09-30.
