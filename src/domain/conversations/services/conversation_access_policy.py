"""Regra de acesso a conversa — best-effort enquanto a auth não está fechada.
Domain Service (regra sem dono natural, regra 6)."""

from src.domain.conversations.entities.conversation import Conversation
from src.support.core.exceptions import UnauthorizedDomainError


class ConversationAccessPolicy:
    @staticmethod
    def assert_can_access(conversation: Conversation, user_email: str | None) -> None:
        owner = conversation.user_email
        if owner and user_email and owner != user_email:
            raise UnauthorizedDomainError("conversa pertence a outro usuário")
