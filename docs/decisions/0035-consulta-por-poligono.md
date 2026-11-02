# ADR-0035 · Consulta por polígono en las copias espaciales

- **Estado:** aceptada (2026-11-01). Sigue a la [ADR-0024](0024-conector-de-copia.md) y usa el `poligono` que el
  contrato `rt/1` ya tenía en `zona_usada` ([ADR-0005](0005-contrato-rt-1.md)).
- **Contexto:**
  - La pregunta de negocio es «¿qué restricciones tiene este lote?», y un lote es un área. Hoy las
    herramientas van por punto, por código o por un rectángulo: 8 por zona y ninguna por polígono.
  - Un rectángulo sobre un lote irregular trae lo que está al lado. Un punto se pierde lo que toca
    solo una esquina.
  - 13 fuentes ya tienen copia con geometría e índice espacial en PostGIS.
- **Decisión:**
  1. **Tipo de entrada `poligono`:** un GeoJSON `Polygon` en EPSG:4326, sin `MultiPolygon` por ahora.
     La puerta lo valida antes de consultar.
  2. **Topes:** 500 vértices y 1 grado de lado (unos 110 km). Es un lote o una finca, no un
     departamento: por encima responde `parametro_invalido`, con el tope en el mensaje.
  3. **Solo sobre copias.** El cruce corre en nuestro PostGIS. En vivo sería mandar polígonos a
     servidores del Estado sin saber lo que cuesta, y la regla es no cargarlos.
  4. **Se reparan los polígonos que se cruzan a sí mismos** con `ST_MakeValid`, como al cargar las
     copias. El vértice llega como parámetro, nunca dentro del SQL.
  5. **Herramientas `…_en_poligono` propias,** no un parámetro más en las de zona: cada una lleva su
     canario y su dorada, y el agente no tiene que elegir entre `bbox` y `poligono`.
- **Consecuencias:**
  - Una fuente en vivo necesita copia antes de cruzarse por polígono.
  - Los resguardos de la ANT y otras capas en vivo quedan fuera de la ficha de un lote hasta tener
    copia, y la ficha lo dice.
  - Lo que se simplificó al ingerir sigue simplificado: el cruce es tan fino como la copia
    (agrología ~11 m, SINCHI ~55 m).
- **Confirmación:** medido el 2026-11-01 con el mismo anillo en PostGIS y en la capa publicada
  (`esriGeometryPolygon`, intersects): 6 lotes de URT y 6 de RUNAP con el mismo resultado exacto. En
  los 5 primeros el rectángulo traía lo mismo; por eso los canarios usan el sexto, una franja en
  diagonal donde el rectángulo trae más (7 contra 4 en URT, 12 contra 2 en RUNAP). URT se comparó
  con su copia completa y RUNAP con las áreas de cada lote, sin rehacer la copia. Hay pruebas de los
  topes y de la entrada inválida.
