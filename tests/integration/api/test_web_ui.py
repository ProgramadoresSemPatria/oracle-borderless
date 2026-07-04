import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_root_serves_chat_page():
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Oracle Borderless" in resp.text
