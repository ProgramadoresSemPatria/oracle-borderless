from datetime import datetime, timezone
from uuid import uuid4

from src.domain.documents.entities.document import Document
from src.support.clients.notion.notion_client import NotionPage


class NotionPageMapper:
    @staticmethod
    def to_document(page: NotionPage) -> Document:
        now = datetime.now(timezone.utc)
        return Document(
            uuid=uuid4(),
            notion_page_id=page.id,
            title=page.title,
            content=page.content,
            source_url=page.url,
            status="approved" if page.is_approved else "pending",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
