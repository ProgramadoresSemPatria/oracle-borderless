from src.domain.documents.entities.document_chunk import DocumentChunk
from src.domain.documents.models.document_chunk import DocumentChunkModel


class DocumentChunkMapper:
    @staticmethod
    def to_entity(model: DocumentChunkModel) -> DocumentChunk:
        return DocumentChunk(
            uuid=model.uuid,
            document_id=model.document_id,
            ordinal=model.ordinal,
            content=model.content,
            embedding=list(model.embedding) if model.embedding is not None else None,
        )

    @staticmethod
    def to_model_attrs(entity: DocumentChunk) -> dict:
        return {
            "uuid": entity.uuid,
            "document_id": entity.document_id,
            "ordinal": entity.ordinal,
            "content": entity.content,
            "embedding": entity.embedding,
        }
