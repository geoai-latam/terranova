# ADR-0005 · Contrato `rt/1`

- **Estado:** aceptada (2026-10-21).
- **Decisión:** un sobre común (especificación en [specs/01-contrato-rt1.md](../specs/01-contrato-rt1.md)) con estado (`encontrado`, `no_encontrado`,
  `fuera_de_cobertura`, `parcial`), procedencia por fuente (entidad, URL, licencia SPDX, atribución,
  `servido_desde`, `consultado_en`, versión, huella, completitud, caché), avisos y errores con código. Para la
  geometría incluye un bloque `geo_result` que es un `GeoResult` v1 completo, anidado en el sobre.
  GEO Copilot lo pinta desanidándolo de forma genérica (geo-copilot#43, spike F0.4).
- **Por qué no basta un sobre mínimo:** sin licencia ni completitud no hay procedencia verificable, y el diferencial
  es justamente la procedencia verificable. Se toman sus buenas ideas: `found`, `served_from`,
  `checked_at`, error con `type/code/param`.
- **Confirmación:** JSON Schema exportado y verificado en CI (`--check`), pruebas de propiedad
  (`vistos ≤ total`, `parcial ⇒ errores ≠ ∅`, toda fuente usada tiene procedencia y licencia) y
  prueba de que el hub de GEO Copilot materializa el bloque `geo_result` (spike F0).
- **Validación (2026-10-21):** Corregido `modo` → `servido_desde` para alinear con la spec 01. El spike F0.3 ya emite el subconjunto; el bloque `geo_result` se confirma en F0.4.
- **Corrección (2026-10-21, spike F0.4):** decía «GEO Copilot lo pinta sin adaptador», y no era
  cierto: el hub solo reconocía el GeoResult en la raíz. Se mantiene el anidado, para no deformar el
  contrato de todos los clientes por uno, y el hub aprendió a desanidarlo. Además, el GeoResult del
  sobre lleva solo la lista blanca, igual que `datos` (regla 10).
