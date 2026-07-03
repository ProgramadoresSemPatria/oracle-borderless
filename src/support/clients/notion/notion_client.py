"""Client da base de conhecimento — Notion via MCP (Model Context Protocol).

Encapsula a integração e expõe ao domínio apenas o necessário. **Só consome
documentos aprovados/liberados** pelas restrições de acesso do MCP do Notion —
nada confidencial entra na base.

O desenho fino da ingestão (full sync vs. incremental, embeddings, cache) é um
ponto em aberto. Este client define a fronteira; a implementação concreta do
transporte MCP entra quando a estratégia for decidida.
"""

from dataclasses import dataclass

from src.support.core.settings import settings


@dataclass
class NotionPage:
    """Página do Notion trazida pelo MCP. Primitivos, não Entity de domínio."""

    id: str
    title: str
    content: str
    url: str
    is_approved: bool


class NotionClient:
    """Fronteira com o Notion via MCP. Só páginas aprovadas."""

    def __init__(self) -> None:
        self._mcp_url = settings.NOTION_MCP_URL
        self._mcp_token = settings.NOTION_MCP_TOKEN

    async def get_page(self, page_id: str) -> NotionPage:
        """Busca uma página aprovada pelo id. (Transporte MCP a implementar.)"""
        raise NotImplementedError(
            "Integração MCP do Notion ainda não implementada — ponto em aberto (ver CLAUDE.md)."
        )

    async def list_approved_pages(self) -> list[NotionPage]:
        """Lista as páginas liberadas/aprovadas. (Transporte MCP a implementar.)"""
        raise NotImplementedError(
            "Integração MCP do Notion ainda não implementada — ponto em aberto (ver CLAUDE.md)."
        )
