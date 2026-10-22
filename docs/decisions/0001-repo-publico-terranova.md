# ADR-0001 · Repo público `terranova`

- **Estado:** aceptada (2026-10-21).
- **Contexto:** GEO_COPILOT es público (Apache 2.0) y personal. Se decide que Terranova arranque
  todo abierto y gratuito.
- **Decisión:**
  - Se crea el repo público `terranova` (cuenta propuesta: `geoai-latam`, donde vive GEO_COPILOT).
  - Contiene la puerta, el núcleo, el catálogo, los mapeos, los canarios, los datasets curados y el
    banco de verdades.
  - Los conectores siguen en GEO_COPILOT y se consumen como imágenes GHCR con versión fija.
  - Licencias: código Apache 2.0; catálogo y datasets CC BY-SA 4.0.
- **Alternativas:**
  - Todo en GEO_COPILOT: mezcla el copiloto con el producto de datos.
  - Repo privado: descartado.
- **Consecuencias:**
  - CI gratis en Actions, porque el repo es público.
  - Nada de secretos ni de datos personales en el repo.
  - El foso deja de ser el catálogo y pasa a ser operarlo y mantenerlo al día.
  - Cualquiera puede montar su propia instancia, y eso está bien.
- **Confirmación:** escaneo de secretos en CI; ningún archivo del catálogo con `datos_personales:
  presentes`.
