# ungrd.emergencias: emergencias de la UNGRD por municipio

- **Fuente:** datos.gov.co, `2343-nuqp` («Emergencias UNGRD V2»), en vivo. Licencia CC BY 4.0.
- **Herramienta:** `ungrd_emergencias_municipio`.

## Lo medido

- **2026-11-04:**
  - 13 012 filas. La fecha va de 2025-01-01 a 2025-12-31.
  - La fuente se actualizó el 2026-09-22 sin traer 2026.
  - Cada emergencia sale dos veces, con filas idénticas, así que se pide con `distinct`.

## Revisión de valor (2026-11-04)

- **Probado en producción:**
  - Medellín: 9 emergencias de 2025 y 3 muertos; el canario da bien.
  - Chía y Puerto Alegría: vacío.
- **Hallazgo:** la herramienta decía «desde 2025», como si llegara hasta hoy. Una pregunta por las
  emergencias de este año salía con las de 2025 sin decirlo, y un vacío se leía como «ninguna
  emergencia».
- **Arreglo:**
  - La descripción y la cobertura dicen «solo 2025».
  - Un aviso con datos dice que 2026 no está.
  - El vacío dice que la falta de registros en 2025 no habla de otros años.
