# gfw.alertas_integradas · Alertas integradas de deforestación de Global Forest Watch

Herramientas:
- `gfw_alertas_deforestacion_en_zona`, por rectángulo (hasta 20° de lado);
- `gfw_alertas_deforestacion_en_poligono`, por polígono (los topes de la ADR-0035).

Las dos piden un periodo de hasta 366 días, desde 2019, con `hasta` exclusivo.

## De dónde sale

- Data API de GFW: `POST data-api.globalforestwatch.org/dataset/gfw_integrated_alerts/<versión>/query/json`
  con una consulta SQL sobre el ráster y la geometría en el cuerpo.
  - Una sola petición da los conteos por fecha y confianza de toda la zona y el periodo, así que
    la respuesta sale completa, sin páginas.
  - Hay una versión por día (`v20261105`). `latest` responde 307 a la del día, y el conector la
    pregunta una vez por hora.
- La llave es gratis y va en el `.env` de la VPS como `GFW_API_KEY`. Solo la lee `amenazas-mcp`,
  la manda en la cabecera `x-api-key` (nunca en la URL) y no sale en errores, hechos ni respuestas
  grabadas.
- GFW no publica su cupo. El conector manda una petición a la vez.
- Licencia: CC BY 4.0, según los metadatos del dataset (`"license":"[CC by 4.0](…)"`). Los
  términos de GFW remiten a esos metadatos y piden atribuir la API. La cita que piden es «Source:
  "Integrated Deforestation Alerts". UMD/GLAD and WUR, accessed through Global Nature Watch on
  [date]».

## Lo medido (2026-11-05)

- En [-74.5, 1.5, -74.0, 2.0], entre Caquetá, Meta y Guaviare, en enero de 2024:
  - high, 13 583 píxeles (167,12 ha);
  - highest, 30 024 (369,40 ha);
  - 13 días con alertas.
  - Las cifras son iguales en las versiones v20260701, v20261101 y v20261105.
- En una franja en diagonal dentro de ese rectángulo hay 4 412 píxeles. Ese es el canario por
  polígono: se pone rojo si el cruce vuelve a ser por rectángulo.
- En [-76, 0, -72, 4], todo 2024: 6 395 552 píxeles (78 680,56 ha), 243 días con alertas y 513
  filas.
- El rectángulo de Colombia y sus vecinos, un año entero, tardó 19,5 s. Uno de 0,5° y un mes,
  3 s.
- Lo reciente es sobre todo nominal. Desde el 2026-09-01, en el rectángulo de Colombia: nominal
  2 912 264, high 1 926 167 y highest 531 420.
- Antes del 2019-01-01 la consulta da vacío, y la herramienta lo rechaza como error de entrada.
- Sobre el mar la respuesta es `{"data": [], "status": "success"}` y sale «no encontrado» con su
  aviso.
- Un píxel mide unas 0,012 ha (536,52 ha / 43 607 píxeles).

## Cuidado al leerlo

- Cada fila cuenta píxeles de 10 m, no eventos. Un píxel de 30 m de GLAD-L se vuelve varios de
  10 m.
- GFW advierte que las alertas marcan perturbaciones del bosque, sin distinguir la tala de otras
  causas, y que no sirven para estimar áreas ni tendencias. Para eso está la pérdida anual de
  cobertura arbórea.
- La confianza «high» es una detección confirmada por un sistema. «highest» quiere decir que la
  vieron dos o tres sistemas.
- Las alertas nominales pueden subir de confianza o borrarse: GLAD a los 180 días y RADD a los 90.
  Por eso el canario usa enero de 2024.
- Sin alertas no quiere decir sin deforestación:
  - los satélites ópticos no ven bajo las nubes;
  - cada sistema solo vigila su máscara de bosque, sin lo talado antes;
  - en esta colección, GLAD-L empieza en 2021 y RADD empieza en 2020 en Suramérica.
