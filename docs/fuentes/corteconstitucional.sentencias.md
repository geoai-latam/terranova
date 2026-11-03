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

1. **Números con letra.** Entre 1993 y 1995 la Corte numeró algunas sentencias con letra:
   C-155A/93, T-539A/93, T-066A/94, T-133A/95… La entrada las rechazaba; ahora las acepta.
2. **El año en curso parece completo.** Medido en la fuente: 584, 530, 520 y 313 sentencias en
   2023-2026. La cifra de 2026, 313, va solo hasta el 30 de septiembre, y nada lo decía.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `corte_constitucional_sentencia` | alto | v2: con `url` del texto en la relatoría y aviso de vacío |
| `corte_constitucional_sentencias_anio` | bajo → medio | v2: con `total_sentencias` y `hasta_fecha` (la última sentencia del año en el índice) |

## Decisiones

- **2026-11-03, patrón F de la revisión de valor:** `corte_constitucional_sentencias_anio` suma un
  complemento con `max(fecha_sentencia)` del año. Si el año no ha terminado, la cifra se lee hasta
  esa fecha. Medido: 2008 suma 1 257 sentencias hasta el 2008-12-19; 2026, 313 hasta el 2026-09-30.
- **2026-11-03, `corte_constitucional_sentencia` v2 (revisión de valor):**
  - **El enlace:** sale `url`, el texto completo en la relatoría. La consulta lo arma con SoQL:
    `'…/relatoria/' || date_extract_y(fecha_sentencia) || '/' || replace(sentencia, '/', '-') || '.htm'`.
  - **Medido el 2026-11-03:**
    - el año del número cuadra con el de la fecha en todas las filas (0 discrepancias);
    - la relatoría responde 200 en T-001/92, C-155A/93, T-133A/95, C-355/06, T-760/08, SU-214/16
      y C-316/26.
  - **Entrada:** `sentencia_cc` y `sentencia_relatoria` aceptan una letra tras el número.
  - **Vacío:** el aviso da la forma correcta del número y recuerda que el índice va unas semanas
    detrás.
