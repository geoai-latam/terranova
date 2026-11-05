# Función Pública: Gestor Normativo (`funcionpublica.gestor_normativo`)

El Gestor Normativo (EVA) de Función Pública: leyes, decretos, circulares, conceptos y sentencias,
con las notas de vigencia de Función Pública. Es HTML público y se lee en vivo con el conector web.
Los textos oficiales son de libre reproducción (Ley 23 de 1982, art. 41).

## Qué publica

- **Una página por norma:** `norma.php?i=<número>`. El `i=` es un número interno del gestor, no el de
  la ley: la Ley 1712 de 2014 es el 56882 y el Decreto 1083 de 2015, el 62866.
- **Un buscador:** `dafpIndexerBGN/norma/index`, que da los resultados de 10 en 10, con su título y
  su enlace.

## Cobertura

Normas nacionales y conceptos de Función Pública. Sin medir cuántas son.

## Trampas medidas

1. **El buscador no dice cuántos resultados hay** ni los ordena por tema: «transparencia y acceso a
   la información» no trae la Ley 1712 de 2014 entre los 10 primeros; «ley 1712 de 2014», sí, de
   primera. El buscador no distingue tildes: con ellas o sin ellas da los mismos 10 (2026-11-05).
2. **La búsqueda dentro de la norma distinguía tildes.** En la Ley 1712, «informacion publica» daba
   0 y «información pública», 30 (2026-11-05).
3. **El comienzo de un decreto único no dice mucho.** En el Decreto 1083 de 2015 (981 311
   caracteres), los 6 000 primeros son la lista de sus 158 temas; la fecha de entrada en vigencia y
   el medio de publicación vienen vacíos en la página.
4. **Un `i=` que no existe responde 302** (redirige): se lee como documento inexistente.

## Herramientas que la usan

| Herramienta | Valor | Estado |
|---|---|---|
| `funcionpublica_normas_buscar` | medio | v2: los 10 primeros resultados; aviso de vacío |
| `funcionpublica_norma_buscar` | alto | v2: sin tildes; aviso de cero apariciones |
| `funcionpublica_norma_inicio` | medio | v2: el comienzo, hasta 6 000 caracteres |

## Decisiones

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
  - `funcionpublica_normas_buscar` lleva aviso de vacío: antes «zzqxw» daba «no encontrado» sin
    explicación.
