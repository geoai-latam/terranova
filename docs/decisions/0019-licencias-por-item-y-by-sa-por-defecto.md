# ADR-0019 · Licencias por ítem y BY-SA por defecto

- **Estado:** aceptada (2026-10-21).
- **Contexto:** todo lo revisado en datos.gov.co es CC BY-SA 4.0, y también los ítems de la base
  catastral IGAC en ArcGIS Online. Otros servicios IGAC se publican bajo la Resolución 616 de 2020
  (CC BY).
- **Decisión:**
  - La licencia se registra **por ítem**, con su evidencia (`licenseInfo` o metadatos); si no se
    sabe, se trata como BY-SA.
  - Toda salida derivada de una fuente BY-SA se marca BY-SA.
  - El valor está en el servicio (acceso, normalización, copias al día, disponibilidad, cruces),
    nunca en la exclusividad de los datos.
  - Los términos de servicio no restringen redistribuir lo recibido.
- **Consecuencia:** el archivo no es el foso; el foso es tenerlo al día, completo, cruzado y con
  procedencia verificable.
- **Validación (2026-10-21):** Quitado «se vende el servicio», que contradecía ADR-0020. La verificación por ítem empieza en F0.5.
