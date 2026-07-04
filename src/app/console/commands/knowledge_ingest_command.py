from src.domain.documents.actions.ingest_document_action import IngestDocumentAction
from src.domain.documents.mappers.notion_page_mapper import NotionPageMapper
from src.support.clients.embeddings.embeddings_client import get_embeddings_client
from src.support.clients.notion.notion_client import NotionClient
from src.support.core.console.command import Command
from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.database import AsyncSessionLocal


class KnowledgeIngestCommand(Command):
    signature = "knowledge:ingest {page_id:str}"
    description = "Ingere uma página aprovada do Notion (MCP) na base de conhecimento."

    async def handle(self) -> None:
        page_id = self.input["page_id"]
        async with AsyncSessionLocal() as session:
            CurrentAsyncSessionContext.set(session)
            try:
                page = await NotionClient().get_page(page_id)
                document = NotionPageMapper.to_document(page)
                action = IngestDocumentAction(embeddings=get_embeddings_client())
                result = await action.execute(document)
                await session.commit()
                print(f"Ingerido: {result.title} ({result.notion_page_id})")
            except Exception:
                await session.rollback()
                raise
            finally:
                CurrentAsyncSessionContext.clear()
