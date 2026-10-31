# La puerta de Terrnova: REST /v1 y MCP en una imagen (F3.7, ADR-0015).
FROM python:3.13-slim

RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.5

WORKDIR /srv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY catalogo ./catalogo
# sin dependencias de desarrollo; con Postgres y Redis (varias réplicas)
RUN uv sync --locked --no-dev --extra postgres --extra redis && rm -rf /root/.cache

RUN useradd --uid 10100 --no-create-home terranova
USER 10100
ENV PATH="/srv/.venv/bin:$PATH" TERRANOVA_HOST=0.0.0.0 TERRANOVA_PUERTO=8100
EXPOSE 8100
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:8100/v1/fuentes > /dev/null || exit 1
CMD ["terranova"]
