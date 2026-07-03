import pytest

from src.support.agent.ports import AgentMessage
from tests.fakes.fake_oracle_engine import FakeOracleEngine


@pytest.mark.asyncio
async def test_fake_engine_streams_text_then_sources():
    engine = FakeOracleEngine(answer="ola mundo")
    chunks = [c async for c in engine.stream_answer("q", history=[AgentMessage("user", "q")])]
    assert chunks[-1].type == "sources"
    text = "".join(c.text for c in chunks if c.type == "text")
    assert "ola" in text and "mundo" in text
