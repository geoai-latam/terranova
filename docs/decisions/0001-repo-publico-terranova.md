# ADR-0001 · Repo público `terranova`

- **Estado:** aceptada (2026-10-21); **enmendada (2026-10-28): el repo pasa a privado**.
- **Contexto:** GEO_COPILOT es público (Apache 2.0) y personal. Se decide que Terrnova arranque
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

## Enmienda (2026-10-28): repo privado

- **Contexto:** Terrnova se va a vender (es el producto central; ADR-0020 la deja gratuita solo al
  inicio). Un repo público regala el código y el catálogo que la hacen funcionar.
- **Decisión:**
  - El repo `geoai-latam/terranova` pasa a **privado**.
  - Se mantiene la higiene de un repo público: ni secretos, ni datos personales, ni notas internas
    (eso sigue en `interno/`), y gitleaks sigue en el CI.
  - El servidor baja el código con una llave de despliegue de **solo lectura**.
  - El CI se ajusta a los 2.000 min/mes de Actions de un repo privado. Cada PR corre solo los
    trabajos que cubren lo que tocó, no se repite todo al fusionar, y hay una pasada completa diaria
    sobre main. Si no alcanza: GitHub Pro (3.000 min) o un runner propio en una VPS aparte; nunca en
    la de producción.
- **Consecuencias:**
  - El código estuvo público una semana bajo Apache 2.0. Quien lo clonó conserva esa licencia sobre
    esa versión: no se puede revocar. GitHub registraba 0 forks y 0 estrellas.
  - **Licencia propietaria** (decisión del dueño, 2026-10-28): código, catálogo y documentación son
    de GeoAI LATAM, con todos los derechos reservados (`LICENSE`). Los datos que se entregan
    conservan la licencia y la atribución de su fuente (ADR-0019), y lo derivado de fuentes
    CC BY-SA que se distribuya, como los datasets curados, sigue siendo CC BY-SA
    (`LICENSE-DATA.md`). Los conectores vendorizados vienen de GEO_COPILOT, del mismo dueño, que
    sigue público con Apache 2.0 en su propio repo.
  - Ya no hay CI ilimitado ni «cualquiera puede montar su propia instancia».
