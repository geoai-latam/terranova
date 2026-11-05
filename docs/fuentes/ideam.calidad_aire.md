# IDEAM: calidad del aire del SISAIRE (`ideam.calidad_aire`)

Las mediciones horarias de calidad del aire del SISAIRE del IDEAM, en datos.gov.co (`g4t8-zkc3`),
con licencia CC BY-SA 4.0. Reúne las redes de las autoridades ambientales (SDA en Bogotá, AMVA en el
Valle de Aburrá, la CAR en Chía…). Se consulta en vivo y la consulta agrega por estación y
contaminante en el año.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `ideam.calidad_aire` | `g4t8-zkc3` | `ideam_calidad_aire_municipio` |

## Qué publica

Una fila por hora, estación y contaminante, con:

- la concentración estándar (`med_concentracion_estandar`, en µg/m³ también para el CO);
- la fecha de inicio de la medición;
- la estación, la autoridad (`nombre_fgda`) y el municipio.

## Campos que importan

- `codigo_municipio`: el DIVIPOLA **sin ceros a la izquierda** (5001 para Medellín). Por eso la
  consulta usa `('{divipola}')::number::text`.
- `msfl_code`: el contaminante (PM2.5, PM10, O3, NO2, SO2, CO).
- `med_fecha_inicio`: texto; el año se filtra con `like 'AAAA-%'`.

## Cobertura

- De 2020 a 2025, y solo municipios con estaciones.
- Medido el 2026-11-03:
  - Medellín 2025: 20 estaciones y 36 series;
  - Bogotá 2024: 21 estaciones y 109 series;
  - Chía 2024: una estación de la CAR, con PM10 y PM2.5.

## La norma (Resolución 2254 de 2017, Tabla 1, vigente desde 2018)

Leída en la tabla del texto oficial (normas.cra.gov.co, imagen de la Tabla 1), el 2026-11-03.

| Contaminante | Límite (µg/m³) | Tiempo de exposición |
|---|---|---|
| PM10 | 50 | anual |
| PM10 | 100 | 24 horas (75 desde el 1 de julio de 2018, parágrafo 1 del art. 2) |
| PM2.5 | 25 | anual |
| PM2.5 | 50 | 24 horas (37 desde el 1 de julio de 2018) |
| SO2 | 50 | 24 horas |
| SO2 | 100 | 1 hora |
| NO2 | 60 | anual |
| NO2 | 200 | 1 hora |
| O3 | 100 | 8 horas |
| CO | 5 000 | 8 horas |
| CO | 35 000 | 1 hora |

La Tabla 2 fija metas más bajas a partir de 2030; la herramienta no las usa.

## Trampas medidas

1. **Promedios sin norma no responden «¿el aire es bueno o malo?».** El PM2.5 de Medellín está entre
   14 y 24 µg/m³, y sin el límite de 25 no se sabe si cumple.
2. **Una serie con pocas horas no es el año.** El Politécnico JIC (S) tiene 110 horas de PM10 en
   2025; Mochuelo, en Bogotá, tiene 3 105 horas de PM10 en 2024 con un promedio de 65,4. Comparar eso
   con el límite anual es engañoso.
3. **Decimales sin sentido.** Venía 19,535869510978046.
4. **Solo se pueden comparar los límites anuales y los de una hora.** Con promedios del año y el
   máximo horario no se calculan los de 8 y 24 horas.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ideam_calidad_aire_municipio` | medio → alto | v2: norma anual y horaria por serie, `supera_norma_anual`, horas sobre la norma horaria, resumen y estaciones de peor a mejor |

## Decisiones

- **2026-11-03, revisión de valor:**
  - **En la consulta (SoQL)** se calculan:
    - `norma_anual`, para PM10, PM2.5 y NO2;
    - `norma_horaria`, para NO2, SO2 y CO;
    - `supera_norma_anual` («sí», «no» o «pocas horas»);
    - `horas_sobre_norma_horaria`.
  - **«Pocas horas»** es el criterio de Terrnova: menos de 6 570 horas, el 75 % de un año.
  - **Orden:** el contaminante, y dentro de él la estación con el promedio más alto primero.
  - **Resumen:** `estaciones` y `series_sobre_norma_anual`.
  - **Decimales:** promedio y máximo con uno.
- **Medido el 2026-11-03:**
  - Bogotá 2024: cuatro series sobre la norma anual, entre ellas el PM10 de Carvajal-Sevillana
    (69,9 µg/m³) y de la estación móvil de Fontibón (56,9). La móvil de Fontibón también tuvo 3 horas
    de NO2 sobre 200.
  - Medellín 2025: una serie, el PM10 de Altavista (52,5).
  - Chía 2024: PM10 de 19,5 y PM2.5 de 10,9, sin superar la norma.
- **Pendiente:** pasarla a copia por año (era lenta: el canario tardó 40 s el 2026-11-02 y 8 s el
  2026-11-03) y calcular los límites de 24 horas con promedios diarios.

## Revisión de valor (2026-11-04)

- **Probado en producción:**
  - Bogotá 2025: 104 series de 21 estaciones, 2 sobre la norma anual, en 32,8 s. Pasa el tope de
    20 s del canario, que es Medellín. Por eso sigue pendiente la copia.
  - Chía 2025: una estación con unas 2 216 horas, que da «pocas horas», bien.
  - Cali 2019: vacío, sin aviso.
- **Arreglo:**
  - `cobertura.desde_anio: 2020`: 2019 da `fuera_de_cobertura` y lo dice.
  - Un aviso en el vacío para el municipio sin estaciones.
