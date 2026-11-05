# Infraestructura energética de la UPME (`upme.infraestructura_energetica`)

Cuatro capas nacionales del geoportal de la UPME (`geo.upme.gov.co/server`), juntas en una copia
espacial con una columna `tipo`. Responde a «quiero una capa limpia de infraestructura crítica de
esta zona» con una sola llamada: `upme_infraestructura_energetica_en_zona`.

## Qué publica

| Capa | Servicio | Elementos (2026-11-04) | Lo propio de la capa |
|---|---|---|---|
| Subestaciones construidas | `Capas_EnergiaElectrica/sistema_transmision_subestaciones_construidas/FeatureServer/18` | 514 | tensión, sistema (STN/STR), AIS/GIS, propietario, municipio |
| Líneas de transmisión construidas | `Capas_EnergiaElectrica/Sistema_transmision_lineas_construidas/FeatureServer/17` | 798 tramos | tensión, sistema, aéreo/subterráneo, longitud, propietario |
| Centrales de generación (XM) | `Capas_EnergiaElectrica/proyectos_generacion_xm/FeatureServer/24` | 687 | capacidad efectiva neta (MW), tipo de generación, estado, agente |
| Ductos de hidrocarburos | `Capas_Hidrocarburos/ductos_hidrocarburos/FeatureServer/3` | 193 tramos | oleoducto, gasoducto, poliducto…; sistema; capacidad y unidad; operador |

La copia trae 2192 filas, las mismas que suman las cuatro capas. Tardó 144 s y no hubo filas
repetidas.

## Licencia

El servicio no declara licencia: `copyrightText` está vacío y el portal de la UPME respondió 403 el
2026-11-04. Es una entidad pública y la capa no tiene datos personales ni reserva, así que va como
**ámbar** (dato público reutilizable, ADR-0019 enmienda), con el aviso de la puerta. Si la UPME
publica sus términos, se verifica y pasa a verde.

## Trampas medidas

1. **Cada capa tiene su esquema.** La tensión solo viene en subestaciones y líneas, los MW solo en
   centrales y la capacidad de transporte solo en ductos. En la copia, las columnas que una capa no
   tiene salen vacías (`copia.opcionales`), no en cero.
2. **-999 y «Sin información».** Los ductos usan -999 en la capacidad y en el número de líneas, y
   «Sin información» en el operador. Se publican como vienen; la ficha y la descripción lo dicen.
3. **La tensión no siempre coincide con el nombre.** «BACATÁ - NOROESTE 230 KV» trae 500 kV en el
   campo. Es lo que publica la UPME.
4. **Una línea son varios tramos.** En el rectángulo de Bogotá, «SISTEMA BOGOTA» aparece en 10
   tramos. El conteo es de tramos, no de circuitos.
5. **Fechas en dos formatos.** Subestaciones y líneas traen `fecha_operacion` como texto d/m/aaaa;
   las centrales, en milisegundos. No se copia, para no mezclar formatos.
6. **Coordenadas.** El servicio está en EPSG:9377 y la copia pide EPSG:4326.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `upme_infraestructura_energetica_en_zona` | alto | nueva (2026-11-04) |

Medido contra la copia el 2026-11-04, desde Colombia por túnel, así que el tiempo incluye la red:

| Rectángulo | Elementos | Desglose | Tiempo |
|---|---|---|---|
| Bogotá y alrededores (`[-74.5, 4.0, -73.5, 5.0]`) | 256 | 138 tramos de línea, 77 subestaciones, 24 centrales (1220 MW), 17 ductos | 4,8 s |
| Medellín | 101 | — | 1,3 s |
| Vaupés | 0 | `no_encontrado`, con el aviso de que no cubre la red de distribución | — |

## Decisiones

- **2026-11-04:** se juntan en una copia, y no en cuatro herramientas, porque la pregunta de quien
  la pide es «qué infraestructura crítica hay aquí». Las capas de detalle (torres, convocatorias,
  estaciones de servicio, procesamiento de hidrocarburos con 20 295 puntos, pozos de la ANH)
  quedan para después. La de procesamiento hay que mirarla primero por categoría.
- **Salud, educación, telecomunicaciones:** no hay capa oficial nacional con geometría y licencia
  usable. El REPS no trae coordenadas; las sedes del MEN en el servicio SISE no declaran licencia,
  y las de datos.gov.co (`x5ay-984n`, CC BY-SA) son de 2019. Siguen como pendientes.
