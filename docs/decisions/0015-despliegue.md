# ADR-0015 · Despliegue

- **Estado:** aceptada (2026-10-21).
- **Decisión:** una VM (2–4 vCPU, 8–16 GB) con Docker Compose: Caddy (TLS automático), puerta (2
  réplicas), conectores, Postgres/PostGIS, Redis, Prometheus, Jaeger. Copias de seguridad diarias de
  Postgres fuera de la VM. Sin gateway externo; se revisa con más tráfico.
- **Consecuencias:** costo estimado USD 50–200/mes (por medir); un solo punto de falla aceptado en
  MVP y declarado en el SLO.
- **Validación (2026-10-21):** Razonable para el MVP. El costo real se mide al desplegar; el punto único de falla queda declarado en el SLO.
