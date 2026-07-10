from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.entities.message import Message
from src.domain.conversations.repositories.conversation_repository import ConversationRepository
from src.domain.conversations.repositories.message_repository import MessageRepository


async def _new_conversation(db_session) -> "Conversation":
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    conv = await ConversationRepository().create(
        Conversation(uuid4(), None, "T", now, now, None)
    )
    await db_session.flush()
    return conv


def _msg(conversation_id, role, content):
    return Message(uuid4(), conversation_id, role, content, datetime.now(timezone.utc))


@pytest.mark.asyncio
async def test_append_and_list_chronological(db_session):
    conv = await _new_conversation(db_session)
    repo = MessageRepository()
    await repo.append(_msg(conv.uuid, "user", "pergunta 1"))
    await repo.append(_msg(conv.uuid, "assistant", "resposta 1"))
    await db_session.flush()

    msgs = await repo.list_by_conversation(conv.uuid)
    assert [m.role for m in msgs] == ["user", "assistant"]
    assert [m.content for m in msgs] == ["pergunta 1", "resposta 1"]


@pytest.mark.asyncio
async def test_load_recent_respects_token_budget(db_session, monkeypatch):
    # Budget minúsculo: cada mensagem de 40 chars ~= 10 tokens (len//4).
    monkeypatch.setattr("src.domain.conversations.repositories.message_repository.settings.MEMORY_RECENCY_TOKEN_BUDGET", 15)
    conv = await _new_conversation(db_session)
    repo = MessageRepository()
    for i in range(5):
        await repo.append(_msg(conv.uuid, "user", "x" * 40))  # ~10 tokens cada
        await db_session.flush()

    recent = await repo.load_recent(conv.uuid)
    # 15 de budget: cabe a última (10) + a próxima excede (20>15) → só 1
    assert len(recent) == 1
    assert recent[0].role == "user"


@pytest.mark.asyncio
async def test_append_bumps_conversation_updated_at(db_session):
    conv = await _new_conversation(db_session)
    before = (await ConversationRepository().get_by_id(conv.uuid)).updated_at
    await MessageRepository().append(_msg(conv.uuid, "user", "nova"))
    await db_session.flush()
    after = (await ConversationRepository().get_by_id(conv.uuid)).updated_at
    assert after >= before
