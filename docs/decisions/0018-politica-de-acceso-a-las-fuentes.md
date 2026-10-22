# ADR-0018 · Política de acceso a las fuentes

- **Estado:** aceptada (2026-10-21).
- **Contexto:** para cubrir las fuentes objetivo, ~50 herramientas salen de sitios sin API y ~9 de backends
  internos de las entidades (Geovisor IGAC, SIIS Supersociedades, CPNU Rama Judicial, suameca, SIATA).
  La Ley 1273 (art. 269A) castiga el acceso a un sistema contra la voluntad de quien puede excluirlo.
- **Decisión:**
  - API o bulk publicados: se usan.
  - HTML público sin captcha: se usa con tasa baja, `User-Agent` propio, caché y copia.
  - Backend interno de la entidad: **solo con permiso o confirmación escrita registrada en el
    catálogo**. Mientras no llegue, no se usa en ningún plan, tampoco en `evaluacion`: el acceso sin
    permiso es el mismo acto con cualquier llave.
  - Backend de un tercero: fuera.
  - Captcha, login, reto de identidad o términos que lo prohíben: **nunca**.
- **Confirmación:** cada fuente del catálogo declara su `clase_acceso` y, si es interna, la evidencia
  del permiso. CI rechaza una fuente interna en producción sin esa evidencia.
- **Validación (2026-10-21):** Endurecida: antes dejaba usar backends internos sin permiso para `evaluacion`. Choca con CLAUDE.md y con la Ley 1273 (art. 269A): ahora no se usan en ningún plan sin permiso escrito.
