# ANT, consejos comunitarios titulados (`ant.consejos_comunitarios`)

La capa «Consejo Comunitario Titulado» de la Agencia Nacional de Tierras: los territorios colectivos
de comunidades negras (Ley 70 de 1993). Está en un FeatureServer de ArcGIS (capa 0, servicio
`DatosAbiertos/Consejo_Comunitario_Titulado`) detrás del proxy público de ArcGIS Online. Licencia
CC BY-SA 4.0, con la cita en la ficha (ítem `abf2f9f6727b4073902c1f57c280d5dc`, verificada el
2026-10-28). Desde el 2026-11-05 se sirve de una copia de Terrnova en PostGIS con los polígonos
completos.

## Qué publica

Un polígono por consejo titulado, con:

- `NOMBRE`;
- `DEPARTAMENTO` y `MUNICIPIO` (DIVIPOLA);
- el último acto administrativo (tipo, número y fecha);
- `AREA_TOTAL_ACTOS_ADMIN`: el área según los actos, en ha.

No trae personas: ni representantes legales ni miembros.

## Cobertura

347 consejos en el país (medido el 2026-11-05 en la fuente y en la copia). Los municipios con más:
Buenaventura (76109), 41; Tumaco (52835), 20; Riohacha (44001), 14.

## Trampas medidas

1. **Solo títulos formalizados.** Las solicitudes en trámite no están en esta capa.
2. **Un territorio, un municipio.** `MUNICIPIO` trae un solo código aunque el territorio cruce
   varios: por municipio salen solo los anotados allí.
3. **Un municipio escrito con nombres.** Uno de los 347 trae «Maguí Payan y Roberto Payan» en vez
   del código, así que no sale por municipio.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ant_consejos_comunitarios_en_punto` | medio | v3: sobre la copia, con aviso de vacío; con `geometria`, el polígono completo |
| `ant_consejos_comunitarios_en_poligono` | alto | v1: «¿este lote cae en un territorio colectivo?», con las hectáreas dentro del lote |
| `ant_consejos_comunitarios_en_zona` | medio | v1: por rectángulo; para pintar la capa |
| `ant_consejos_comunitarios_municipio` | medio | v1: los que la ANT anota en el municipio, con su aviso |

## Decisiones

- **2026-11-05, copia y herramientas por zona y municipio:**
  - **Copia:** origen `arcgis`, capa 0, clave `OBJECTID`, 25 por página, índice en `MUNICIPIO`,
    sin `tolerancia`: los polígonos se guardan completos. En vivo, la forma completa de un
    territorio grande tardaba más de 90 s. Ingerida en producción el 2026-11-05 (tabla
    `copia.ant_consejos_comunitarios_20261105160017654739`): 347 filas, 571 226 vértices, todas
    las geometrías válidas.
  - **Geometría fiel:** el cruce usa siempre la forma completa. La de polígono va de a 20 por
    página y por eso `geometria` la devuelve entera. La de zona y la de municipio van de a 1000,
    simplificadas a unos 55 m, con el aviso del motor.
  - **Medido en la fuente el 2026-11-05** (returnCountOnly), igual en la copia:
    - Franja de Buenaventura (canario de polígono): 7, y 14 con su rectángulo.
    - Rectángulo [-77,5, 5, -76,5, 6]: 33.
    - `MUNICIPIO = 76109`: 41.
