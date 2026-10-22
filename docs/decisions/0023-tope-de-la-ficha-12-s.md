# ADR-0023 · Tope de la ficha en 12 s: el gate F4 no espera la copia de agrología

- **Estado:** aceptada (2026-10-22). Reemplaza la consecuencia de ADR-0022 que dejaba abierto el
  gate F4 hasta tener la copia.
- **Contexto:**
  - F4.3 pide p95 < 15 s en vivo. Con el tope de 20 s, el p95 lo marcaba la agrología del IGAC, que
    tarda de 30 a 85 s en frío (ADR-0022). La copia depende de una respuesta del IGAC sobre licencia
    y descarga, sin fecha.
  - El dueño decidió no esperar esa respuesta (2026-10-22).
  - La ficha ya no cancela la parte lenta al vencer el tope: sigue en segundo plano y llena la caché
    (F4.2). La siguiente ficha del mismo lugar sale completa desde la caché.
- **Decisión:**
  - El tope total de la ficha baja de 20 a **12 s** (spec 03). Lo que no llega sale como
    `fuente_lenta` en esa parte y la ficha queda `parcial`, con su aviso.
  - Las partes que no dependen del IGAC responden muy por debajo de 12 s: las restricciones salen
    del curado y los sismos y la cobertura tardan alrededor de 1 s.
  - La copia de agrología sigue como en ADR-0022, cuando se pueda. Al tenerla, se revisa si el tope
    vuelve a subir.
- **Medición (2026-10-22, compose local, 10 fichas en serie en puntos nuevos, sin caché):**
  - Tiempos: 4,4 · 5,9 · 9,1 y siete de 12,2 s.
  - p95 de 12,2 s ✓ (< 15 s); con caché, 0,02 s ✓.
  - 7 de las 10 salieron `parcial`, sobre todo por la agrología (vocación, 47 s de media) y, ese
    día, el catastro del IGAC (de 4 a 8 s por consulta).
- **Consecuencias:**
  - Se cierra F4.3 y, con E2E-07 y E2E-08 en verde, el gate F4.
  - En frío, la ficha sale `parcial` más a menudo. Es el estado honesto: dice qué parte faltó y por
    qué, nunca un dato viejo disfrazado.
  - La alerta `FichaLenta` (p95 > 15 s en 1 h) queda como guarda: con este tope solo se dispararía
    si la puerta misma se degrada.
- **Confirmación:** la medición se repite con `scripts/e2e_ficha.py` o por REST contra el compose.
  El canario de cada parte sigue marcando la lentitud de su fuente.
