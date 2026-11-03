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
- **Enmienda (2026-11-03), puntos 2 y 4, por un hallazgo de GEO Copilot:**
  - **Punto 4, se rechaza, no se repara.** Un polígono que se cruza a sí mismo, que no tiene área
    (vértices alineados) o que tiene menos de 3 vértices distintos responde `parametro_invalido`.
    El mensaje dice el motivo y, en un cruce, los dos lados que se cruzan.
    - Antes, `ST_MakeValid` lo reparaba en la base. Uno degenerado quedaba como una línea o vacío,
      y salía «no encontrado»: una respuesta falsa a una pregunta mal hecha.
    - La validación corre en la puerta, sin la base. El cruce de lados se busca entre todos los
      pares: con 500 vértices son unos 125 000 y tarda unos 100 ms (medido el 2026-11-03).
    - `ST_MakeValid` se queda en la consulta como defensa. Con la validación, ya no cambia nada.
  - **Punto 2, `zona_demasiado_grande`.** Pasar de 500 vértices o de 1 grado de lado responde
    `zona_demasiado_grande`, el código que la spec 01 ya reservaba para eso, no
    `parametro_invalido`.
  - **Los topes van en el esquema.** El esquema del polígono pone `maxItems: 500` por anillo y
    cada vértice como `[lon, lat]`. Los dos topes van también en `x-terrnova-max-vertices` y
    `x-terrnova-max-lado-grados`, porque la suma de vértices de todos los anillos no cabe en JSON
    Schema.
