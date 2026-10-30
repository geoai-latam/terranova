# ADR-0025 · El documento de contratistas y proponentes de SECOP se muestra como lo publica la fuente

- **Estado:** aceptada (2026-10-22). Enmienda la spec 06 §13.3 («cédulas enmascaradas por defecto»)
  para SECOP.
- **Contexto:**
  - Colombia Compra Eficiente publica, en datos abiertos, el número de documento del contratista y
    del proponente de cada contrato y proceso. Cuando es persona natural, es su cédula.
  - Terrnova ocultaba ese número y dejaba solo su tipo (ADR-0014, spec 06 §13.3). Así no se puede
    distinguir a dos contratistas con el mismo nombre ni cruzar un contrato con el RUES.
  - El dueño decidió que se muestre como lo expone la fuente: «nosotros solo mostramos»
    (2026-10-22).
- **Decisión:**
  - En las herramientas que devuelven **un registro de SECOP** (un contrato por su id, los
    proponentes de un proceso), el documento del contratista o proponente sale tal como lo publica
    la fuente, con su tipo.
  - Sigue prohibido, igual que antes (ADR-0014):
    - buscar por cédula o por nombre de una persona;
    - armar perfiles que crucen fuentes.

    El documento es un dato del registro, no una llave de búsqueda.
  - Siguen fuera los teléfonos, los correos, las cuentas bancarias y los datos del representante
    legal, del supervisor y del ordenador del gasto.
  - El repo es público: las respuestas grabadas (`tests/doradas/`) de estas herramientas usan
    registros de personas jurídicas, y una prueba impide grabar una cédula.
- **Consecuencias:**
  - La fuente sigue marcada `datos_personales: filtrados`: muestra el documento del contratista,
    pero filtra lo demás.
  - Si Colombia Compra deja de publicar un documento, Terrnova deja de mostrarlo (sale lo que
    sale de la fuente).
  - Aplica solo a SECOP. Cualquier otra fuente con documentos de personas se decide aparte.
- **Confirmación:**
  - `secop_contrato_por_id` y `secop_proponentes_proceso` devuelven el documento.
  - `tests/test_doradas.py` falla si una dorada guarda el documento de una cédula de ciudadanía.
