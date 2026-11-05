# Supersolidaria, entidades del sector solidario (`supersolidaria.entidades`)

Conjunto `kg2d-yfyg` de datos.gov.co. Lo publica la Superintendencia de la Economía Solidaria.
Licencia CC BY-SA 4.0. Se consulta en vivo y se actualiza cada mes.

## Qué publica

Una fila por entidad y periodo de reporte: cooperativas, fondos de empleados y mutuales que
reportan a la Supersolidaria. Medido el 2026-10-23: 126 837 filas para 5 639 entidades, de 2017 a
2026. Cada entidad se repite por periodo, así que la herramienta agrupa por entidad y da su último
año.

## Campos que importan

- `nombreentidad`: la razón social. **Muchas entidades no se conocen por ella.** Coomeva es
  «COOPERATIVA MEDICA DEL VALLE Y DE PROFESIONALES DE COLOMBIA».
- `sigla`: 5 384 siglas distintas, y 249 entidades sin sigla (2026-11-02). Es por donde se busca
  a muchas.
- `supervision`: nivel 1, 2 o 3. La fuente no dice qué quiere decir cada uno («nivel de supervisión
  asignado a la entidad»). Medido en 2026: las grandes están en 1 (Coomeva, Comedal, el Fondo de
  Empleados de Coomeva). Hay 397 entidades en nivel 1, 508 en nivel 2 y 1 309 en nivel 3.
- `nit`: con guiones y dígito de verificación (`890-300-625-1`), distinto del resto de Terrnova.

## Cobertura

- 2017 a 2026.
- Una entidad que dejó de reportar sigue en el listado con su último año: CONFIARCOOP, 2017.
- En 2026 reportan 2 214 de las 5 639, sumando los tres niveles. El año va por la mitad, así que
  esto no mide cuántas dejaron de reportar.

## Trampas medidas

1. **La sigla.** Hasta la v1, la herramienta buscaba solo en la razón social. Con «COOMEVA» daba el
   Colegio Cooperativo Coomeva y el Fondo de Empleados de Coomeva, pero no la cooperativa
   (890-300-625-1, nivel 1, reporta en 2026). Medido el 2026-11-02.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `supersolidaria_entidades_buscar` (v2) | bajo → alto | busca en la razón social y en la sigla, con la sigla exacta primero |

## Decisiones

- **2026-11-02, error 7 de la revisión de valor:**
  - La búsqueda mira la razón social y la sigla.
  - El orden pone primero la sigla exacta (`case()` en SoQL) y luego la razón social más corta.
  - El canario pasa a «COOMEVA», que es la trampa.
  - El nivel de supervisión se describe con lo medido; no se le pone un significado que la fuente
    no publica.
- **Pendiente (patrón H):** el NIT sin guiones, con el dígito de verificación aparte, como en el
  resto de Terrnova.

## Revisión de valor, 2026-11-05

- **Una entidad salía varias veces.** La búsqueda agrupaba por todos los atributos y se quedaba
  con el año mayor, y el grupo se partía cada vez que un atributo cambiaba entre periodos. Con
  «COOPERATIVA», de 50 filas había 14 NIT repetidos. Las causas medidas:
  - **Codificación.** Parte de los periodos trae el texto UTF-8 leído como Latin-1 o Windows-1252
    (BOGOTÃ, MEDELLÃN, SAN JOSÃ‰ DE CÃšCUTA).
  - **Cambio de tipo.** El 800-102-813-1 era Multiactiva en 2025 y Fondo de empleados en 2026.
  - Diferencias que no se ven: la Cooperativa AVP tenía una fila de 2025 y otra de 2026, con los
    mismos valores a la vista.
- **Arreglo:**
  - El texto se repara con `reparar_codificacion`, que deshace el error y no inventa nada.
  - Queda una fila por NIT, la de su último reporte (`unico_por: nit`, `unico_mayor:
    ultimo_reporte`). Se piden 200 grupos para que alcancen después de juntar.
  - Resultado: «COOPERATIVA» da 141 entidades, sin NIT repetidos ni texto roto.
- La fuente no da el total, y la respuesta lo avisa.
