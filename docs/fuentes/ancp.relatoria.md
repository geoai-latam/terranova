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
4. **El tema viene con entidades HTML** (`&#8211;`) y la relatoría lo parte en varias negrillas
   seguidas («<strong>CONTRATACIÓN DIRECTA </strong><strong>–</strong><strong> Deber…»). Tomar
   solo la primera negrilla dejaba el tema a medias.
5. **El título de una providencia es el radicado.** Sin el tema no se sabe de qué trata.
6. **Dos formatos de providencia.** Las reseñadas desde 2025 empiezan por el tema en negrilla. Las
   cargadas el 2024-04-24 (de sentencias desde los noventa) traen «Detalle: radicado – Fecha –
   Demandado – Actor – … – Descriptor: A,B,C – Restrictor: …», con los descriptores separados por
   coma.
7. **La fuente corta la lista de descriptores.** En las providencias viejas viene truncada:
   «…DAÑO ANTIJURÍDICO,DAÑO PRECONTRAC» (85001-23-31-000-2011-00109-01, medido el 2026-11-03). La
   herramienta la entrega como llega.
8. **Un concepto tiene varios descriptores.** Buscar por «contratacion directa» trae conceptos cuyo
   tema principal es otro («DEFENSA Y SEGURIDAD – Concepto Jurídico Indeterminado»): también están
   etiquetados con CONTRATACIÓN DIRECTA.
9. **`descriptor=` vacío no filtra.** Sin ids, la relatoría devuelve todo; con `descriptor=0`,
   nada. Por eso la previa, si no halla descriptores, pasa «0».

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `ancp_conceptos_buscar` (v3) | medio | por palabras en todo el texto; con `tema` entero; sin tildes ni eñes; acepta números («Ley 80»); aviso de vacío |
| `ancp_providencias_buscar` (v3) | medio | igual |
| `ancp_conceptos_por_tema` | alto | nueva: por los descriptores de la relatoría |
| `ancp_providencias_por_tema` | medio → alto | nueva: igual, en providencias |

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
  - **El orden sigue siendo por fecha,** y la descripción lo dice.
  - **Medido en producción:**

    | Búsqueda | Conceptos | Providencias |
    |---|---|---|
    | «garantias» | 1 215 | 95 |
    | «Ley 80 de 1993» | 2 185 | |
    | «contratación directa» | 2 034 (antes 7 761) | |
    | «daño antijurídico» | 8 | |
    | sin coincidencias | `no_encontrado` con aviso | |

    Todas respondieron entre 0,6 y 1,7 s.
- **2026-11-03, búsqueda por tema (v3 y dos herramientas nuevas):**
  - **Por descriptor.** Una previa busca en `/descriptor?search=<texto>` (5 640 descriptores) y
    pasa sus ids a `?descriptor=<ids>`. Para eso, la previa tiene la opción nueva `formato: coma`
    (ids separados por coma; «0» si no halla ninguno) y el patrón `id_numerico`.
  - **El tema entero.** El patrón nuevo toma el primer párrafo en negrilla, aunque venga partido en
    varias negrillas, y en las providencias viejas, lo que sigue a «Descriptor:» hasta
    «Restrictor».
  - **Se queda la búsqueda por texto.** Encuentra lo que no está etiquetado; la de tema remite a
    ella cuando no halla nada.
  - **Medido en producción:**

    | Tema | Conceptos | Providencias | Por texto (conceptos) |
    |---|---|---|---|
    | «contratacion directa» | 134 | 11 | 2 034 |
    | «supervision» | 146 | | |
    | «daño antijuridico» | | 12 | 8 |
    | «zzzqqq» | `no_encontrado` con aviso | | |

    Respondieron entre 1,5 y 2,8 s (dos llamadas).

## Revisión de valor (2026-11-04)

- **Conceptos:**
  - Búsqueda por texto, «garantías»: 1 216 conceptos. Los 20 primeros van por fecha y casi ninguno
    trata de garantías, como advierte la ficha.
  - Búsqueda por tema:
    - «contratación directa»: 134 conceptos, casi todos del tema.
    - «garantías»: 696, que mezclan la ley de garantías electorales con las garantías
      contractuales.
- **Providencias:** «contratación directa» da 135 por texto y 11 por tema.
- **Hallazgo:** la descripción de `ancp_providencias_por_tema` traía las cifras de los conceptos
  (134 y 2 034), copiadas de su gemela. Ahora trae las de las providencias.
- **Pendiente:** devolver los nombres de los descriptores que casaron, para que quien pregunta pueda
  afinar. Hace falta que la `previa` devuelva los nombres además de los id.
