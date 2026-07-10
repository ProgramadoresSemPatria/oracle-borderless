from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.domain.conversations.actions.answer_question_action import AnswerQuestionAction
from src.domain.conversations.entities.conversation import Conversation
from src.support.agent.ports import AgentStreamChunk
from src.support.core.exceptions import NotFoundError


class _FakeSearch:
    async def execute(self, question):
        return []


class _FakeEngine:
    def __init__(self):
        self.received_history = None

    async def stream_answer(self, question, history, knowledge):
        self.received_history = history
        yield AgentStreamChunk(type="text", text="ok")


class _FakeConvRepo:
    def __init__(self, existing=None):
        self.existing = existing
        self.created = None

    async def get_by_id(self, cid):
        return self.existing

    async def create(self, conversation):
        self.created = conversation
        return conversation


class _FakeMsgRepo:
    def __init__(self):
        self.appended = []
        self.recent = []

    async def append(self, message):
        self.appended.append(message)
        return message

    async def load_recent(self, cid):
        return self.recent


def _make(engine, search, conv_repo, msg_repo):
    action = AnswerQuestionAction(engine=engine, search=search)
    action.conversations = conv_repo
    action.messages = msg_repo
    return action


@pytest.mark.asyncio
async def test_new_conversation_persists_user_and_sets_title():
    engine, conv_repo, msg_repo = _FakeEngine(), _FakeConvRepo(), _FakeMsgRepo()
    action = _make(engine, _FakeSearch(), conv_repo, msg_repo)

    conversation_id, stream = await action.execute("qual o onboarding?", None, "a@x.com")

    assert conv_repo.created is not None
    assert conv_repo.created.title == "qual o onboarding?"
    assert conv_repo.created.user_email == "a@x.com"
    assert conversation_id == conv_repo.created.uuid
    assert msg_repo.appended[0].role == "user"
    assert msg_repo.appended[0].content == "qual o onboarding?"
    # drena o stream
    chunks = [c async for c in stream]
    assert any(c.type == "text" for c in chunks)


@pytest.mark.asyncio
async def test_missing_conversation_id_raises_not_found():
    action = _make(_FakeEngine(), _FakeSearch(), _FakeConvRepo(existing=None), _FakeMsgRepo())
    with pytest.raises(NotFoundError):
        await action.execute("oi", uuid4(), "a@x.com")


@pytest.mark.asyncio
async def test_recency_loaded_before_appending_current_message():
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    existing = Conversation(uuid4(), "a@x.com", "T", now, now, None)
    engine, msg_repo = _FakeEngine(), _FakeMsgRepo()
    from src.support.agent.ports import AgentMessage
    msg_repo.recent = [AgentMessage(role="user", content="turno anterior")]
    action = _make(engine, _FakeSearch(), _FakeConvRepo(existing=existing), msg_repo)

    _, stream = await action.execute("nova pergunta", existing.uuid, "a@x.com")
    [c async for c in stream]

    # histórico passado ao engine = turnos anteriores, sem a pergunta atual
    assert engine.received_history == [AgentMessage(role="user", content="turno anterior")]
