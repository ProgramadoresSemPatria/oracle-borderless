"""Client da base de conhecimento — Notion via MCP (Model Context Protocol).

Fronteira com o Notion. **Só expõe conteúdo aprovado**: a curadoria
(`KnowledgeCurationPolicy`) barra linhas de banco (trackers/PII), deixando
passar só páginas-documento. Transporte via `@notionhq/notion-mcp-server`
(ADR-0010); truncagem de páginas grandes é contornada pelo
`PageMarkdownAssembler`.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.documents.services.knowledge_curation_policy import (
    KnowledgeCurationPolicy,
    NotionPageRef,
)
from src.support.clients.notion.mcp_session import ToolCall, notion_mcp_session
from src.support.clients.notion.page_markdown_assembler import PageMarkdownAssembler


@dataclass
class NotionPage:
    """Página do Notion trazida pelo MCP. Primitivos, não Entity de domínio."""

    id: str
    title: str
    content: str
    url: str
    is_approved: bool
    last_edited_time: datetime | None = None


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_title(page: dict[str, Any]) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            parts = prop.get("title", [])
            return "".join(t.get("plain_text", "") for t in parts) or "(sem título)"
    return "(sem título)"


class NotionClient:
    """Fronteira com o Notion via MCP. Só páginas aprovadas."""

    def __init__(self) -> None:
        self._policy = KnowledgeCurationPolicy()

    async def get_page(self, page_id: str) -> NotionPage:
        """Página completa (metadados + markdown, sem truncagem)."""
        async with notion_mcp_session() as call:
            page = await call("API-retrieve-a-page", {"page_id": page_id})
            markdown = await self._assemble(call, page_id)

        title = _extract_title(page)
        parent_type = page.get("parent", {}).get("type", "")
        ref = NotionPageRef(object_type="page", parent_type=parent_type, title=title)
        return NotionPage(
            id=page_id,
            title=title,
            content=markdown,
            url=page.get("url", ""),
            is_approved=self._policy.should_ingest(ref),
            last_edited_time=_parse_ts(page.get("last_edited_time")),
        )

    async def get_page_markdown(self, page_id: str) -> str:
        """Markdown completo da página, contornando a truncagem do MCP."""
        async with notion_mcp_session() as call:
            return await self._assemble(call, page_id)

    async def list_approved_pages(self) -> list[NotionPage]:
        """Lista (metadados) as páginas-documento aprovadas pela curadoria."""
        async with notion_mcp_session() as call:
            raw = await self._search_all(call)

        approved: list[NotionPage] = []
        for item in raw:
            if item.get("object") != "page":
                continue
            title = _extract_title(item)
            ref = NotionPageRef(
                object_type="page",
                parent_type=item.get("parent", {}).get("type", ""),
                title=title,
            )
            if self._policy.should_ingest(ref):
                approved.append(
                    NotionPage(
                        id=item["id"],
                        title=title,
                        content="",
                        url=item.get("url", ""),
                        is_approved=True,
                        last_edited_time=_parse_ts(item.get("last_edited_time")),
                    )
                )
        return approved

    # --- transporte MCP (privado) ---

    async def _assemble(self, call: ToolCall, page_id: str) -> str:
        assembler = PageMarkdownAssembler(
            lambda bid: self._fetch_markdown(call, bid),
            lambda bid: self._list_child_ids(call, bid),
        )
        return await assembler.assemble(page_id)

    @staticmethod
    async def _fetch_markdown(call: ToolCall, block_id: str) -> tuple[str, bool]:
        data = await call("API-retrieve-page-markdown", {"page_id": block_id})
        return data.get("markdown", ""), bool(data.get("truncated"))

    @staticmethod
    async def _list_child_ids(call: ToolCall, block_id: str) -> list[str]:
        ids: list[str] = []
        cursor: str | None = None
        while True:
            args: dict[str, Any] = {"block_id": block_id, "page_size": 100}
            if cursor:
                args["start_cursor"] = cursor
            data = await call("API-get-block-children", args)
            ids.extend(b["id"] for b in data.get("results", []))
            if not data.get("has_more"):
                return ids
            cursor = data.get("next_cursor")

    @staticmethod
    async def _search_all(call: ToolCall) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            args: dict[str, Any] = {"query": "", "page_size": 100}
            if cursor:
                args["start_cursor"] = cursor
            data = await call("API-post-search", args)
            results.extend(data.get("results", []))
            if not data.get("has_more"):
                return results
            cursor = data.get("next_cursor")
