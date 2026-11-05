# ani.trafico_peajes · Tráfico mensual de los peajes de la ANI

## Revisión de valor (2026-11-04)

- FUSCA 2026: 5 meses y 760 048 vehículos, sin decir que el año va incompleto. FUSCA 2013: vacío,
  cuando la serie empieza en 2014.
- Arreglo, el mismo del recaudo:
  - `ultimo_mes`, y un aviso cuando hay menos de 12 meses;
  - `desde_anio: 2014`.
