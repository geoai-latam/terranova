# IDEAM: temperatura del aire de las estaciones automáticas (`ideam.temperatura`)

Las observaciones de temperatura de las estaciones del IDEAM en datos.gov.co (`sbwg-7ju4`), con
licencia CC BY-SA 4.0. Se consultan en vivo, agregadas por día en la consulta.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `ideam.temperatura` | `sbwg-7ju4` | `ideam_temperatura_diaria_estacion` |

## Qué publica

Una fila por observación: estación, sensor, fecha y hora, y valor en °C. Una misma estación puede
tener dos sensores:

- **0068:** horario, 24 observaciones al día.
- **0071 (GPRS):** cada 2 minutos, 720 al día.

## Campos que importan

- `codigoestacion` (10 dígitos con ceros, «0028025502») y `codigosensor`.
- `fechaobservacion` y `valorobservado`.
- La herramienta agrega por día: el promedio, la mínima y la máxima de cada sensor, y cuántas
  observaciones hubo.

## Cobertura

Datos de hace un día. Medido el 2026-11-02 en el aeropuerto Alfonso López de Valledupar.

## Trampas medidas

1. **Dos sensores, dos números por día.** En Valledupar casi coinciden: el 25 de octubre de 2026,
   28,9 °C de promedio en el 0068 y 28,7 en el 0071. Aquí sirve tener los dos. En la lluvia no pasa
   lo mismo (revisión de valor, `ideam_lluvia_diaria_estacion`).
2. **El promedio de la consulta trae 16 decimales** (27.2083333333333333).

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ideam_temperatura_diaria_estacion` | alto | v2: promedio, mínima y máxima con un decimal |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor (decimales de sobra):**
  - El motor suma `decimales` a los derivados (`redondear`), para los promedios que se calculan en
    la consulta.
  - Aquí va un decimal, como mide el sensor.
