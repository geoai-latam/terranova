# TransMilenio: paraderos zonales del SITP

Fuente `transmilenio.paraderos_zonales`. Herramienta: `transmilenio_paraderos_en_zona`.

## Qué es

Capa 0 de `gis.transmilenio.gov.co/arcgis/rest/services/Zonal/consulta_paraderos/FeatureServer`:
los 7 610 paraderos (2026-11-04) de los buses azules, alimentadores, complementarios y servicios
especiales. Van en una copia espacial (ADR-0024) que se bajó en 12 s.

## Licencia

Ítem «Paraderos Zonales del SITP» (70b111e96b514bdfb36a7eb532d0eb4f), con la misma autorización
y cita que las demás capas de TransMilenio. El portal la marca CC BY 4.0.

## Lo medido

- El servicio está en EPSG:3116; la copia pide EPSG:4326. Trae latitud y longitud como atributos;
  se usa la geometría.
- `tipo_m_s` (S 5 600, M 1 653, vacío 357) y `cantidad_mm` no tienen diccionario: salen tal cual.
  `estado_multiple` dice si el paradero múltiple está implementado (1 172) o proyectado (78).
- La consola repite dirección y cenefa: no se copia.
- Canario: 87 paraderos en [-74.065, 4.65, -74.05, 4.665] (76 en Chapinero, 11 en Barrios
  Unidos); la copia da lo mismo.

## Lo que no trae

- Qué rutas paran en cada paradero.
- Las estaciones troncales: `transmilenio.infraestructura_troncal`.
