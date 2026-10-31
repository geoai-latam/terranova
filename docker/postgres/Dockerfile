# Postgres de Terrnova: pgvector (catálogo de descubrimiento, G6/ADR-0028) + PostGIS (dataset
# curado de restricciones, F4.1). Base pgvector:pg17 (Debian bookworm): la imagen postgis:17-3.5
# quedaba en Debian bullseye, cuyo repo PGDG ya no trae Release file y rompía `apt-get`.
FROM pgvector/pgvector:pg17
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-17-postgis-3 postgresql-17-postgis-3-scripts \
    && rm -rf /var/lib/apt/lists/*
# La base pgvector no corre los init de postgis; se crean las dos extensiones al iniciar la base.
COPY docker/postgres/initdb/ /docker-entrypoint-initdb.d/
