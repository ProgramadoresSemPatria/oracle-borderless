import pytest

from src.domain.conversations.actions.answer_question_action import AnswerQuestionAction
from src.domain.shared.value_objects.citation import Citation
from src.support.agent.ports import KnowledgeSnippet
from tests.fakes.fake_oracle_engine import FakeOracleEngine


class _FakeSearch:
    def __init__(self, snippets):
        self.snippets = snippets
        self.called_with = None

    async def execute(self, query, top_k=None):
        self.called_with = query
        return self.snippets


@pytest.mark.asyncio
async def test_answer_retrieves_then_streams():
    snippets = [KnowledgeSnippet("ctx", Citation("notion", "Onboarding", "u", "s", "pid"))]
    search = _FakeSearch(snippets)
    action = AnswerQuestionAction(engine=FakeOracleEngine(answer="resposta final"), search=search)

    chunks = [c async for c in await action.execute("pergunta?", [])]

    assert search.called_with == "pergunta?"
    assert any(c.type == "text" for c in chunks)
    sources = [c for c in chunks if c.type == "sources"][0]
    assert any(cit.title == "Onboarding" for cit in sources.citations)
