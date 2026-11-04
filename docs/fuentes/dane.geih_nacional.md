# DANE: mercado laboral, total nacional (`dane.geih_nacional`)

El anexo mensual de la Gran Encuesta Integrada de Hogares (GEIH), hoja «Total nacional». Términos de
dane.gov.co, verificados el 2026-11-04 (ADR-0039): verde, con la cita textual «Fuente: Departamento
Administrativo Nacional de Estadística: www.dane.gov.co». Terrnova lo **copia** (ADR-0024): el DANE
responde 403 a la IP del servidor, y la copia se baja a mano desde Colombia.

| Fuente | Origen | Herramientas |
|---|---|---|
| `dane.geih_nacional` | `anex-GEIH-<mes><año>.xlsx`, hoja «Total nacional» | `dane_mercado_laboral_nacional` |

## Qué publica

La serie mensual desde enero de 2001 de ocho tasas (% de población en edad de trabajar, TGP, TO, TD,
TS, TCSD, TCDFTP, MCSFT) y ocho poblaciones en miles (total, PET, fuerza de trabajo, ocupada,
desocupada, fuera de la fuerza de trabajo, subocupada, fuerza de trabajo potencial).

## Campos que importan

- `Concepto`: el indicador. Algunos traen espacios al final («Fuerza de trabajo  »).
- `columna` y `subcolumna`: el año y el mes («Ene» … «Dic»), tras pasar la tabla ancha a larga.
- `valor`: porcentaje en las tasas, miles de personas en las poblaciones. Viene con 15 decimales; el
  DANE lo publica con uno, y así sale.

## Cobertura

El anexo de septiembre de 2026 se publicó el 30 de octubre. La copia se reconstruyó con él el
2026-11-02, desde Colombia: 4 944 filas, ninguna repetida.

## Trampas medidas

1. **La hoja apila dos tablas.** «Total Nacional» (filas 12 a 30) y «Total Cabeceras» (32 a 52),
   con los mismos indicadores. La copia leía las dos sin cortar. Así, la herramienta daba cada
   indicador dos veces por mes sin decir cuál era cuál: en enero de 2026, población de 52 339 y de
   40 765 miles; desempleo de diciembre de 2001, 13,6 y 15,6. Además se colaban filas basura
   («Concepto» y filas sin indicador) del encabezado de la segunda tabla. Medido el 2026-11-02 en
   `anex-GEIH-sep2026.xlsx`.
2. **TCDFTP, MCSFT y fuerza de trabajo potencial valen 0** en los primeros años: no se medían.
3. **Notas del anexo que cambian los datos:** la PET es de 15 años y más; de 2001 a 2020 los datos
   están retroproyectados con el censo de 2018; en agosto de 2026 se ajustó la expansión por el
   sismo del 10 de agosto.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `dane_mercado_laboral_nacional` | alto | v2: solo total nacional, un decimal, resumen del último mes |

## Decisiones

- **2026-11-02, patrón E de la revisión de valor:**
  - La copia corta en la fila 30 (`hasta_fila`, como el PIB y el IPC). Se reconstruyó el
    2026-11-02, y en producción el desempleo de septiembre de 2026 da 8,0 %.
  - Arriba van `ultimo_mes` y las tasas de desempleo, ocupación y participación de ese mes.
  - El motor suma `decimales` por campo; aquí, uno.
  - No se da la tabla de cabeceras: si hace falta, va como herramienta aparte, con su nombre.

## Revisión de valor (2026-11-04)

- El anexo pone 0 donde no se medía: TCDFTP, MCSFT y la fuerza de trabajo potencial antes de 2021, y
  la subocupación de marzo a julio de 2020 (nota* por la pandemia). Ahora el 0 sale vacío.
- Cada fila trae su `unidad` (% o miles de personas), el nombre de la sigla, el mes sin asterisco
  y la nota literal del DANE.
- El canario volvió a verde (2026-11-04, 09:03 UTC).
