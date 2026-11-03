# Colombia Compra Eficiente: relatoría (`ancp.conceptos`, `ancp.providencias`)

Es la relatoría de la Agencia Nacional de Contratación Pública (Colombia Compra Eficiente). Tiene
dos colecciones:

- los conceptos que emite la Agencia;
- las providencias judiciales de contratación que reseña.

Es un WordPress con su API REST pública: `wp-json/wp/v2/conceptos` y `/providencias`. Se consulta
en vivo. No declara licencia: es dato público reutilizable (ámbar, con aviso).

## Qué publica

Por documento:

- `id`, fecha y `link`;
- el título: «C-1438 de 2026» en los conceptos y el radicado en las providencias
  («76001233300720170164401 de 2026»);
- `content`, el resumen de la relatoría en HTML, de 2 a 30 KB. Empieza por el tema en negrilla:
  «GARANTÍAS CONTRACTUALES – Exigencia – Obligación del proponente – Finalidad».

También tiene taxonomías (`descriptor`, `restrictor`) con ids de términos. `excerpt` viene vacío.

## Cobertura

7 761 conceptos, medido el 2026-11-03, y las providencias que la Agencia ha reseñado (95 con
«garantias»).

## Trampas medidas

1. **Una letra fuera de ASCII devuelve todo.** «contratación directa», «garantías» y «daño
   antijurídico» dan 7 761, el total de conceptos. Sin tildes ni eñes dan 2 034, 1 215 y 8. Quien
   escribe en buen español recibía cualquier cosa.
2. **No ordena por pertinencia.** `orderby=relevance` pone primero las coincidencias en el título,
   y el título es un número: en la práctica queda por fecha. Con «garantias», los primeros son
   sobre publicidad o pliegos.
3. **Sin lematizar.** «garantia» da 1 596 y «garantias», 1 215.
4. **El tema viene con entidades HTML** (`&#8211;`) y a veces con etiquetas dentro de la
   negrilla. Una providencia de 10 no tiene negrilla, y su tema sale vacío.
5. **El título de una providencia es el radicado.** Sin el tema no se sabe de qué trata.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ancp_conceptos_buscar` | bajo → medio | v2: con `tema`; busca sin tildes ni eñes; acepta números («Ley 80»); aviso de vacío |
| `ancp_providencias_buscar` | bajo → medio | igual |

## Decisiones

- **2026-11-03, revisión de valor:**
  - **`tema`** sale del resumen con un derivado `columna`:
    - patrón `(?s)<strong>(.+?)</strong>`;
    - la opción nueva `html: true`, que quita etiquetas y lee entidades.

    El resumen entero no sale.
  - **Búsqueda sin tildes.** El texto va con el modificador nuevo `{texto:ascii}`, que quita
    tildes y eñes: «daño» se busca como «dano».
  - **Entrada `str`.** El tipo `nombre` no aceptaba números («Ley 80» se rechazaba). El texto va a
    un parámetro de la URL, no a SQL, así que basta `str`.
  - **El orden sigue siendo por fecha,** y la descripción lo dice. No se probó buscar por la
    taxonomía `descriptor` (`/descriptor?search=…` y luego `?descriptor=<ids>`): pide dos llamadas y
    el motor no tiene cómo pasar una lista de ids. Queda pendiente.
  - **Medido en producción:**

    | Búsqueda | Conceptos | Providencias |
    |---|---|---|
    | «garantias» | 1 215 | 95 |
    | «Ley 80 de 1993» | 2 185 | |
    | «contratación directa» | 2 034 (antes 7 761) | |
    | «daño antijurídico» | 8 | |
    | sin coincidencias | `no_encontrado` con aviso | |

    Todas respondieron entre 0,6 y 1,7 s.
