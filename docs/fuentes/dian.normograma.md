# DIAN · Normograma (compilación jurídica)

La fuente es `dian.normograma` y la herramienta, `dian_normograma_buscar`.

## Qué publica

- **Contenido:** la compilación jurídica de la DIAN, con leyes, decretos, resoluciones y el Estatuto
  Tributario, cada uno con sus modificaciones anotadas en el mismo texto.
- **Formato:** una página HTML por documento, en
  `normograma.dian.gov.co/dian/compilacion/docs/<nombre>.htm`. Es el mismo gestor «Alejandría» de la
  CREG y de la Función Pública.
- **Licencia:** Ley 23 de 1982, art. 41 (textos oficiales).

## Campos

| Salida | Nota |
|---|---|
| `titulo` | p. ej. «Compilación Jurídica de la DIAN - Decreto 624 de 1989» para el Estatuto |
| `caracteres`, `apariciones` | tamaño del texto y cuántas veces aparece lo buscado |
| `n`, `posicion`, `texto` | hasta 20 fragmentos alrededor de cada aparición |

## Nombres medidos (2026-11-03)

| Nombre | HTTP | Tamaño |
|---|---|---|
| `estatuto_tributario` | 200 | 11,9 MB, 6,9 millones de caracteres; 2,2 s |
| `decreto_1625_2016` (decreto único tributario) | 200 | 13,2 MB |
| `decreto_1165_2019` (régimen aduanero) | 200 | 3,2 MB |
| `estatuto_aduanero` | 404 | |
| `regimen_sancionatorio` | 404 | |

Las normas siguen la forma `tipo_número_año`. El Estatuto Tributario es la excepción: no lleva año.

## Trampas medidas

1. **El Estatuto Tributario no se podía pedir** (revisión de valor, patrón H).
   - El tipo `documento_normativo` exigía que el nombre terminara en año, y la llamada se rechazaba
     antes de llegar a la fuente.
   - La descripción lo daba como ejemplo.
2. **La búsqueda distinguía tildes, no mayúsculas** (hasta el 2026-11-05).
   - En el Estatuto, «ARTÍCULO 240.» aparece 17 veces: el artículo vigente y las normas que lo
     modifican.
   - «ARTICULO 240», sin tilde, aparece 3 veces, solo en textos antiguos (Ley 1607 de 2012).
3. **Las modificaciones se compilan en el mismo documento.** En el decreto 1165, «ARTÍCULO 1o» pasó
   de 3 a 6 apariciones con la actualización del 2026-10-28. Por eso el canario busca «ARTÍCULO 1o.
   ALCANCE», que aparece una vez.
4. **Documentos grandes.** El Estatuto pesa 11,9 MB y cabe en el tope del conector web (40 MB).

## Decisiones

- **v3, 2026-11-03.**
  - `documento_normativo` acepta nombres sin año. El patrón sigue cerrando rutas, puntos y barras,
    y un nombre que no existe responde 404 con el aviso de documento inexistente.
  - La descripción da los nombres medidos y avisa de la tilde.
- No se partió el Estatuto por artículos: la búsqueda por fragmentos ya responde en segundos.
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
  - La descripción ya no pide la tilde: «ARTICULO 240.» encuentra también «ARTÍCULO 240.».
