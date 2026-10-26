# Postgres de Terranova: PostGIS (dataset curado de restricciones, F4.1) + pgvector (catálogo de
# descubrimiento, G6/ADR-0028). La imagen oficial de PostGIS no trae pgvector; se añade la extensión.
FROM postgis/postgis:18-3.6
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-17-pgvector \
    && rm -rf /var/lib/apt/lists/*
