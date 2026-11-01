# Estado

*Actualizado: 2026-10-31.*

## Estado consolidado del producto (2026-10-28, `main` en #182)

Esta sección es la foto vigente; las de abajo son el registro de cómo se llegó aquí.

- **En producción:** https://terrnova.com sirve el commit de `main` (REST `/v1` y MCP, contrato
  `rt/1`, llave obligatoria). Los 17 servicios del compose están arriba: puerta, Postgres (PostGIS +
  pgvector), Redis, Caddy, los 6 conectores, embeddings, descubrimiento, canarios, copias, respaldo,
  Prometheus y Grafana.
- **Catálogo:** 207 herramientas sobre 180 fuentes (178 publicadas y 2 en borrador) de 49 entidades.
  177 fuentes son colombianas y 3 globales. Por familia: estadísticas 44, territorio 43, contratación 42,
  justicia 27, ambiente 21, empresas 18, normativa 11 y meta 1.
- **Cómo se sirven:** 155 fuentes en vivo y 25 por copia (12,4 M filas vigentes en `copia`). Entre
  las copias están el SINIC en 333 municipios (6,1 M terrenos), el comex de la DIAN, los anexos del
  DANE (IPC, PIB, proyecciones de población, CNPV), las alertas diarias del IDEAM y las capas de
  Bogotá. Las copias que el datacenter no alcanza se bajan desde Colombia con
  `interno/despliegue/refrescar_desde_colombia.sh`.
- **Salud medida al cierre:**
  - Canario diario: 165 de 180 fuentes en verde tras el despliegue.
  - Los rojos de ese corrido eran casi todos de latencia (el canario corrió con todo en frío). Medidos
    uno por uno después, 12 de 13 quedaron dentro de su tope; policía lesiones, en el límite (10,6 s
    contra 10 s).
  - Rojos reales: SECOP modificaciones, porque la fuente se republicó con menos filas (corregido en
    #182), y `dane_poblacion_municipio`, porque el geoportal del DANE está caído. Ese responde
    `fuente_lenta` en problem+json; la población proyectada (`dane_poblacion_proyectada_municipio`)
    lo cubre.
  - `nasa.firms` no tiene datos (no hay ventana fija para una verdad).
- **Pruebas:** CI verde (lint, tipos, pruebas con piso de cobertura, catálogo, descripciones, pip-audit
  y trivy). El e2e con LLM real (gpt-5.4-mini) de la última tanda dio 29 de 29.
- **Repo:** `main` limpio, sin ramas ni worktrees abiertos (salvo el de este PR).
- **Pendiente del dueño (no hay trabajo técnico abierto):**
  1. Registrar el refresco diario desde Colombia: `programar_refresco.ps1`. Sin él, las alertas del
     IDEAM (SLA de un día) se quedan viejas.
  2. La sonda externa (UptimeRobot). El correo soporte@terrnova.com ya recibe (Cloudflare Email
     Routing).
  3. La revisión legal de los términos y la privacidad, para publicarlos con el SLA.
  4. El token de Copernicus para ERA5-Land, que reemplaza a Open-Meteo.
  5. Decisiones abiertas: la base legal de las licencias DANE para los planes de pago, la DIAN
     («sin fines de lucro»), los excedentes de créditos y la URL de Inspow.
- **Huecos conocidos de fuentes (no son tareas):**
  - La deforestación del IDEAM solo sale en PDF.
  - Las alertas hidrológicas OSPA vienen por subzona.
  - La llegada de desplazados del RUV no se sirve: la fuente la mide mal.
  - El estado de los puentes no se publica (lo último es de 2015).
  - Las fuentes ámbar que esperan un derecho de petición: SIAC, el Atlas de la UNGRD, TerriData, XM y
    el visualizador del IDEAM.

## Sitio v2, fases 5 y 6: el texto que vende y móvil, accesibilidad y peso (2026-11-01, PR #212 sin fusionar)

- **Para quien decide:** la portada va en ocho secciones (héroe «Datos oficiales de Colombia para tu
  organización y tus agentes», soluciones por sector con lo que decide cada área, la prueba, lo que
  te ahorras, tres formas de usarlo, qué no hacemos, precios y preguntas frecuentes con quién está
  detrás), 736 palabras visibles en `main`. Sin MCP, REST ni nombres de herramientas en titulares ni
  entradas: eso va en /desarrolladores («La misma consulta, tres caminos», con la respuesta real del
  predio de Santa Marta).
- **Decisiones del dueño aplicadas:** precios de lanzamiento en pesos más IVA (mes y año, de
  `PLANES` en `construir.py`; créditos de `NIVELES`), solo la llave de prueba (el plan Gratis no se
  anuncia en ninguna página ni en el formulario de contacto), «Terrnova es un producto de GeoAI
  LATAM…», sin DANE en servicios ni soluciones, Estado y academia a pedido. Piloto de dos semanas a
  precio fijo, sin cifra, con lo que se entrega de verdad.
- **Verdad:** «revisión ambiental por finca» (no EUDR), «10.000», los 6,13 M terrenos del SINIC
  citados de la ficha de la fuente, la llave llega por un enlace de correo.
- **Front:** menú móvil con Escape y cierre al elegir, `aria-controls`; objetivos de 44 px; encabezados
  sin saltos; contraste AA en /fuentes; Geist servida desde el sitio con precarga (sin `@import`);
  `?v=` en CSS y JS; og:image 1200 × 630 por página (`web/og.py`). axe: 0 graves en las diez páginas;
  CLS 0 a 390 px; sin desborde a 360/390/414.
- **Pendiente fuera del PR:** el Caddyfile en `main` (caché larga para `?v=`), los textos de `src/`
  que aún dicen «plan gratis» (`llms.txt` en `descripcion.py`, el asunto `plan-gratis` en `alta.py`).

## Sitio v2, fase 4: las ocho figuras rehechas (2026-11-01, rama `feat/sitio-anatomy`, PR #212 sin fusionar)

- **Motor nuevo (`js/figuras.js`):** cada figura es `pose(turno, t)`, una función pura del tiempo que
  pone las piezas vivas y da la lectura de ese instante; dos capas por SVG (fija y viva, solo
  `transform` y `opacity`); un planificador único (la figura más visible, dos ciclos al entrar,
  puntero, toque, foco y flechas, 60/30 fps, cero cuadros en reposo). Fuera los bucles de ambiente,
  `getPointAtLength`, los halos con `blur` y las transiciones de `fill`.
- **Las ocho**, con un material por figura y un solo ámbar en la pieza que actúa: capas (teal: el
  dato sube y la pantalla del módulo responde), ruta (agua: ficha, barrera con canto, tapa de la
  columna), prueba (bosque: la ficha sube; la huella se sella), revisión (ocre: estaciones colgadas,
  banda que va con la ficha), tablero (agua: aguja que se asienta, pórtico que vuelve, serie que se
  dibuja), vigilancia (teal: banderita, registro, tique), asistente (bosque: clavija que cambia de
  boca, siglas grabadas, respuesta legible) y cobertura (rampa agua → teal hondo: maqueta con la
  forma del país, columnas que crecen, alfileres).
- **Verdad:** sin DANE en tablero ni asistente, sin alertas del IDEAM; revisión por contrato con
  herramientas que reciben id de SECOP II (lo comprueba el build); `test_figuras_solo_nombran_
  herramientas_vendibles_y_sin_dane`.
- **Medido** (390 px, CPU 4×): ninguna tarea > 33 ms; pintados en 3 s de reposo de 96–870 a 0 (4 en la
  vigilancia, su latido). `lines.mjs` 0 extremos sueltos en las ocho.

## Sitio v2: el héroe vuelve a como estaba (2026-11-01, rama `feat/sitio-anatomy`, PR #212 sin fusionar)

- El dueño no quería tocar la animación principal del héroe (el giro de los predios). La escena
  vuelve a la de antes de las fases 2 y 3 (`js/escena-predios.js`, `js/comun3d.js`, three.js
  también en móvil, imagen de respaldo y `datos/calles.json` de antes). Salen `js/maqueta.js`,
  `js/heroe.js`, `web/figuras/heroe.mjs` y el póster SVG.
- Se quedan tres arreglos que no cambian cómo se ve: con movimiento reducido un solo render; el giro
  y la subida por tiempo (dt), no por cuadros; y la atribución de OpenStreetMap tocable y fuera de
  `role="img"` (la imagen accesible es el lienzo).
- La consola rt/1 vuelve encima de la escena como estaba (pestañas Predio, Empresa y Norma, su
  reproducción y la guía al predio), con las fechas en DD-MM-AAAA. Sale el sobre de una sola respuesta.

## Sitio v2, fases 2 y 3: base visual y héroe como figura cero, revertido (2026-11-01, rama `feat/sitio-anatomy`, PR #212 sin fusionar)

- **Base visual:** tokens de color por papel en `estilo.css` (estructura, líneas, sujeto por
  material, oscuro, acento, estado) y los materiales de las figuras pasados a esas rampas; un solo
  ámbar por pantalla (el botón del menú es secundario, pestañas en tinta); sello «ilustrativo» con
  un estilo; mono solo para datos; el logo ya no se lee «Termova» a 1x (650, 20 px, +0,02 em) y el
  del pie lleva la puerta clara y el punto ámbar. `docs/DISENO.md` al día (color por papeles,
  movimiento, héroe).
- **Héroe = figura cero:** maqueta de los predios SINIC alrededor del punto consultado
  (`js/maqueta.js`), póster SVG con el kit de Anatomy (`img/figuras/heroe.svg`, 58 KB) y la misma
  escena en three.js con la misma cámara 45°/30° y sombreado de cuatro tonos; three.js solo se
  carga en vista, ocioso y sin ahorro de datos, movimiento reducido, poca memoria ni táctil
  (`js/heroe.js`). Render bajo demanda. Al lado, el sobre rt/1 real del predio con procedencia,
  licencia, completitud y `servido_desde` resaltados. Calles de OSM con sus ejes en `datos/calles.json`.
- **Medido:** móvil antes de desplazarse 235 KB sin three.js (antes 743 KB); con movimiento
  reducido 0 cuadros WebGL (antes ~130 por segundo). Siguen las fases 4 (figuras), 5 (texto), 6 y 7
  del plan.

## Sitio con figuras Anatomy integradas y texto recortado (2026-10-31, rama `feat/sitio-anatomy`, PR sin fusionar)

- **Ocho figuras isométricas** dibujadas con el kit de Anatomy (`web/figuras`, un módulo por figura y
  `comun.mjs` con la cámara y la escala comunes): capas (bastidor), ruta (banco con barrera), prueba
  (fichero con las cinco capas de una respuesta real de la TRM), revisión (banda de inspección),
  tablero (relojes y trazador), vigilancia (buzones, lector e impresora), asistente (tablero de
  conmutación) y cobertura (maqueta de Colombia con la muestra SINIC). Sustituyen las viñetas 3D
  (`escena-vinetas.js`), las maquetas HTML de /servicios y la escena 3D de cobertura; el héroe 3D de
  predios de Santa Marta no cambió.
- **Integradas, sin tarjeta:** sin borde ni fondo propio; la lectura en vivo es una línea mono debajo.
  Los SVG viven en `web/publico/img/figuras/` y `figuras.js` los trae al acercarse a la vista
  (index.html bajó de 243 KB a 29 KB). Con movimiento reducido quedan quietas y completas.
- **Verdad:** todo lo que muestran sale de `web/figuras/datos.json`, que escribe `construir.py` desde el
  catálogo (y `datos/co.json` para la cobertura); lo inventado (hallazgos, cifras del tablero,
  cambios vigilados) lleva el sello «ilustrativo». `lines.mjs` de Anatomy: 0 extremos sueltos en las ocho.
- **Texto recortado** (palabras visibles): portada 1.546 → 707, servicios 959 → 374, fuentes 1.335 →
  771, precios 600 → 471, desarrolladores 776 → 659, contacto 178 → 94. Fuera «Lo que ya existe» de
  /servicios (GEO Copilot todavía no consume el MCP en producción y la cifra de la tesis no está en
  el repo).
- **Siguiente paso:** que el dueño revise el PR en local (`uv run python web/servir.py`) y decida si se
  fusiona y despliega.

## Lo que dejó la auditoría integral (2026-10-31, #203–#207)

- **En `main`, sin desplegar todavía:** la portada nueva y la marca Terrnova (#203); la puerta que
  resiste sus fallas, la ficha con el predio del SINIC y el saldo en la base (#204); alertas,
  reglas del catálogo y la llave de prueba con correo verificado (#205); la fase comercial F8 y el
  modelo operativo de la expansión (#206); y el #207:
  - **`terranova embudo`:** las métricas del viernes desde la base (altas, primera llamada,
    activación, llaves activas), con índices en `eventos`. Sale la alerta `OutboxAtascado`.
  - **Registro MCP:** `server.json` (`com.terrnova/terrnova`), la tarjeta SEP-2127 en
    `/mcp/server-card` y `/.well-known/ai-catalog.json`. Publicar: RUNBOOK §7.
  - **`ficha_empresa`:** RUES, establecimientos, Supersociedades, Superfinanciera y SECOP II por NIT
    de persona jurídica, en `/mcp/empresas` y `POST /v1/fichas/empresa`. Las fichas compuestas
    viven en un registro (`compuestas.py`).
  - **Seguridad de las plantillas (C27):** sin inyección explotable; se cerraron huecos latentes.
- **Estudio de región (interno):** la distancia no explica la lentitud; lo único que resuelve estar
  en Colombia es el bloqueo por IP del DANE y del IDEAM. No mover la puerta; ingesta desde Colombia.
- **Pendiente de Claude:** OAuth (C20), vigencia de planes (C21), monitores (C23), respaldo externo
  (C24, con credenciales del dueño), niveles de calidad y `nueva_fuente.py` (C25), conectores en el
  CI (C26), el peso de `/mcp` (C9), rangos de los `int` y `format: date` en el OpenAPI (C27).
- **Pendiente del dueño:** desplegar; Email Routing para `soporte@`; un SMTP con SPF y DKIM
  (`TERRANOVA_SMTP_URL`); el bot de Telegram para las alertas; confirmar la llave de prueba (300
  créditos y 15 días, confirmado); publicar en el registro MCP (TXT en el DNS); la analítica web de Cloudflare;
  registrar `programar_refresco.ps1`; y lo legal (Esri, entidad que factura, términos, DANE, DIAN).

## Alta de la llave de prueba con correo verificado (2026-10-31, ADR-0034, auditoría C11 y C12)

- `/precios#empezar` tiene un formulario: llega un enlace al correo (vence en 24 h), se confirma
  con un botón y la llave se ve una sola vez. Nivel `prueba`: 300 créditos al mes, todas las
  familias, vence a los 15 días. Una llave por correo, cinco altas por hora por IP, sin correos
  desechables y con un campo trampa contra robots.
- `/contacto` tiene un formulario propio: guarda el mensaje y lo reenvía a soporte. Los botones del
  sitio que eran `mailto:` llevan al formulario con el asunto puesto.
- Correo saliente: Resend (SMTP con TLS, región sa-east-1) con SPF, DKIM y DMARC (`p=none`) en
  `terrnova.com`, desde `no-responder@terrnova.com`; `soporte@` llega por Cloudflare Email Routing.
  300 créditos y 15 días confirmados por el dueño el 2026-11-01.
- **Plantillas de correo (#210, aprobadas por el dueño):** `src/terranova/correos.py`. HTML y texto,
  solo tema claro, una columna de 600 px y una ficha clave-valor con el dato real: la solicitud
  (hora y vigencia del enlace), la llave, el contacto (referencia `TN-XXXXXX` en el acuse y en el
  aviso interno) o, en la bienvenida, la respuesta real de `sinic_predio_en_punto` para el predio
  que dibuja la cabecera (`img/correo-predio.png`, desde `datos/sm.json`). Si esa respuesta cambia
  en la fuente, se vuelve a medir y se actualizan `EJEMPLO` y la imagen juntos.

## Reglas nuevas del catálogo (2026-10-31, auditoría integral C2 y C17)

- **Sin uso comercial no se publica** salvo una `excepcion_uso_comercial` escrita con su decisión.
  La única hoy es la DIAN de usuarios aduaneros («sin fines de lucro»), por decisión del dueño del
  2026-10-28; se decide antes del primer cobro. El sitio no la anuncia.
- **Producción solo ve lo vendible (2026-11-01, ADR-0007 enmendada):** una llave `rt_live_` lista y
  usa solo las 205 herramientas de fuentes publicadas con uso comercial (antes `/mcp`,
  `/v1/herramientas` y `/llms.txt` daban 207). La DIAN de usuarios aduaneros y `catalogo_buscar`
  quedan para llaves `rt_test_`. Caddy sirve la 404 del sitio y ya no deja salir `/metrics`.
- **El `nit` de una empresa va con el tipo `nit_empresa`** (empieza por 8 o 9, nueve dígitos): un
  `int` dejaba pasar la cédula de una persona natural (ADR-0014). Cambiaron las ocho herramientas
  del RUES y de Supersociedades que pedían `nit: int`: ahora el NIT va como texto
  (`"899999068"`). Las de entidades públicas (`nit_entidad`) siguen como entero.

## Las alertas le llegan a una persona (2026-10-31, auditoría integral C7)

- Alertmanager (perfil `observabilidad`) recibe lo que dispara Prometheus y lo manda por Telegram
  con `ALERTAS_TELEGRAM_TOKEN` y `ALERTAS_TELEGRAM_CHAT` del `.env` del servidor. Sin destino, avisa
  en su log. Antes no había receptor: ninguna alerta llegaba a nadie.
- Reglas nuevas: `ErroresInternos` (la puerta respondió `error_interno` fuera de una herramienta) y
  `CacheFallando`. Prometheus guarda 400 días (antes, 15).
- El CI valida la configuración de Alertmanager con `amtool`, con y sin destino. Simulacro en el
  RUNBOOK (§6). **Pendiente del dueño:** crear el bot, poner el destino y hacer el simulacro.

## La puerta resiste sus propias fallas (2026-10-31, auditoría integral C3, C4, C6, C14)

- **Nada sale como un 500 en texto plano:** lo que falle fuera de FastAPI (llave, tasa o créditos
  con Postgres o Redis caídos) responde problem+json `error_interno` con su `solicitud_id` y suma
  `rt_errores_internos`.
- **`/listo`:** 200 si responden la base de llaves y Redis; 503 con la parte que falla. `/salud`
  sigue diciendo solo que el proceso vive. La sonda externa del SLA debe mirar `/listo`.
- **La caché deja pasar:** si Redis falla, la consulta sigue hacia la fuente sin caché
  (`rt_cache_fallos`). Los créditos siguen necesitando Redis: sin él, `error_interno`.
- **Copias y descubrimiento se reconectan solos** y cortan cada consulta a los 15 s
  (`TERRANOVA_COPIAS_TIMEOUT_MS`), con un reintento si la conexión se cayó. Antes, un reinicio de
  Postgres dejaba las 26 copias en `fuente_no_disponible` hasta reiniciar la puerta.
- **MCP:** el texto (`content`) lleva el sobre en JSON, con estado, datos, avisos, procedencia,
  licencia, completitud y huella (sin la geometría; tope de 24.000 caracteres). Los errores salen
  con `isError` y el objeto de problema en `structuredContent`, como pide la spec 01 §6.3.
- **`ficha_lugar` toma el predio de la copia del SINIC** cuando el punto cae en un municipio con
  gestor propio (milisegundos) y solo si no, del IGAC en vivo, que llegó a tardar 38 s. Si la
  copia falla, sigue con el IGAC y la deja en la procedencia (regla 3). Las construcciones del
  IGAC no cubren a esos gestores: la ficha lo dice en un aviso.
- **El saldo de créditos vive en la base** (`saldos`, en la misma base de las llaves), como dice la
  ADR-0010: un reinicio de Redis o su política de expulsión ya no pone a todos en cero. Se
  descuenta con un `UPDATE` condicional (sin sobreconsumo entre réplicas) y devolver nunca baja
  de cero. La tasa por llave sigue en Redis. Al desplegar, el saldo del mes empieza en cero en la
  base: hoy no hay planes de pago, así que no se pierde nada que se cobre.
- **Canarios:** una copia vencida sale `vencido`, no verde. En `/estado` y `/v1/estado`, lo que
  solo está lento o vencido se ve degradado (ámbar o `degradada`), no rojo.

## La portada vende soluciones y la marca es Terrnova (2026-10-31)

- **Marca:** se escribe **Terrnova**, como el dominio. Cambió en todo el texto versionado (sitio,
  `llms.txt`, OpenAPI, avisos de las respuestas, catálogo, documentos). Los identificadores internos
  (`terranova` del paquete, la CLI, los contenedores, el repo, las variables `TERRANOVA_*` y la clave
  `_meta.terranova` del MCP) no cambian.
- **Portada:** «Del dato oficial a la solución». La capa de datos es el producto; encima se
  construyen analítica, automatizaciones y agentes, por el cliente con su agente o por nosotros.
  Seis sectores con soluciones selladas como ilustrativas y las herramientas reales que usan. La
  consola muestra un predio, una empresa (RUES) y una norma (SUIN), capturados el 2026-10-30. Los
  servicios van sobre fondo claro. El mapa de predios SINIC pasó a `/fuentes`.
- **Checklist de salida de la auditoría integral (interno, 2026-10-31):** el sitio solo anuncia
  fuentes publicadas y con uso comercial (sale la DIAN de usuarios aduaneros; un assert y una prueba
  lo cuidan), sin «cumple la ley» ni «nuestro equipo», sin promesas sobre las alertas del IDEAM, con
  la instrucción copiable hacia `/mcp/catalogo`, cifras con fecha y lo que cuentan, atribución de
  OpenStreetMap y una guía de clientes que ya no recomienda claude.ai ni la interfaz de ChatGPT
  (piden OAuth). Falta lo del dueño: el correo `soporte@` no recibe (el dominio no tiene MX).

## Sitio público (2026-10-29, #190)

- **Qué:** la cara pública de terrnova.com con el sistema de diseño v4: fondo claro, Geist, y 3D
  con datos reales (predios de Santa Marta y un mapa hexagonal de cobertura). Páginas: `/`,
  `/servicios`, `/fuentes` (buscador del catálogo), `/precios`, `/desarrolladores`, `/aliados`,
  `/contacto`, `/terminos` y `/privacidad` (ambas en revisión legal) y `404`. `/estado` sigue
  saliendo de la puerta (`pagina_estado.py`), ya con el mismo lenguaje visual.
- **Cómo:** `web/construir.py` genera `web/publico/` desde el catálogo real; ninguna cifra se
  escribe a mano. Se regenera con `uv run python web/construir.py` tras cambiar el catálogo, y
  `tests/test_web.py` falla si las páginas quedan viejas. Caddy sirve el sitio con `file_server`
  (matcher `@sitio`, montado en `/srv/web`); el resto va a la puerta igual que antes.
- **Validado:** capturas con Edge headless a 1440 y 390 px sin desborde horizontal, el Caddyfile
  probado en un contenedor y `make check` en verde.
- **Landing nueva (#193, #197, #198):** el héroe muestra el producto funcionando. El mapa de predios va a
  todo lo ancho y una consola reproduce dos respuestas reales capturadas (predio y TRM); el predio
  sube cuando llega su respuesta. Siguen la instrucción copiable para el agente, la configuración
  por cliente, el muro de entidades, 25 preguntas reales por sector (sin casos ilustrativos) y la
  respuesta `rt/1` anotada. Las entidades se cuentan por nombre, sin el índice propio: son 47.
- **Servicios y precios en la landing:** la página habla también al público general. Tras el héroe
  van dos caminos (te hacemos el trabajo / conecta tu agente); los servicios son la segunda
  sección, en una banda oscura, cada uno en una fila con su viñeta three.js (`escena-vinetas.js`).
  Las viñetas nombran cosas reales que `construir.py` toma del catálogo (`data-datos`):
  - la revisión de una lista: cada predio, empresa o contratista se cruza con sus cuatro fuentes
    (12 herramientas reales) y entra al expediente;
  - el tablero: un tablero despiezado en capas (vista explotada) que se arma sobre su ventana: el
    mapa de Colombia en hexágonos extruidos, el ranking de tu municipio frente a diez comparables y
    una tarjeta por indicador (DANE, MinEducación, ADRES) con su tendencia; con cada indicador
    cambian las tres capas y un pulso une el municipio en el mapa con su columna;
  - la vigilancia: carriles de SECOP II, SUIN-Juriscol, IDEAM y la SIC que cruzan la línea de hoy;
  - el asistente: preguntas reales del catálogo que viajan a la entidad que las responde, con su
    licencia.
  «Cada respuesta trae su prueba» es una pila 3D con las capas de una respuesta real de la TRM, en
  lugar del JSON. `/servicios` se rehízo: cada servicio con su viñeta y, debajo, una maqueta de lo
  que se recibe (sellada como ilustrativa, salvo la del asistente, que es real), cómo trabajamos y
  cómo se cobra. El sitio no dice que un agente hace el trabajo: lo hace el equipo. La lista larga
  de entidades salió de la landing y quedó en `/fuentes#entidades`: nombra los sistemas conocidos de
  cada entidad (SECOP, RUES, SINIC, censo…), y `construir.py` valida cada uno contra los títulos
  del catálogo. La sección «Conéctalo con tu llave» salió de la landing: el camino técnico lleva a
  `/desarrolladores`, cuyo inicio rápido trae ahora la instrucción copiable para el agente. Los
  precios van en la landing sin el detalle de créditos por consulta, que queda en `/precios`. Las
  animaciones ya no dicen «ejemplo» y las escenas 3D llevan luz con sombras, un crecimiento desde el
  predio consultado y una onda en la GPU; la de cobertura crece desde Bogotá, con ciudades y conteo
  al pasar el puntero.
- **Contenido verificado (2026-10-29):** cada afirmación del sitio se contrastó con el catálogo,
  el código y la fuente. La TRM capturada (3.162,35 del 29-10-2026) coincide con datos.gov.co. Los
  conteos solo cuentan fuentes publicadas (178 de 46 entidades; NASA FIRMS es borrador y salió).
  Las viñetas ya no nombran herramientas con el canario en rojo (población del censo, Saber 11) ni
  la DIAN, cuyos términos prohíben el uso con fines de lucro. Las licencias se describen como en la
  enmienda de ADR-0019 (abierta verificada o dato público con aviso), los créditos se descuentan por
  organización, la tabla de errores es la del código y el soporte excluye festivos.
- **Siguiente:** llevar el lenguaje de la landing a las páginas interiores (todavía con rótulos
  de cejilla y etiquetas en mayúsculas).
- **Desplegado (2026-10-29):** la VPS quedó en #201. Caddy hubo que recrearlo
  (`docker compose up -d --no-deps caddy`): llevaba la configuración anterior a #190 sin el montaje
  `/srv/web` y todo el sitio daba 404. Verificado por https://terrnova.com: las páginas, las
  escenas, `/v1` y `/mcp` (401 sin llave). Las ramas fusionadas se borraron.
- **Sistema de diseño:** `docs/DISENO.md` (reglas que no se leen en el CSS). Para ver el sitio en
  local: `web/servir.py` y `web/capturar.py`.
- **Pendiente del dueño:** el buzón
  soporte@terrnova.com que reciben los formularios por correo, el logo oficial de Atalaya Mapas,
  el texto legal definitivo y la URL de Inspow para «Empieza gratis», que hoy pide la llave por
  correo.

## MCP a escala (2026-10-28 a 29, #183–#189, ADR-0031 y ADR-0032)

- **Pregunta:** con 209 herramientas, ¿sigue siendo MCP plano el camino? Se investigó cómo lo
  resuelven otros proveedores y clientes, y se midió con el banco de escala
  (`scripts/banco_mcp_escala.py`, gpt-5.4-mini, 60 preguntas, cinco escenarios contra `terrnova.com`).
- **Resultado (éxito con el evaluador corregido / herramienta correcta / tokens por pregunta):**
  - perfil por familia: 87 % / 98 % / 22 488;
  - plano: 82 % / 93 % / 94 923;
  - catálogo: 72 % / 77 % / 11 004;
  - búsqueda por familias: 72 % / 82 % / 8 872;
  - búsqueda: 70 % / 82 % / 8 996.
- **Decisión (ADR-0031):** se mantienen las herramientas tipadas. El perfil por familia es la vía
  recomendada y `/mcp` completo sigue. `/mcp/catalogo` (buscar → consultar, nuevo en #183) queda en
  beta hasta ≥ 85 %. La confirmación de la ADR-0006 queda cumplida.
- **Evaluador:** el banco contaba como falla un municipio dicho por su nombre, aunque la puerta lo
  resuelve. Ahora compara la entrada como la ve la puerta.
- **Arreglos (#186):** el ranking de `ficha_lugar`, la desambiguación SINIC/IGAC, el `codigo` con
  ceros de la ficha y `fuente_describir` con ids con punto o nombres de familia.
- **Curva de tamaño (2026-10-29, ADR-0031 §7):**
  - 35, 90, 140 y 209 herramientas visibles dan los mismos aciertos (49 o 50 de 59). La precisión no
    cae con el tamaño; lo que crece es el costo, unos 470 tokens por herramienta y pregunta.
  - **Regla:** un perfil tiene como tope 90 herramientas (costo y topes de Windsurf y VS Code). Una
    familia que lo pase se parte por tema. Hoy la mayor tiene 44.
- **Catálogo:**
  - Segunda corrida: 44 de 59 (83 % de herramienta correcta). El mapa de familias de
    `buscar_herramienta` ponía áreas protegidas, resguardos y sismos en territorio, pero son de
    `ambiente`, así que el filtro por familia ocultaba la herramienta.
  - Arreglo (#187): se corrigió el mapa y el filtro ya no oculta el mejor resultado.
  - Tercera corrida, desplegado: 51 de 60 (85 %, 93 % de herramienta correcta, ~10 500 tokens por
    pregunta). **Sale de beta.**
- **Cliente real (2026-10-29, `scripts/banco_claude_code.py`):** Opus 5.5 desde Claude Code en
  modo headless, 180 corridas.
  - **Resultados** (éxito / herramienta correcta / tokens por pregunta):
    - perfil: 83 % / 97 % / 22 897;
    - catálogo: 82 % / 93 % / 32 574;
    - `/mcp` completo: 82 % / 93 % / 34 534.
  - **El modelo no era el problema:** Opus acierta lo mismo que el mini.
  - Con Claude, `/mcp` completo sale barato, porque busca sus herramientas.
  - **Hallazgo:** la geometría completa (de 25 000 a 294 000 caracteres) no le llega al modelo.
- **Geometría bajo pedido (ADR-0032):** el parámetro común `geometria`. Por defecto, cada polígono
  o línea sale como su envolvente (`bbox`); los puntos salen completos. Es igual en MCP y en REST.
- **Guía para clientes** (`docs/CLIENTES.md`): qué URL usar según el cliente.
- **Banco:**
  - t06 pregunta ahora por la base pública del gestor IGAC, porque SINIC también es del IGAC y sí
    cubre Bogotá;
  - t22 acepta `upra_rangos_precio_municipio`;
  - las dos UPRA dicen qué trae cada una (el total o el desglose por rango).
- **Segunda corrida con cliente real** (#189 y #191 desplegados, mismas 180 preguntas):
  - perfil, catálogo y `/mcp` completo dan **88 % de éxito y 98 % de herramienta correcta**; antes
    eran 82–83 % y 93–97 %;
  - tokens por pregunta: 21 139, 31 702 y 33 757;
  - se arreglaron t06 y t12 (geometría) y t21 y t22 (descripciones UPRA).
- **Listas largas y fallas comunes (2026-10-29, ADR-0033):**
  - **Listas por páginas:** si `datos.elementos` pasa de 50, sale por páginas de 50 (parámetro
    común `pagina`), con un aviso que dice cómo seguir. Los totales de `datos` cuentan todo.
  - Los puntos de `geo_result` también apuntan a su elemento (`properties.elemento`).
  - Medido sobre los sobres reales de producción: t11 pasa de 59 538 a 19 141 caracteres y t17 de
    39 025 a 15 310, con `total: 169` y `total_en_catalogo: 139` intactos.
  - **t20 (censo 2018):** el geoportal del DANE no abre conexión desde la VPS (desde Colombia
    responde en 0,3 s). `dane.cnpv2018.municipio` pasa a copia del origen `arcgis` sin geometría:
    1 122 municipios en 3 s, bajados desde Colombia. Ese servidor rechaza `1=1` y los paréntesis
    con un 500, así que la copia ArcGIS sin filtro pide ahora `clave IS NOT NULL`.
  - **Evaluador del banco:** acepta una entrada equivalente:
    - un `bbox` a ≤ 0,1° por borde (t16, t18);
    - un `hasta` del día siguiente (rango excluido, t18);
    - `3` igual a `3.0`;
    - las entradas `libres` de la verdad (s09: «los últimos días» no dice cuántos).
  - t17 nombra su rectángulo: la cifra depende de él.
  - **Medido tras el despliegue (#194):**
    - Opus en vivo (perfil y catálogo, por túnel a la puerta) pasa t11 y t17: «169 áreas
      protegidas», «139 sismos, el mayor de 5,6».
    - Re-evaluada con el evaluador nuevo, la corrida anterior de 180 preguntas pasa de 88 % a 93 %
      en los tres modos.
    - `/mcp` completo no se pudo medir en vivo: la red local intercepta terrnova.com y por túnel
      su lista de herramientas (1,4 MB) no alcanza a cargar.
  - **Estaciones del IDEAM sin repetir:** el conjunto `hp9r-jxuu` trae cada estación dos veces,
    idéntica (19 828 filas, 9 914 códigos). `ideam_estaciones_en_zona` pide `distinct`: alrededor de
    Chía salían 88 filas y son 44 estaciones.
  - **Evaluador:** `geometria` y `pagina` son de presentación y no cuentan como otra entrada; el
    mini los manda con su valor por defecto.
  - **Canarios y copias a hora fija (2026-10-29):** `--cada-horas 24` contaba desde el arranque del
    contenedor, y cada despliegue movía la hora. Al recrearlos, los canarios corrieron a media
    mañana de Colombia y salieron 16 rojos, 15 de ellos solo por lentitud: datos.gov.co está más
    cargado de día. Ahora el compose usa `--a-las HH:MM` (UTC):
    - copias a las 08:00 UTC (03:00 en Colombia);
    - canarios a las 09:00 UTC (04:00 en Colombia), con las copias ya rehechas.
  - **t20 cerrado:** la copia del censo 2018 se cargó desde Colombia (1 122 municipios, 8 s). La
    puerta responde desde la copia con la verdad del canario (Bogotá: 7 181 469 personas,
    2 523 519 viviendas, 2 514 482 hogares). Opus pasa t20 en perfil y catálogo, y también t16
    tras quitar las estaciones repetidas.

## Auditoría integral (2026-10-26)

Una auditoría integral del código y el comportamiento encontró, por impacto: disponibilidad de la
capa de datos, fugas de honestidad de estado en rutas de error, inconsistencias de licencia, defectos
del descubrimiento G6, y brechas de ops/pruebas. Se cierran por workstreams, cada uno un PR con CI en
verde (WS1–WS7):

- **WS1 · capa de datos resiliente (#109):** pool Postgres con reconexión (`psycopg_pool`), medición
  e `ultimo_uso` fuera del event loop (`asyncio.to_thread`), `cargar_cobertura` memoizado por proceso.
- **WS2 · honestidad de estado en los errores (#110):** nada escapa como 500 text/plain
  (`exception_handler` catch-all → `error_interno` problem+json); datos de fuente inválidos →
  `fuente_respuesta_invalida`; el `ConectorCatalogo` no disfraza sus bugs de `fuente_no_disponible`;
  `forma="uno"` con `datos={}` → `no_encontrado`; el canario atrapa lo inesperado y sigue.
- **WS3 · licencias y catálogo (#111, #112):** gestores catastrales con su `fuente_id` y licencia
  reales (`igac.gestores_catastrales`, CC-BY-SA-4.0), typo `terrminos`→`terminos` en 4 fichas DANE,
  guardia de catálogo contra cédulas de persona natural en la lista blanca (ADR-0014). **Pendiente del
  dueño:** registrar `LicenseRef-dane-terminos` en `m1.yaml` con la base legal escrita y reconciliar el
  CNPV con el mismo criterio.
- **WS4 · blindar G6 (#113):** `parecido` recortado a [0,1], huella del modelo junto a los vectores,
  `embeber_catalogo` por lotes con tope en `/embed`, aviso de truncamiento de la cosecha ICDE.
- **WS5 · endurecimiento de despliegue y pruebas (#114):** tope de cuerpo REST, `mem_limit`/
  `pids_limit` en todos los contenedores y Redis con `--maxmemory`/LRU (que un desborde no mate los
  procesos de video del dueño), `pytest-cov` con piso 70 % en `make check`, pip-audit + trivy +
  dependabot en CI, y el piso de CONTEO del canario (no solo `elementos[0]`). Queda documentado, para
  aplicar con prueba en la VM: read_only/cap_drop en los servicios con estado y el rate_limit de borde
  en Caddy (exige compilar con xcaddy).
- **WS6a · concurrencia y degradación (#122):** un `asyncio.Lock` por `ConectorMCP` reabre la sesión
  caída una sola vez bajo llamadas en paralelo; una fuente de varias capas con una capa caída degrada
  a `parcial` (con el error en `errores`, regla 5) en vez de fallar entera; y una prueba en intérprete
  limpio fija la frontera ADR-0012/0028 (la ruta del dato no importa el modelo de embeddings).
- **WS6b · encapsular estado y paridad de entrada:** el estado mutable de `puerta.py` pasa de variables
  de módulo sueltas a un objeto `EstadoPuerta` (cohesión y aislamiento); y la coerción de entrada queda
  pareja REST↔MCP (ADR-0004: `5.0` ya no lo acepta MCP y lo rechaza REST; ambos exigen entero). El
  trabajo de import perezoso se dejó como está a propósito: `terranova.app:app` es el punto de entrada
  ASGI documentado y el catálogo se necesita al importar para construir las herramientas.
- **Pendiente de la auditoría (dueño):** la base legal DANE (WS3) y el despliegue en la VM (WS5:
  endurecimiento con prueba; e2e de las 153 herramientas; primera promoción y afinado del piso G6).

## Despliegue en producción (2026-10-27)

**Terrnova está desplegada, pública y autocontenida**, sirviendo datos reales. Decisión de infra en
[ADR-0030](decisions/0030-despliegue-vps-unica-compose.md): una sola VPS con todo el `docker compose`,
sin servicios gestionados (~10–30× más barata que la nube grande).

- **Pública con TLS:** API en un dominio propio con certificado Let's Encrypt automático (Caddy); REST
  `/v1` y MCP, autenticación por llave (401 sin llave), http→https.
- **Stack:** Postgres (PostGIS + pgvector) + Redis + puerta (1 réplica) + Caddy + los 6 conectores +
  el microservicio de embeddings. Ajustado a 12 GB (1 réplica, Redis con tope, `mem_limit`).
- **Autocontenida (#134):** los 6 conectores (datos-abiertos, arcgis, dane, web, imagery, amenazas) y
  `geo_mcp_kit` se vendorizaron a `conectores/`. **Terrnova ya no depende de geo-copilot**: todas las
  herramientas viven y corren aquí; geo-copilot será solo un cliente más por el MCP.
- **Datos:** comex (importaciones + exportaciones) servido por copia (ingesta por túnel desde una IP
  colombiana); el resto de las fuentes en vivo por sus conectores.
- **Bugs reales que destapó el primer despliegue, corregidos:** #130 (ZIP sin cerrar en Windows), #133
  (`httpx` fuera del runtime + base de Postgres en bullseye con PGDG roto → bookworm), #134 (CA público
  excluido por `*.pem`; `conectores/` fuera del lint).
- **Canarios (prueba completa):** 121 verdes / 14 no-verde de 135; **cero fallos nuevos** del
  despliegue. Los 14: 6 diferidos por decisión (fuentes DANE bloqueadas por IP de datacenter +
  `catalogo_buscar`), 5 fuentes lentas conocidas (agrología/RUNAP/UPRA), 1 copia de SECOP sin ingerir,
  1 sin canario por diseño (FIRMS), 1 transitorio.
- **Patrón confirmado:** las llamadas en vivo (respuestas chicas) funcionan desde el datacenter; las
  **descargas grandes** (copias y la cosecha del catálogo DCAT) se caen o se bloquean (el DANE bloquea
  la IP del datacenter, 403 — no se evade, ADR-0018) → las **copias y cosechas se ingieren desde una IP
  colombiana** (túnel). Pendiente: respaldo a objeto off-site, el lote de fuentes DANE y el refresco
  recurrente de copias desde Colombia.
- **SECOP-copia ingerida** (por túnel): 3.661.398 filas desde 2023; `secop_contratos_buscar` responde.
- **Descubrimiento en producción con e5-large (#136, #137).** La cosecha del catálogo DCAT **no** estaba
  bloqueada: los cortes eran transitorios. Ahora reintenta con backoff y corre completa en el servidor
  (Socrata: 33.726 datasets sin fallos). El cuello real era el embebido:
  - e5-large en CPU va a ~1,3 textos/s.
  - El servicio con lotes de 64 superaba los 3 GB y el kernel lo mataba: ahora va de a 8, con 4g.
  - Hay **caché de vectores por huella** (modelo + texto): la ingesta retoma tras un corte y la pasada
    diaria solo embebe lo nuevo. La primera pasada tomó ~6 h.

  `descubrimiento.datasets` tiene **los dos catálogos completos con vector**: 33.726 datasets de
  Socrata y 10.000 capas de ICDE (el tope conocido del feed). El **canario de `catalogo_buscar` está
  verde**. Los resultados son pertinentes: «calidad del agua en ríos» trae el ICA de los ríos de Cali
  y del río Cauca.
- **Piso de similitud recalibrado para e5 (#139): 0,40 → 0,84**, medido en producción con 100
  consultas:
  - Las 20 ajenas al catálogo (coseno máximo 0,838) ya no traen nada.
  - Las 20 temáticas sí traen candidatos.
  - «bitcoin», «receta de arepas» y «asdkjfh qwerty» dan `no_encontrado`.
  - «calidad del agua en ríos» da 48 coincidencias (antes, el catálogo entero).

  Solo responde a llaves de evaluación mientras la licencia de los catálogos DCAT siga por verificar
  (ADR-0019).
- **E2E con LLM real de las 159 herramientas en producción (2026-10-27,
  [`scripts/e2e_agente.py`](../scripts/e2e_agente.py)).** Un agente con `gpt-5.4-mini` se conecta
  por MCP remoto (TLS + llave de evaluación) al perfil de cada familia. Para cada herramienta recibe
  la pregunta del catálogo con los datos de su canario, y se mide contra la verdad del canario.

  **Resultado:** **138 éxitos de 159 (87 %)**, herramienta correcta 99 %, entrada correcta 99 %,
  1,9 llamadas y ~21 000 tokens por pregunta. Cada caso que no salió en éxito se revisó a mano. En
  ninguno la puerta dijo «no hay» cuando no pudo consultar: siempre «no pude», con la causa.
  - **8 cortes pasajeros** (SECOP 503, IDEAM 503): al repetir, los 8 dan éxito.
  - **Bloqueos por IP del datacenter, persistentes:** DANE (6, ya conocido y diferido) y **RUNAP de
    PNN (2, hallazgo nuevo):** 403 desde el servidor y 200 desde Colombia. No se evade (ADR-0018):
    va al lote de copias ingeridas desde Colombia.
  - **UPRA (2):** timeout; es la fuente lenta conocida.
  - **Verdad vieja de un canario:** `secop_garantias_contrato`. SECOP re-publicó las pólizas y el
    contrato del canario quedó sin filas; la puerta respondió bien «0 pólizas». Se midió una verdad
    nueva y se grabó su dorada.
  - **Ambigüedad del catálogo:** facturas vs. plan de pagos de SECOP. El plan de pagos se describía
    como «facturas y pagos»; ahora cada descripción remite a la otra.
  - **Falso negativo de la medida:** `suin_norma` (respuesta correcta; el canario dice «ley» y el
    agente mandó «LEY»). El banco ahora compara la entrada sin distinguir mayúsculas.
- **Copias espaciales de capas ArcGIS (2026-10-27, enmienda de la ADR-0024).** RUNAP (403 de
  Cloudflare al datacenter), UPRA (inalcanzable desde la UE; desde Colombia responde en 1,2 s) y la
  agrología del IGAC (~54 s por punto desde la UE) se sirven ahora desde una copia en PostGIS:
  - **Origen `arcgis` en el conector de copia:** baja la capa entera con su lista blanca y la geometría
    en EPSG:4326, simplificada si la ficha lo declara (`tolerancia`; agrología a ~11 m, por debajo del
    error de un mapa 1:100.000). Pagina por la clave (`clave > última`), no por desplazamiento: en el
    IGAC, ~2 s por página contra ~50 s. Si el conteo del servicio no cuadra, la copia no se publica.
  - **`consultar_copia` espacial:** `punto` y `bbox` (ST_Intersects, índice GiST), geometría
    `completa | simplificada | ninguna`, responde una colección de rasgos. Las geometrías inválidas se
    reparan al cargar (ST_MakeValid), por tandas y solo hasta 50.000 vértices. Un único UPDATE sobre
    conflictos de uso hizo que el kernel matara a Postgres por memoria (se recuperó en ~5 s). Los 12
    polígonos inválidos enormes quedan como vienen, y el cruce por punto los responde igual.
  - **`copias actualizar --solo-vencidas`:** solo rehace las copias que faltan o van por la mitad de
    su SLA; el refresco recurrente desde Colombia puede correr seguido sin rebajar nada.
  - **Ingeridas por túnel desde Colombia:** RUNAP 1.936 áreas (268 s), UPRA 178.973 zonas (549 s),
    capacidad de uso 64.771 polígonos (854 s), vocación de uso. Seis herramientas pasan a la copia
    con sus doradas regrabadas y los canarios con las verdades de la fuente. **Conflictos de uso**
    (548.423 polígonos) se bajó desde el servidor en 19 min (2–5 s por página de 2.000): el IGAC sí
    se deja copiar desde el datacenter, así que su refresco va en el job diario del servidor. Con
    él, las 7 herramientas de RUNAP, UPRA y agrología salen de la copia, y también la ficha de un
    lugar.

## Estado, SLA y guía para clientes (2026-10-28)

- **`GET /estado`:** página pública de estado, en HTML, sin dependencias externas y legible en
  móvil. Muestra la puerta y cada fuente en verde, ámbar o rojo, según su último canario:
  - ámbar = unas herramientas pasan y otras no, o el canario tiene más de 48 h;
  - lleva la hora de la última verificación;
  - **sin porcentajes de disponibilidad:** no hay histórico medido.

  Con los canarios de producción del 2026-10-28: 121 verdes, 13 rojas, 1 ámbar y 1 sin canario.
  `src/terranova/pagina_estado.py`; `/v1/estado` (JSON) no cambia.
- **`docs/SLA.md`** (borrador):
  - 99,5 % mensual de la puerta en los planes de pago, sin compromiso en Gratis;
  - créditos de servicio solo en A medida;
  - las fuentes oficiales quedan excluidas;
  - tiempos de atención por severidad.

  Coincide con el SLO de la spec 05. Pendiente: el canal de soporte y una sonda externa para
  medir la disponibilidad.
- **`docs/CLIENTES.md`:** inicio rápido (curl verificado contra producción), MCP con perfiles
  (Cursor, Claude Code, Claude Desktop), llaves, créditos por tipo de pregunta, `/v1/uso`, el
  sobre `rt/1`, errores y estado. Sin precios: viven en Inspow.
- **`llms.txt`** ya no dice «abierta y gratuita» (ADR-0029). Ahora menciona `/v1/uso`, el 402 y
  `/estado`.

## Diez fuentes colombianas nuevas (2026-10-28, #158–#169)

Cada fuente lleva una licencia verificada por ítem, un perfil medido, un canario medido en la fuente
y una dorada grabada en el servidor. La prueba de punta a punta con gpt-5.4-mini contra producción
dio 18 de 18 éxitos (10 en las olas 1 y 2, 8 en la ola 3), con las respuestas revisadas una a una.
El SINIC llegó al final: tiene canario y dorada, y su prueba de punta a punta va tras el despliegue.

- **Olas 1 y 2, en vivo (#158, #159):**
  - ANT: consejos comunitarios y UAF.
  - URT: zonas microfocalizadas.
  - CAR: rondas hídricas.
  - ANI: concesiones viales y peajes.
  - INS: calidad del agua (IRCA).
  - UNGRD: emergencias por municipio.
  - IDEAM: lluvia diaria por estación.
  - INVÍAS: tarifas de peajes.
- **Ola 3:**
  - IDEAM: calidad del aire por municipio y año (#163).
  - SINCHI: pérdida de bosque en la Amazonia, por copia (#161).
  - Bogotá, por copia ingerida desde Colombia (IDECA y la SDP no responden a la VPS):
    - valor de referencia del m² de la UAECD (#162);
    - POT 555: tratamiento urbanístico y área de actividad (#165);
    - estrato por manzana (#166);
    - amenaza por movimiento en masa (#167), con el suelo rural desde #171.
  - CAR: zonificación del POMCA del río Bogotá, en vivo (#168).
  - CAR: los otros POMCA, en vivo (#170). `car_pomca_en_punto` consulta a la vez nueve cuencas
    (Bogotá, Carare-Minero, Garagoa, Negro, Alto Suárez, Medio y Bajo Suárez, Seco, Guavio,
    Guayuriba). El Sumapaz va en `car_pomca_rio_sumapaz_en_punto`, como BY-SA, porque su ítem no
    declara licencia.
  - IGAC SINIC: predio en un punto de 21 ciudades con gestor catastral propio (#169). Desde la
    etapa 2 (#181) cubre los 333 municipios que la base del IGAC no tiene.
- **Piezas nuevas de la copia:**
  - Un rasgo cuya geometría el servicio no sabe dar ya no tumba la copia. Se rescata la página
    sin geometría y luego las geometrías por rangos de la clave; el rasgo roto queda sin geometría,
    con aviso.
  - `filtro` copia una parte de una capa ArcGIS.
  - Origen `geojson` (enmienda de la ADR-0024), con `proyeccion` para la cartesiana de Bogotá.
  - `alias` en un campo de la lista blanca: cuando capas de servicios distintos nombran distinto el
    mismo dato (`CAT_ORD`, `CAT_ORD_A`, `CATEGORIA`), vale el primero que traiga la fila.
  - Honestidad (#160): una fuente que dice «hay N» y no entrega ninguno es «no se pudo».
- **No se puede:** las alertas tempranas de deforestación del IDEAM solo salen en boletines PDF, sin
  API ni bulk (ADR-0018).
- **SINIC etapa 2 (#181):** 6 134 392 terrenos de 333 municipios.
  - Dos ingestas por túnel se cayeron: una por un corte de red a 1 h 9 min, la otra porque el PC se
    quedó sin memoria.
  - Lo que funcionó:
    1. Se cargó en un Postgres local con la imagen del servidor, con la ingesta dentro de Docker:
       1 h 40 min.
    2. Se pasó con `pg_dump` (699 MB) y `rsync --partial`, que se puede retomar.
    3. Se publicó como lo hace la copia: la vista cambia y `copia.versiones` la marca vigente, en
       una sola transacción.
  - Unos pocos terrenos llegan sin geometría porque el servicio no la da; quedan con aviso.

## Segunda tanda de fuentes colombianas (2026-10-28, #172–#181)

Todas tienen licencia verificada por ítem, perfil, canario medido en la fuente y dorada grabada en
el servidor. La prueba de punta a punta con gpt-5.4-mini contra producción dio 21 de 21 éxitos
(#172, #174–#178), con las respuestas revisadas una a una. Las fallas que se vieron son del agente,
no de la puerta: listar las alertas más viejas en vez de las recientes, o dar solo el total cuando
se pidió mes a mes.

- **IDEAM:**
  - Temperatura y nivel de los ríos por estación y día, y normales climatológicas (#174, en vivo).
  - Alertas diarias por deslizamiento e incendio forestal por municipio (#176). Son por copia del CSV
    nocturno de la OSPA, con el origen nuevo `csv`; `bart.ideam.gov.co` no responde al datacenter.
- **ANH (#175):** producción de crudo y gas, y regalías liquidadas, por campo y por municipio.
  - El crudo y las regalías no traen DIVIPOLA: se piden por nombre y departamento.
  - Nuevo tipo de entrada `campo_hidrocarburos`.
- **Aerocivil y Supertransporte (#177):** pasajeros y carga por aeropuerto (IATA), operaciones (OACI),
  y toneladas y contenedores por zona portuaria.
  - Los pasajeros son origen-destino del viaje, no el tramo volado: la descripción lo dice.
- **INVÍAS y ANI (#178):** red vial nacional y puentes en una zona (por el ArcGIS de hermes2), y
  tráfico y recaudo mensual de los peajes de la ANI.
  - El estado de los puentes no se publica: las inspecciones son de 2015 o antes.
- **UARIV y ADRES (#180), solo sumas (ADR-0014):** víctimas del RUV por municipio y por hecho, el
  desplazamiento (expulsión) por año, y los afiliados al régimen contributivo y al subsidiado por EPS.
  - El RUV acumula un corte por mes: se toma el más reciente.
  - La «llegada» de desplazados no se sirve porque la fuente no la mide bien: 27 106 llegadas contra
    816 111 expulsados en 2002.
- **DANE:**
  - Población proyectada por municipio y año, 2018-2042 (#172).
  - Índice del IPC mes a mes desde 2003 y crecimiento anual del PIB trimestral (#179), por copia
    de sus anexos.
  - `web_tabla` gana `hasta_fila`, para las hojas con varias tablas apiladas.
  - El SDMX del BanRep no tiene IPC, PIB ni desempleo (33 dataflows medidos). El desempleo ya lo da
    la GEIH.

## Copias del DANE (2026-10-28)

- **Las 5 herramientas del DANE que leen anexos xlsx salen de copia:** IPM municipal, privaciones,
  IPM departamental, IPM nacional y GEIH. `www.dane.gov.co` responde 403 al datacenter.
  - Origen nuevo `conector` (enmienda de la ADR-0024): el job le pide la tabla entera al mismo
    `web_tabla` que la servía en vivo y la guarda tal cual.
  - Bajadas desde Colombia en 30 s; los 5 canarios pasan desde la copia con las verdades de la
    fuente.
  - Las privaciones pasan a su propia fuente (`dane.ipm_municipal_2018_privaciones`).
- **Población proyectada por municipio y año (`dane_poblacion_proyectada_municipio`):** las
  proyecciones oficiales 2018-2042 (actualización del 30-07-2025), por cabecera, rural y total.
  - Por copia del xlsx: 84 229 filas en 20 s desde Colombia.
  - El tope de filas del `web_tabla` y de la copia sube de 50 mil a 100 mil.
  - Es la cifra oficial entre censos. Corrige la omisión censal: Bogotá 2018 tiene 7 391 056
    proyectados contra 7 181 469 censados.
- **La población del censo 2018** (`dane_poblacion_municipio`) se sirve por copia desde el
  29-10-2026 (#194): el geoportal del DANE no abre conexión desde la VPS.
- **Refresco desde Colombia en un paso:** un script interno abre el túnel, levanta el `web-mcp` con
  una llave de un solo uso y corre `copias actualizar --solo-vencidas` sobre las 21 copias que solo
  se bajan desde Colombia:
  - las del DANE (con la población proyectada, el IPC y el PIB);
  - las 2 alertas diarias del IDEAM;
  - RUNAP y UPRA;
  - comercio exterior y SECOP;
  - las 5 de Bogotá;
  - el SINIC.

  Si nada venció tarda ~20 s. Tiene que correr cada día, por las alertas del IDEAM. Hay un script
  interno listo para registrarlo como tarea diaria de Windows: falta que el dueño lo corra, porque
  crear una tarea persistente en su máquina le toca a él.

## Repo privado y licencia propietaria (2026-10-28, #147)

- **El repo `geoai-latam/terranova` pasa a privado** (enmienda de la ADR-0001), porque Terrnova es un
  producto comercial. Se mantiene la higiene de un repo público (gitleaks sigue en el CI).
  **Por ahora sigue público, a propósito y solo mientras se consolida el MVP.** Los 2.000 min/mes de
  Actions privados de la cuenta ya los gastó `GEO_COPILOT` en octubre, y con el tope de gasto en 0
  el CI no corría. Se vuelve a privado apenas termine la consolidación, idealmente con GitHub Pro y
  un presupuesto de Actions. Mientras tanto, la licencia propietaria ya protege el código.
- **Licencia propietaria:** © GeoAI LATAM, todos los derechos reservados. Los datos que se entregan
  conservan la licencia de su fuente, y lo derivado de CC BY-SA sigue siendo CC BY-SA. `/llms.txt` y
  la tarjeta MCP ya no dicen «Apache» ni «abierto».
- **El servidor baja el código con una llave de despliegue de solo lectura.**
- **El CI está ajustado a los 2.000 min/mes de un repo privado:** cada PR corre solo lo que cubre lo
  que tocó, y hay una pasada completa diaria sobre main a las 06:00 UTC.
- **Pendiente del dueño:**
  - Términos de servicio (necesarios antes de vender; el `LICENSE` remite a ellos).
  - Qué hacer con GEO Copilot. Hoy llama a sus propias copias de los 6 conectores en vez del MCP de
    Terrnova, y su repo `geo-copilot` es público.

## Operación del MVP encendida (2026-10-28, #143–#145)

- **Servidor en `main` limpio:** `docker/compose.prod.yml` versionado (sin secretos) reemplaza los
  parches a mano. Caddy toma las réplicas de `TERRANOVA_REPLICAS`, `puerta-b` queda tras un perfil, y
  se despliega siempre con `--no-deps` (sin él compose recrea Postgres).
- **Jobs diarios encendidos:**
  - `canarios`: primer pase, **153 verdes de 159**. Los 6 rojos son del DANE, que bloquea al datacenter.
  - `copias --solo-vencidas`: las 8 copias al día.
  - `descubrimiento`.
  - `respaldo`: `pg_dump` diario con 14 días de retención; el primero pesó 1,7 GB.
- **Prometheus y Grafana encendidos** (perfil `observabilidad`). Prometheus descubre las réplicas por
  DNS; Grafana solo escucha en `127.0.0.1` del servidor y se ve por túnel SSH, en solo lectura.
- **Ficha de un lugar en producción:** 200, con áreas protegidas y agrología por copia. Sale `parcial`
  en ~15 s porque la población del DANE cae en `fuente_lenta` (bloqueo de IP); se arregla con la copia
  del DANE.
- **Pendiente del dueño:**
  - Canal de alertas (`TERRANOVA_ALERTA_URL`, pospuesto).
  - Respaldo fuera del servidor: se baja a la máquina del dueño con un script interno.
  - Base legal de la licencia DANE.
  - Qué hacer con `OutboxAtascado`: los eventos de uso solo crecen porque no hay sistema de cobro que
    los consuma (ADR-0020).

## Créditos por tipo de pregunta (2026-10-27, enmienda de la ADR-0010)

- Los créditos de cada ficha estaban puestos a mano (1 a 20) y no seguían «en vivo 10, copia 1».
- Ahora cada herramienta declara su `cobro` y el crédito sale de la tarifa: `codigo` 1, `registro`
  2, `agregado` 5, `punto` 10 y `zona` 20.
- El catálogo valida que lo espacial se cobre como espacial, y pasar una fuente a copia ya no cambia
  su precio.
- Cambian 113 de las 159 herramientas; el promedio pasa de 4,43 a 4,33 créditos por consulta.
- Entra a producción en el siguiente despliegue de la puerta.

## Planes de pago (2026-10-27, ADR-0029)

- **La ADR-0029 reemplaza a la ADR-0020:** freemium de pago. Se cobra el servicio, nunca el dato.
- **Niveles nuevos en `cuota.py`:** `con_llave` (gratis) baja de 20.000 a 1.500 créditos al mes, y
  entran `basico`, `pro`, `empresa` y `escala`. `ampliado` sigue con 200.000. Los precios no están
  en el repo.
- **Saldo agotado: 402** (antes 429), con la fecha de reinicio y, si `TERRANOVA_URL_PLANES` está
  definida, dónde subir de plan. 429 queda solo para la tasa. `GET /v1/uso` dice `reinicia`.
- **`terranova orgs listar`:** cada organización con su nivel, sus créditos al mes y sus llaves
  vigentes. Muestra las que no tienen nivel fijado.
- **`terranova orgs uso [--org X] [--mes AAAA-MM]`:** saldo y consumo del mes de cada organización:
  límite, usados (de la cuota en Redis, lo que la puerta descuenta), disponibles, peticiones y las
  tres herramientas que más créditos gastan (de la medición). Sin Redis, lo usado sale de la
  medición; el saldo de un mes vive 40 días en Redis.
- **Antes de desplegar:** las organizaciones internas pasan a `ampliado`. Hecho el 2026-10-27
  (`geoai`, la única).
- **Pendiente:** excedentes y paquetes adicionales; licencias DANE y DIAN (términos «sin fines de
  lucro») para los planes de pago; términos de servicio.
- **Open-Meteo retirado (2026-10-28):** su API gratis es solo no comercial y Terrnova ya cobra.
  Salen `open_meteo_clima_serie`, su fuente y su dorada; ADR-0021 queda superada. El reemplazo es
  ERA5-Land del CDS de Copernicus (CC BY 4.0), que espera la llave del CDS.
- **SLA:** soporte en soporte@terrnova.com (lunes a viernes, 8:00 a 18:00, hora de Colombia) y sonda
  externa UptimeRobot sobre `GET /salud` cada 5 minutos. `/salud` no toca fuentes ni la base.

## Dónde estamos

**Gates F0 a F4 cerrados (2026-10-22).** La puerta está completa: REST y MCP generados del catálogo, identidad, cuota, medición, caché, cortacircuitos y despliegue con dos réplicas. E2E-01 a E2E-08 en verde. El gate F4 se cerró sin esperar la copia de agrología del IGAC (ADR-0023: tope de la ficha en 12 s). Siguen **F5** (expansión hasta la paridad, por olas) y **F6** (GEO Copilot como cliente).

**Dirección nueva (2026-10-25):** la cobertura de la cola larga de datos.gov.co (~miles de datasets) se
da con **conector genérico + buscador de catálogo (G6) + promoción curada**, no un tool por dataset
([ADR-0026](decisions/0026-cobertura-datos-abiertos-buscador-no-tool-por-dataset.md),
[spec 09](specs/09-descubrimiento.md)). Y se abre el bloque de **canales de cliente** sobre el REST
`/v1`: un **CLI de cliente** delgado con `catalogo buscar` y el batch `verificar <archivo>`
([ADR-0027](decisions/0027-cli-de-cliente.md), [spec 10](specs/10-cli.md)), junto con la API con cuota,
OGC API y archivos.

**G6 · ingesta del catálogo DCAT (primer entregable, 2026-10-25):** `src/terranova/descubrimiento.py` +
`terranova catalogo-dcat ingerir` cosechan la Discovery API de datos.gov.co (metadatos, en serie, con
`User-Agent` propio; funciones puras probadas sin red). Una muestra de 2.000 datasets **confirma la
ADR-0026**: solo **36 %** declara licencia (ADR-0019: sin licencia no sale a producción), y un solo
publicador (MinTIC) acapara ~63 % de la cuenta, mientras los que **deciden** (Colombia Compra, UPRA,
IDEAM, MinEducación, INVIMA…) son decenas cada uno — «unos pocos cientos deciden», medido.

**G6 · buscador y CLI de cliente (2026-10-25).** El núcleo desarrollable quedó completo y validado:
- **Buscador `catalogo_buscar`** (#86): `buscar` (puro) casa una pregunta contra título + descripción +
  columnas + entidad y ordena por licencia declarada > vivo > uso; `terranova catalogo-dcat buscar`.
  Validado en vivo: «contratos» → datasets de Colombia Compra/SECOP, con su licencia.
- **CLI de cliente MVP** (#87, ADR-0027): cliente delgado del REST `/v1` — `consultar / fuentes /
  herramientas / uso`, con exit codes que distinguen «no encontrado» de «no se pudo».
- **Validación crítica** de las ADR/specs (#85): el catálogo es **metadatos** en `descubrimiento.datasets`,
  no un `copia` (ADR-0024); licencia **declarada** (verificar es manual, al promover); orden del CLI.
- **Runtime del catálogo con embeddings — NÚCLEO COMPLETO (PRs #94–#99, 2026-10-25).** Descubrimiento
  semántico de punta a punta, todo probado sin red (y el `<=>` contra pgvector en CI); falta solo el
  **despliegue** (bajar el modelo, levantar el compose), que es del dueño (Q3).
  1. **Microservicio de embeddings** (#94): el modelo (ONNX/fastembed) en un contenedor aparte, `/embed`
     por HTTP, `EmbedderRemoto` para la puerta y el job — no se duplica en cada réplica.
  2. **Almacén pgvector** (#95): `AlmacenDescubrimiento` (`descubrimiento.datasets` con columna `vector`,
     refresco entero por catálogo), `catalogo-dcat ingerir --a-postgis`, job `descubrimiento` en el
     compose, imagen Postgres con postgis **y** pgvector, y job de CI con imagen pgvector.
  3. **Conector interno `catalogo_dcat`** (#96): embebe la consulta y busca con `<=>` + piso + orden por
     valor; registrado en `conectores_desde_entorno`; honesto si falta el embebedor.
  4. **Ficha `catalogo_buscar` `rt/1`** (#97): familia nueva `meta`, perfil, ficha técnica, dorada y
     canario reproducible; sale por REST/MCP y en los perfiles por familia.
  5. **Pasada completa** (#98): Socrata con `scroll_id` (sin el tope de 10k), ICDE con `?page=N`.
  6. **Promoción data-driven** (#99): `candidatos_a_promover` + `catalogo-dcat promover` ordenan la cola
     por cobertura medida del banco de verdades, no por intuición.
  **Despliegue pendiente (dueño):** `docker compose … up -d --build` levanta `embeddings`, la imagen
  Postgres con pgvector y el job `descubrimiento`; luego la primera promoción (`catalogo-dcat promover`)
  y afinar el piso de similitud con el banco de verdades. La ficha `catalogo_buscar` ya es `rt/1`; su
  canario va verde cuando el almacén tiene datos.
- **Buscador semántico con embeddings (#93, ADR-0028).** El recuperador del catálogo pasa de léxico a
  **embeddings**: modelo multilingüe local y **fijado** (`paraphrase-multilingual-MiniLM-L12-v2`, ONNX vía
  `fastembed`, extra `terranova[descubrimiento]`), orden por coseno con **piso** y desempate por valor,
  **re-embed completo por pasada** (no incremental). Reconciliado con ADR-0012: los embeddings viven
  **solo en el descubrimiento**, nunca en la ruta del dato (el sobre `rt/1` sigue determinista). Sin el
  extra, cae al léxico. Lógica pura probada sin red (embebedor falso); la corrida real con `fastembed` y
  el índice en pgvector van con el runtime del catálogo. Las API de búsqueda de los portales (Socrata/Hub)
  quedan como complemento, no como recuperador.
- **Segundo catálogo DCAT: las capas (ICDE, #91).** El Hub de datos abiertos de la ICDE
  (`datos.icde.gov.co`) expone un feed **DCAT-US 1.1** — el centro autoritativo nacional de datos
  espaciales, el análogo ArcGIS del DCAT de Socrata. `de_dcat_us` (puro) lo interpreta a la misma
  `DatasetDescubrible` (`protocolo=arcgis_rest`, `url`=endpoint REST); `catalogo-dcat ingerir --fuente
  icde` lo cosecha y el buscador cubre los dos catálogos a la vez. Validado en vivo: 10.000 ítems,
  **100 % CC BY 4.0 declarada**, pero **~89 % es restitución cartográfica del IGAC** (mapa base) y solo
  ~11 % «Dato temático»; por eso `de_dcat_us` marca la **clase** y la promoción se centra en el resto.
  Su valor es el **inventario** y un puñado de capas temáticas, no entidades nuevas (ver
  [FUENTES_OBJETIVO.md](FUENTES_OBJETIVO.md)). Colombia en Mapas / GeoNetwork IGAC (CSW) queda por confirmar.

**Lo que queda, bloqueado por dependencias** (no por falta de desarrollo):
- exponer `catalogo_buscar` como herramienta **`rt/1`** del gateway (REST/MCP) pide un conector interno
  nuevo + un `modo` en el ejecutor + ficha que pase las 19 reglas con **canario reproducible** + un
  **almacén en runtime** (PostGIS): es una decisión de **deploy** del catálogo (dónde vive, cómo se
  refresca, cómo canariza), no solo código;
- la **pasada completa con `scroll`** a PostGIS (el offset topa en ~10.000) depende de ese almacén;
- en el CLI, `catalogo buscar` (necesita el `rt/1` anterior), `exportar` (GDAL) y `verificar` (las
  **reglas de la obligación EUDR**, de F4/F5) esperan sus dependencias.

**F6 en el navegador (2026-10-23):** GEO Copilot conectado a la puerta (Caddy, dos réplicas) con una llave propia y cuatro perfiles (justicia, estadísticas, normativa, territorio: 97 herramientas, bajo el tope de 128 de OpenAI), LLM gpt-5.4-mini. Cuatro preguntas reales con la cifra medida en la fuente: homicidios (8) y hurto de vehículos (95; 28 automotores y 67 motos) de Chía 2024; vigencia y artículos de la Ley 1581 (30); masacres en Granada (74); y el predio de un punto de Chía con su ficha, pintado y encuadrado en el mapa. La prueba halló tres fallas, corregidas: la cuota por llave se gastaba en abrir sesión y listar herramientas por MCP (un cliente con cuatro perfiles quedaba sin cupo: ahora solo `tools/call` gasta); el sobre no decía el lugar de un código DIVIPOLA (el agente supuso 05380 por Granada y entregó los datos de La Estrella: ahora `zona_usada.nombre`, regla 11 de `rt/1`, y el agente se corrige solo); y el juez de GEO Copilot leía solo 400 caracteres de cada resultado y le hizo retractar una cifra correcta (geo-copilot). MCP queda sin estado (`stateless_http`), porque Caddy reparte entre réplicas sin afinidad. Falta F6.2 (el panel «Cómo lo hice» con fuente y licencia), F6.3 (E2E en Playwright) y F6.4 (misma huella por las tres puertas).

**Fiabilidad del agente con GEO Copilot (2026-10-24/25):** GEO Copilot hizo un plan de fiabilidad sobre la puerta con gpt-5.4-mini, y su batería de 32 preguntas pasó de 84,9 % a 29/32 en una corrida completa. Las tres fallas se arreglaron y, repetidas sobre el estado final, dieron 6/6. Cuatro cambios fueron de la puerta:
- un municipio se puede pedir por su nombre; si es ambiguo, la puerta responde `parametro_invalido` con los candidatos (regla 12 de `rt/1`, #76);
- un código con homónimos lleva un aviso que los lista, también desde la caché (#76). Antes, un agente puso 08001 (Barranquilla) por «San Andrés»;
- la ficha cierra con «sin uso comercial» cuando la fuente no lo permite (#77). Con «licencia: CC BY 4.0» a secas, un agente dijo que Open-Meteo se podía usar comercialmente;
- la ficha del contrato de SECOP dice quién lo firmó, con quién y por cuánto (#78). Su descripción no tenía esas palabras y la búsqueda por palabras la ponía en el puesto 11.

Queda abierto que el agente suponga el NIT de una entidad. Una salida es que la puerta resuelva la entidad por su nombre.

**Auditoría de fuentes (2026-10-25):** se revisaron las 130 fuentes y las 153 herramientas: canarios en vivo (en serie, una llamada por herramienta), licencias, personas, doradas, frescura y evidencias de licencia.
- **Canarios:** 144/153 en la primera pasada. Repetidos los rojos, quedan 3, las capas de agrología del IGAC: la consulta más liviana tarda 30 s en la fuente, y siguen esperando la copia (ADR-0023). Los demás rojos fueron pasajeros (PNN, RUES, ICFES, INVIMA y una suspensión de SECOP) o un dato reprocesado por la fuente (Open-Meteo: 92,2 mm, antes 91,5).
- **Frescura:** el sobre dice «Datos no recientes» cuando la ficha técnica lo muestra (regla 13). Le pasa a 15 fuentes, entre ellas ICFES, internet fijo, víctimas de minas y la UPRA.
- **Evidencias de licencia:** 3 estaban rotas (la Ley 23 en el Senado y los créditos de la DIAN) y ya se corrigieron.
- **Pendientes:** 5 fuentes en borrador con la licencia por verificar (ADR-0019) y la copia de agrología.

| Spec F0 | Estado |
|---|---|
| F0.1 Repo y estructura | ✅ `pyproject` (uv, Python 3.13), ruff y mypy estricto fijados, pytest, pre-commit, CI; `make check` verde |
| F0.2 ADR aceptadas | ✅ las 20 aceptadas el 2026-10-21, con su validación escrita; 0005, 0007, 0010, 0014, 0018 y 0019 se corrigieron al revisarlas |
| F0.3 Spike de protocolo (FastMCP 4.1 ↔ conector `mcp` 1.28, Claude Code, Inspector) | ✅ las tres pruebas de ADR-0003 pasan; salto p95 3,1 ms ([informe](spikes/F0.3-protocolo.md)) |
| F0.4 Spike GeoResult en GEO Copilot | ✅ pintado en el navegador ([informe](spikes/F0.4-geo-result.md)); el hub desanida el sobre (geo-copilot#43) |
| F0.5 Licencias de las fuentes M1 | ✅ decididas con evidencia en [`catalogo/licencias/m1.yaml`](../catalogo/licencias/m1.yaml): 12 a producción, 4 a evaluación (DANE, IDEAM geoservicios, SIAC, ambiente alojado en IGAC), SGC fuera |
| F0.6 PR de amenazas y clima en GEO Copilot + Open-Meteo | ✅ geo-copilot#38 (V5 3×4 revisada, fusionado) |
| F0.7 Banco de verdades del producto (40 preguntas) | ✅ [`catalogo/verdades_producto.yaml`](../catalogo/verdades_producto.yaml): 22 de territorio, 6 de contratación, 6 de empresas y 6 de normativa, medidas en la fuente el 2026-10-22. 26 con herramienta del catálogo (o `ficha_lugar`) y 14 de fuentes objetivo (SECOP agregado, RUES, SUIN). `tests/test_verdades.py` exige que no contradigan a los canarios |
| F0.8 Solicitudes por derecho de petición | ⬜ (humano) |

## F1 · Contrato y catálogo

| Spec F1 | Estado |
|---|---|
| F1.1 Modelos `rt/1` + JSON Schema `--check` + propiedades | ✅ `src/terranova/contrato.py`: reglas 1–9 como validadores, la 10 como función; esquemas en `esquemas/`; 38 pruebas (propiedades y casos), verificadas por mutación |
| F1.2 Modelos del catálogo + validador CI | ✅ `src/terranova/catalogo.py` + `scripts/validar_catalogo.py` en `make check`; 19 reglas rotas probadas; semilla: `igac.catastro.terreno` e `igac_predio_en_punto` |
| F1.3 Códigos de error y completitud en el kit (GEO Copilot) | ✅ geo-copilot#45 (kit, `arcgis-mcp`) y #46 (`datos-abiertos`, `dane`); la puerta lee `codigo` y `completitud` |
| F1.4 Catálogo inicial M1 | ✅ 18 fuentes y 20 herramientas, cada canario medido en la fuente el 2026-10-21; las fichas con `where` usan tipos con patrón (no hay `str` libre dentro de un texto: inyección) |
| F1.5 Índice de cobertura catastral | ✅ `catalogo/cobertura/cobertura_catastral.yaml`, medido por los sectores de la base: 780 municipios con datos. Bogotá y El Carmen de Viboral dan `fuera_de_cobertura` (0 créditos), verificado en vivo |

## F2 · Núcleo

| Spec F2 | Estado |
|---|---|
| F2.1 Ejecutor: catálogo → conector → lista blanca → `rt/1` | ✅ `src/terranova/ejecutor.py` + puerta generada (una herramienta MCP por ficha). Las 20 doradas se grabaron en vivo con su canario en verde (`scripts/grabar_doradas.py`) y se reproducen sin red; verificadas por mutación. E2E por MCP: 16/20, porque RUNAP estaba caído y ANT dio un error pasajero |
| F2.2 Compuerta de licencia y saneamiento | ✅ el ejecutor recibe el plan: `por_verificar` da `licencia_no_habilitada` sin llamar a la fuente salvo con plan `evaluacion`; NC con aviso; E2E-14 (texto malicioso y campo no declarado) en prueba; guarda contra caracteres invisibles en el código. El plan sale de `TERRANOVA_PLAN` hasta la identidad de F3.2 |
| F2.3 Caché con frescura y `obsoleto` | ✅ `src/terranova/cache.py`: el TTL es el `frescura.ttl_cache_s` de la fuente y un acierto no descuenta. Con la fuente caída sale `obsoleto`, con su `consultado_en` original y aviso; `frescura=estricta` prefiere el error; un error de la petición no se tapa con caché. Redis si hay `TERRANOVA_REDIS_URL` y, si no, memoria |
| F2.4 Cortacircuitos y bulkhead por fuente | ✅ `src/terranova/proteccion.py`: tras 3 caídas el circuito de esa fuente se abre 30 s y `fuente_no_disponible` sale en menos de 1 s sin tocarla (con copia, `obsoleto`); medio abierto; un reintento con jitter solo ante «no disponible»; 4 llamadas simultáneas por fuente |

## F3 · Puerta

| Spec F3 | Estado |
|---|---|
| F3.1 Adaptadores REST + MCP desde el catálogo; perfiles por familia | ✅ `src/terranova/app.py`: una ruta `POST /v1/co/{familia}/{herramienta}` por ficha (`operationId` = herramienta, entrada con patrones), errores problem+json con `Retry-After`, catálogo público en `/v1/fuentes` y `/v1/herramientas`; MCP en `/mcp` y en un perfil por familia; **paridad REST ≡ MCP en las 20 herramientas** en CI. Verificado en vivo con uvicorn |
| F3.2 Identidad: orgs, llaves, scopes, CLI | ✅ `src/terranova/identidad.py` y `terranova llaves crear/revocar/listar`: `rt_live_` (normal) y `rt_test_` (evaluación); solo se guarda el HMAC-SHA256 con pimienta; scopes por familia; vencimiento y `ultimo_uso`; la revocación surte efecto en la siguiente petición. REST y MCP sin llave dan 401 y sin scope 403; el catálogo es público. SQLite por ahora (Postgres con F3.7). Verificado en vivo |
| F3.3 Cuota (Redis) y saldo | ✅ `src/terranova/cuota.py`: token bucket por llave (20 de ráfaga, 60/min; 429 `limite_tasa` con `Retry-After` y `RateLimit-*`) y saldo mensual por organización (con_llave 20 000, ampliado 200 000; `terranova orgs nivel`). El costo se reserva antes de llamar y se devuelve lo no cobrado. **50 llamadas simultáneas sin sobreconsumo**, en memoria y en Redis (Lua atómico, probado con fakeredis) |
| F3.4 Medición (outbox) | ✅ `src/terranova/medicion.py`: un evento por solicitud, con el `solicitud_id` como clave (sin duplicados); las fallas y la caché quedan con 0 créditos y el resultado o código. Si el outbox falla, la respuesta sale igual. `Idempotency-Key` (REST): mismo sobre, sin ejecutar, cobrar ni medir otra vez (E2E-10); la misma clave con otra entrada da 400 |
| F3.5 Errores RFC 9457 y Schemathesis | ✅ Schemathesis sobre el OpenAPI publicado (`tests_lentos/`, job de CI aparte): 23 rutas sin 5xx ni respuestas fuera de esquema. Encontró y quedaron arreglados `false` aceptado como 0.0 (entrada estricta), un 500 con cuerpo vacío, errores de FastAPI fuera de problem+json y un 405 sin `Allow` |
| F3.6 OpenAPI, `llms.txt`, server card | ✅ OpenAPI 3.1, `/llms.txt` y `/.well-known/mcp/server-card.json` generados del catálogo; `docs/HERRAMIENTAS.md` también, con `--check` en CI |
| F3.7 Compose de despliegue | ✅ `Dockerfile` (98 MB, sin privilegios, falla cerrado sin pimienta) y `docker/compose.yml`: Caddy como única entrada, `puerta-a` y `puerta-b`, Postgres (llaves y uso) y Redis (caché y cuota) compartidos, y `arcgis-mcp` en la red interna. **E2E-01 a E2E-06 en verde contra el compose** (`scripts/e2e.py`, `scripts/e2e_gate_f3.py`) |

## F4 · Ficha y dataset de restricciones

| Spec F4 | Estado |
|---|---|
| F4.1 Dataset de restricciones v0 | ✅ `src/terranova/datasets/restricciones.py` + `scripts/dataset_restricciones.py`: RUNAP (1934) + resguardos (989) + zonas de reserva campesina (30) = 2953 filas, CC BY-SA 4.0; pandera, GeoParquet, PostGIS (`curado.restricciones`) y contrato ODCS. **Misma huella tras volver a descargar** (`sha256:fc56a228…`). Ley 2.ª fuera por licencia |
| F4.2 `ficha_lugar` | ✅ `src/terranova/ficha.py`; MCP `ficha_lugar` (en `/mcp` y `/mcp/territorio`) y REST `POST /v1/fichas`. Dos etapas en paralelo: 10 partes por punto y, con el predio, construcciones, población y precio de la tierra. Una parte que falla deja la ficha `parcial` con su error y su procedencia; la que no se consulta (licencia o scope) va a `avisos`. Tope de 20 s; la parte que no llega sigue en segundo plano y llena la caché. Hasta 50 créditos. **En vivo** (`scripts/e2e_ficha.py`): E2E-07 ✓, la ficha de Chía en 13,3 s, con el predio, las restricciones (contra el GeoParquet curado), los sismos (USGS `count` = 0) y UPRA (Chía no está) iguales a lo medido en la fuente; E2E-08 ✓ (amenazas caído → `parcial`, solo el error de sismos) |
| F4.3 Rendimiento de la ficha | ✅ Las restricciones salen del dataset curado (PostGIS, `servido_desde: curado`). Tope de la ficha en 12 s (ADR-0023): lo que no llega sale `fuente_lenta` y sigue en segundo plano para la caché. En vivo (2026-10-22, 10 puntos nuevos en serie): p95 12,2 s ✓ (< 15 s), 7 de 10 `parcial` por la agrología del IGAC y la lentitud del catastro ese día; con caché, p95 0,02 s ✓ |

## F5 · Expansión hasta las fuentes objetivo

Plan: [`PLAN_EXPANSION.md`](PLAN_EXPANSION.md). Avance: **81 herramientas** de ~139 (cuentan al tener 3 días de canario verde).

| Pieza u ola | Estado |
|---|---|
| G2 Corte mensual del IGAC | ✅ `scripts/corte_igac.py`: lee la fecha de corte de la descripción de cada servicio, no del nombre (`…_IGAC_de_octubre` es el corte de octubre de **2025**); con `--escribir` actualiza las fichas catastrales. Vigente al 2026-10-22: `06_2026` |
| G1 Agregados en Socrata | ✅ `group` y `having` en `datos_consultar` (geo-copilot#51). Con datos de personas, `having count(*) >= 10` en la ficha (ADR-0014) |
| G3 Conector de copia | ✅ ADR-0024. `terranova copias actualizar` (y el servicio `copias` del compose, diario) baja la ventana de la fuente con solo su lista blanca a `copia.<tabla>_<versión>` y cambia la vista vigente de una vez; manifiesto con huella, filas, ventana y repetidas. El conector interno `copia` arma SQL parametrizado con vocabulario cerrado (filtros, texto en español, count/sum/avg/median, group) y responde `servido_desde: copia` con la fecha de la copia, `obsoleto` si pasó su SLA y un aviso con la ventana. Primera copia: SECOP II contratos (en local, desde 2026-07-01: 334 428 filas en 131 s; 3 claves repetidas en la fuente) |
| G4 Conector web (primera parte) | ✅ `web-mcp` (geo-copilot#53): `web_json` (API REST de WordPress, total de `X-WP-Total`) y `web_sdmx` (SDMX-ML 2.1 generic y structure specific). Lista de dominios, solo https, `robots.txt` y una petición por segundo por sitio. Falta la segunda parte: HTML con estado (WebForms/JSF) para normas y jurisprudencia |
| Perfil de la fuente (spec 07) | ✅ **las 77 fuentes perfiladas (2026-10-22)**; una fuente nueva sin perfil rompe el CI. `scripts/perfilar_fuente.py` mide Socrata y ArcGIS (con `--punto`). El perfil corrigió 12 herramientas: ICFES (estudiantes repetidos), SECOP Integrado (un contrato por estado: Pitalito 2025 sumaba $174 000 M, son $63 157 M), SIC (sancionados ≠ resoluciones), copias en SECOP II e INVIMA, y predio en punto (265 polígonos con número en ceros). Se corrigieron etiquetas: el clima de Open-Meteo no es ERA5 puro (es su mezcla con IFS) y BanRep trae fechas futuras (TRM de mañana, UVR hasta el 15 del mes siguiente); la vigencia de las zonas homogéneas viene vacía en ~12 % y con años imposibles. Pendiente: repetir el 2026-10-29 si la mezcla de Open-Meteo cambia los últimos días |
| Ficha técnica de la fuente (spec 08) | ✅ las 77 fuentes con ficha técnica: 66 cosechadas de la fuente (`scripts/cosechar_metadatos.py`, `src/terranova/cosecha.py`) y 11 a mano. Junta lo curado, lo cosechado (fechas, frecuencia y cobertura declaradas, geometría, CRS, extensión, capas, diccionario de campos con nulos, mínimo, máximo y códigos) y el perfil, y calcula alertas. Se sirve en `GET /v1/fuentes/{id}` y en MCP `fuente_describir`. Hallazgos: el ICFES declara actualización semestral y no cambia desde 2023-08; el SUIT «histórico» cubre 2018–2021; UPRA sin cambios desde 2022; fechas imposibles en SECOP; la «fecha cero» de Excel (1899-12-30) en las vigencias del IGAC. La cosecha no guarda valores de columnas de personas ni texto libre: el máximo de `ppto_total` en el PAA era el teléfono de una alcaldesa. Canario de deriva: `--comprobar`, entra con F7.1 |
| G5 Herramientas de la fábrica | 🟨 `docker/compose.desarrollo.yml` expone los conectores en 127.0.0.1 para grabar doradas desde el host |
| Ola 1 · IGAC catastro | 🟨 8 nuevas. Base catastral: `igac_registro_predio` (REGISTRO_1), `igac_caracteristicas_predio` (REGISTRO_2), `igac_perimetro_urbano_en_punto`, `igac_sector_en_punto`. Zonas homogéneas 2026: `igac_zona_geoeconomica_en_punto` (valor del suelo) y `igac_zona_fisica_en_punto`. `igac_estadisticas_catastrales_municipio` (predios, áreas y avalúos por año y estado; licencia por verificar: solo evaluación) e `igac_gestor_catastral_municipio` (datos.gov.co, sin los contactos de personas). Las tablas necesitan geo-copilot#50. En la fuente, `codigo_municipio` dice 23175 para Chía: no se usa |
| Ola 1 · Agregados (G1) | 🟨 4 nuevas: `icfes_saber11_municipio` (estudiantes y puntajes promedio por periodo, solo grupos con n ≥ 10), `men_educacion_municipio` y `men_educacion_departamento` (cobertura, deserción, aprobación desde 2011) e `igac_compraventas_municipio` (compraventas por año 2015–2023; el valor solo desde 2021; promedio, no mediana: la mediana espera la copia, G3) |
| Ola 1 · SECOP | 🟨 11 nuevas (13 con las de M1): `secop_proceso_por_id` (acepta el proceso de compra CO1.BDOS o una fase CO1.REQ), `secop_proponentes_proceso`, `secop_contratos_entidad` y `secop_integrado_contratos_entidad` (SECOP I y II, por año), y el detalle de un contrato: adiciones, garantías, ejecución, pagos, modificaciones, suspensiones y sanciones. Por número de registro o NIT de entidad, nunca por persona; sin documentos, supervisores, asegurados ni contactos. Cada ficha pide a la fuente solo su lista blanca (`select`), así la dorada tampoco guarda datos de personas. `secop_contratos_buscar` (texto del objeto, desde la copia G3: 0,24 s). Falta proveedores por NIT (el NIT puede ser una cédula) |
| SECOP completo | 🟨 15 nuevas sobre el inventario de los 46 conjuntos oficiales ([plan](PLAN_EXPANSION.md#inventario-de-secop-46-conjuntos-oficiales-de-colombia-compra-en-datosgovco)): SECOP II facturas, compromisos, rubros, CDP, ubicaciones, cronograma, BPIN y convenios; SECOP I proceso por constancia, adiciones, modificaciones de procesos y de adjudicaciones, origen de los recursos, proponentes y documentos. Verdades medidas en la fuente con `fabrica_secop` (canario de persona jurídica cuando sale el documento, ADR-0025). Ofertas y archivos de SECOP II necesitan copia (la fuente no responde a tiempo). Sumados el PAA de SECOP I (encabezado y detalle). Proveedores registrados no se sirve: su `nit` trae cédulas y datos engañosos |
| Ola 2 · datos.gov.co | 🟨 8 nuevas: INVIMA (medicamentos por principio activo y por expediente, dispositivos médicos, registros de alimentos y cosméticos), sanciones de la SIC por sector y año, trámites del SUIT por entidad, RUES por NIT (solo personas jurídicas: 7 de 9,4 M registros son personas naturales) y las 10 000 empresas más grandes (cifras en billones de pesos, como texto de la fuente). Sumados los estados financieros NIIF de Supersociedades (situación financiera, resultado integral, flujo de efectivo, otro resultado integral y carátula) por NIT. Sumados BanRep (TRM, tasa de política, IBR, DTF, UVR: últimas observaciones; el servicio no filtra por fecha) y la relatoría de Colombia Compra (conceptos y providencias por palabras), BanRep con licencia verificada (aviso legal §2, confirmado por el dueño el 2026-10-22: reproducción libre sin alterar, con fuente y fecha de consulta); la relatoría por verificar (no está confirmado que la Ley 23 cubra los conceptos). Falta el directorio DIAN (bulk) |

## F7 · Operación (en paralelo desde F3)

| Spec F7 | Estado |
|---|---|
| F7.1 Canarios diarios | 🟨 `terranova canarios [--cada-horas 24]` (`src/terranova/vigilancia.py`). Corre los 20 canarios en serie, sin caché, y guarda cada resultado (SQLite o Postgres). Con `TERRANOVA_ALERTA_URL`, avisa por POST lo que salga rojo. `GET /v1/estado` da el estado por fuente. El compose suma el servicio `canarios`. Primera corrida en vivo (2026-10-22): 17 verdes; rojos la capacidad de uso del IGAC (20 s, arranque en frío) y los dos de RUNAP (el servicio de Parques tarda 60 s por punto). El compose ya trae los cinco conectores del catálogo (antes solo `arcgis-mcp`). Corrida del 2026-10-22 con todos: 18 verdes y 2 rojos (agrología del IGAC, 44–84 s); RUNAP ya en verde. Una segunda corrida dio 15 verdes y 5 lentos: la agrología y tres a menos de 1,5 s por encima de su tope de 5 s (IDEAM, SECOP, UPRA). Falta la aceptación: 7 días seguidos registrados en un despliegue |
| F7.2 Métricas y tablero | ✅ `/metrics` en cada réplica con las métricas de la spec 05 §12.2 (`src/terranova/metricas.py`), bloqueado en Caddy; Prometheus y Grafana en el perfil `observabilidad`, 8 reglas probadas con `promtool` en CI y un tablero de 12 paneles. **Verificado en el compose local (2026-10-22):** las dos réplicas leídas, las 8 reglas cargadas, el tablero y su fuente de datos en Grafana, y cada uno de los 12 paneles con datos tras tráfico de prueba (caché, errores de fuente provocados apagando un conector, llamadas en vivo). Se corrigió que una ficha con el predio en caché y el resto en vivo contara como caché y disparara `LatenciaConCacheAlta`. Los rechazos del borde (400 de validación, 401, 429) no pasan por el ejecutor y no cuentan en `rt_solicitudes_total`, como pide el SLO |
| F7.3 Runbook | ✅ [`docs/RUNBOOK.md`](RUNBOOK.md): fuente caída, cambio de esquema, llave filtrada y restauración, con un simulacro de cada uno (2026-10-22, registro en el runbook §5). Cada canario declara sus `campos` (`scripts/campos_canario.py`): un campo que la fuente renombra sale `esquema_cambiado`. Servicio `respaldo` (`pg_dump` diario, 14 días); restaurado en una base nueva en 15 s, con la llave funcionando |
| F7.4 Página de estado pública | ⬜ (M2) |

## Decisiones tomadas

- Nombre **Terrnova**; repo público `geoai-latam/terranova`.
- **Todo open source y gratuito** al inicio: código Apache 2.0, datos CC BY-SA 4.0. Los créditos son
  cuota (protegen las fuentes y el gasto), no cobro.
- Hitos: **M1** (puerta, contrato, catálogo, ficha, GEO Copilot como cliente, sobre las fuentes que
  ya existen) y **M2** (las ~139 herramientas de [FUENTES_OBJETIVO.md](FUENTES_OBJETIVO.md), lotes,
  trabajos lentos).
- Sin `TERRANOVA_PIMIENTA` la puerta no arranca. El plan sale de la llave; `TERRANOVA_PLAN` solo rige en pruebas sin identidad.
- Personas por cédula o nombre: fuera. Captchas y backends sin permiso: nunca, en ningún plan (ADR-0018).
- Cuota agotada: 429 `saldo_agotado`, sin 402 (ADR-0010). Licencia `por_verificar`: solo llaves de evaluación (ADR-0007).
- Open-Meteo: API gratis mientras Terrnova sea gratuito, con caché y tope propio; salida a Copernicus directo (ADR-0021).
- Escaneo de secretos (gitleaks) en CI, sobre toda la historia (ADR-0001).
- Boletines de Contraloría y BDME: se evalúan con asesoría legal antes de incluirlos.

## Pendiente de decidir

Lo vigente está en el [estado consolidado](#estado-consolidado-del-producto-2026-10-28-main-en-182)
(pendientes del dueño).

## Siguiente paso concreto

*Registro del 2026-10-23; lo vigente está en el estado consolidado, arriba.*

**Al 2026-10-23 (madrugada del 24): 153 herramientas sobre 130 fuentes, más que las ~139 abiertas de la referencia**, cada una con perfil (spec 07), ficha técnica (spec 08), canario medido en la fuente y dorada grabada en vivo. Olas 1 y 2 cerradas, salvo lo que no se puede servir sin carga ni permiso. De la ola 3 ya están: Corte Constitucional (índice y texto), normas en HTML (Función Pública, Normograma DIAN, CREG), anexos del DANE (IPM, GEIH), usuarios aduaneros de la DIAN, historia registral por folio, IPM municipal, Superfinanciera, Supersolidaria, REPS, los siete reportes de delitos de la Policía Nacional, Medicina Legal, las once modalidades del SIEVCAC del CNMH, víctimas de minas, proyectos y presupuesto de regalías, EVA agrícola e internet fijo. **Banco de agente (2026-10-23, `scripts/banco_agente.py`, gpt-5.4-mini, 60 preguntas en seis familias, cada una en su perfil):** herramienta correcta 97 % (ADR-0006 pide ≥ 90 %), éxito estricto 73 %, 2,2 llamadas y ~17 000 tokens por pregunta. Halló dos fallas de la puerta, ya corregidas: el esquema de `ficha_lugar` con `oneOf` arriba hacía que OpenAI rechazara la lista entera de herramientas, y el esquema de entrada no decía la forma de los códigos (el agente leyó «DIVIPOLA seguido de 000» en la ficha técnica y mandó 25175000). `/mcp` completo (150) ya pasa el tope de 128 herramientas de OpenAI: esos clientes usan los perfiles por familia. **Segunda ronda (mismo día):** con las herramientas de nombre a código (`dane_divipola_buscar` y `secop_entidades_municipio`, en todos los perfiles), SUIN-Juriscol (`suin_norma`, `suin_normas_anio`) y `secop_contratos_entidad_anio`, el éxito estricto subió a 83 % (herramienta correcta 93 %). Se corrigió además: las búsquedas por nombre (RUES, Superfinanciera, Supersolidaria, DIVIPOLA) ponen primero la coincidencia más corta (con orden alfabético, «ECOPETROL» llenaba los 50 con asociaciones); SECOP por municipio no distingue mayúsculas; las herramientas por NIT de entidad devuelven el nombre de la entidad en cada fila, para que un NIT supuesto se note; y una fuente que a veces responde vacío sin error (zonas de reserva campesina de la ANT, ~25 %) se reintenta hasta 3 veces antes de decir «no encontrado» (`comportamiento.reintentos_si_vacio`). Lo que queda es del modelo mini y no de la puerta: a veces supone un NIT pese a la instrucción, suma mal filas que ya vienen totalizadas o prefiere Función Pública a SUIN para la vigencia (respuesta correcta en esa fuente). Las fuentes lentas o caídas (RUNAP ~35 s, BanRep 502, ANT «Unable to complete operation») se informan como «no se pudo», no como «no hay». Siguiente: la pieza «scrape con estado». Piezas nuevas en GEO Copilot: `arcgis_estadisticas`, `web_html`, `web_tabla` y el intermedio TLS verificado de Función Pública. Avance frente a Croma en [`PLAN_EXPANSION.md`](PLAN_EXPANSION.md#avance-frente-a-croma).

0. **Spec 08 (hecha):** siguen los códigos sin dominio (usos del suelo, destino económico, clases agrológicas) con su resolución del IGAC, la geometría del DANE y el canario de deriva en F7.1.
1. **F5 · expansión hasta la paridad** (plan en [`PLAN_EXPANSION.md`](PLAN_EXPANSION.md)): primero las dos piezas
   genéricas (conector de copia y conector de scrape con estado) y la ola 1. La ola 6 espera permisos.
   **F6** arranca en paralelo. La VM espera: todo se valida en local.
2. **En paralelo:**
   - **F0.6 (hecho):** la V5 de amenazas con LLM real halló dos fallas del conector, corregidas en
     geo-copilot#38: el resumen de sismos y focos se calculaba antes de recortar al área (los
     «sismos más fuertes de Colombia» salían de Panamá y Venezuela) y `clima_serie` no decía que
     el límite va en `punto`. La V5 necesita `lugares-mcp` arriba; sin él, el agente espera 300 s
     una aprobación humana. geo-copilot#43 ya estaba fusionado.
   - **F0.8:** las solicitudes por derecho de petición están en borrador en `interno/borradores/`;
     las envía el dueño. Se sumaron DANE (redistribución del MGN y el CNPV) y SGC (la licencia de
     MIIG choca con los ítems CC BY en ArcGIS Online).

## Hechos medidos que sirven de canario

| Verdad | Valor |
|---|---|
| Predio en (-74.0262, 4.8619), Chía | `251750000000000050067000000000` (R_TERRENO, corte 06_2026), ~0,5 s directo |
| SECOP, contratos de Chía | 12 147 contratos, $1,29 billones, 1,7 s |
| RUNAP en el bbox de prueba | 169 áreas |
| Población de Bogotá (CNPV 2018) | 7 181 469 |
| REGISTRO_1 IGAC (corte 06-2026) | 6 812 177 predios |
| Transacciones inmobiliarias IGAC | 30,9 M |

## Versiones de referencia (2026-10-21)

| Pieza | Versión |
|---|---|
| Especificación MCP | 2026-07-28 |
| FastMCP | 4.1.3 |
| SDK `mcp` (Python) | 2.3.0 (los conectores de GEO Copilot siguen en 1.28.1) |
| Herramientas en los conectores de GEO Copilot | 49, en 12 servicios |

## Hallazgos abiertos

- IGAC: `codigo_municipio` errado en la fuente (Chía sale `23175`). Hace falta un canario en F1.
- IGAC: el último corte mensual es `06_2026`; revisar `Base_Catastral_Publica_IGAC_de_octubre` en F1.5.

- IGAC: El Carmen de Viboral (05148) figura con gestor IGAC y no tiene datos en la base; 63 municipios
  están igual. Por eso la cobertura se mide y no sale del registro de gestores.
- IDEAM `hp9r-jxuu`: la columna `ubicaci_n` trae latitud y longitud cruzadas; la herramienta usa
  `latitud`/`longitud`.
- SECOP: los totales de un municipio crecen cada día, así que el canario usa `minimos`. Las peticiones
  tienen que ir en UTF-8 («Chía»).
- FIRMS y GloFAS no tienen ventana fija para medir una verdad: sin herramienta en el catálogo hasta que
  haya canarios estructurales (F2).
- Minambiente: las reservas forestales con geometría no tienen licencia; RUNAP ya las cubre (BY-SA).
- RUNAP, ANT y agrología IGAC: el polígono completo hacía tardar más de 90 s una consulta por punto.
  Ahora se pide `geometria: simplificada` (geo-copilot#48) y RUNAP en punto tarda 1,2 s.
- `datos-abiertos-mcp`: un `count`/`sum` con `$order=:id` daba HTTP 400 (geo-copilot#47).
- Tras un timeout, la sesión MCP con el conector quedaba inservible; `ConectorMCP` ahora la reabre.
- Conectores de GEO Copilot (mcp 1.28): una tool `def` corría dentro del bucle de eventos y una fuente
  lenta dejaba el servidor sin atender nada, ni siquiera un `GET`. Ahora corren en un hilo
  (geo-copilot#49, fusionado). En vivo, la ficha pasó de caer entera por tiempo a 13 s.
- Agrología del IGAC (`mapas.igac.gov.co`): arranque en frío de ~45 s en la primera consulta después
  de un rato; luego 1 a 2 s. Es lo que hoy impide cumplir el p95 en vivo de la ficha.
- RUES (`c82u-588k`, CC BY-SA): mezcla personas naturales, con nombre y cédula, y jurídicas. Una
  herramienta futura filtra solo personas jurídicas y usa lista blanca de campos (ADR-0014). EPM no
  está (no se matricula).
- SUIN-Juriscol (`fiev-nid6`): el tipo va en mayúsculas («LEY») y hay errores de clasificación (la
  Ley 2.ª de 1959 sale con materia «Administración de justicia»). Se cita lo que dice la fuente.
- RUNAP (`mapas.parquesnacionales.gov.co`): el 2026-10-22 una consulta por punto tardó 60 s (los
  metadatos, 0,4 s). Lo detectó el primer canario diario.
- Compose: un conector caído al arrancar tumbaba la puerta, que entraba en un ciclo de reinicios.
  Ahora arranca igual. La primera llamada con el conector caído tarda unos 7 s (DNS de Docker más 3 s
  de sesión); tras 3 caídas se abre el circuito y la respuesta baja a menos de 1 s.

## Cómo correr las comprobaciones

`make check` (CI, Linux) o `uv run scripts/check.py` (Windows sin `make`): ruff, formato, mypy y
pytest. `make instalar` sincroniza dependencias e instala los ganchos de pre-commit.
