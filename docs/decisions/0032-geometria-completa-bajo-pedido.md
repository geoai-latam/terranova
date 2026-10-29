# ADR-0032 · La geometría completa, bajo pedido: por defecto cada polígono va como su envolvente

- **Estado:** aceptada (2026-10-29). Complementa la [ADR-0005](0005-contrato-rt-1.md) (`geo_result`)
  y la [ADR-0031](0031-mcp-a-escala-perfiles-y-catalogo.md).
- **Contexto:**
  - El banco de escala con un cliente real (`scripts/banco_claude_code.py`) corrió 180 preguntas con
    Opus 5.5 desde Claude Code contra el MCP desplegado.
  - **El hallazgo:** Claude Code le pasa al modelo el `structuredContent`, y cuando pasa de su
    tope, lo guarda en un archivo y al modelo solo le da el esquema. El sobre lleva la geometría
    completa de cada elemento y pesa:
    - `ant_resguardos_en_punto`: 66 000 caracteres, el 97 % geometría;
    - `pnn_areas_protegidas_en_punto`: 25 000;
    - `pnn_areas_protegidas_en_zona` (t11): 294 000.

    En t11 y t12, Opus llamó la herramienta correcta, no vio los datos y respondió con honestidad
    «no pude obtener la cifra». Otros clientes truncan.
  - El banco del mini no lo veía porque recortaba la salida a 8 000 caracteres, con los datos
    primero.
  - Los atributos de cada elemento ya están en `datos` (y en las `properties`). La geometría
    completa solo hace falta para dibujarla.
- **Decisión:**
  1. **Parámetro común `geometria` (booleano, opcional)** en las herramientas que pueden devolver
     geometría: las espaciales (`en_punto`, `en_zona`), las de capas ArcGIS, las copias con
     geometría y la ficha de un lugar. Las demás no lo tienen, y si llega, se rechaza como
     cualquier parámetro que sobra.
  2. **Por defecto, cada polígono o línea de `geo_result` sale como su envolvente**, con
     `geometry: null` y `bbox` (RFC 7946 §5), y un aviso que dice cómo pedir la forma completa.
     - Los puntos salen completos, porque pesan poco y son lo que un mapa de sismos o estaciones
       necesita.
     - Las `properties` de cada elemento repiten uno de `datos`. Van como su posición
       (`{"elemento": i}`).
     - `datos` y la `huella` no cambian.
     - **Medido en producción:**
       - un resguardo pasa de 65 856 a 2 626 caracteres;
       - 169 áreas protegidas, de 294 000 a 93 756 solo con la envolvente;
       - las 169 áreas, sin propiedades repetidas, quedan en unos 57 000.
  3. **Igual en MCP y en REST** (ADR-0004): el resumen se hace en `puerta.ejecutar`, el camino
     común. La caché, la idempotencia y las composiciones internas (la ficha usa el polígono del
     predio para hallar su punto interior) siguen con la geometría completa.
  4. `geometria: true` devuelve el sobre como antes.
- **Resultado:** el banco con cliente real volvió a correr con esto desplegado. Perfil, catálogo y
  `/mcp` completo pasaron de 82–83 % a 88 % de éxito, y de 93–97 % a 98 % de herramienta correcta.
  Queda una lista de 169 elementos (t11) sobre el tope: el siguiente paso es paginar las listas
  largas.
- **Consecuencias:**
  - **Cambio visible para los clientes REST** que dibujaban polígonos: deben pedir
    `geometria: true`. Hoy no hay clientes de pago (ADR-0020), y GEO Copilot todavía no consume
    Terranova. Queda en la guía para clientes.
  - Las respuestas espaciales bajan de decenas o cientos de KB a unos pocos KB, también en la red y
    en la caché del cliente.
  - El banco con cliente real queda como prueba de regresión junto al del mini. Se vuelve a correr
    al cambiar la salida MCP.
  - **Corrección de la guía:** decía que se podía pedir `crs_salida: EPSG:9377`, y ese parámetro no
    existe en ninguna herramienta. La regla 8 de `rt/1` lo sigue previendo, pero no está
    implementado.
