# Hoja de ruta: fases, specs y gates

Cada fase cierra con un **gate**: criterios medibles; si no se cumplen, no se pasa. Tamaño: S (< 1
día), M (1–3 días), L (> 3 días) de trabajo enfocado.

## F0 · Cimientos y decisiones

| Spec | Qué | Aceptación | Tamaño |
|---|---|---|---|
| F0.1 | Repo público `terranova` creado (hecho), estructura, `pyproject`, ruff, mypy, pytest, pre-commit | `make check` verde en local | S |
| F0.2 | ADR 0001–0017 revisadas y aceptadas (o cambiadas) | ADR con estado `aceptada` | S |
| F0.3 | Spike de protocolo: puerta FastMCP 4.1 mínima con 1 herramienta; Claude Code + MCP Inspector; cliente FastMCP 4 → conector `mcp` 1.28 | las tres pruebas de ADR-0003 pasan; salto p95 < 50 ms | M |
| F0.4 | Spike GeoResult: el hub de GEO Copilot materializa el bloque `geo_result` de un `rt/1` | capa pintada en el mapa (navegador) | S |
| F0.5 | Verificación de licencias de las fuentes M1 (PNN, DANE, UPRA, IDEAM, ANT, Minambiente) y de las de [FUENTES_OBJETIVO.md](FUENTES_OBJETIVO.md) | cada una `si/no` con evidencia en el catálogo | M (humano) |
| F0.6 | Cerrar el PR de amenazas y clima de GEO Copilot y decidir Open-Meteo (suscripción o Copernicus directo) | decisión registrada | S |
| F0.7 | Banco de verdades del producto: 40 preguntas con verdad medida en la fuente (territorio, contratación, empresas, normativa) | `verdades_producto.yaml` | M |
| F0.8 | Solicitudes por derecho de petición ([FUENTES_OBJETIVO.md](FUENTES_OBJETIVO.md)), sin firmar contratos: IGAC (Geovisor, BY vs BY-SA), Supersociedades (SIIS), CSJ (CPNU), AMVA (SIATA), DNP (TerriData), BanRep | enviadas; respuesta registrada en el catálogo | S (humano) |

**Gate F0:** ADR aceptadas, spikes verdes, licencias M1 decididas.

## F1 · Contrato y catálogo

| Spec | Qué | Aceptación | Tamaño |
|---|---|---|---|
| F1.1 | Modelos `rt/1` (Pydantic) + exportación JSON Schema con `--check` | esquema en CI; 10 invariantes del contrato como pruebas de propiedad (Hypothesis) | M |
| F1.2 | Modelos del catálogo + validador CI (specs/02-catalogo.md) | catálogo inválido rompe CI | M |
| F1.3 | En el kit público: códigos de error estables en `ToolRunner` y bloque `consulta`/`completitud` en los `facts` | conectores devuelven `codigo` y `vistos/total`; pruebas del kit | M |
| F1.4 | Catálogo inicial: fuentes y herramientas M1 (~25 herramientas) | todas validan; licencia decidida | M |
| F1.5 | Índice de cobertura catastral por municipio | `fuera_de_cobertura` para Bogotá en catastro IGAC | S |

**Gate F1:** contrato y catálogo en CI; conectores M1 emiten códigos y completitud.

## F2 · Núcleo

| Spec | Qué | Aceptación | Tamaño |
|---|---|---|---|
| F2.1 | Ejecutor de herramienta: catálogo → llamada al conector → mapeo con lista blanca → `rt/1` | pruebas doradas con cassettes (pytest-recording) por herramienta | L |
| F2.2 | Compuerta de licencia y saneamiento de texto | pruebas: SGC bloqueado; control/bidi eliminados; largo máximo | S |
| F2.3 | Caché Redis por (herramienta, entrada normalizada, versión) con TTL de frescura; `obsoleto` etiquetado | pruebas de caché y de obsoleto con fuente caída simulada | M |
| F2.4 | Cortacircuitos y bulkhead por fuente; reintento con jitter solo en lecturas | fuente caída → `fuente_no_disponible` en < 1 s con circuito abierto | M |
| F2.5 | Operaciones geo genéricas `capa_en_punto`/`capa_en_zona` con tope de área | pruebas doradas | M |

**Gate F2:** cada herramienta M1 pasa su prueba dorada y su canario en vivo una vez.

## F3 · Puerta

| Spec | Qué | Aceptación | Tamaño |
|---|---|---|---|
| F3.1 | Generador de adaptadores REST + MCP desde el catálogo; perfiles por familia | prueba de paridad verde para todas las herramientas | L |
| F3.2 | Identidad: orgs, llaves, scopes, CLI `rt llaves crear/revocar/listar` | matriz de permisos; revocación < 5 s | M |
| F3.3 | Cuota (Redis) y saldo; 429 (`limite_tasa`, `saldo_agotado`) con encabezados | prueba de concurrencia: sin sobreconsumo con 50 llamadas simultáneas | M |
| F3.4 | Medición: outbox con `solicitud_id` único; no descuenta fallas ni caché | pruebas: reintento idempotente no duplica; falla del outbox no rompe la respuesta | M |
| F3.5 | Errores RFC 9457 y su espejo MCP | Schemathesis sin 5xx ni violaciones de esquema | S |
| F3.6 | OpenAPI 3.1, `llms.txt`, server card, documentación generada | Schemathesis corre sobre el OpenAPI publicado | S |
| F3.7 | Compose de despliegue (Caddy, puerta ×2, conectores en red interna, Postgres, Redis) | `docker compose up` y E2E-01 pasa contra él | M |

**Gate F3:** E2E-01 a E2E-06 verdes (specs/04-pruebas.md).

## F4 · Ficha y dataset de restricciones

| Spec | Qué | Aceptación | Tamaño |
|---|---|---|---|
| F4.1 | Pipeline del dataset de restricciones v0: descarga → validación (pandera) → unión → GeoParquet + PostGIS → huella → versión | dos corridas sobre la misma fuente dan la misma huella; contrato ODCS del dataset | L |
| F4.2 | `ficha_lugar` (specs/03-superficie.md) con partes en paralelo y estado `parcial` | ficha del predio de Chía = verdades; con una fuente caída sale `parcial` | M |
| F4.3 | Rendimiento de la ficha | p95 < 15 s en vivo, < 2 s con caché | S |

**Gate F4:** E2E-07 y E2E-08 verdes.

## F5 · Fuentes objetivo (la fábrica en olas)

- **Unidad de trabajo:** una ficha de fuente + sus herramientas + mapeo + canario con verdad, escrita
  por un agente de la fábrica, revisada y aprobada por una persona, validada por CI.
- **Olas** (detalle en [FUENTES_OBJETIVO.md](FUENTES_OBJETIVO.md)):
  1. IGAC base catastral (job del corte mensual), `$group` en Socrata, SECOP con copia nocturna:
     ~35 herramientas.
  2. Victorias rápidas: INVIMA, directorio DIAN, sanciones SIC, SUIT, ANCP-CCE, BanRep SDMX, UPRA,
     NIIF de Supersociedades, RUES abierto: ~21.
  3. Corte Constitucional y gestores normativos (Función Pública, CREG, DIAN, SFC, SIC), anexos
     DANE, TerriData: ~21.
  4. SAMAI, Consejo de Estado, CNDJ, Imprenta, SIATA, ANM: ~27.
  5. SIPI y gaceta de la SIC, Corte Suprema: ~13.
  6. Con permiso: Geovisor IGAC (avalúo), SIIS, CPNU: ~9.
- Piezas genéricas que aceleran todo (detalle en [PLAN_EXPANSION.md](PLAN_EXPANSION.md)): G1
  agregados en Socrata, G2 corte mensual del IGAC, G3 **conector de copia** (bulk → PostGIS con
  huella y frescura), G4 **conector de scrape con estado** (WebForms/JSF, con copia y canario) y G5
  herramientas de la fábrica.
- **Por ola:** herramientas en el catálogo, pruebas doradas, canario 3 días verde, banco de agente
  sobre la familia ≥ 90 %.
- **Métrica de la fábrica:** horas desde «fuente elegida» hasta «canario verde 3 días», por fuente.

**Gate F5:** [FUENTES_OBJETIVO.md](FUENTES_OBJETIVO.md) al 100 % en «abiertas y factibles».

## F6 · GEO Copilot como cliente

| Spec | Qué | Aceptación | Tamaño |
|---|---|---|---|
| F6.1 | `config/mcp_servers.yaml` con la puerta como servidor (llave propia, perfil `territorio`) | el copiloto lista y llama herramientas de la puerta | S |
| F6.2 | El panel «Cómo lo hice» muestra fuente, licencia y `servido_desde` de cada parte | visible en navegador | M |
| F6.3 | E2E en navegador (Playwright) con backend real: «ficha de este predio» | pasa; captura guardada | M |
| F6.4 | Las tres puertas: la misma pregunta por Claude (MCP), REST y el copiloto | misma huella en las tres | S |

**Gate F6 = M1** (si F5 aún no terminó) o **M2** (si sí).

## F7 · Operación

| Spec | Qué | Aceptación | Tamaño |
|---|---|---|---|
| F7.1 | Canarios diarios (cron) + resultados en Postgres + alerta | 7 días seguidos registrados | M |
| F7.2 | Métricas y tablero (specs/05-metricas-slo.md) + alertas de SLO | tablero con las métricas de specs/05-metricas-slo.md | M |
| F7.3 | Runbook: fuente caída, cambio de esquema, llave filtrada, restauración de respaldo | simulacro de cada uno hecho una vez | M |
| F7.4 | Página de estado pública (M2) | publica el estado de canarios por fuente | S |

F7.1 y F7.2 empiezan en paralelo con F3: los canarios valen desde la primera herramienta.

## Definición de terminado

**M1** — todos: gates F0–F4 y F6; E2E-01 a E2E-11 y E2E-14 verdes; canarios 7 días; SLO de
latencia y conformidad cumplidos en la ventana; demo grabada de las tres puertas con la misma huella.

**M2** — M1 más: F5 completa; E2E-12 y E2E-13; banco de agente ≥ 90 % en las cinco familias; SLO de
disponibilidad y correctitud 14 días; página de estado; cuotas y medición funcionando; términos de uso y
privacidad publicados.

**Demo de 5 minutos:** 1) se crea una llave; 2) Claude pregunta por un predio y recibe la ficha con
fuentes y licencias; 3) la misma llamada por `curl`; 4) GEO Copilot la pinta en el mapa; 5) se apaga
una fuente y la respuesta lo dice; 6) el tablero muestra canarios y créditos.
