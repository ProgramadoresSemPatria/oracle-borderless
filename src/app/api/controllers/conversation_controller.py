import json
import logging
from typing import AsyncIterator

from fastapi import Request
from fastapi.responses import StreamingResponse

from src.app.api.requests.ask_question_request import AskQuestionRequest
from src.domain.conversations.actions.answer_question_action import AnswerQuestionAction
from src.domain.documents.actions.search_knowledge_base_action import SearchKnowledgeBaseAction
from src.support.agent.oracle_engine import get_oracle_engine
from src.support.agent.ports import AgentMessage
from src.support.clients.embeddings.embeddings_client import get_embeddings_client

logger = logging.getLogger(__name__)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class ConversationController:
    @staticmethod
    async def ask(request: Request, data: AskQuestionRequest) -> StreamingResponse:
        history = [AgentMessage(role=m.role, content=m.content) for m in data.history]
        search = SearchKnowledgeBaseAction(embeddings=get_embeddings_client())
        action = AnswerQuestionAction(engine=get_oracle_engine(), search=search)

        # retrieval acontece aqui (sessão viva); stream só faz HTTP depois
        stream = await action.execute(data.question, history)

        async def event_source() -> AsyncIterator[str]:
            try:
                async for chunk in stream:
                    if chunk.type == "text":
                        yield _sse("token", {"text": chunk.text})
                    elif chunk.type == "sources":
                        yield _sse(
                            "sources",
                            {
                                "citations": [
                                    {
                                        "source_type": c.source_type,
                                        "title": c.title,
                                        "url": c.url,
                                        "snippet": c.snippet,
                                    }
                                    for c in chunk.citations
                                ]
                            },
                        )
            except Exception:
                logger.exception("stream falhou durante /conversations/ask")
                yield _sse("error", {"message": "erro ao gerar a resposta"})
            finally:
                yield _sse("done", {})

        return StreamingResponse(event_source(), media_type="text/event-stream")
