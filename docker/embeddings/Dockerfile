# Microservicio de embeddings (ADR-0028, Q2): el modelo (ONNX, fastembed) en un solo contenedor,
# en la red interna. La puerta y el job de ingesta lo llaman por HTTP. El modelo se BAJA al construir
# la imagen, así en runtime es offline (coherente con «nunca carga a ciegas» y con el aire acotado).
FROM python:3.13-slim

RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.12.5

WORKDIR /srv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
# sin dependencias de desarrollo; con el extra de embeddings (fastembed + uvicorn)
RUN uv sync --locked --no-dev --extra descubrimiento && rm -rf /root/.cache

# hornear el modelo fijado en la imagen (se baja una vez, al construir; runtime offline)
ENV PATH="/srv/.venv/bin:$PATH"
ENV FASTEMBED_CACHE_PATH=/srv/modelos
RUN python -c "from terranova.descubrimiento import MODELO_EMBEDDING; from fastembed import TextEmbedding; TextEmbedding(MODELO_EMBEDDING)"

RUN useradd --uid 10101 --no-create-home embeddings && chown -R 10101 /srv/modelos
USER 10101
ENV TERRANOVA_EMBEDDINGS_HOST=0.0.0.0 TERRANOVA_EMBEDDINGS_PUERTO=9950
EXPOSE 9950
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -fsS http://localhost:9950/salud > /dev/null || exit 1
CMD ["terranova", "embeddings-servicio"]
