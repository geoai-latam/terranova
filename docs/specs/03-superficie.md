# Superficie: REST, MCP y ficha de un lugar

## 8.1 REST `/v1`

| Ruta | Qué |
|---|---|
| `GET /v1/fuentes`, `GET /v1/fuentes/{id}` | catálogo público (entidad, licencia, cobertura, estado del canario) |
| `GET /v1/herramientas` | lista con esquemas |
| `POST /v1/co/{familia}/{herramienta}` | una herramienta (una ruta por herramienta, generada) |
| `POST /v1/co/{familia}/{herramienta}/lote` | lote ≤ 50 (M2) |
| `POST /v1/geo/capa-en-punto`, `/v1/geo/capa-en-zona` | operación genérica sobre una capa del catálogo |
| `POST /v1/fichas` | ficha de un lugar (punto, polígono, código predial o DIVIPOLA) |
| `GET /v1/datasets`, `GET /v1/datasets/{id}/versiones` | datasets curados y sus huellas |
| `GET /v1/trabajos/{id}` | estado de un trabajo lento (M2) |
| `GET /v1/uso` | saldo y consumo de la propia llave |
| `GET /v1/estado` | estado por fuente (canarios) |
| `GET /openapi.json`, `/llms.txt` | descripción para personas y agentes |

Encabezados: `Authorization`, `Idempotency-Key`, `Prefer: wait=N` (M2), `X-Request-Id`,
`RateLimit-Policy`, `RateLimit`, `X-Cache`, `ETag`/`If-None-Match`, `Deprecation`, `Sunset`.

## 8.2 MCP

`/mcp` (todo) y perfiles por familia; herramientas generadas con `inputSchema`, `outputSchema`,
anotaciones (`readOnlyHint: true`, `idempotentHint: true`, `openWorldHint: true`); `buscar_herramientas`,
`ficha_lugar`, `capa_en_punto`, `capa_en_zona`; `server/discover` y server card en
`/.well-known/mcp/server-card.json`.

## 8.3 Ficha de un lugar (M1)

Entrada: punto, polígono (≤ tope), número predial o DIVIPOLA. Partes, en paralelo, cada una con su
procedencia y su error propio:

| Parte | Fuente | Estado de licencia |
|---|---|---|
| Predio y construcciones | IGAC catastro | ✅ BY o BY-SA según el ítem |
| Restricciones | dataset curado v0 (Ley 2.ª IGAC + RUNAP si se verifica + lo que pase la compuerta) | parcial |
| Amenaza de inundación | IGAC | ✅ |
| Sismos recientes (radio) | USGS | ✅ dominio público |
| Focos de calor (7 días) | NASA FIRMS | ✅ |
| Suelo (vocación y conflictos) | IGAC | ✅ |
| Cobertura del suelo | ESA WorldCover | ✅ CC BY |
| Población | DANE (si se verifica) o WorldPop | DANE por verificar |
| Contexto municipal | TerriData / SECOP resumen | según licencia |

Tope de tiempo total 12 s (ADR-0023); lo que no llega a tiempo sale como error de esa parte (`parcial`) y sigue en segundo plano para llenar la caché.
