# ADR-0024 · Conector de copia (G3): copias en PostGIS servidas por la puerta

- **Estado:** aceptada (2026-10-22).
- **Contexto:**
  - ADR-0008 define el modo `copia`, pero hasta hoy solo existía el `curado` de F4.1.
  - Varias herramientas de la ola 1 en adelante no se pueden servir en vivo:
    - buscar en el texto de SECOP: un `like` sin índice pasa de 90 s;
    - medianas de precios: SoQL no tiene mediana;
    - TerriData y los anexos del DANE: solo existen como archivo.
  - Paginar en vivo un servicio del Estado para cada pregunta sería carga.
- **Decisión:**
  - **El job.** `terranova copias actualizar [<fuente>]` construye una versión nueva de la copia:
    - solo las columnas de la lista blanca y la ventana que declara la ficha;
    - páginas grandes, en serie, ordenadas por la clave y con `User-Agent` propio;
    - una vez al día, nunca por pregunta.
    - La primera versión reconstruye la ventana completa en cada corrida, que es lo más simple y
      lo más fácil de verificar. El incremento por marca de agua se suma cuando una copia sea
      demasiado grande para reconstruirla a diario.
    - El resultado queda en PostGIS, en `copia.<tabla>_<versión>`, con su manifiesto en
      `copia.versiones`: huella, filas, ventana y fecha.
    - La vista `copia.<tabla>` apunta a la versión vigente y el cambio es atómico, como en el
      curado.
  - **La ficha de la fuente.** `modo: copia` y un bloque `copia:` que declara:
    - el origen: hoy `socrata` (la API de datos.gov.co); `bulk` queda para TerriData y el DANE;
    - la tabla, la clave, la ventana y los índices (incluido texto completo en español).
  - **El conector.** `copia` es un conector interno de la puerta, con la misma interfaz que los
    MCP: `ConectorCopia`, con la herramienta `consultar_copia`.
    - Las consultas son SQL **parametrizado**: el catálogo da la forma y la entrada va como
      parámetro, nunca interpolada (ADR-0012).
    - Lo que se puede pedir es un vocabulario cerrado: filtros de igualdad, búsqueda de texto,
      agregados `count`/`sum`/`avg`/`median` y `group`.
  - **Honestidad.**
    - Cada respuesta sale con `servido_desde: copia` y su `consultado_en` es la fecha de la copia,
      no la de la pregunta.
    - Si la copia pasó su `sla_actualizacion`, sale `obsoleto`, con un aviso (ADR-0008).
    - La ventana se dice en `completitud`: «2026 en adelante» no es «todos los contratos».
  - **Memoria local.** En el equipo de desarrollo, la ventana se puede acotar con
    `TERRANOVA_COPIA_DESDE`. La copia completa se construye en la VM.
- **Alternativas descartadas:**
  - **DuckDB:** es más liviano, pero sería una segunda base. PostGIS ya está en el compose, tiene
    búsqueda de texto en español y respaldo diario (F7.3).
  - **Copiar a través de los conectores MCP:** la copia es un trabajo por lotes de la puerta. Pasar
    millones de filas por MCP no aporta nada y pesa.
- **Consecuencias:**
  - Una copia hereda la licencia y la lista blanca de su fuente (ADR-0008, ADR-0014). Nada fuera de
    la lista blanca se copia.
  - El respaldo diario incluye las copias. Si se pierden, se reconstruyen desde la fuente, como el
    curado.
  - Se suma un servicio `copias` al compose (diario) y el canario de cada herramienta sobre copia
    mide también la edad de la copia.
- **Confirmación:**
  - Prueba sin red del job (incremento, huella, cambio atómico de versión) y del conector
    (parámetros, vocabulario cerrado, `obsoleto`).
  - En vivo: búsqueda por texto en SECOP con una verdad medida en la fuente.
