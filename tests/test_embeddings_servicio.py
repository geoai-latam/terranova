"""Microservicio de embeddings (ADR-0028, Q2): la app con un embebedor falso y el cliente remoto,
sin modelo ni red real."""

import httpx
from fastapi.testclient import TestClient

from terranova.descubrimiento import EmbedderRemoto
from terranova.embeddings_servicio import crear_app


class _EmbedderFalso:
    def consulta(self, texto: str) -> tuple[float, ...]:
        return (1.0, 0.0, 0.0)

    def documentos(self, textos: list[str]) -> list[tuple[float, ...]]:
        return [(float(len(t)), 0.0, 0.0) for t in textos]


def _cliente() -> TestClient:
    return TestClient(crear_app(embedder=_EmbedderFalso()))


def test_salud() -> None:
    r = _cliente().get("/salud")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"
    assert "e5" in r.json()["modelo"]  # intfloat/multilingual-e5-small


def test_embed_consulta() -> None:
    r = _cliente().post("/embed", json={"consulta": "dónde hay agua"})
    assert r.status_code == 200
    assert r.json() == {"vectores": [[1.0, 0.0, 0.0]]}


def test_embed_documentos() -> None:
    r = _cliente().post("/embed", json={"documentos": ["ab", "abcd"]})
    assert r.json()["vectores"] == [[2.0, 0.0, 0.0], [4.0, 0.0, 0.0]]


def test_embed_exige_uno_u_otro() -> None:
    assert _cliente().post("/embed", json={}).status_code == 422
    c = _cliente()
    assert c.post("/embed", json={"consulta": "x", "documentos": ["y"]}).status_code == 422


def test_embedder_remoto_habla_con_el_servicio() -> None:
    capturado: dict[str, object] = {}

    def handler(req: httpx.Request) -> httpx.Response:
        import json

        capturado["url"] = str(req.url)
        capturado["body"] = json.loads(req.content)
        return httpx.Response(200, json={"vectores": [[0.1, 0.2, 0.3]]})

    http = httpx.Client(transport=httpx.MockTransport(handler))
    emb = EmbedderRemoto("http://embeddings:9950", cliente=http)

    assert emb.consulta("agua") == (0.1, 0.2, 0.3)
    assert capturado["url"] == "http://embeddings:9950/embed"
    assert capturado["body"] == {"consulta": "agua"}
    assert emb.documentos([]) == []  # lista vacía no llama al servicio
