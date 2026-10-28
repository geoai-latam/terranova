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

## Enmienda (2026-10-27): copias espaciales de capas ArcGIS

- **Contexto:** el e2e y los canarios en producción mostraron capas que el servidor no puede
  consultar en vivo. El servicio del RUNAP (PNN) responde a la IP del datacenter con un reto
  antibots, y el de la UPRA ni acepta la conexión; desde Colombia ambos responden en 1 s. La
  agrología del IGAC tarda ~50 s por punto. Ninguna de esas tres cosas se evade (ADR-0018).
- **Decisión:**
  - **Origen `arcgis`.** La ficha declara la `capa`, la `clave` (el identificador del servicio) y
    `por_pagina`.
    - El job baja la capa con la lista blanca y la geometría en EPSG:4326, página por página y
      ordenada por la clave, hasta una página vacía. Pagina por la clave (`clave > última vista`),
      no por `resultOffset`: con desplazamiento el servicio del IGAC recorre lo ya visto y tardaba
      ~50 s por página; así, ~2 s. Una capa que no respete ese orden corta la copia con error.
    - Va una petición a la vez, con pausa entre páginas.
    - Si el servicio sabe contar y no llegó todo, la copia no se publica, y la tabla a medias no
      queda.
  - **Simplificación declarada.** `tolerancia`, en grados, solo cuando la escala de la fuente es
    más gruesa: la agrología, a 1:100.000, se copia a ~11 m. Los límites legales, como el RUNAP,
    van completos.
  - **Geometría en la copia.** Va en `_geom` con índice GiST. Los polígonos inválidos se reparan
    al cargar, no al consultar, por tandas de la clave (5.000) y solo hasta 50.000 vértices. Un
    único UPDATE sobre los 548 mil polígonos de conflictos de uso llevó el proceso de Postgres a
    ~850 MB y el límite del contenedor (1 GB) lo mató. `ST_MakeValid` de un solo polígono de 498
    mil vértices pide ~1 GB, y el método `structure` (~300 MB) cambia el área de 0,88 a 1,69
    grados². Los 12 polígonos enormes inválidos quedan como vienen, con aviso. El cruce por punto
    responde igual sobre ellos (anillos), sin error. Con las tandas, toda la capa se repara en ~20 s
    con un pico de ~335 MB.
  - **Cruce espacial en `consultar_copia`.**
    - `punto` ([lon, lat]) o `bbox`: `ST_Intersects`, con las coordenadas como parámetros.
    - `geometria` (`completa`, `simplificada` a ~55 m, como el conector ArcGIS, o `ninguna`):
      con geometría, la respuesta es una `feature_collection`.
  - **Refresco.**
    - `terranova copias actualizar --solo-vencidas` rehace solo las copias que no existen o que
      van por la mitad de su `sla_actualizacion`.
    - Así un refresco diario no vuelve a bajar una capa que cambia una vez al año, y la copia no
      llega a vencerse.
    - Las que bloquean el datacenter se ingieren desde una IP colombiana, por túnel al Postgres
      del servidor.
- **Confirmación:**
  - Pruebas sin red: plan espacial, EWKT, paginación y conteo con un servicio falso, y la
    respuesta del conector.
  - Prueba en PostGIS: cruce por punto y por zona, reparación de un polígono inválido y una carga
    rota que no deja tabla.
  - Doradas regrabadas desde las copias reales.

## Enmienda (2026-10-28): copias de lo que lee un conector (origen `conector`)

- **Contexto:** las 5 herramientas del DANE que leen anexos xlsx (IPM municipal, privaciones, IPM
  departamental, IPM nacional y GEIH) caían en producción: `www.dane.gov.co` responde 403 a la IP del
  datacenter, y no se evade (ADR-0018). El lector de esas hojas (encabezados de varias filas, formato
  largo) ya vive en `web_tabla` del conector `web-mcp`.
- **Decisión:**
  - **Origen `conector`.** La ficha declara el `conector`, la `tool` y sus `argumentos`, sin filtros
    (la copia es la fuente entera; los filtros van en la herramienta). El job le pide la tabla al
    mismo conector que la servía en vivo y la guarda tal cual: lo copiado es idéntico a lo que se
    servía y no hay un segundo lector que mantener.
  - **`_fila`**, el orden de la fila en lo que dio el conector, sirve de clave a las tablas sin
    columna única (los anexos en formato largo).
  - Si el conector dice que cortó la tabla (completitud truncada o menos filas que su total) o la da
    vacía, la copia no se publica. `web_tabla` sube su tope a 50.000 filas (la GEIH tiene ~10 mil).
  - Un filtro toma el tipo de la columna en la ficha (un año que entra como número contra una columna
    de texto).
  - La hoja de privaciones pasa a una fuente propia (`dane.ipm_municipal_2018_privaciones`): cada
    copia es una tabla.
- **Confirmación:**
  - Las 5 copias se bajaron desde Colombia en 30 s (1.122, 16.830, 784, 153 y 10.190 filas) y sus 5
    canarios pasan desde la copia con las verdades medidas en la fuente.
  - Pruebas sin red: la tabla entera con `_fila` y solo la lista blanca, el corte y la tabla vacía
    que no se publican, las reglas del origen y el tipo del filtro.
  - El refresco desde Colombia (el DANE publica la GEIH cada mes) corre con
    `copias actualizar --solo-vencidas`, con el `web-mcp` local y un túnel al servidor.

## Enmienda (2026-10-28): GeoJSON publicado como archivo (origen `geojson`)

- **Contexto:** la amenaza por movimiento en masa del POT de Bogotá solo se puede bajar como archivo
  del CKAN de Datos Abiertos Bogotá: el servicio ArcGIS de la SDP (`POT555/AMENAZAS_Y_RIESGOS`)
  responde «not started». El GeoJSON viene exportado de un escritorio: sin clave y en la cartesiana
  de Bogotá (PCS_CarMAGBOG), no en lon/lat.
- **Decisión:**
  - **Origen `geojson`.** La ficha declara las URLs del archivo en `descargas`; se copia la lista
    blanca de las propiedades y la geometría.
  - Sin clave en el archivo, la clave (`_fila`) es el orden del rasgo en los archivos, desde 1. La
    copia se rehace entera, así que no tiene que coincidir entre versiones.
  - **`proyeccion`:** la cadena proj de las coordenadas del archivo, si no son EPSG:4326. PostGIS
    las pasa a lon/lat sobre el mismo elipsoide, sin cambio de datum: la cartesiana de Bogotá infla
    el GRS80 2.550 m para que sus lat/lon sean las de MAGNA-SIRGAS, y pasar por WGS84 las corría
    ~1,4 m.
  - Un archivo sin rasgos no se publica.
- **Confirmación:**
  - El origen de la cartesiana vuelve exacto a lon −74,14659167 y lat 4,680486111.
  - Los 3.459 polígonos caen dentro de Bogotá urbana.
  - Dos puntos de control dan la misma categoría que la capa rotulada del IDIGER de 2016 (alta y
    baja).
  - Pruebas sin red: numeración entre archivos, solo la lista blanca, archivo vacío y las reglas del
    origen. Prueba en PostGIS: un cuadro en la cartesiana se encuentra por su lon/lat.
