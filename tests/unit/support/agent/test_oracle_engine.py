import pytest

from src.domain.shared.value_objects.citation import Citation
from src.support.agent.oracle_engine import OracleEngine
from src.support.agent.ports import AgentStreamChunk, KnowledgeSnippet


@pytest.mark.asyncio
async def test_engine_streams_text_and_final_sources():
    from pydantic_ai.models.test import TestModel  # modelo de teste do pydantic_ai

    engine = OracleEngine(model=TestModel())
    knowledge = [KnowledgeSnippet("o onboarding leva 7 dias", Citation("notion", "Onboarding", "u", "s", "pid"))]

    chunks = [c async for c in engine.stream_answer("quantos dias?", [], knowledge)]

    assert any(c.type == "text" for c in chunks)
    sources = [c for c in chunks if c.type == "sources"]
    assert len(sources) == 1
    # a citação da base injetada deve aparecer nas fontes finais
    assert any(cit.title == "Onboarding" for cit in sources[0].citations)
