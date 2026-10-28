# ADR-0001 · Repo público `terranova`

- **Estado:** aceptada (2026-10-21); **enmendada (2026-10-28): el repo pasa a privado**.
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

## Enmienda (2026-10-28): repo privado

- **Contexto:** Terranova se va a vender (es el producto central; ADR-0020 la deja gratuita solo al
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
  - **Pendiente del dueño:** la licencia del código de aquí en adelante (los archivos `LICENSE` y
    `LICENSE-DATA.md` siguen como estaban hasta que lo decida). Las obligaciones de atribución y
    ShareAlike de las fuentes siguen aplicando a los datos que se sirven, sea cual sea la licencia
    del código.
  - Ya no hay CI ilimitado ni «cualquiera puede montar su propia instancia».
