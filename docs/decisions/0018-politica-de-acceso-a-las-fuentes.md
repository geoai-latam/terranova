# ADR-0018 · Política de acceso a las fuentes

- **Estado:** propuesta.
- **Contexto:** para cubrir las fuentes objetivo, ~50 herramientas salen de sitios sin API y ~9 de backends
  internos de las entidades (Geovisor IGAC, SIIS Supersociedades, CPNU Rama Judicial, suameca, SIATA).
  La Ley 1273 (art. 269A) castiga el acceso a un sistema contra la voluntad de quien puede excluirlo.
- **Decisión:**
  - API o bulk publicados: se usan.
  - HTML público sin captcha: se usa con tasa baja, `User-Agent` propio, caché y copia.
  - Backend interno de la entidad: **solo con permiso o confirmación escrita**; mientras tanto, nada
    más para el plan `evaluacion`.
  - Backend de un tercero: fuera.
  - Captcha, login, reto de identidad o términos que lo prohíben: **nunca**.
- **Confirmación:** cada fuente del catálogo declara su `clase_acceso` y, si es interna, la evidencia
  del permiso. CI rechaza una fuente interna en producción sin esa evidencia.
