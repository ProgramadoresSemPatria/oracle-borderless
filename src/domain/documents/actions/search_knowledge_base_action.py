from src.domain.documents.repositories.document_chunk_repository import DocumentChunkRepository
from src.support.agent.ports import KnowledgeSnippet
from src.support.clients.embeddings.embeddings_client import EmbeddingsClient


class SearchKnowledgeBaseAction:
    """RAG clássico: embed da query → busca top-k na base → trechos com citação."""

    def __init__(self, embeddings: EmbeddingsClient, chunk_repo=None) -> None:
        self.embeddings = embeddings
        self.chunk_repo = chunk_repo or DocumentChunkRepository()

    async def execute(self, query: str, top_k: int | None = None) -> list[KnowledgeSnippet]:
        vector = await self.embeddings.embed_query(query)
        return await self.chunk_repo.search_similar(vector, top_k=top_k)
