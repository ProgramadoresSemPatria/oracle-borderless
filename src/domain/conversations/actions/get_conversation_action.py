from uuid import UUID

from src.domain.conversations.entities.conversation import Conversation
from src.domain.conversations.entities.message import Message
from src.domain.conversations.repositories.conversation_repository import ConversationRepository
from src.domain.conversations.repositories.message_repository import MessageRepository
from src.domain.conversations.services.conversation_access_policy import ConversationAccessPolicy
from src.support.core.exceptions import NotFoundError


class GetConversationAction:
    def __init__(self) -> None:
        self.conversations = ConversationRepository()
        self.messages = MessageRepository()

    async def execute(
        self, conversation_id: UUID, user_email: str | None
    ) -> tuple[Conversation, list[Message]]:
        conversation = await self.conversations.get_by_id(conversation_id)
        if conversation is None:
            raise NotFoundError(f"conversa {conversation_id} não encontrada")
        ConversationAccessPolicy.assert_can_access(conversation, user_email)
        messages = await self.messages.list_by_conversation(conversation_id)
        return conversation, messages
