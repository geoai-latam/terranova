# cce.secop1.procesos y cce.secop1.procesos_historico: procesos de SECOP I

- **Fuentes:** datos.gov.co, en vivo. Licencia CC BY-SA 4.0.
  - Lo cargado desde 2018: `secop1_proceso_por_constancia`.
  - Lo cargado de 2004 a 2017: `secop1_proceso_historico_por_constancia`.

## Revisión de valor (2026-11-04)

- **Probado en producción:**
  - El 19-12-10176235 de Mongua: contratación directa, celebrado, 18 millones. Una fila completa.
  - El 15-13-3881619 de Covarachía, en el histórico: mínima cuantía, convocado y «Sin
    Adjudicar», con `valor_contrato` 0.
  - Cada constancia en la herramienta que no le toca sale vacía, sin aviso.
- **Arreglo:** cada vacío dice que los dos primeros dígitos de la constancia son el año y remite a
  la otra herramienta.
- **Pendiente:** en un proceso sin adjudicar, `valor_contrato` 0 no es un contrato de 0 pesos. Hoy
  no se puede avisar, porque el aviso con `si` mira solo los campos de arriba de `datos`, no los de
  cada elemento.
