# ADR-0022 · Agrología del IGAC en vivo, con caché, hasta tener copia

- **Estado:** aceptada (2026-10-22); su consecuencia sobre el gate F4 la reemplaza ADR-0023.
- **Contexto:**
  - La ficha de un lugar (F4.2) pide al IGAC tres capas de agrología: vocación, capacidad y
    conflictos de uso (`mapas.igac.gov.co/server/rest/services/agrologia/…`).
  - Medido en vivo el 2026-10-22, una consulta por punto tarda de 1 a 2 s en caliente, pero ~45 s
    en la primera después de un rato y con mucha variación entre corridas. Cinco fichas en serie
    tardaron 20, 16, 20, 9 y 9 s: un p95 de 20 s contra la meta de 15 s (spec 05). Con caché,
    0,01 s.
  - ADR-0008 permite `copia` cuando mejora la latencia, y la agrología es estática (P1Y). Lo que
    hay para copiar:
    - El geoportal (`geoportal.igac.gov.co/contenido/datos-abiertos-agrologia`) publica zip
      nacionales de vocación (349 MB) y conflictos (994 MB), del corte 2017. El MapServer de
      conflictos dice 2012: hay que comparar antes de sustituir uno por el otro.
    - Capacidad de uso solo se ofrece por departamento, y los enlaces responden 401.
    - Ninguno declara licencia por ítem. La Res. IGAC 616 de 2020 adopta CC BY 4.0 en general,
      pero su enlace oficial está caído, y los ítems catastrales del IGAC en ArcGIS Online dicen
      BY-SA.
  - Alternativa evaluada (2026-10-22): el IGAC aloja en su ArcGIS Online una capa nacional de
    capacidad de uso (`capacidadusodelatierra`, 64 220 polígonos) que responde en 0,6 s. No se
    adopta: trae «Clase II / Subclase c» en lugar de la unidad «2c» y su descripción, sale de
    estudios departamentales (Cundinamarca 2001) y no de la correlación nacional del MapServer, y no
    declara licencia. Además, solo resolvería una de las tres capas: vocación y conflictos no están
    alojadas a escala nacional.
  - Paginar los 57 000, 64 000 y 548 000 polígonos del MapServer sería carga contra un servidor
    del Estado: no se hace.
- **Decisión:**
  - En M1 la agrología sigue en vivo, con caché de 7 días.
  - Al vencer el tope de la ficha, la consulta sigue en segundo plano y llena la caché (F4.2): la
    lentitud del IGAC no se repite para el mismo lugar.
  - La `copia` se construye como el dataset de F4.1 (pandera, huella, GeoParquet y PostGIS)
    desde los zip oficiales cuando se cumplan dos cosas: la licencia por ítem está verificada
    (ADR-0019) y hay descarga de capacidad de uso. Se pregunta al IGAC por derecho de petición; el
    borrador está en `interno/` y lo envía el dueño.
  - No se precalienta la fuente con consultas sintéticas: eso es carga.
- **Consecuencias:**
  - F4.3 queda a medias: con caché se cumple (p95 0,01 s); en vivo, no, hasta tener copia.
  - El gate F4 (E2E-07 con p95 < 15 s) sigue abierto por esa sola razón. E2E-07 sin el p95 y
    E2E-08 están en verde.
  - Mientras tanto, la ficha en frío puede salir `parcial` con `fuente_lenta` en la agrología.
    Es el estado honesto, nunca un dato viejo disfrazado.
- **Confirmación:** `scripts/e2e_ficha.py` mide el p95 en vivo y con caché; con la copia, la
  procedencia de esas partes dirá `servido_desde: copia` y el p95 en vivo debe bajar de 15 s.
