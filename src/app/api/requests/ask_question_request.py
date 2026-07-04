from pydantic import BaseModel, Field


class MessageIn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str


class AskQuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    history: list[MessageIn] = Field(default_factory=list)
