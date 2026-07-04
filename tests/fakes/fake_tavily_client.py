from src.support.clients.tavily.tavily_client import WebResult


class FakeTavilyClient:
    def __init__(self, results: list[WebResult] | None = None) -> None:
        self._results = results or []

    async def search(self, query: str, max_results: int = 5) -> list[WebResult]:
        return self._results[:max_results]
