import pytest

from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.session_scope import run_in_async_session


@pytest.mark.asyncio
async def test_run_in_async_session_populates_and_clears_context(monkeypatch):
    seen = {}

    class FakeSession:
        async def commit(self): seen["committed"] = True
        async def rollback(self): seen["rolledback"] = True
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False

    monkeypatch.setattr("src.support.core.session_scope.AsyncSessionLocal", lambda: FakeSession())

    async def work():
        assert CurrentAsyncSessionContext.get() is not None  # sessão viva durante fn
        return "ok"

    result = await run_in_async_session(work)

    assert result == "ok"
    assert seen.get("committed") is True
    assert CurrentAsyncSessionContext.get() is None  # limpo ao final
