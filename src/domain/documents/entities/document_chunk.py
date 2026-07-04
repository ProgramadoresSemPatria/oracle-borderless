from dataclasses import dataclass
from uuid import UUID


@dataclass
class DocumentChunk:
    """Trecho de um Document, com seu vetor de embedding. Domínio puro."""

    uuid: UUID
    document_id: UUID
    ordinal: int
    content: str
    embedding: list[float] | None = None
