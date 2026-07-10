from datetime import datetime, timezone
from uuid import uuid4

from src.domain.conversations.entities.message import Message
from src.domain.conversations.mappers import MessageMapper
from src.domain.shared.value_objects.citation import Citation


def test_message_to_model_attrs_serializes_sources():
    cid, mid = uuid4(), uuid4()
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    msg = Message(
        uuid=mid, conversation_id=cid, role="assistant", content="oi",
        created_at=now,
        sources=[Citation("notion", "Doc", "https://n", "trecho", "pid-1")],
    )
    attrs = MessageMapper.to_model_attrs(msg)
    assert attrs["role"] == "assistant"
    assert attrs["sources"] == [
        {"source_type": "notion", "title": "Doc", "url": "https://n", "snippet": "trecho", "page_id": "pid-1"}
    ]
    assert "created_at" not in attrs  # timestamp é server default


def test_message_to_model_attrs_none_sources():
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    msg = Message(uuid=uuid4(), conversation_id=uuid4(), role="user", content="q", created_at=now)
    assert MessageMapper.to_model_attrs(msg)["sources"] is None


def test_message_empty_sources_roundtrip_preserves_empty_list():
    now = datetime(2026, 7, 10, tzinfo=timezone.utc)
    msg = Message(
        uuid=uuid4(), conversation_id=uuid4(), role="assistant", content="oi",
        created_at=now, sources=[],
    )
    # empty list must NOT collapse to None
    assert MessageMapper.to_model_attrs(msg)["sources"] == []

    class FakeModel:
        uuid = uuid4(); conversation_id = uuid4(); role = "assistant"; content = "oi"
        created_at = now
        sources = []

    entity = MessageMapper.to_entity(FakeModel())
    assert entity.sources == []


def test_message_to_entity_deserializes_sources():
    class FakeModel:
        uuid = uuid4(); conversation_id = uuid4(); role = "assistant"; content = "oi"
        created_at = datetime(2026, 7, 10, tzinfo=timezone.utc)
        sources = [{"source_type": "web", "title": "T", "url": "https://x", "snippet": "s", "page_id": None}]

    entity = MessageMapper.to_entity(FakeModel())
    assert entity.sources[0] == Citation("web", "T", "https://x", "s", None)
