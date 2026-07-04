import pytest

from src.support.clients.embeddings.embeddings_client import (
    OpenAIEmbeddingsClient,
    get_embeddings_client,
)


def test_factory_returns_openai_client():
    client = get_embeddings_client()
    assert isinstance(client, OpenAIEmbeddingsClient)


@pytest.mark.asyncio
async def test_fake_embeddings_are_deterministic_and_sized():
    from tests.fakes.fake_embeddings_client import FakeEmbeddingsClient

    fake = FakeEmbeddingsClient(dim=8)
    a = await fake.embed_query("hello")
    b = await fake.embed_query("hello")
    assert a == b and len(a) == 8
