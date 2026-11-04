# dnp.proyectos_sgr: proyectos del Sistema General de Regalías

- **Fuente:** datos.gov.co, `mzgh-shtp`, en vivo. Licencia CC BY-SA 4.0.
- **Herramienta:** `dnp_proyecto_sgr_por_bpin`. Agrupa por BPIN: una fila por departamento beneficiado.

## Revisión de valor (2026-11-04)

- **Probado en producción:**
  - El canario (Somondoco): terminado, al 100 %.
  - 2021000100001: Universidad de los Llanos, en ejecución, al 86 %.
  - Un BPIN de ceros: vacío.
  - Un BPIN de 11 dígitos: 400, por el patrón.
- **Hallazgo:**
  - Cada proyecto salía con el aviso «no se sabe si vino todo». Con `max_filas: 1`, el único
    grupo del BPIN llegaba al tope y el conector lo daba por cortado.
  - El vacío no decía nada.
- **Arreglo:**
  - `max_filas: 2`.
  - Un aviso en el vacío dice que la fuente trae solo proyectos del SGR.
  - Los nombres salen como los publica la fuente («BOYACa», espacios dobles).
