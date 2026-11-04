# cce.secop2.bpin: el proyecto de inversión de un proceso de SECOP II

- **Fuente:** datos.gov.co, `d9na-abhe`, en vivo. Licencia CC BY-SA 4.0.
- **Herramienta:** `secop_bpin_proceso`, por id de fase (CO1.REQ.), proceso (CO1.BDOS.) o
  contrato (CO1.PCCNTR.).

## Revisión de valor (2026-11-04)

- **Probado en producción:**
  - El canario CO1.REQ.11194762: 41 filas, una por contrato, todas del BPIN 2024080010085.
  - Uno de sus contratos: 1 fila.
  - Un id inventado: vacío, sin aviso.
- **Hallazgo:** para saber «con qué proyecto» había que leer 41 filas iguales en el BPIN.
- **Arreglo:**
  - `contratos_por_bpin` (conteo por BPIN) arriba.
  - Un aviso en el vacío: los procesos de funcionamiento no llevan BPIN.
