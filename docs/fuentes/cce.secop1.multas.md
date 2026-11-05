# cce.secop1.multas: multas y sanciones a contratistas en SECOP I

- **Fuente:** datos.gov.co, `4n4q-k399`, en vivo. Licencia CC BY-SA 4.0.
- **Herramienta:** `secop1_multas_municipio`, por el nombre del municipio. Sin las filas de prueba.

## Revisión de valor (2026-11-04)

- **Probado en producción:**
  - Girardot (el canario): 11 multas.
  - Chía: 1, del SENA.
  - Medellín: 58.
  - Bogotá: vacío.
- **Hallazgo:**
  - La fuente escribe «Bogotá D.C.», con 712 filas y 632 sin las de prueba. Con «Bogotá», la
    herramienta decía que no hay multas.
  - Hay 4 filas de relleno, con contratista «O», documento «0» y valor 0; una sale en Medellín. Se
    dejan como las publica la fuente.
- **Arreglo:** el filtro acepta el nombre o el nombre con « D.C.».
- **Pendiente:** un nombre sin tilde («Bogota», «Medellin») sigue sin casar.
