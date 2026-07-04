"""Client de embeddings — OpenAI text-embedding-3-small (ver ADR-0008).

Primitiva de vetorização; desacoplada do provedor de chat.
"""

from abc import ABC, abstractmethod

from src.support.core.settings import settings


class EmbeddingsClient(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]


class OpenAIEmbeddingsClient(EmbeddingsClient):
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.EMBEDDING_MODEL

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]


def get_embeddings_client() -> EmbeddingsClient:
    # Só OpenAI por ora (ver settings.EMBEDDING_PROVIDER).
    return OpenAIEmbeddingsClient()
