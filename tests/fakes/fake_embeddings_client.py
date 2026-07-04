"""Embeddings determinísticos para testes — sem I/O externo."""

import hashlib

from src.support.clients.embeddings.embeddings_client import EmbeddingsClient


class FakeEmbeddingsClient(EmbeddingsClient):
    def __init__(self, dim: int = 1536) -> None:
        self.dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        # repete o digest até preencher dim; normaliza para [0,1)
        raw = (digest * (self.dim // len(digest) + 1))[: self.dim]
        return [b / 255.0 for b in raw]
