"""Motor real do oráculo sobre Pydantic AI (ADR-0007). Único lugar que importa
pydantic_ai. RAG clássico (knowledge injetado) + tools HTTP agênticas."""

from typing import AsyncIterator

from pydantic_ai import Agent

from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import AgentMessage, AgentStreamChunk, KnowledgeSnippet
from src.support.agent.prompts import SYSTEM_PROMPT
from src.support.agent.tools import FetchNotionTool, WebSearchTool, format_knowledge, wrap_tool_content
from src.support.clients.notion.notion_client import NotionClient
from src.support.clients.tavily.tavily_client import TavilyClient
from src.support.core.settings import settings


def _model_id() -> str:
    if settings.LLM_PROVIDER == "openai":
        return f"openai:{settings.OPENAI_MODEL}"
    return f"anthropic:{settings.ANTHROPIC_MODEL}"


def _build_prompt(question: str, history: list[AgentMessage], knowledge: list[KnowledgeSnippet]) -> str:
    parts: list[str] = []
    for msg in history:
        parts.append(f"{msg.role}: {msg.content}")
    parts.append("Contexto recuperado da base de conhecimento:")
    parts.append(format_knowledge(knowledge))
    parts.append(f"Pergunta do usuário: {question}")
    return "\n\n".join(parts)


class OracleEngine:
    def __init__(self, model=None) -> None:
        self._model = model or _model_id()

    async def stream_answer(
        self,
        question: str,
        history: list[AgentMessage],
        knowledge: list[KnowledgeSnippet],
    ) -> AsyncIterator[AgentStreamChunk]:
        web_citations: list[Citation] = []
        web_tool = WebSearchTool(tavily=TavilyClient(), collected=web_citations)
        notion_tool = FetchNotionTool(notion=NotionClient())

        agent = Agent(self._model, system_prompt=SYSTEM_PROMPT)

        @agent.tool_plain
        async def web_search(query: str) -> str:
            """Busca informação pública na web quando a base interna não cobre."""
            try:
                return await web_tool.run(query)
            except Exception as exc:  # falha de tool não deve derrubar o streaming
                return wrap_tool_content(f"(falha ao buscar na web: {exc})")

        @agent.tool_plain
        async def fetch_notion_page(page_id: str) -> str:
            """Busca o conteúdo completo/atualizado de uma página do Notion."""
            try:
                return await notion_tool.run(page_id)
            except Exception as exc:  # falha de tool não deve derrubar o streaming
                return wrap_tool_content(f"(falha ao buscar página do Notion: {exc})")

        prompt = _build_prompt(question, history, knowledge)
        async with agent.run_stream(prompt) as result:
            async for delta in result.stream_text(delta=True):
                yield AgentStreamChunk(type="text", text=delta)

        kb_citations = [s.citation for s in knowledge]
        yield AgentStreamChunk(type="sources", citations=kb_citations + web_citations)


def get_oracle_engine() -> "OracleEngine":
    return OracleEngine()
