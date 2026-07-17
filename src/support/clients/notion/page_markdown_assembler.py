"""PageMarkdownAssembler — monta o markdown completo de uma página do Notion.

O tool `retrieve-page-markdown` do MCP **trunca** páginas grandes
(`truncated: true`) — visto em SOPs longos com muitos toggles. Não há cursor
para pedir o restante, mas o mesmo tool aceita **block id** e devolve a
subárvore daquele bloco. Então, quando a página vem truncada, este assembler
desce nos blocos-filhos de topo, busca o markdown de cada um (recursivamente,
se um filho também truncar) e concatena na ordem.

Puro em relação ao transporte: recebe as primitivas de fetch por injeção,
então é testável sem MCP e reusável quando o `NotionClient` implementar o
transporte real.
"""

from collections.abc import Awaitable, Callable

# Busca o markdown de uma página/bloco: retorna (markdown, truncated).
FetchMarkdown = Callable[[str], Awaitable[tuple[str, bool]]]
# Lista os ids dos blocos-filhos diretos (já paginado pelo transporte).
ListChildIds = Callable[[str], Awaitable[list[str]]]


class PageMarkdownAssembler:
    def __init__(
        self,
        fetch_markdown: FetchMarkdown,
        list_child_ids: ListChildIds,
        max_depth: int = 5,
    ) -> None:
        self._fetch_markdown = fetch_markdown
        self._list_child_ids = list_child_ids
        self._max_depth = max_depth

    async def assemble(self, page_id: str) -> str:
        markdown, truncated = await self._fetch_markdown(page_id)
        if not truncated:
            return markdown
        return await self._assemble_children(page_id, depth=1)

    async def _assemble_children(self, block_id: str, depth: int) -> str:
        child_ids = await self._list_child_ids(block_id)
        parts: list[str] = []
        for child_id in child_ids:
            markdown, truncated = await self._fetch_markdown(child_id)
            if truncated and depth < self._max_depth:
                markdown = await self._assemble_children(child_id, depth + 1)
            if markdown.strip():
                parts.append(markdown)
        return "\n\n".join(parts)
