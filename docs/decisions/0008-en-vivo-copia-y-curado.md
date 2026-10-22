# ADR-0008 · En vivo, copia y curado

- **Estado:** propuesta.
- **Decisión:** tres modos por fuente en el catálogo:
  `en_vivo` (por defecto), `copia` (fuente abierta en bloque copiada completa y actualizada, cuando
  mejora latencia o resiste caídas, p. ej. normativa, jurisprudencia, SECOP si se decide) y `curado`
  (dataset unido y versionado por nosotros, p. ej. restricciones).
- **Caché:** TTL por fuente según su frescura; si la fuente cae y hay copia en caché, se sirve **con
  `servido_desde: obsoleto` y su `consultado_en` original**, nunca como actual; el cliente puede pedir
  `frescura=estricta` para recibir error en su lugar.
- **Consecuencias:** la copia de una fuente BY-SA hereda BY-SA; nada con datos personales se copia
  sin la decisión de ADR-0014.
