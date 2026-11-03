# IDEAM: normales climatológicas (`ideam.normales_climatologicas`)

Un conjunto de datos.gov.co, publicado por el IDEAM con licencia CC BY-SA 4.0. Se consulta en vivo.

| Fuente | Conjunto | Herramientas |
|---|---|---|
| `ideam.normales_climatologicas` | `nsz2-kzcq` | `ideam_normales_climatologicas_estacion` |

## Qué publica

El valor normal de cada mes y el anual, por estación, variable y periodo de 30 años (1961-1990,
1971-2000, 1981-2010 y 1991-2020). Solo están las estaciones que cumplieron la Directriz 1203 de la
OMM sobre el cálculo de normales.

## Campos que importan

- `c_digo`: el código de la estación, numérico, sin los ceros a la izquierda (28025502). La
  herramienta recibe los 10 dígitos y lo compara como número.
- `par_metro`: la variable, en mayúsculas y con tildes. Son ocho (filas medidas el 2026-11-02):

| Variable | Filas | Unidad | El anual es |
|---|---|---|---|
| PRECIPITACIÓN | 5 458 | mm en el mes | la suma de los meses |
| No. DE DIAS CON LLUVIA ≥ 1 mm | 5 990 | días en el mes | la suma de los meses |
| TEMPERATURA MEDIA, MÁXIMA y MÍNIMA | 992, 929 y 1 091 | °C | el promedio de los meses |
| HUMEDAD RELATIVA | 918 | % | el promedio de los meses |
| BRILLO SOLAR | 825 | horas por día | el promedio de los meses |
| EVAPORACIÓN | 558 | mm por día | el promedio de los meses |

- `ene` … `dic`, `anual`: texto con punto decimal.

## Trampas medidas

1. **La unidad no estaba en el dato.** La ficha del conjunto la dice, pero cada fila no. Un brillo
   solar de 7,4 no dice si son horas al día o al mes.
2. **Brillo solar y evaporación son por día.** La ficha dice «horas» para el brillo solar. Medido:
   ningún mes pasa de 9,3 h ni de 8,7 mm de evaporación en todo el conjunto, así que son promedios
   diarios, no totales del mes.
3. **El anual no siempre suma.** En Valledupar 1991-2020, la precipitación anual (1 016,7 mm) es la
   suma de los meses (1 016,8 por redondeo), y la temperatura media anual (29,1 °C) es el promedio.
4. **Una estación sin normal no es un error.** La de la Universidad de la Sabana se instaló en 2018 y
   no puede tener 30 años.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ideam_normales_climatologicas_estacion` | alto | v2: `unidad` y `anual_es` en cada fila, aviso en el vacío |

## Decisiones

- **2026-11-02, patrón D de la revisión de valor:**
  - Cada fila dice `unidad` y `anual_es`, con un derivado `codigo` sobre la variable.
  - En el vacío, el aviso explica que la normal pide 30 años y remite a `ideam_estaciones_en_zona`.
  - No se busca sola la estación más cercana con normal: pediría una segunda consulta espacial.
    Queda como pendiente si hace falta.
