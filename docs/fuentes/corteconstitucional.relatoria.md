# Corte Constitucional: texto de las sentencias (`corteconstitucional.relatoria`)

El texto completo de cada sentencia, en la relatoría de la Corte. Es HTML estático:
`relatoria/<año>/<número>.htm`. Se lee en vivo con el conector web; `robots.txt` permite
`/relatoria/`. La licencia es la Ley 23 de 1982, art. 41, que permite reproducir las decisiones
judiciales.

## Qué publica

Una página por sentencia, con el texto en este orden:

1. número;
2. notas de relatoría;
3. descriptores (los temas en mayúscula, con su síntesis);
4. antecedentes y consideraciones;
5. la parte resolutiva («RESUELVE»);
6. firmas y salvamentos o aclaraciones de voto.

Son largas: la T-760/08 tiene 1,4 millones de caracteres y la C-355/06, 1,7 millones.

## Cobertura

De 1992 a hoy. Dónde está cada una lo dice el índice (`corteconstitucional.sentencias`), con su
enlace.

## Trampas medidas

1. **El título de la página no sirve.** Viene como «***» (T-760/08), «VI» (C-355/06), «Sentencia
   No» (T-406/92) o «REPÚBLICA DE COLOMBIA». Se quitó de la salida.
2. **Las SU van sin el primer guion.** El archivo es `SU214-16.htm`, no `SU-214-16.htm`.
3. **Un 200 vacío.** Lo que no existe responde 200 con una página de 8 607 bytes y 32 caracteres
   de texto («CORTE CONSTITUCIONAL DE COLOMBIA»). Pasó con C-104-24 y SU-214-15. La herramienta
   lo trata como vacío por `minimo_caracteres: 500`.
4. **La decisión está lejos del comienzo.** En la C-355/06, el «RESUELVE» empieza en el carácter
   657 966 de 1 738 699. Después vienen más de un millón de caracteres de salvamentos y
   aclaraciones.
5. **«resuelve» también es un verbo.** En la C-355/06, una línea empieza «resuelve la tensión
   constitucional…» antes de la parte resolutiva. La búsqueda distingue mayúsculas y pide una línea
   que sea solo «RESUELVE», con dos puntos o sin ellos.
6. **Una sentencia puede tener dos «RESUELVE».** La T-760/08 trae otro en la posición 933 305, en
   el auto anexo. Cuenta el primero.
7. **Frases partidas en dos líneas.** La T-760/08 escribe «DERECHO A LA» y, en la línea siguiente,
   «SALUD-…». Buscar «derecho fundamental a la salud» daba 32 apariciones; con los saltos de línea,
   son 51 (medido el 2026-11-05). El canario pasó de 32 a 51: es la nueva verdad medida.
8. **Fragmentos repetidos.** Dos apariciones cercanas daban casi el mismo párrafo dos veces: n 1 y
   n 2 de «dignidad humana» en la C-355/06.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `corte_constitucional_texto_inicio` | medio | v3: sin el título basura; aviso de vacío; acepta SU-214-16 |
| `corte_constitucional_texto_buscar` | alto | v3: los fragmentos que se tocan van en uno (`veces_en_fragmento`); el tope cuenta las apariciones cubiertas; sin tildes ni saltos de línea que corten la frase |
| `corte_constitucional_resuelve` | alto | v1: la parte resolutiva, hasta 15 000 caracteres |

## Decisiones

- **2026-11-03, revisión de valor:**
  - **`resuelve`.** El conector web suma `desde`: el texto desde la primera línea que cumple una
    expresión regular. La herramienta pide `R\s*E\s*S\s*U\s*E\s*L\s*V\s*E\s*:?\s*$`. Medido en 9
    sentencias de 1992 a 2021 (T-406/92, T-025/04, C-355/06, T-760/08, C-577/11, T-622/16,
    T-302/17, SU-095/18, C-233/21): en todas sale lo resuelto, «PRIMERO.- …».
  - **Fragmentos.** El conector funde los fragmentos que se tocan. Cada uno dice cuántas
    apariciones trae y su `n` es el de la primera.
    - En la C-355/06, «dignidad humana» da 152 apariciones; el primer fragmento lleva 4.
    - En la T-406/92, «Estado social» da 23 apariciones en 15 fragmentos, sin tope.
    - El aviso de tope cuenta apariciones: en la T-760/08 son 22 de 32 en 20 fragmentos.
  - **Entrada.** `sentencia_relatoria` acepta SU-214-16 y SU214-16, en mayúscula o minúscula, y
    deja la forma de la relatoría (SU214-16). En C y T el guion sigue siendo obligatorio.
  - **Fecha.** No se saca del texto: se escribe de muchas formas («Bogotá, DC, treinta y uno (31)
    de julio…», «a los cinco ( 5 ) días del mes de junio…»). La da el índice
    (`corte_constitucional_sentencia`).
  - **Prueba en producción.** El conector web de la rama corrió en un contenedor aparte,
    `web_mcp_prueba`, y la puerta lo usó solo para estas pruebas. El conector desplegado no se
    tocó: el cambio sale con el despliegue.
- **2026-11-05, búsqueda sin tildes (revisión de valor):**
  - **El conector web** busca sin distinguir mayúsculas ni tildes, y un espacio de lo buscado vale
    por cualquier espacio o salto de línea del texto (`paginas.patron_de_busqueda`). La eñe no se
    toca: «ano» no es «año».
  - **Medido el 2026-11-05, antes y después, con el extractor del conector:**
    - Ley 1712 de 2014 (Función Pública, i=56882): «informacion publica», 0 → 32; «información
      pública», 30 → 32 (dos estaban partidas en dos líneas).
    - Resolución CREG 101-131 de 2026: «energia», 0 → 19.
    - T-760/08 (Corte): «proteccion», 1 → 500; «derecho fundamental a la salud», 32 → 51.
    - Los canarios de la CREG («ARTÍCULO 1», 4), la DIAN («ARTÍCULO 1o. ALCANCE», 1) y la Función
      Pública («ARTÍCULO 5», 2) no cambian.
  - **Cero apariciones.** El documento existe, pero no tiene lo buscado: antes salía «encontrado»
    con una lista vacía y sin aviso. Ahora un aviso lo dice y sugiere menos palabras.
