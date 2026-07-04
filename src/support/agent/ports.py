"""Fronteira fina entre domínio e o motor Pydantic AI (ver ADR-0007).

O domínio (AnswerQuestionAction) consome estes tipos; NÃO importa pydantic_ai.
"""

from dataclasses import dataclass, field
from typing import AsyncIterator, Literal, Protocol

from src.domain.shared.value_objects.citation import Citation


@dataclass
class AgentMessage:
    role: str  # "user" | "assistant"
    content: str


@dataclass
class AgentStreamChunk:
    type: Literal["text", "sources"]
    text: str = ""
    citations: list[Citation] = field(default_factory=list)


@dataclass
class KnowledgeSnippet:
    """Trecho recuperado da base (RAG clássico), com sua fonte para citação."""

    content: str
    citation: Citation


class OracleEnginePort(Protocol):
    def stream_answer(
        self,
        question: str,
        history: list[AgentMessage],
        knowledge: list[KnowledgeSnippet],
    ) -> AsyncIterator[AgentStreamChunk]: ...
