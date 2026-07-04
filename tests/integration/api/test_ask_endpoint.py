import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_ask_streams_sse(monkeypatch):
    import src.app.api.controllers.conversation_controller as ctrl
    from tests.fakes.fake_embeddings_client import FakeEmbeddingsClient
    from tests.fakes.fake_oracle_engine import FakeOracleEngine

    monkeypatch.setattr(ctrl, "get_oracle_engine", lambda: FakeOracleEngine(answer="resposta de teste"))
    # A base pode estar vazia no banco de teste; isolamos de rede trocando o client
    # de embeddings real (que chamaria a OpenAI) pelo fake determinístico.
    monkeypatch.setattr(ctrl, "get_embeddings_client", lambda: FakeEmbeddingsClient())

    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversations/ask",
            json={"question": "o que é o onboarding?", "history": []},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "resposta" in body
        assert "sources" in body  # evento final de fontes
