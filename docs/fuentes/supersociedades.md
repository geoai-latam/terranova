# Supersociedades: estados financieros NIIF y las 10 000 empresas (`supersociedades.*`)

Seis conjuntos de datos.gov.co, publicados por la Superintendencia de Sociedades con licencia CC BY-SA
4.0. Se consultan en vivo. Cinco son los estados financieros que las sociedades vigiladas reportan
en XBRL. El sexto es el reporte de las 10 000 empresas más grandes.

| Fuente | Conjunto | Herramienta |
|---|---|---|
| `supersociedades.niif_situacion_financiera` | `pfdp-zks5` | `supersociedades_situacion_financiera` |
| `supersociedades.niif_resultado_integral` | `prwj-nzxa` | `supersociedades_resultado_integral` |
| `supersociedades.niif_flujo_efectivo` | `ctcp-462n` | `supersociedades_flujo_efectivo` |
| `supersociedades.niif_otro_resultado_integral` | `y3gh-x5g7` | `supersociedades_otro_resultado_integral` |
| `supersociedades.niif_caratula` | `6hqw-m3dm` | `supersociedades_caratula` |
| `supersociedades.empresas_grandes` | `6cat-2gcs` | `supersociedades_empresa_grande_por_nit` |

## Qué publica

- **NIIF:** una fila por concepto, periodo y reporte. Cada reporte trae «Periodo Actual» y «Periodo
  Anterior». Una sociedad con subsidiarias reporta el estado separado y el consolidado del mismo
  corte (`punto_entrada`), y una pyme reporta el individual. Hay de 2015 a 2025; en la carátula
  son 29 219 reportes del corte 2025.
- **10 000 empresas:** una fila por empresa y año de corte (2021 a 2025), con ingresos,
  ganancia, activos, pasivos y patrimonio en billones de pesos.

## Campos que importan

- `valor` (NIIF): **en miles de pesos.** La unidad solo la declara la carátula, en el concepto
  «Unidad de diligenciamiento utilizada en este reporte», y solo desde el corte 2025. Medido el
  2026-11-02:
  - en 2025 la declaran 29 211 de los 29 219 reportes, todos «MILES DE PESOS»;
  - antes de 2025 ningún reporte la declara;
  - de 2022 a 2024 los valores cuadran con las 10 000 empresas en miles de pesos. En Alpina, el
    total de activos separado fue 1 581 896 347 en 2022, 1 536 664 368 en 2023 y 1 431 184 168 en
    2024, frente a $1.58, $1.54 y $1.43 billones. En Integral S.A. fue 252 177 848 y en Royal Films
    250 164 365 en 2022, frente a $0.25 billones en los dos;
  - antes de 2022 no hay con qué compararlo: sin verificar.
- `punto_entrada`: «20 NIIF Plenas - Separado Grupo 1», «30 … Consolidado …», «40 NIIF Pymes -
  Individual Grupo 2». En Alpina 2023 hay dos «Total de activos, Periodo Actual»: 1 536 664 368
  (separado) y 1 689 053 919 (consolidado).
- `concepto`: algunas tildes llegan dañadas desde la fuente («Ganancia (p�rdida)»).
- Cifras de las 10 000 (`ingresos_operacionales` y las demás): **texto con signo de pesos y dos
  decimales** («$84.95»; «$ 2.31», con espacio, desde 2025; «-$0.00»). El redondeo es de ±0,005
  billones, unos ±5 000 millones. En 2024, 1 528 empresas salen con ingresos de «$0.02» y 1 826 con
  «$0.03».

## Cobertura

- NIIF: las sociedades vigiladas por Supersociedades. Las que vigila otra superintendencia no salen.
  Una pyme que dejó de reportar se queda en su último corte: 830010665 llega a 2018.
- 10 000 empresas: también trae vigiladas por otras superintendencias (Ecopetrol:
  SUPERFINANCIERA).

## Trampas medidas

1. **Cifras sin unidad.** Un agente que lea 1 344 661 181 puede decir «1 344 millones»: son 1,34
   billones (Alpina, total de activos 2025).
2. **Separado y consolidado juntos.** Sumarlos o compararlos sin mirar `punto_entrada` da cifras
   que no existen.
3. **Las 10 000 redondeadas.** Para la mayoría de las empresas la cifra no dice nada, y una
   ganancia de «-$0.00» es una pérdida menor que 5 000 millones.
4. **Filas repetidas:** Integral S.A. 2022 trae dos veces el total de activos del separado y dos
   veces el del consolidado. Por qué, sin medir.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `supersociedades_situacion_financiera` (v3) | medio | avisa la unidad y el separado/consolidado; faltan el filtro por corte y el volumen (487 filas en Alpina) |
| `supersociedades_resultado_integral` (v3) | medio | igual |
| `supersociedades_flujo_efectivo` (v3) | medio | igual |
| `supersociedades_otro_resultado_integral` (v3) | bajo | igual |
| `supersociedades_caratula` | medio | 179 filas de texto; lo útil cabe en 10 campos |
| `supersociedades_empresa_grande_por_nit` (v3) | medio | cifras como número y aviso del redondeo; falta el puesto en el ranking |

## Decisiones

- **2026-11-02, error 8 de la revisión de valor:**
  - Las cuatro de estados financieros avisan que los valores están en miles de pesos, con lo
    medido, y que separado y consolidado van por aparte. Ordenan por corte, punto de entrada y
    concepto.
  - El motor suma `moneda` por campo. Las cifras de las 10 000 salen como número, conservando el
    signo de «-$0.00», y la herramienta avisa el redondeo y remite a las NIIF para la cifra exacta.
- **Pendiente:**
  - El puesto en el ranking de las 10 000, que pide una segunda consulta.
  - Por defecto, solo el último corte y el periodo actual.
  - Arreglar las tildes de los conceptos.
  - Una ficha corta de la carátula.
