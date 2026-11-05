# TransMilenio: estaciones troncales, TransMiCable y trazados troncales

Fuente `transmilenio.infraestructura_troncal`. Herramienta: `transmilenio_troncal_en_zona`.

## Qué es

Hay tres capas del servicio ArcGIS de planificación del SITP:
`gis.transmilenio.gov.co/arcgis/rest/services/ConsultaSubgerenciaPlanificacionSITP/Consulta_Planificacion_SITP/FeatureServer`.

| Capa | Qué trae | Elementos (2026-11-04) |
|---|---|---|
| 2 | Estaciones troncales | 153 |
| 11 | Estaciones de TransMiCable | 4 |
| 5 | Trazados troncales | 22 |

Van en una copia espacial (ADR-0024) con una columna `tipo`. La copia tiene 179 filas y se bajó
en 84 s.

## Licencia

El ítem de cada capa en el portal de datos abiertos de TransMilenio
(`datosabiertos-transmilenio.hub.arcgis.com`) dice: «Se autoriza el uso, aprovechamiento y
construcción de análisis con la información contenida, siempre y cuando se haga la siguiente cita
textual: "Fuente: TRANSMILENIO S.A: www.transmilenio.gov.co"». El portal marca las capas CC BY 4.0.
La atribución de la ficha es esa cita.

## Lo medido

- El servicio está en EPSG:3116 (MAGNA-SIRGAS Bogotá); la copia pide EPSG:4326.
- `tipo_esta`, `eta_oper` y `esta_oper` no traen dominio en el servicio. Su significado sale del
  diccionario de datos del ítem 5365d814bbdd4062a59234eea7d70db7:
  - tipo: 1 portal, 2 intermedia, 3 intercambio, 4 sencilla, 5 por definir;
  - etapa: 1 operativa, 2 operativa con obras, 3 cierre temporal por obras, 4 cierre temporal por
    otras causas;
  - estado: 1 existente.
- Canario: en [-74.10, 4.62, -74.04, 4.68] (Teusaquillo y Chapinero) hay 32 estaciones troncales,
  0 de cable y 8 trazados (`returnCountOnly`). La copia da lo mismo, en 2,1 s por el túnel.
- Calle 45 y Calle 63 salen con etapa 3, cierre temporal por obras.

## Lo que no trae (y dónde está)

- Rutas troncales y zonales con horarios (capa 15) y paraderos zonales (7 610): siguiente tarea.
- Validaciones y salidas por estación: el bucket `validaciones_tmsa` responde 403 (2026-11-04).
- Posición de los buses en tiempo real: el GTFS-RT `gis.transmilenio.gov.co/gtfs/` responde
  HTTP 500 (2026-11-04).
