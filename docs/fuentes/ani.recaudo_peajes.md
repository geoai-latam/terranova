# ani.recaudo_peajes · Recaudo mensual de los peajes de la ANI

## Revisión de valor (2026-11-04)

- Probado en producción:
  - SIBERIA 2021 (canario): 12 meses, $90 167 509 500 sin repetidos.
  - FUSCA 2026: **5 meses** (enero a mayo) con `total_recaudo` de $12 417 millones, sin decir
    que el año va incompleto. Un agente lo daría como el recaudo de 2026.
  - ANDES 2013: vacío sin aviso, cuando la serie empieza en 2014.
- Arreglo:
  - `ultimo_mes`, y un aviso cuando el año trae menos de 12 meses;
  - `desde_anio: 2014` en la cobertura, para que 2013 salga como «fuera de cobertura».
