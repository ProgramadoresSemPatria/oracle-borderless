from uuid import UUID

from sqlalchemy import func, select, update

from src.domain.conversations.entities.message import Message
from src.domain.conversations.mappers import MessageMapper
from src.domain.conversations.models.conversation import ConversationModel
from src.domain.conversations.models.message import MessageModel
from src.support.agent.ports import AgentMessage
from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.settings import settings


def _estimate_tokens(text: str) -> int:
    """Heurística barata (regra 10: sem dependência nova). ~4 chars por token."""
    return max(1, len(text) // 4)


class MessageRepository:
    def __init__(self) -> None:
        self.session = CurrentAsyncSessionContext.get()

    async def append(self, message: Message) -> Message:
        model = MessageModel(**MessageMapper.to_model_attrs(message))
        self.session.add(model)
        # Bump de recência da conversa (para ordenar a sidebar por atividade).
        await self.session.execute(
            update(ConversationModel)
            .where(ConversationModel.uuid == message.conversation_id)
            .values(updated_at=func.now())
        )
        await self.session.flush()
        await self.session.refresh(model)
        return MessageMapper.to_entity(model)

    async def load_recent(self, conversation_id: UUID) -> list[AgentMessage]:
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            # Tiebreak por uuid: created_at é server-side func.now(), que no Postgres é o
            # timestamp de início da transação — turnos gravados na mesma transação teriam
            # created_at idêntico. uuid7 (HasUUID) é gerado client-side e é monotônico
            # crescente por inserção, garantindo ordem determinística.
            .order_by(MessageModel.created_at.desc(), MessageModel.uuid.desc())
            .limit(settings.MEMORY_RECENCY_MAX_MESSAGES)
        )
        rows = (await self.session.execute(stmt)).scalars().all()  # mais novo → mais antigo

        budget = settings.MEMORY_RECENCY_TOKEN_BUDGET
        picked: list[MessageModel] = []
        used = 0
        for m in rows:
            cost = _estimate_tokens(m.content)
            if picked and used + cost > budget:
                break
            picked.append(m)
            used += cost

        picked.reverse()  # ordem cronológica para o prompt
        return [AgentMessage(role=m.role, content=m.content) for m in picked]

    async def list_by_conversation(self, conversation_id: UUID) -> list[Message]:
        stmt = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            # Tiebreak por uuid: created_at (func.now()) fica congelado no início da transação,
            # então turnos da mesma transação empatam; uuid7 é client-side monotônico e
            # desempata na ordem de inserção — cronológico determinístico.
            .order_by(MessageModel.created_at.asc(), MessageModel.uuid.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [MessageMapper.to_entity(m) for m in rows]
