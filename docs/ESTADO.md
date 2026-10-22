# Estado

*Actualizado: 2026-10-22.*

## Dónde estamos

**Gates F0 a F4 cerrados (2026-10-22).** La puerta está completa: REST y MCP generados del catálogo, identidad, cuota, medición, caché, cortacircuitos y despliegue con dos réplicas. E2E-01 a E2E-08 en verde. El gate F4 se cerró sin esperar la copia de agrología del IGAC (ADR-0023: tope de la ficha en 12 s). Siguen **F5** (expansión hasta la paridad, por olas) y **F6** (GEO Copilot como cliente).

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

Plan: [`PLAN_EXPANSION.md`](PLAN_EXPANSION.md). Avance: **44 herramientas** de ~139 (cuentan al tener 3 días de canario verde).

| Pieza u ola | Estado |
|---|---|
| G2 Corte mensual del IGAC | ✅ `scripts/corte_igac.py`: lee la fecha de corte de la descripción de cada servicio, no del nombre (`…_IGAC_de_octubre` es el corte de octubre de **2025**); con `--escribir` actualiza las fichas catastrales. Vigente al 2026-10-22: `06_2026` |
| G1 Agregados en Socrata | ✅ `group` y `having` en `datos_consultar` (geo-copilot#51). Con datos de personas, `having count(*) >= 10` en la ficha (ADR-0014) |
| G3 Conector de copia | ✅ ADR-0024. `terranova copias actualizar` (y el servicio `copias` del compose, diario) baja la ventana de la fuente con solo su lista blanca a `copia.<tabla>_<versión>` y cambia la vista vigente de una vez; manifiesto con huella, filas, ventana y repetidas. El conector interno `copia` arma SQL parametrizado con vocabulario cerrado (filtros, texto en español, count/sum/avg/median, group) y responde `servido_desde: copia` con la fecha de la copia, `obsoleto` si pasó su SLA y un aviso con la ventana. Primera copia: SECOP II contratos (en local, desde 2026-07-01: 334 428 filas en 131 s; 3 claves repetidas en la fuente) |
| G5 Herramientas de la fábrica | 🟨 `docker/compose.desarrollo.yml` expone los conectores en 127.0.0.1 para grabar doradas desde el host |
| Ola 1 · IGAC catastro | 🟨 8 nuevas. Base catastral: `igac_registro_predio` (REGISTRO_1), `igac_caracteristicas_predio` (REGISTRO_2), `igac_perimetro_urbano_en_punto`, `igac_sector_en_punto`. Zonas homogéneas 2026: `igac_zona_geoeconomica_en_punto` (valor del suelo) y `igac_zona_fisica_en_punto`. `igac_estadisticas_catastrales_municipio` (predios, áreas y avalúos por año y estado; licencia por verificar: solo evaluación) e `igac_gestor_catastral_municipio` (datos.gov.co, sin los contactos de personas). Las tablas necesitan geo-copilot#50. En la fuente, `codigo_municipio` dice 23175 para Chía: no se usa |
| Ola 1 · Agregados (G1) | 🟨 4 nuevas: `icfes_saber11_municipio` (estudiantes y puntajes promedio por periodo, solo grupos con n ≥ 10), `men_educacion_municipio` y `men_educacion_departamento` (cobertura, deserción, aprobación desde 2011) e `igac_compraventas_municipio` (compraventas por año 2015–2023; el valor solo desde 2021; promedio, no mediana: la mediana espera la copia, G3) |
| Ola 1 · SECOP | 🟨 11 nuevas (13 con las de M1): `secop_proceso_por_id` (acepta el proceso de compra CO1.BDOS o una fase CO1.REQ), `secop_proponentes_proceso`, `secop_contratos_entidad` y `secop_integrado_contratos_entidad` (SECOP I y II, por año), y el detalle de un contrato: adiciones, garantías, ejecución, pagos, modificaciones, suspensiones y sanciones. Por número de registro o NIT de entidad, nunca por persona; sin documentos, supervisores, asegurados ni contactos. Cada ficha pide a la fuente solo su lista blanca (`select`), así la dorada tampoco guarda datos de personas. `secop_contratos_buscar` (texto del objeto, desde la copia G3: 0,24 s). Falta proveedores por NIT (el NIT puede ser una cédula) |

## F7 · Operación (en paralelo desde F3)

| Spec F7 | Estado |
|---|---|
| F7.1 Canarios diarios | 🟨 `terranova canarios [--cada-horas 24]` (`src/terranova/vigilancia.py`). Corre los 20 canarios en serie, sin caché, y guarda cada resultado (SQLite o Postgres). Con `TERRANOVA_ALERTA_URL`, avisa por POST lo que salga rojo. `GET /v1/estado` da el estado por fuente. El compose suma el servicio `canarios`. Primera corrida en vivo (2026-10-22): 17 verdes; rojos la capacidad de uso del IGAC (20 s, arranque en frío) y los dos de RUNAP (el servicio de Parques tarda 60 s por punto). El compose ya trae los cinco conectores del catálogo (antes solo `arcgis-mcp`). Corrida del 2026-10-22 con todos: 18 verdes y 2 rojos (agrología del IGAC, 44–84 s); RUNAP ya en verde. Una segunda corrida dio 15 verdes y 5 lentos: la agrología y tres a menos de 1,5 s por encima de su tope de 5 s (IDEAM, SECOP, UPRA). Falta la aceptación: 7 días seguidos registrados en un despliegue |
| F7.2 Métricas y tablero | ✅ `/metrics` en cada réplica con las métricas de la spec 05 §12.2 (`src/terranova/metricas.py`), bloqueado en Caddy; Prometheus y Grafana en el perfil `observabilidad`, 8 reglas probadas con `promtool` en CI y un tablero de 12 paneles. **Verificado en el compose local (2026-10-22):** las dos réplicas leídas, las 8 reglas cargadas, el tablero y su fuente de datos en Grafana, y cada uno de los 12 paneles con datos tras tráfico de prueba (caché, errores de fuente provocados apagando un conector, llamadas en vivo). Se corrigió que una ficha con el predio en caché y el resto en vivo contara como caché y disparara `LatenciaConCacheAlta`. Los rechazos del borde (400 de validación, 401, 429) no pasan por el ejecutor y no cuentan en `rt_solicitudes_total`, como pide el SLO |
| F7.3 Runbook | ✅ [`docs/RUNBOOK.md`](RUNBOOK.md): fuente caída, cambio de esquema, llave filtrada y restauración, con un simulacro de cada uno (2026-10-22, registro en el runbook §5). Cada canario declara sus `campos` (`scripts/campos_canario.py`): un campo que la fuente renombra sale `esquema_cambiado`. Servicio `respaldo` (`pg_dump` diario, 14 días); restaurado en una base nueva en 15 s, con la llave funcionando |
| F7.4 Página de estado pública | ⬜ (M2) |

## Decisiones tomadas

- Nombre **Terranova**; repo público `geoai-latam/terranova`.
- **Todo open source y gratuito** al inicio: código Apache 2.0, datos CC BY-SA 4.0. Los créditos son
  cuota (protegen las fuentes y el gasto), no cobro.
- Hitos: **M1** (puerta, contrato, catálogo, ficha, GEO Copilot como cliente, sobre las fuentes que
  ya existen) y **M2** (las ~139 herramientas de [FUENTES_OBJETIVO.md](FUENTES_OBJETIVO.md), lotes,
  trabajos lentos).
- Sin `TERRANOVA_PIMIENTA` la puerta no arranca. El plan sale de la llave; `TERRANOVA_PLAN` solo rige en pruebas sin identidad.
- Personas por cédula o nombre: fuera. Captchas y backends sin permiso: nunca, en ningún plan (ADR-0018).
- Cuota agotada: 429 `saldo_agotado`, sin 402 (ADR-0010). Licencia `por_verificar`: solo llaves de evaluación (ADR-0007).
- Open-Meteo: API gratis mientras Terranova sea gratuito, con caché y tope propio; salida a Copernicus directo (ADR-0021).
- Escaneo de secretos (gitleaks) en CI, sobre toda la historia (ADR-0001).
- Boletines de Contraloría y BDME: se evalúan con asesoría legal antes de incluirlos.

## Pendiente de decidir


## Siguiente paso concreto

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
