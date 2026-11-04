# ADR-0038 · Exportar capas completas desde las copias, fuera del MCP

- **Estado:** propuesta (2026-11-02). El diseño técnico queda escrito; no se implementa hasta que el
  dueño decida el cobro y el trato de BY-SA al exportar (abajo). Sigue a la
  [ADR-0024](0024-conector-de-copia.md) y respeta la [ADR-0014](0014-datos-de-personas.md) y la
  [ADR-0019](0019-licencias-por-item-y-by-sa-por-defecto.md).
- **Contexto:**
  - GEO Copilot pide capas completas para pintarlas, y hoy solo recibe lo que cabe en una consulta por
    punto, zona o polígono. Los conectores y el MCP están hechos para respuestas que lee un agente,
    no para 200 000 elementos.
  - Exportar desde la fuente en vivo sería carga contra servidores del Estado. Esa regla no se
    negocia.
  - 27 fuentes ya tienen copia en PostGIS. Por licencia: 9 son CC BY 4.0, 9 CC BY-SA 4.0 y 9 siguen
    los términos del DANE (resueltos en la ADR-0039: verde).
- **Decisión propuesta:**
  1. **Solo desde una copia vigente.** Una fuente en vivo no se exporta: el archivo sale de la
     versión publicada en `AlmacenCopias`, nunca de la fuente.
  2. **Fuera del MCP:** `GET /v1/exportar/{fuente_id}` en la API REST, con llave y el scope
     `exportar`. Un token OAuth de MCP no sirve (ADR-0037). Ninguna herramienta del MCP exporta.
  3. **Formatos:** GeoJSON (`FeatureCollection`) para las capas espaciales y JSON por líneas para las
     tablas. Se escribe por partes desde un cursor del servidor, sin cargar la capa en memoria.
  4. **La licencia va dentro del archivo, no solo en las cabeceras.** En GeoJSON, como miembros de la
     colección escritos antes de los elementos: `licencia` (SPDX y URL), `atribucion`,
     `version_copia`, `copiado`, `servido_desde: copia` y `completitud`. En JSON por líneas, la
     primera línea es ese mismo objeto. Si se corta la transferencia, falta el cierre y el archivo
     no se puede leer como completo.
  5. **Solo los campos de la lista blanca** del catálogo, los mismos que salen por consulta. Una
     fuente con `datos_personales` distinto de `ninguno` no se exporta (ADR-0014).
  6. **Qué fuentes:** licencia verificada, `uso_comercial: si` y licencia verde o ámbar según la
     enmienda de la ADR-0019. Las del DANE entran desde la ADR-0039.
  7. **Topes:** una exportación a la vez por organización, 500 000 elementos como máximo y
     `statement_timeout` de la base. Lo que pase del tope sale truncado y lo dice en `completitud`.
- **Lo que decide el dueño antes de implementar:**
  - **Cobro.** Propuesta por defecto: 1 crédito por cada 100 elementos (200 000 elementos son 2 000
    créditos, lo mismo que 100 consultas por zona). Mientras no se decida, el endpoint no existe.
  - **BY-SA al exportar.** Quien recibe una capa BY-SA y la publica modificada debe compartirla con
    la misma licencia. Propuesta: el archivo lo dice en `licencia.obligaciones`, y los términos de
    uso lo repiten. Falta decidir si las capas BY-SA se exportan en todos los planes o solo en los
    de pago.
  - **DIAN**, con la decisión de cobro y licencias que ya está pendiente (el DANE se resolvió en la ADR-0039).
- **Consecuencias:**
  - GEO Copilot podría pintar una capa entera sin repetir consultas por zona, y sin tocar al Estado.
  - Una exportación es tan vieja como su copia: `copiado` y el SLA de frescura van en el archivo.
  - La aceptación del plan (200 000 elementos sin caer la puerta) se mide en la VPS, con la
    capa más grande que tenga copia.
- **Alternativas descartadas:**
  - Exportar por el MCP: el cliente metería el archivo en el contexto del agente.
  - Exportar desde la fuente en vivo: carga contra el Estado.
  - Shapefile o GeoPackage en la primera versión: piden armar un archivo binario completo antes de
    enviarlo, y GeoJSON lo abre cualquier SIG.
