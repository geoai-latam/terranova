# ADR-0039 · Las licencias del DANE: tres regímenes, no uno

- **Estado:** aceptada (2026-11-04). Cierra la decisión pendiente de la
  [ADR-0029](0029-de-pago-freemium.md) sobre las fuentes del DANE en los planes de pago. Aplica la
  [ADR-0019](0019-licencias-por-item-y-by-sa-por-defecto.md) y quita la exclusión del DANE en la
  [ADR-0038](0038-exportar-capas-desde-las-copias.md).
- **Contexto:**
  - Hasta hoy todo el DANE se juzgaba con los términos de dane.gov.co. Esos términos autorizan el
    uso, el aprovechamiento, la transformación y el análisis, pero no dicen nada de redistribuir.
    Por eso el catálogo tenía 9 fuentes en ámbar, el MGN estaba en `evaluacion` con
    `redistribucion: por_verificar`, y el DANE no entraba ni en los planes de pago ni en la
    exportación.
  - El DANE publica con tres regímenes distintos. Se leyeron en la fuente el 2026-11-04:
    1. **Geoportal** (`geoportal.dane.gov.co/acerca-del-geoportal/licencia-y-condiciones-de-uso/`):
       «El DANE ofrece la descarga y uso de información georreferenciada producida por la entidad
       bajo una licencia Creative Commons, reservando el derecho de autor sobre la obra». La página
       enlaza a CC BY 4.0, cita su sección 3(a)(1) y fija la atribución: «Departamento
       Administrativo Nacional de Estadística - DANE: www.dane.gov.co». No dice NC ni SA. La reserva
       del derecho de autor es la de cualquier licencia CC: el autor conserva la obra y la licencia.
    2. **Portal dane.gov.co** (términos y condiciones):
       - Cláusula 1: «queda por lo tanto prohibida **para la Entidad y sus servidores públicos**
         toda comercialización o usufructo de este derecho de acceso». La prohibición recae sobre el
         DANE, no sobre el usuario.
       - Cláusula 2: autoriza el uso con la cita textual «Fuente: Departamento Administrativo
         Nacional de Estadística: www.dane.gov.co».
       - Cláusula 12: el DANE no tiene política propia de derecho de autor y se acoge a la norma
         general (Ley 23 de 1982 y Decisión Andina 351, entre otras).
    3. **Microdatos (ANDA, microdatos.dane.gov.co):** reserva estadística. Esos
       datos solo se dan a conocer en resúmenes numéricos. La página pública del ANDA no trae una
       cláusula de términos propia; solo invita a citar al DANE.
  - Por la Decisión Andina 351, la protección de una base de datos no se extiende a los datos que
    compila. Un IPC o una población proyectada son hechos. Colombia no tiene un derecho sui generis
    sobre bases de datos, y Terrnova no copia la presentación del DANE: la normaliza a `rt/1`.
- **Decisión:**
  1. **Lo que sale del Geoportal es CC BY 4.0, en verde.** Eso cubre el MGN y el CNPV integrado al
     MGN (`dane.cnpv2018.municipio`). Va con la atribución que fija la página.
  2. **Los anexos y cuadros de dane.gov.co se sirven en verde con `LicenseRef-dane-terminos`,**
     verificada y con la cita textual de la cláusula 2 en la atribución. Son el IPC, el PIB, la
     GEIH, los IPM y las proyecciones. Pueden ir en los planes de pago: Terrnova cobra el servicio
     (consulta, normalización y procedencia), no el dato (ADR-0029). El DANE no puede cobrar el
     acceso; un tercero que construye un servicio encima sí puede.
  3. **Microdatos: nunca el archivo, solo agregados.** Una fuente que ingiere microdatos los agrega
     en la ingesta y no guarda ni sirve líneas individuales. Es lo que ya hace el comex
     (`dian.comex_*`), que además tiene CC BY-SA 4.0 declarada en datos.gov.co.
  4. **La exportación (ADR-0038)** ya no excluye al DANE. Lo verde del Geoportal se exporta como
     cualquier CC BY. Para los anexos sigue valiendo la regla de copia vigente y lista blanca.
- **Consecuencias:**
  - Las 9 fuentes pasan de ámbar a verde y dejan de llevar el aviso de dato público.
  - El MGN, con los límites oficiales de municipios y departamentos con geometría, puede entrar al
    catálogo. Sigue haciendo falta copiarlo desde Colombia, porque el geoportal no responde a la IP
    del datacenter.
  - El derecho de petición al DANE sobre el MGN y el CNPV deja de ser condición. Se puede mandar
    igual, para tener la confirmación por escrito.
  - Si el DANE cambia sus términos (la cláusula 1 se reserva ese derecho), la licencia se vuelve a
    leer al refrescar la copia.
- **Alternativas descartadas:**
  - Dejar el DANE en ámbar hasta que responda por escrito. Ninguno de sus textos prohíbe el uso que
    hace Terrnova, y el Geoportal ya da una licencia abierta explícita.
  - Leer la cláusula 1 como una prohibición para el usuario. El texto la limita a la entidad y a sus
    servidores.
