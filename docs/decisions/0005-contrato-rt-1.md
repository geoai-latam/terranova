# ADR-0005 · Contrato `rt/1`

- **Estado:** propuesta.
- **Decisión:** un sobre común (especificación en [specs/01-contrato-rt1.md](../specs/01-contrato-rt1.md)) con estado (`encontrado`, `no_encontrado`,
  `fuera_de_cobertura`, `parcial`), procedencia por fuente (entidad, URL, licencia SPDX, atribución,
  `modo`, `consultado_en`, versión, huella, completitud, caché), avisos y errores con código. Para la
  geometría incluye un bloque `geo_result` compatible con `GeoResult` v1, así GEO Copilot lo pinta
  sin adaptador.
- **Por qué no basta un sobre mínimo:** sin licencia ni completitud no hay procedencia verificable, y el diferencial
  es justamente la procedencia verificable. Se toman sus buenas ideas: `found`, `served_from`,
  `checked_at`, error con `type/code/param`.
- **Confirmación:** JSON Schema exportado y verificado en CI (`--check`), pruebas de propiedad
  (`vistos ≤ total`, `parcial ⇒ errores ≠ ∅`, toda fuente usada tiene procedencia y licencia) y
  prueba de que el hub de GEO Copilot materializa el bloque `geo_result` (spike F0).
