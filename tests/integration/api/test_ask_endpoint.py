from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture(autouse=True)
async def _dispose_db_engine_between_tests():
    """Cada teste roda em seu próprio event loop (asyncio_mode=auto, escopo function).
    O engine assíncrono global (src.support.core.database.engine) é criado uma única
    vez no import e mantém conexões asyncpg presas ao loop do teste anterior — sem
    dispose, o segundo teste que bate no app real (via ASGITransport) reusa uma
    conexão de um loop fechado. Descartar o pool aqui isola os testes deste arquivo."""
    yield
    from src.support.core.database import engine

    await engine.dispose()


class FailingOracleEngine:
    """Motor fake que emite um chunk de texto e então explode — simula falha
    no meio do streaming, depois que os headers 200 + SSE já foram enviados."""

    async def stream_answer(self, question, history, knowledge=None) -> AsyncIterator:
        from src.support.agent.ports import AgentStreamChunk

        yield AgentStreamChunk(type="text", text="ola ")
        raise RuntimeError("boom: engine caiu no meio do stream")


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


@pytest.mark.asyncio
async def test_ask_stream_failure_emits_error_and_done(monkeypatch):
    import src.app.api.controllers.conversation_controller as ctrl
    from tests.fakes.fake_embeddings_client import FakeEmbeddingsClient

    monkeypatch.setattr(ctrl, "get_oracle_engine", lambda: FailingOracleEngine())
    monkeypatch.setattr(ctrl, "get_embeddings_client", lambda: FakeEmbeddingsClient())

    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversations/ask",
            json={"question": "o que é o onboarding?", "history": []},
        )
        # Headers já foram enviados (200) antes da falha ocorrer no meio do stream;
        # o erro é sinalizado via evento SSE, não via status code.
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "event: error" in body
        assert "event: done" in body
