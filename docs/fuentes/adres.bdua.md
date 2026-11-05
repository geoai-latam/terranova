# ADRES: afiliados de la BDUA por municipio y EPS

Fuentes `adres.bdua_contributivo` (`tq4m-hmg2`) y `adres.bdua_subsidiado` (`d7a5-cnra`), de
datos.gov.co. Herramientas: `adres_afiliados_contributivo_municipio` y
`adres_afiliados_subsidiado_municipio` (valor alto).

## Qué publica

Conteos de afiliados de la Base de Datos Única de Afiliados (BDUA) por departamento, municipio,
EPS, sexo, edad y zona. Es el corte vigente: la tabla se reemplaza cada mes. Las filas no traen la
fecha del corte; la ficha de datos.gov.co marcó la última actualización el 2026-11-03.

## Campos que importan

- `dpr_nombre` y `mnc_nombre`: nombres a modo de la ADRES, sin tildes y sin código DIVIPOLA
  (SANTIAGO DE CALI, TUMACO, VALLE, NARINO, BOGOTA D.C.).
- `ent_id` y `ent_nombre`: la EPS. «-CM» son afiliados por movilidad entre regímenes.
- `cantidad`: el conteo de la celda. Muchas celdas por sexo, edad y zona valen 1.

## Trampas medidas (2026-11-05)

- Sin fecha del corte en las filas: el total de un municipio cambia de un mes a otro. Cali dio
  1 492 604 en 17 EPS el 2026-10-28 y 1 496 849 en 16 EPS el 2026-11-05.
- Los nombres no coinciden con DIVIPOLA. Se resolvió con la comparación sin tildes y con «X de
  nombre» en los dos sentidos: Cali, Bogotá, Medellín y Tumaco salen.

## Decisiones

- ADR-0014: se agrupa en la fuente por municipio y EPS. Las celdas por sexo, edad y zona no salen.
- Avisos: el de vacío sugiere el nombre corto y la grafía de la ADRES, y el de encontrado dice que
  la cifra es la del último corte mensual, sin fecha en las filas.
