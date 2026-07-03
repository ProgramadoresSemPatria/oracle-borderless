"""Client de LLM do oráculo — Claude (Anthropic) ou GPT (OpenAI), selecionável.

Este é um **client fino de integração** (uma primitiva de geração de texto), NÃO o
agente. O desenho interno do agente (orquestração, tools, RAG sobre a base) é um
ponto em aberto e não vive aqui.

O provedor é escolhido por `LLM_PROVIDER` (`anthropic` | `openai`) nas settings.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.support.core.settings import settings


@dataclass
class LLMMessage:
    """Mensagem no formato role/content (comum a Claude e GPT)."""

    role: str  # "user" | "assistant"
    content: str


class LLMClient(ABC):
    """Interface comum aos provedores de LLM."""

    @abstractmethod
    async def complete(self, messages: list[LLMMessage], system: str | None = None) -> str:
        """Gera uma resposta de texto a partir das mensagens."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> str: ...


class AnthropicLLMClient(LLMClient):
    """Provedor Claude (Anthropic)."""

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self._model = settings.ANTHROPIC_MODEL

    @property
    def model(self) -> str:
        return self._model

    async def complete(self, messages: list[LLMMessage], system: str | None = None) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system or "",
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )
        return "".join(block.text for block in response.content if block.type == "text")


class OpenAILLMClient(LLMClient):
    """Provedor GPT (OpenAI)."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL

    @property
    def model(self) -> str:
        return self._model

    async def complete(self, messages: list[LLMMessage], system: str | None = None) -> str:
        payload = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend({"role": m.role, "content": m.content} for m in messages)

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=payload,
        )
        return response.choices[0].message.content or ""


def get_llm_client() -> LLMClient:
    """Fábrica: devolve o client conforme `LLM_PROVIDER`."""
    if settings.LLM_PROVIDER == "openai":
        return OpenAILLMClient()
    return AnthropicLLMClient()
