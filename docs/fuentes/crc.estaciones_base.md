# CRC, Postdata: sitios de estaciones base por municipio (`crc.estaciones_base`)

El archivo `F3_RES175_2.csv` del conjunto «Infraestructura de redes de acceso móvil» de Postdata,
la plataforma de datos de la CRC. Lo reportan los operadores móviles con el formato 3 de la
Resolución MinTIC 175 de 2021. Terrnova lo sirve desde una copia (ADR-0024, origen `csv`).

| Fuente | Archivo | Periodo | Herramienta |
|---|---|---|---|
| `crc.estaciones_base` | `F3_RES175_2.csv` (11,5 MB, del 2026-09-16) | 2021-2T al 2026-2T | `crc_estaciones_base_municipio` |

## Qué publica

Una fila son los sitios de un operador en un municipio y un trimestre, con una combinación de
tecnologías (2G, 3G, 4G, 5G) y un tipo de sitio (propio o en coubicación). Un sitio es una
ubicación física con estaciones base. Se actualiza cada trimestre.

## Licencia

El recurso dice «Licencia no especificada» y el federado de datos.gov.co (`pyy9-82ts`) no trae
licencia. Rigen los términos de uso de Postdata
(<https://www.postdata.gov.co/terminos-y-condiciones-de-uso-de-postdata>): uso, redistribución y
transformación libres, con la cita «Datos recuperados de Postdata» y la fecha de la última
actualización del conjunto. Leído el 2026-11-05.

## Campos que importan

- `CODIGO_DANE_MUNICIPIO`: DIVIPOLA sin el cero inicial (5001 para Medellín). La copia lo rellena a
  5 dígitos.
- `SITIO_PROPIO_COUBICACION`: 1 = propio, 2 = coubicación (Resolución 175, formato 3, variable 10).
- `TECNOLOGIA_ESTACION_BASE_2G/3G/4G/5G`: 1 si la fila tiene esa tecnología y 0 si no.
- `SITIOS`: número de sitios con esa combinación.

## Cobertura

Medido el 2026-11-05: 144 414 filas, del 2021-2T al 2026-2T. El 2026-2T suma 35 675 sitios en
1 100 municipios.

## Trampas medidas

1. **No hay coordenadas.** El formato 3 pide latitud y longitud de cada sitio, pero la CRC solo
   publica el conteo por municipio. No existe una capa pública nacional de antenas: la ANE no
   publica una, y el conjunto de la ANE `xhu9-3dq9` son mediciones de campos electromagnéticos, no
   antenas.
2. **La Resolución codifica cada tecnología como 1 = sí, 2 = no; el CSV publica 1 y 0.**
3. **203 filas no tienen ninguna de las cuatro tecnologías** (otra tecnología, sin medir cuál).
4. **Una torre puede contar para varios operadores:** cada operador cuenta sus sitios, y los de
   coubicación son infraestructura de otro propietario. El total no es el número de torres.
5. **El DIVIPOLA viene sin el cero inicial.**

## Decisiones

- Copia trimestral del CSV; consulta por municipio, año y trimestre.
- Derivados: total de sitios, sitios con 2G, 3G, 4G y 5G, sitios en coubicación y sitios por
  operador.
- El aviso `encontrado` dice que es un conteo municipal sin puntos y que el total no es el número
  de torres.
- Canario: Chía 2026-2T, 145 sitios (16 con 2G, 99 con 3G, 145 con 4G, 23 con 5G, 102 en
  coubicación), medido en el CSV el 2026-11-05.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `crc_estaciones_base_municipio` | medio | v1: conteo por municipio y trimestre; le falta la cobertura por centro poblado (`Datos_Cobertura_Movil_1T_2023-4T_2025.csv`, 73,8 MB) |
