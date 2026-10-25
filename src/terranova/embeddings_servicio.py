"""Microservicio de embeddings (ADR-0028, Q2): aísla el modelo (onnxruntime, `fastembed`) del
proceso de la puerta —así no se duplica en cada réplica— y lo sirve por HTTP en la red interna.

La puerta (el conector del catálogo) y el job de ingesta lo llaman con `EmbedderRemoto`
(`descubrimiento.py`). Solo expone `POST /embed` y `GET /salud`; no toca fuentes ni base, y no lleva
llave (vive en la red interna, como los conectores MCP, ADR-0002). El modelo se fija en
`descubrimiento.MODELO_EMBEDDING` y se hornea en la imagen (offline en runtime).

    terranova embeddings-servicio        # uvicorn en TERRANOVA_EMBEDDINGS_PUERTO (9950 por defecto)
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, model_validator


class PeticionEmbed(BaseModel):
    """O una `consulta` (una pregunta) o `documentos` (textos de datasets), no ambos ni ninguno."""

    model_config = ConfigDict(extra="forbid", strict=True)
    consulta: str | None = None
    documentos: list[str] | None = None

    @model_validator(mode="after")
    def _uno_u_otro(self) -> PeticionEmbed:
        if (self.consulta is None) == (self.documentos is None):
            raise ValueError("manda exactamente uno: 'consulta' o 'documentos'")
        return self


def crear_app(embedder: Any = None) -> FastAPI:
    """La app. Con `embedder` inyectado se prueba sin modelo ni red; sin él, carga `FastEmbedder`
    (el modelo real) perezosamente en la primera petición."""
    app = FastAPI(title="terranova-embeddings", version="1")
    estado: dict[str, Any] = {"embedder": embedder}

    def _embedder() -> Any:
        if estado["embedder"] is None:
            from terranova.descubrimiento import FastEmbedder

            estado["embedder"] = FastEmbedder()
        return estado["embedder"]

    @app.get("/salud")
    def salud() -> dict[str, str]:
        return {"estado": "ok", "modelo": _nombre_modelo()}

    @app.post("/embed")
    def embed(p: PeticionEmbed) -> dict[str, list[list[float]]]:
        e = _embedder()
        if p.consulta is not None:
            return {"vectores": [list(e.consulta(p.consulta))]}
        return {"vectores": [list(v) for v in e.documentos(p.documentos or [])]}

    return app


def _nombre_modelo() -> str:
    from terranova.descubrimiento import MODELO_EMBEDDING

    return MODELO_EMBEDDING


app = crear_app()


def main() -> None:
    import uvicorn

    uvicorn.run(
        app,
        host=os.environ.get("TERRANOVA_EMBEDDINGS_HOST", "127.0.0.1"),
        port=int(os.environ.get("TERRANOVA_EMBEDDINGS_PUERTO", "9950")),
    )
