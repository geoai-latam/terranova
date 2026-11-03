# CREG · gestor normativo (resoluciones)

La fuente es `creg.gestor_normativo` y la herramienta, `creg_resolucion_buscar`.

## Qué publica

- **Qué es:** el texto de las resoluciones de la Comisión de Regulación de Energía y Gas en su
  gestor normativo «Alejandría».
- **Cómo está:** una página HTML por documento, en
  `gestornormativo.creg.gov.co/gestor/entorno/docs/<nombre>.htm`.
- **Licencia:** Ley 23 de 1982, art. 41: los textos oficiales son de libre uso.
- **Sin índice ni buscador público.** `docs/` responde 403 y la portada carga los documentos con
  JavaScript, así que hay que saber el nombre exacto del documento.

## Campos

| Salida | Nota |
|---|---|
| `titulo` | el de la página: «Alejandría - Resolución 15 de 2018 CREG» |
| `caracteres`, `apariciones` | tamaño del texto y cuántas veces aparece lo buscado |
| `n`, `posicion`, `texto` | hasta 20 fragmentos alrededor de cada aparición |

## Cómo se nombran los documentos (medido el 2026-11-03)

| Nombre | HTTP |
|---|---|
| `resolucion_creg_0015_2018` | 200 (2,5 MB) |
| `resolucion_creg_015_2018` | 404 |
| `resolucion_creg_0101_2019` | 200 |
| `resolucion_creg_101_2019` | 404 |
| `resolucion_creg_0001_2022` | 200 |
| `resolucion_creg_101-131_2026` | 200 |
| `resolucion_creg_101-001_2023`, `…_2024`, `…_2025` | 404 |

Hasta 2022 el número va en cuatro cifras. En 2026 la numeración es nueva, con guion (101-131).
Entre 2023 y 2025 no se encontró la forma, y no se adivinó.

## Trampas medidas

1. **Con tres cifras, el documento no existe.** La 015 de 2018 se pide como `0015`. Antes la
   respuesta era «no encontrado» con «la fuente no dijo cuántos elementos hay», un aviso que no
   explicaba nada (revisión de valor, patrón H).
2. **El DNS de la VPS falla a ratos para este dominio** (2026-11-03).
   - El resolvedor de Contabo devolvió SERVFAIL para el registro A, y la VPS solo veía el AAAA.
   - Por IPv6 no hay ruta, así que la herramienta respondió «no se resuelve el host».
   - Minutos después resolvía bien (141.148.2.149) en los dos servidores de Contabo.
   - Los DNS públicos (8.8.8.8, 1.1.1.1) siempre dieron la IPv4.
3. **El canario prueba poco.** «ARTÍCULO 1» en la 101-131 de 2026 encuentra «el artículo 1 de la
   Constitución» de los considerandos. Sirve para saber que la fuente responde, no para saber que
   la búsqueda es fina.
4. **Documentos grandes.** La 015 de 2018 tiene 610 755 caracteres y «cargos por uso» aparece 87
   veces. La respuesta trae 20 fragmentos y avisa «Vinieron 20 de 87».

## Decisiones

- **v3, 2026-11-03.** La descripción da la forma del nombre, con la 015 de 2018 como ejemplo y la
  numeración nueva con guion.
- **Motor.** Un documento que la fuente dice que no existe (`documento_ausente`) cuenta 0 de 0 y
  trae el aviso «la fuente respondió que ese documento no existe: revise cómo se escribe su
  nombre». Vale igual para la DIAN y la Función Pública.
- **Pendiente:**
  - si el DNS vuelve a fallar, fijar resolvedores públicos para el contenedor web en
    `docker/compose.yml` (cambio de infraestructura, con el dueño);
  - un canario más fino.
