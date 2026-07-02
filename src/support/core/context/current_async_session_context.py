"""ContextVar da sessão SQLAlchemy assíncrona da request atual."""

from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession

_current_async_session: ContextVar[AsyncSession | None] = ContextVar(
    "current_async_session", default=None
)


class CurrentAsyncSessionContext:
    """Acesso à sessão async populada pelo DBSessionMiddleware.

    Repositórios acessam via `.get()` — nunca criam sessão manualmente.
    """

    @staticmethod
    def set(session: AsyncSession) -> None:
        _current_async_session.set(session)

    @staticmethod
    def get() -> AsyncSession | None:
        return _current_async_session.get()

    @staticmethod
    def clear() -> None:
        _current_async_session.set(None)
