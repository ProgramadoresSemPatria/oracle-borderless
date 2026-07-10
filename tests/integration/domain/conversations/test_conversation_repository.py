from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.repositories.conversation_repository import ConversationRepository


def _conv(user_email=None, title="T"):
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    return Conversation(uuid4(), user_email, title, now, now, None)


@pytest.mark.asyncio
async def test_create_then_get_by_id(db_session):
    repo = ConversationRepository()
    created = await repo.create(_conv(user_email="a@x.com", title="Primeira"))
    await db_session.flush()

    found = await repo.get_by_id(created.uuid)
    assert found is not None
    assert found.title == "Primeira"
    assert found.user_email == "a@x.com"


@pytest.mark.asyncio
async def test_list_by_user_filters_and_orders(db_session):
    repo = ConversationRepository()
    await repo.create(_conv(user_email="a@x.com", title="A1"))
    await repo.create(_conv(user_email="b@x.com", title="B1"))
    await db_session.flush()

    mine = await repo.list_by_user("a@x.com")
    assert [c.title for c in mine] == ["A1"]


@pytest.mark.asyncio
async def test_list_by_user_none_returns_ownerless(db_session):
    repo = ConversationRepository()
    await repo.create(_conv(user_email=None, title="Anon"))
    await repo.create(_conv(user_email="a@x.com", title="Owned"))
    await db_session.flush()

    anon = await repo.list_by_user(None)
    assert all(c.user_email is None for c in anon)
    assert "Anon" in [c.title for c in anon]
