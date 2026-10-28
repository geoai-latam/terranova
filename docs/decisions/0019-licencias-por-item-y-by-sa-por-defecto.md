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

## Enmienda (2026-10-26): «dato público reutilizable» en vez de BY-SA bloqueante

- **Contexto:** el default pesimista «si no se sabe → BY-SA» frenaba fuentes públicas de alto valor
  (p.ej. comercio exterior por NIT) sin un fundamento legal real. La Ley 1712 de 2014 define el dato
  abierto del Estado como de libre reutilización, y las entidades ya licencian con un modelo de
  «aviso + traslado de responsabilidad» (p.ej. Superfinanciera, Res. 1519/2020). El fundamento legal
  completo se documenta aparte (no se versiona).
- **Decisión — tres clasificaciones por ítem** (`clasificacion_licencia`):
  - 🟢 **verde:** licencia abierta verificada (SPDX + evidencia). Sirve a todas las llaves. Igual que
    antes.
  - 🟡 **ámbar:** dato público de entidad pública, con términos no verificados y **sin** datos
    personales ni contenido reservado. **Sale a producción** con `uso_comercial: si` y un **aviso**
    en cada respuesta (campo `avisos` del sobre `rt/1`): la exactitud y la vigencia son
    responsabilidad de la fuente y el usuario verifica los términos para su uso. Queda exenta de la
    regla «uso_comercial decidido exige licencia verificada» (ADR-0007), nunca de la línea roja.
  - 🔴 **rojo:** no se publica (queda en borrador). Un aviso **no** cura estos casos:
    - **datos personales** / persona natural identificable (ADR-0014, Ley 1581/2012; el perfilado por
      cédula o nombre con ánimo de lucro es el blanco del art. 269F del Código Penal);
    - **contenido bajo reserva legal** (p.ej. bases gravables de declaraciones, art. 583 ET);
    - **prohibición expresa** de redistribuir o de uso comercial en los términos de la fuente.
- **Qué NO cambia:** la licencia se sigue registrando por ítem con su evidencia; una fuente verde
  sin SPDX verificado sigue siendo inválida; `por_verificar` (aún no decidida) sigue respondiendo
  solo a llaves de evaluación; BY-SA se sigue propagando a la salida.
- **Consecuencia:** el foso sigue siendo el servicio (al día, completo, cruzado, con procedencia),
  no la exclusividad; y el default deja de bloquear dato público por desconocer su licencia.
