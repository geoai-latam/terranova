# IDEAM: lluvia de las estaciones automáticas (`ideam.precipitacion`)

Las observaciones de precipitación de las estaciones automáticas del IDEAM, en datos.gov.co
(`s54a-sgyg`), con licencia CC BY-SA 4.0. Se consultan en vivo y la consulta las suma por día.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `ideam.precipitacion` | `s54a-sgyg` | `ideam_lluvia_diaria_estacion` |

## Qué publica

Una fila por observación: estación, sensor, fecha y hora, y los milímetros caídos en ese intervalo.
Una estación puede tener dos sensores de lluvia:

- **0240 («PRECIPITACIÓN»):** cada 10 minutos, 144 observaciones al día.
- **0257 («GPRS - PRECIPITACIÓN»):** cada 2 minutos, 720 al día.

## Campos que importan

- `codigoestacion`: 10 dígitos con ceros a la izquierda («0028025502»).
- `codigosensor` y `descripcionsensor`.
- `fechaobservacion` y `valorobservado` (mm).
- La herramienta suma por día y por sensor, y cuenta las observaciones. Un día con pocas tuvo huecos:
  el 20 de octubre de 2026, el 0240 de Valledupar tuvo 143 de 144.

## Cobertura

- Solo estaciones **automáticas**. Las convencionales no están, aunque estén activas.
- Datos de hace un día. Medido el 2026-11-03:
  - Universidad Nacional (Bogotá) tiene los 31 días de octubre de 2026;
  - el aeropuerto de Valledupar llega hasta el 1 de noviembre.

## Trampas medidas

1. **Dos sensores que no coinciden.** Valledupar, del 18 de octubre al 1 de noviembre de 2026:
   - el 0240 suma 55,79 mm;
   - el 0257 (GPRS) suma 25,1 mm, y dio 0,0 casi todos los días del 18 al 26 mientras el otro
     medía lluvia.
   - Sumarlos da un número que no midió nadie; tomar uno al azar puede dar la mitad.
2. **«0 registros» no es «no llovió».** Una estación convencional, una suspendida o un código mal
   escrito salen vacíos. El 0,0 de un día con todas sus observaciones sí es «no llovió».
3. **La suma de la consulta puede traer ruido de coma flotante.** Se redondea a dos decimales.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ideam_lluvia_diaria_estacion` | medio → alto | v2: `mm_por_sensor`, `sensores`, `dias_con_datos` y `ultimo_dia`; aviso cuando hay más de un sensor y aviso de vacío |

## Decisiones

- **2026-11-03, revisión de valor y hallazgo #10 de GEO Copilot** («0 registros en octubre»):
  - **Qué pasó:** las estaciones medidas sí tienen octubre. El vacío de GEO Copilot sale de la
    estación que consultó: convencional, suspendida o un código mal escrito.
  - **El aviso de vacío** lo dice y remite a `ideam_estaciones_en_zona`.
  - **No se elige un sensor «principal».** No hay una regla publicada del IDEAM que lo diga.
    - Se da el total de cada uno (derivado `suma_por`).
    - Cuando hay más de uno, el aviso explica cómo reconocer el que falla, con el caso medido.
  - `mm` sale con dos decimales.
- **Pendiente: un complemento que corra con el resultado vacío** para decir la fecha de la última
  observación de la estación (plan de producto, B5).

## Revisión de valor (2026-11-04)

- Probado en producción:
  - Universidad de la Sabana (2120500135), del 25-10 al 03-11: 6,0 mm el 28-10 y 0,0 los otros
    días. Se comprobó en la fuente: son 11 lecturas que suman exactamente 6,0.
  - Almaviva (convencional): vacío, con el aviso correcto.
- Lo mismo que en el nivel: son datos crudos sin validar, y eso no se decía. Ahora lleva un aviso
  con datos.
