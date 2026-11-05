# Bogotá: estaciones de calidad del aire (RMCAB)

Fuente `bogota.calidad_aire_estaciones`. Herramienta: `bogota_calidad_aire_estaciones_en_zona`.

## Qué es

La ubicación de las 20 estaciones de la Red de Monitoreo de Calidad del Aire de Bogotá (RMCAB),
que opera la Secretaría Distrital de Ambiente (SDA). Dos son móviles (Móvil 7ma y Móvil
Fontibón).

- **Capa:** `mapas.ambientebogota.gov.co/server/rest/services/Calidad_aire/Estacion_calidad_aire/MapServer/0`.
- **Copia:** se baja a mano desde Colombia, como las demás capas del Distrito. Es una copia
  espacial en la tabla `bogota_calidad_aire_estaciones`.
- **Herramienta:** por rectángulo, con el punto, el nombre, el código, la dirección, la sede, la
  altitud y la altura de la toma.

## Licencia

Paquete `estaciones-calidad-del-aire-bogota-d-c` del portal datosabiertos.bogota.gov.co, que
apunta a la capa 0: `license_id: CC-BY-4.0`. Verificada el 2026-11-05 en
<https://datosabiertos.bogota.gov.co/api/3/action/package_show?id=estaciones-calidad-del-aire-bogota-d-c>.

## Las mediciones no entran

El visor de la RMCAB (`rmcab.ambientebogota.gov.co`) muestra las mediciones, pero no publica una
licencia ni una API documentada, y el portal de datos abiertos no tiene un paquete con las
mediciones de las estaciones (búsquedas «calidad del aire», «rmcab», «PM2.5», «IBOCA» del
2026-11-05). Sin licencia verificada no se suman (ADR-0019).

El portal sí publica, con CC BY 4.0, las superficies interpoladas de PM2.5, PM10 y ozono por año
(`pm-25-promedio-anual-bogota-d-c` y otras). Son candidatas para una herramienta por punto.

## Lo medido (2026-11-05)

- **Filas:** 20 estaciones; el código es único.
- **Proyección:** la capa está en EPSG:4686; la copia pide EPSG:4326.
- **Campos que no se copian:**
  - `proposito`, `administrador`, `sect_loc` y `activo`: códigos (01, 02…) sin tabla publicada;
  - `url`: fichas PDF en una IP del servidor viejo (`190.27.245.107`).
- **Siete estaciones más nuevas** (Colina, Usme, Ciudad Bolívar, Jazmín, Fontibón y las dos
  móviles): no traen altitud ni altura sobre el suelo, y en la sede repiten la dirección.
- **Texto roto en la fuente:** «Ciudad Bolívar», «Jazmín» y la sede de Guaymaral traen la «í»
  rota.
- **Códigos con espacio:** `COL` y `USM` vienen con un espacio delante.
- **Canario:** 5 estaciones en [-74.12, 4.6, -74.06, 4.67] (CDAR, JAZ, MAM, MOV y PTE), medidas
  en la capa y en la copia.

## Lo que no trae

- Las mediciones de cada estación.
- Las estaciones del resto del país.
