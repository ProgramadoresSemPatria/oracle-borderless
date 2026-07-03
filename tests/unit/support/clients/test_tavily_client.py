import pytest

from src.support.clients.tavily.tavily_client import TavilyClient, WebResult


@pytest.mark.asyncio
async def test_search_returns_empty_when_no_api_key(monkeypatch):
    monkeypatch.setattr("src.support.clients.tavily.tavily_client.settings.TAVILY_API_KEY", None)
    assert await TavilyClient().search("qualquer") == []


@pytest.mark.asyncio
async def test_fake_tavily_returns_canned_results():
    from tests.fakes.fake_tavily_client import FakeTavilyClient

    fake = FakeTavilyClient([WebResult(title="T", url="https://x", content="c")])
    results = await fake.search("q")
    assert results[0].url == "https://x"
