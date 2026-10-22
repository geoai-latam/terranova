# Arquitectura

```
                CLIENTES: Claude / ChatGPT / Cursor · scripts · SIG · GEO Copilot (llave propia)
                         │ MCP (streamable HTTP)            │ REST /v1 (OpenAPI 3.1)
                ┌────────▼──────────────────────────────────▼────────┐
  PUERTA        │ Caddy (TLS) → servicio «puerta» (FastAPI + FastMCP 4 montado)   │
  (abierto)     │  identidad (llave→org→plan→scopes) · cuota (Redis) · medición    │
                │  (outbox Postgres) · errores RFC 9457 · idempotencia · versión   │
                ├──────────────────────────────────────────────────────┤
  NÚCLEO        │ herramientas generadas del CATÁLOGO · operaciones geo · ficha    │
  (abierto)     │ compuerta de licencia · lista blanca de campos · caché + frescura│
                │ cortacircuitos por fuente · ensamblado del contrato rt/1          │
                └────────┬────────────────────┬───────────────────────────┘
                         │ MCP red interna     │ SQL
                ┌────────▼─────────┐   ┌──────▼───────────────────────────────┐
  CONECTORES    │ 12 servicios MCP  │   │ PostGIS: datasets curados versionados │
  (público,     │ (GEO_COPILOT,     │   │ + copias de fuentes abiertas en bloque│
  Apache 2.0)   │ Apache 2.0)       │   │ Postgres: orgs, llaves, uso, auditoría│
                └────────┬─────────┘   └───────────────────────────────────────┘
                         ▼
  FUENTES       IGAC · PNN · DANE · datos.gov.co/SECOP · SIC · Supersociedades · cortes · BanRep ·
                SIATA · Copernicus · USGS · NASA · …
  OPERACIÓN     canarios diarios por fuente · OTel → Jaeger · Prometheus · alertas · tablero
```

**Todo abierto (ADR-0001):** los conectores (GEO_COPILOT) y la puerta, el catálogo, los mapeos,
los canarios y los datasets (`terranova`) son públicos. El código va con Apache 2.0, y el catálogo y
los datasets con CC BY-SA 4.0 (compatible con las fuentes BY-SA). Lo que no se copia leyendo el repo
es **operarlo**: mantener ~150 fuentes al día, con canarios verdes, copias frescas y respuesta a las
caídas.
