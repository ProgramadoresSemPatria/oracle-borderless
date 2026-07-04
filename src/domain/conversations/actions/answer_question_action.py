from typing import AsyncIterator

from src.domain.documents.actions.search_knowledge_base_action import SearchKnowledgeBaseAction
from src.support.agent.ports import AgentMessage, AgentStreamChunk, OracleEnginePort


class AnswerQuestionAction:
    """Caso de uso do oráculo: recupera a base (RAG clássico) e delega o streaming
    ao motor. Composição de Action (SearchKnowledgeBaseAction) + engine."""

    def __init__(self, engine: OracleEnginePort, search: SearchKnowledgeBaseAction) -> None:
        self.engine = engine
        self.search = search

    async def execute(
        self, question: str, history: list[AgentMessage]
    ) -> AsyncIterator[AgentStreamChunk]:
        knowledge = await self.search.execute(question)  # sessão viva aqui
        return self.engine.stream_answer(question, history, knowledge)
