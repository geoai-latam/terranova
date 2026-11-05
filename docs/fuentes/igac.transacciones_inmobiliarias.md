# IGAC, registro de transacciones inmobiliarias 2015–2023 (`igac.transacciones_inmobiliarias`)

## Qué publica

- Una fila por anotación registral de la SNR (30,9 millones), consolidada por el IGAC en
  datos.gov.co (`7y2j-43cv`). Licencia CC BY-SA 4.0.
- Años de radicación de 2015 a 2023. Datos sin cambios desde el 2025-04-04 (ficha cosechada).

## Campos que importan

- `matricula`: oficina de registro y número del folio (`50N-20849403`). `orip` es el prefijo.
- `num_anotacion`, `fecha_radica_texto`, `year_radica`: la anotación y cuándo se radicó.
- `cod_natujur` y `nombre_natujur`: el acto (125 = compraventa).
- `valor` y `tiene_valor`: el valor solo viene desde 2021. Sin valor, `valor` viene nulo, no 0: el
  promedio no se hunde (Chía 2021: 3 744 compraventas, 2 836 con valor y 908 nulas; medido el
  2026-11-05).
- `count_a` y `count_de`: cuántos intervinientes reciben y otorgan, sin nombres.
- `divipola`, `municipio`, `departamento`, `tipo_predio_zona` (URBANO o RURAL) y
  `fecha_apertura_texto` (apertura del folio).
- `numero_catastral` viene vacío en todas las filas (ficha cosechada el 2026-10-22).
- `documento_justificativo` (escritura, notaría o juzgado) no sale (ADR-0014).

## Trampas medidas (2026-11-05)

1. **El promedio de SoQL trae 8 decimales** (250271740.84908321 en Chía 2021). Se redondea al
   peso.
2. **Un folio puede empezar a media historia:** 50N-20849403, abierto el 2019-04-08, empieza en la
   anotación 2.
3. **`year_radica` es texto:** `year_radica = 2021` falla con «type-mismatch»; va entre comillas.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `igac_compraventas_municipio` | alto | por año: compraventas, con valor y promedio al peso; aviso en el vacío |
| `igac_transacciones_folio` (v2) | alto | la historia del folio, ahora con municipio, zona, oficina y apertura; avisos de cobertura |

## Decisiones

- **2026-11-05, revisión de valor:** el folio sacaba 11 columnas de las que publica la fuente y
  dejaba fuera el municipio, la zona y la fecha de apertura; ahora salen. Los dos vacíos dicen por
  qué, y el folio encontrado avisa que solo están 2015–2023 y que no es el certificado de tradición.
