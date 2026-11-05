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
3. **El enlace de las SU.** El índice escribe SU-214/16, pero la relatoría guarda el texto como
   `SU214-16.htm`, sin el primer guion. `SU-214-16.htm` responde 200 con una página vacía de
   8 607 bytes: un 200 no prueba que el enlace sirva; hay que medir el tamaño.
4. **El número va en tres cifras.** El índice guarda T-001/92, C-005/93 y T-025/04, y también
   cuatro cifras (T-1025/02). Quien escribe T-25/04, como se cita a menudo, no encontraba la
   sentencia del desplazamiento forzado. Medido el 2026-11-05.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `corte_constitucional_sentencia` | alto | v3: con `url` del texto en la relatoría (bien también en las SU) y aviso de vacío; acepta el número como lo escribe un abogado |
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
    - la relatoría responde 200 en T-001/92, C-155A/93, T-133A/95, C-355/06, T-760/08 y C-316/26.
      En SU-214/16 también daba 200, pero era la página vacía (ver la trampa 3): se corrigió en la
      v3.
  - **Entrada:** `sentencia_cc` y `sentencia_relatoria` aceptan una letra tras el número.
  - **Vacío:** el aviso da la forma correcta del número y recuerda que el índice va unas semanas
    detrás.
- **2026-11-03, v3:** el enlace de las SU sale sin el primer guion:
  `replace(replace(sentencia, '/', '-'), 'SU-', 'SU')`. Se midió por tamaño: `SU214-16.htm` pesa
  2,5 MB y `SU-214-16.htm`, 8 607 bytes. El texto de la sentencia está en
  [corteconstitucional.relatoria.md](corteconstitucional.relatoria.md).
- **2026-11-05, el número como lo escribe un abogado (revisión de valor):**
  - **Antes:** `t-760/08` y `T-760-08` daban 400 en el índice; `T-760/08` daba 400 en las
    herramientas del texto, y `T-25/04` salía «no encontrado».
  - **Ahora:** `sentencia_cc` y `sentencia_relatoria` aceptan el mismo patrón: mayúscula o
    minúscula, con barra o guion, con «de» y el año en cuatro cifras (T-025 de 2004), con o sin el
    guion tras el tipo (SU214/16). `normalizar_sentencia` arma de nuevo lo que va a la fuente: el
    número en tres cifras como mínimo, el año en dos y la forma de cada sitio (T-025/04 en el
    índice; T-025-04 y SU214-16 en la relatoría). Lo que va a la consulta sale de los grupos del
    patrón, nunca del texto crudo.
  - **Medido el 2026-11-05 con el conector desplegado:** «T-25 de 2004» da la T-025/04 (ponente
    Manuel José Cepeda Espinosa) y «su214/16», la SU-214/16; `corte_constitucional_resuelve` con
    «T-25/04» da lo resuelto en la posición 275 877, como el canario.
