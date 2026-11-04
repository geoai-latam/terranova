# cce.secop1.adiciones: adiciones de las adjudicaciones de SECOP I

- **Fuente:** datos.gov.co, `7fix-nd37`, en vivo. Licencia CC BY-SA 4.0.
- **Herramienta:** `secop1_adiciones_adjudicacion`, por el `id_adjudicacion` que da
  `secop1_proceso_por_constancia`.

## Revisión de valor (2026-11-04)

- **Probado en producción:**
  - El canario (9378960): una adición de 5 millones y 6 meses.
  - 10000645: cuatro adiciones, tres prórrogas de 29 a 30 días sin valor y una de 30 millones
    con 30 días.
  - El id 1: vacío.
- **Hallazgo:**
  - La pregunta de quien consulta es «¿cuánto se adicionó?», y la respuesta obligaba a sumar a
    mano.
  - El vacío no decía que el id no es la constancia.
- **Arreglo:**
  - `adicion_valor_total`, `adicion_dias_total` y `adicion_meses_total`, como sumas.
  - Un aviso en el vacío.
