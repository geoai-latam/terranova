# ADR-0013 · Observabilidad y canarios

- **Estado:** aceptada (2026-10-21).
- **Decisión:** OTel en la puerta (spans `tools/call <herramienta>` y un hijo por llamada a fuente con
  `fuente_id`, caché, estado del cortacircuitos) → Jaeger; métricas Prometheus de la puerta ([specs/05-metricas-slo.md](../specs/05-metricas-slo.md));
  canarios diarios por fuente con GitHub Actions programado (repo público) y, para fuentes que
  bloqueen las IP de Actions, desde el servidor con `cron`;
  resultado de cada canario guardado en Postgres para el tablero y la página de estado.
- **Validación (2026-10-21):** Sin conflictos. Los canarios diarios hacen una consulta por fuente, no carga.
