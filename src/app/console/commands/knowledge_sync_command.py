from src.domain.documents.actions.ingest_document_action import IngestDocumentAction
from src.domain.documents.actions.sync_knowledge_base_action import SyncKnowledgeBaseAction
from src.support.clients.embeddings.embeddings_client import get_embeddings_client
from src.support.clients.notion.notion_client import NotionClient
from src.support.core.console.command import Command
from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.database import AsyncSessionLocal


class KnowledgeSyncCommand(Command):
    signature = "knowledge:sync {--force:bool} {--limit:int=}"
    description = (
        "Sincroniza as páginas aprovadas do Notion na base (pgvector): "
        "ingere novas/editadas e remove as que saíram do escopo. Idempotente. "
        "--force reingere tudo; --limit N faz bootstrap parcial (sem remoção)."
    )

    async def handle(self) -> None:
        force = bool(self.input.get("force"))
        limit = self.input.get("limit")
        async with AsyncSessionLocal() as session:
            CurrentAsyncSessionContext.set(session)
            try:
                action = SyncKnowledgeBaseAction(
                    notion=NotionClient(),
                    ingest=IngestDocumentAction(embeddings=get_embeddings_client()),
                )
                report = await action.execute(force=force, limit=limit)
                await session.commit()
                print(f"Sync concluído: {report}")
            except Exception:
                await session.rollback()
                raise
            finally:
                CurrentAsyncSessionContext.clear()
