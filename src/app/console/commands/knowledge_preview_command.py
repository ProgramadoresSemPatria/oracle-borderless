from src.domain.documents.services.chunking_service import ChunkingService
from src.domain.documents.services.notion_markup_cleaner import NotionMarkupCleaner
from src.support.clients.notion.notion_client import NotionClient
from src.support.core.console.command import Command


class KnowledgePreviewCommand(Command):
    signature = "knowledge:preview {page_id:str}"
    description = (
        "Busca uma página do Notion (MCP), limpa e chunka — sem persistir. "
        "Diagnóstico do pipeline de ingestão."
    )

    async def handle(self) -> None:
        page_id = self.input["page_id"]
        page = await NotionClient().get_page(page_id)
        cleaned = NotionMarkupCleaner().clean(page.content)
        chunks = ChunkingService().split(cleaned)

        print(f"Título:            {page.title}")
        print(f"URL:               {page.url}")
        print(f"Aprovado (curadoria): {'sim' if page.is_approved else 'NÃO — seria bloqueado'}")
        print(
            f"Conteúdo:          {len(page.content)} chars crus "
            f"-> {len(cleaned)} limpos -> {len(chunks)} chunks"
        )
        if not page.is_approved:
            print("\n⚠️  Curadoria bloquearia esta página (não é documento aprovado).")
        for i, chunk in enumerate(chunks):
            preview = chunk[:70].replace("\n", " ")
            print(f"  [{i:>2}] {len(chunk):>4}c | {preview}…")
