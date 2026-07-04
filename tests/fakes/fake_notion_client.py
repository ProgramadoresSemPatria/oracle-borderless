from src.support.clients.notion.notion_client import NotionPage


class FakeNotionClient:
    def __init__(self, pages: dict[str, NotionPage] | None = None) -> None:
        self._pages = pages or {}

    async def get_page(self, page_id: str) -> NotionPage:
        if page_id not in self._pages:
            raise KeyError(f"página {page_id} não encontrada no fake")
        return self._pages[page_id]

    async def list_approved_pages(self) -> list[NotionPage]:
        return [p for p in self._pages.values() if p.is_approved]
