# Estado

*Actualizado: 2026-10-21.*

## Dónde estamos

**Gates F0 a F3 cerrados (2026-10-22).** La puerta está completa: REST y MCP generados del catálogo, identidad, cuota, medición, caché, cortacircuitos y despliegue con dos réplicas. E2E-01 a E2E-06 pasan contra el compose. Sigue **F4 · Ficha y dataset de restricciones**.

| Spec F0 | Estado |
|---|---|
| F0.1 Repo y estructura | ✅ `pyproject` (uv, Python 3.13), ruff y mypy estricto fijados, pytest, pre-commit, CI; `make check` verde |
| F0.2 ADR aceptadas | ✅ las 20 aceptadas el 2026-10-21, con su validación escrita; 0005, 0007, 0010, 0014, 0018 y 0019 se corrigieron al revisarlas |
| F0.3 Spike de protocolo (FastMCP 4.1 ↔ conector `mcp` 1.28, Claude Code, Inspector) | ✅ las tres pruebas de ADR-0003 pasan; salto p95 3,1 ms ([informe](spikes/F0.3-protocolo.md)) |
| F0.4 Spike GeoResult en GEO Copilot | ✅ pintado en el navegador ([informe](spikes/F0.4-geo-result.md)); el hub desanida el sobre (geo-copilot#43) |
| F0.5 Licencias de las fuentes M1 | ✅ decididas con evidencia en [`catalogo/licencias/m1.yaml`](../catalogo/licencias/m1.yaml): 12 a producción, 4 a evaluación (DANE, IDEAM geoservicios, SIAC, ambiente alojado en IGAC), SGC fuera |
| F0.6 PR de amenazas y clima en GEO Copilot + Open-Meteo | ⬜ |
| F0.7 Banco de verdades del producto (40 preguntas) | ⬜ |
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
| F4.2 `ficha_lugar` | ⬜ |
| F4.3 Rendimiento de la ficha | ⬜ |

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

1. **F4.2 y F4.3:** `ficha_lugar` con sus partes en paralelo y estado `parcial`; p95 < 15 s en vivo.
2. **En paralelo:**
   - **F0.6:** repetir la tanda V5 del PR geo-copilot#38 (la que quedó a medias por falta de memoria)
     y fusionarlo. También fusionar geo-copilot#43.
   - **F0.7:** banco de 40 verdades medidas en la fuente.
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
- Compose: un conector caído al arrancar tumbaba la puerta, que entraba en un ciclo de reinicios.
  Ahora arranca igual. La primera llamada con el conector caído tarda unos 7 s (DNS de Docker más 3 s
  de sesión); tras 3 caídas se abre el circuito y la respuesta baja a menos de 1 s.

## Cómo correr las comprobaciones

`make check` (CI, Linux) o `uv run scripts/check.py` (Windows sin `make`): ruff, formato, mypy y
pytest. `make instalar` sincroniza dependencias e instala los ganchos de pre-commit.
