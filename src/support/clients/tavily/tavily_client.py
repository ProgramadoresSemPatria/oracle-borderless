"""Tavily web-search client — resultados com URL para citação (ver spec MVP)."""

from dataclasses import dataclass

from src.support.core.settings import settings


@dataclass
class WebResult:
    title: str
    url: str
    content: str


class TavilyClient:
    def __init__(self) -> None:
        self._api_key = settings.TAVILY_API_KEY

    async def search(self, query: str, max_results: int = 5) -> list[WebResult]:
        if not self._api_key:
            return []
        from tavily import AsyncTavilyClient

        client = AsyncTavilyClient(api_key=self._api_key)
        response = await client.search(query=query, max_results=max_results)
        return [
            WebResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
            )
            for item in response.get("results", [])
        ]
