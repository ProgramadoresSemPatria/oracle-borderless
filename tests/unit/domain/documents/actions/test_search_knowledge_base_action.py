import pytest

from src.domain.documents.actions.search_knowledge_base_action import SearchKnowledgeBaseAction
from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import KnowledgeSnippet
from tests.fakes.fake_embeddings_client import FakeEmbeddingsClient


class _FakeChunkRepo:
    def __init__(self):
        self.called_with = None

    async def search_similar(self, embedding, top_k=None):
        self.called_with = (embedding, top_k)
        return [KnowledgeSnippet("ctx", Citation("notion", "D", "u", "s", "p"))]


@pytest.mark.asyncio
async def test_search_embeds_query_and_returns_snippets():
    repo = _FakeChunkRepo()
    action = SearchKnowledgeBaseAction(embeddings=FakeEmbeddingsClient(), chunk_repo=repo)
    hits = await action.execute("como funciona o onboarding?", top_k=3)
    assert len(hits) == 1 and hits[0].content == "ctx"
    assert repo.called_with[1] == 3
    assert len(repo.called_with[0]) == 1536  # vetor da query
