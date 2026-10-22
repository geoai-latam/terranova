# Métricas y SLO

## 12.1 SLI y SLO de M1/M2

| SLI | Definición | SLO |
|---|---|---|
| Disponibilidad de la puerta | respuestas no-5xx propias / total (los 502/504 de fuente no cuentan como nuestros, se reportan aparte) | ≥ 99,5 % mensual |
| Latencia con caché | p95 de respuestas `cache`/`copia`/`curado` | < 300 ms |
| Latencia en vivo | p95 por herramienta | < 5 s (o el p95 medido de la fuente + 1 s) |
| Latencia de la ficha | p95 en vivo | < 15 s |
| Correctitud | canarios verdes / canarios ejecutados por día | ≥ 95 % |
| Frescura | respuestas dentro del SLA de frescura de su fuente | ≥ 99 % |
| Completitud | respuestas con `truncado: true` sin que el cliente pidiera límite | < 1 % |
| Paridad | herramientas REST ≡ MCP | 100 % |
| Conformidad | respuestas que validan `rt/1` | 100 % |
| Agente | tasa de éxito del banco | ≥ 90 % |

## 12.2 Métricas operativas (Prometheus)

`rt_solicitudes_total{herramienta,estado,codigo}`, `rt_latencia_segundos{herramienta,servido_desde}`,
`rt_fuente_latencia_segundos{fuente}`, `rt_cache_aciertos_total`, `rt_circuito_abierto{fuente}`,
`rt_creditos_total{nivel}`, `rt_canario{fuente,resultado}`, `rt_outbox_pendientes`.

## 12.3 Métricas de producto y de la fábrica

| Métrica | Para qué |
|---|---|
| Herramientas con canario verde / herramientas objetivo | avance (FUENTES_OBJETIVO.md) |
| Horas por fuente nueva (elegida → canario verde 3 días) | velocidad de la fábrica |
| Llaves activas por semana; consultas por llave; retención a 4 semanas | ¿se usa? |
| Usuarios que vuelven y fuentes que piden | ¿sirve? |
| Fuentes rotas por semana y tiempo de reparación | costo real de mantener |
