# usgs.sismos · Catálogo mundial de sismos de la USGS

## Revisión de valor (2026-11-04)

- Probado en producción:
  - El canario, Colombia en 2024 con M ≥ 4: 139 sismos. El mayor es M5.6, a 7 km de Cartago,
    a 65 km de profundidad. El rectángulo también incluye Perú y Ecuador.
  - Bogotá y alrededores, octubre de 2026, M ≥ 2.5: `total_en_catalogo: 0` **sin aviso**. Un
    agente lo leería como «no hubo sismos». Fuera de Estados Unidos, el catálogo de la USGS solo
    está completo, en general, desde M4.5. Los pequeños de Colombia los registra el SGC, cuya
    licencia no permite servirlos aquí.
- Arreglo: con 0 resultados sale un aviso (`si: total_en_catalogo = 0`), que dice el umbral y
  remite al SGC.
