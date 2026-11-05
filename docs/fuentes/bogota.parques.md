# Bogotá: parques del IDRD

Fuente `bogota.parques`. Herramienta: `bogota_parques_en_zona`.

## Qué es

El inventario geográfico del Sistema Distrital de Parques y Escenarios Públicos Deportivos, que
lleva el Instituto Distrital de Recreación y Deporte (IDRD). Un polígono por parque.

- **Capa:** `visorsrv.idrd.gov.co/srv/rest/services/ParquesIDRD/Parques/MapServer/0`, el servidor
  propio del IDRD (no el de Catastro).
- **Copia:** se baja a mano desde Colombia, como las demás capas del Distrito. Es una copia
  espacial en la tabla `bogota_parques`.
- **Herramienta:** por rectángulo, con el polígono completo, el total y el conteo por escala.

## Licencia

Paquete `sistema-distrital-de-parques-y-escenarios-publicos-deportivos` del portal
datosabiertos.bogota.gov.co, que apunta a la capa 0: `license_id: CC-BY-4.0`. Verificada el
2026-11-05 en
<https://datosabiertos.bogota.gov.co/api/3/action/package_show?id=sistema-distrital-de-parques-y-escenarios-publicos-deportivos>.

## Lo medido (2026-11-05)

- **Filas:** 5 309 polígonos: 3 512 vecinales, 1 649 de bolsillo, 95 zonales, 34
  metropolitanos, 10 escenarios deportivos, 4 regionales y propuestos, y 5 sin tipo.
- **Código del parque:** único salvo el 03-035, que sale en dos polígonos. La clave de la copia
  es `OBJECTID`.
- **Fecha de incorporación:** 3 066 polígonos traen el 2004-01-01, la fecha mínima de la capa, y 3
  vienen sin fecha. Esa fecha no dice cuándo entró cada parque: la herramienta lo avisa.
- **Proyección:** la capa está en EPSG:4686; la copia pide EPSG:4326.
- **Campos que no se copian:**
  - `TIPOLOGIA`, `NIVEL` y `RULEID`: códigos sin tabla publicada;
  - `ADMINISTRA`: solo viene en 138 de los 5 309 polígonos.
- **Canario:** 66 parques en [-74.09, 4.6, -74.06, 4.63], medidos en la capa (intersección con el
  rectángulo) y en la copia.

## Lo que no trae

- La capa «parque» del POT (Secretaría de Planeación): es otra.
- Canchas, gimnasios y demás dotación de cada parque: son otras capas del IDRD.
- El resto del país.
