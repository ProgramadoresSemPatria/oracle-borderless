import pytest

from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import KnowledgeSnippet
from src.support.agent.tools import (
    WebSearchTool,
    format_knowledge,
    wrap_tool_content,
)
from tests.fakes.fake_tavily_client import FakeTavilyClient


def test_wrap_tool_content_uses_markers():
    out = wrap_tool_content("abc")
    assert out.startswith("<<TOOL_CONTENT>>") and out.endswith("<</TOOL_CONTENT>>")


def test_format_knowledge_labels_sources():
    snips = [KnowledgeSnippet("trecho", Citation("notion", "Regras", "u", "s", "pid"))]
    text = format_knowledge(snips)
    assert "Regras" in text and "trecho" in text
    assert text.startswith("<<TOOL_CONTENT>>")


@pytest.mark.asyncio
async def test_web_search_tool_collects_citations():
    from src.support.clients.tavily.tavily_client import WebResult

    collected: list[Citation] = []
    fake = FakeTavilyClient(results=[WebResult(title="Artigo", url="https://ex/a", content="corpo")])
    tool = WebSearchTool(tavily=fake, collected=collected)
    out = await tool.run("pergunta pública")
    assert out.startswith("<<TOOL_CONTENT>>")
    assert "Artigo" in out
    assert len(collected) == 1
    assert all(c.source_type == "web" for c in collected)
