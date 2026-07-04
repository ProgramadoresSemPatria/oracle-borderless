from uuid import uuid4

from src.domain.documents.entities.document import Document
from src.domain.documents.entities.document_chunk import DocumentChunk
from src.domain.documents.repositories.document_chunk_repository import DocumentChunkRepository
from src.domain.documents.repositories.document_repository import DocumentRepository
from src.domain.documents.services.chunking_service import ChunkingService
from src.support.clients.embeddings.embeddings_client import EmbeddingsClient
from src.support.core.exceptions import DomainError


class IngestDocumentAction:
    """Ingere um Document aprovado na base: chunking → embeddings → persistência.

    Idempotente: re-ingerir a mesma notion_page_id substitui documento e chunks.
    Source-agnostic: o Document já vem montado (Notion MCP ou seed).
    """

    def __init__(self, embeddings: EmbeddingsClient) -> None:
        self.embeddings = embeddings
        self.chunking = ChunkingService()
        self.documents = DocumentRepository()
        self.chunks = DocumentChunkRepository()

    async def execute(self, document: Document) -> Document:
        if not document.is_approved():
            raise DomainError("Documento não aprovado não pode ser ingerido na base.")

        persisted = await self.documents.upsert(document)

        texts = self.chunking.split(document.content)
        vectors = await self.embeddings.embed(texts)
        entities = [
            DocumentChunk(
                uuid=uuid4(),
                document_id=persisted.uuid,
                ordinal=i,
                content=text,
                embedding=vectors[i],
            )
            for i, text in enumerate(texts)
        ]
        await self.chunks.replace_for_document(persisted.uuid, entities)
        return persisted
