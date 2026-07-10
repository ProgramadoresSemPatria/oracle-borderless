from uuid import UUID

from pydantic import BaseModel, Field


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    conversation_id: UUID | None = None
