# cce.secop1.paa y cce.secop1.paa_detalle: planes anuales de adquisiciones de SECOP I

- **Fuentes:** datos.gov.co, `prdx-nxyp` (encabezado) y `azeg-sgqg` (ítems), en vivo. Licencia
  CC BY-SA 4.0.
- **Herramientas:** `secop1_paa_entidad`, por NIT, y `secop1_paa_detalle`, por `id_paa`.

## Revisión de valor (2026-11-04)

- **Probado en producción:**
  - Cabuyaro (el canario, NIT 892099232): cuatro planes, de 2020 a 2023.
  - El plan 244479, de 2020, sale vacío en el detalle.
- **Medido en la fuente:**
  - Las «11 versiones» de cada plan eran 11 copias idénticas del encabezado, con la misma fecha de
    cargue. No son versiones. Se quitó el conteo; el agrupado sigue sacando una fila por plan.
  - El detalle no está para todos los planes. De los cuatro de Cabuyaro solo el de 2023 (339335)
    tiene ítems, 7 en total. El detalle tiene 600 020 ítems, con id de plan entre 272187 y 373017,
    pero los id no van en orden de año.
- **Arreglo:**
  - Se quita `versiones`.
  - El vacío del detalle dice que el plan puede no tener ítems publicados.
- **origen de recursos:** el canario da «Otros recursos» con la descripción «PROPIOS», y el aviso
  ya lo advertía. Tardó 15,9 s, contra el tope de 20 s.
