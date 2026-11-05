# TransMilenio: servicios (rutas) del SITP

Fuente `transmilenio.rutas_sitp`. Herramientas: `transmilenio_rutas_en_zona` (qué rutas pasan por
un rectángulo) y `transmilenio_ruta_buscar` (una ruta por código, origen, destino u operador).

## Qué es

Capa 15 («Servicios») del servicio ArcGIS de planificación del SITP:
`gis.transmilenio.gov.co/arcgis/rest/services/ConsultaSubgerenciaPlanificacionSITP/Consulta_Planificacion_SITP/FeatureServer/15`.
Son 693 servicios (2026-11-04), cada uno en un sentido y con su trazado. Van en una copia espacial
(ADR-0024) que se bajó en 13 s.

## Licencia

Ítem «Servicios de rutas SITP» (5dbc76af14a940939727c45aac1ae8de) del portal de datos abiertos de
TransMilenio: «Se autoriza el uso, aprovechamiento y construcción de análisis con la información
contenida, siempre y cuando se haga la siguiente cita textual: "Fuente: TRANSMILENIO S.A:
www.transmilenio.gov.co"». El portal la marca CC BY 4.0.

## Lo medido

- El servicio está en EPSG:3116; la copia pide EPSG:4326.
- Cada sentido es una fila: la línea GA503 tiene «A503-1» (San Bernardino → Est. Calle 100) y
  «G503-2» (el regreso).
- Las localidades de origen y destino traen dominio en el servicio (0 Soacha, 1 Usaquén… 20
  Sumapaz): salen con su nombre.
- Tipo de ruta, estado, tipo de bus, de servicio, días, tipo de horario, componente y ruta rural son
  códigos sin dominio. El diccionario del ítem dice qué es cada campo, no qué es cada valor, así
  que salen tal cual. Lo observado: `comp_sitp` 2 en 567 servicios y 1 en 126; `tip_bus` de 1 a 6.
- El diccionario dice que `nom_ruta` es el sitio de finalización. En los datos es «origen -
  destino» en las zonales y el código de la línea en otras.
- `created_user` y `last_edited_user` (usuarios internos) no se copian.
- Canario: 95 servicios cruzan [-74.065, 4.65, -74.05, 4.665] (`returnCountOnly`); la copia da lo
  mismo.

## Lo que no trae

- Paraderos: `transmilenio.paraderos_zonales`. Qué rutas paran en cada paradero no está en
  ninguna de las dos capas.
- Frecuencias y tiempos de recorrido: el GTFS estático más reciente en el portal es de 2021.
- Posición de los buses en tiempo real: el GTFS-RT de TransMilenio responde HTTP 500 (2026-11-04).
