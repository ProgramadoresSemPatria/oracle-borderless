import pytest

from src.support.agent.ports import AgentMessage, AgentStreamChunk, KnowledgeSnippet
from src.domain.shared.value_objects.citation import Citation
from tests.fakes.fake_oracle_engine import FakeOracleEngine


def test_text_chunk_defaults():
    c = AgentStreamChunk(type="text", text="olá")
    assert c.text == "olá" and c.citations == []


def test_sources_chunk_carries_citations():
    from src.domain.shared.value_objects.citation import Citation

    c = AgentStreamChunk(type="sources", citations=[Citation("web", "T", "u", "s")])
    assert c.type == "sources" and len(c.citations) == 1


def test_agent_message():
    m = AgentMessage(role="user", content="oi")
    assert m.role == "user"


def test_knowledge_snippet_carries_content_and_citation():
    snip = KnowledgeSnippet(
        content="texto",
        citation=Citation("notion", "Doc", "https://n/a", "trecho", "pid"),
    )
    assert snip.content == "texto"
    assert snip.citation.is_notion()


@pytest.mark.asyncio
async def test_fake_engine_accepts_knowledge_argument():
    engine = FakeOracleEngine(answer="ola mundo")
    snippets = [KnowledgeSnippet("ctx", Citation("notion", "D", "u", "s", "p"))]
    chunks = [c async for c in engine.stream_answer("q?", [], snippets)]
    assert any(c.type == "text" for c in chunks)
    assert any(c.type == "sources" for c in chunks)
