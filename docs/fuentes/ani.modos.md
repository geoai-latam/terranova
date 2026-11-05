# ANI: puertos, aeropuertos y corredores férreos

Fuentes:
- `ani.puertos`, herramienta `ani_puertos_en_zona`;
- `ani.aeropuertos`, herramienta `ani_aeropuertos_en_zona`;
- `ani.red_ferrea`, herramienta `ani_red_ferrea_en_zona`.

## Qué es

Son las capas 0, 1 y 2 del servicio `Hosted/ModosANI` del ArcGIS Server de la ANI, el mismo de
`ani.peajes` (capa 5) y `ani.concesiones_viales` (capa 3). Se consultan en vivo por zona, con el
conector `arcgis-mcp`.

| Capa | Qué trae | n | Geometría |
|---|---|---|---|
| 0 «Portuarias» | concesiones portuarias | 63 | punto |
| 1 «Areopuertos» (así, con la errata) | aeropuertos concesionados | 19 | multipunto de un punto |
| 2 «Férreo» | corredores con contrato de la ANI | 4 | línea |

## Licencia

CC BY-SA 4.0. La ANI la declara en su página de datos abiertos para «Concesiones ANI», como en
`ani.peajes`.

## Lo medido (2026-11-05)

- Las tres capas no se editan desde el 2023-09-27: todas las filas tienen esa fecha de edición.
- **Puertos:**
  - por zona: Cartagena 30, Buenaventura 11, Santa Marta y Ciénaga 5;
  - por servicio: 43 públicos y 20 privados;
  - `num` e `id_join` repiten el `objectid`, y `url_video` y `url_imag` vienen vacíos: no se
    publican;
  - `fecha_fin` sale como fecha (DEXTON: 2031-09-29).
- **Aeropuertos:**
  - 16 en operación y 3 en estructuración;
  - el enlace a la ficha es el mismo para todos (la portada de fichas del aniscopio).
- **Férreo:**
  - los corredores son Atlántico, Pacífico, Bogotá - Belencito - La Dorada - Chiriguaná y uno en
    estructuración;
  - empleos y población beneficiada vienen vacíos;
  - algunos concesionarios empiezan con un espacio de ancho cero (U+200B), como los publica la
    ANI.
- **Canarios:**
  - 23 puertos en la bahía de Cartagena;
  - El Dorado en Bogotá;
  - la Red férrea del Atlántico por Santa Marta.

## Lo que no trae

- Puertos, muelles y aeródromos sin concesión de la ANI. Son unos 2 000 aeródromos. Las fuentes
  que los traen (UPIT, Fuerza Aeroespacial y MEN) no tienen licencia de reutilización
  verificada.
- Vías férreas sin contrato de la ANI, y estaciones.
