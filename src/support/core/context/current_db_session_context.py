"""ContextVar da sessão SQLAlchemy síncrona (lazy) da request atual.

A sessão síncrona só é criada quando alguém chama `.get()` — usada em casos
específicos (jobstore do APScheduler, scripts síncronos raros).
"""

from contextvars import ContextVar
from typing import Callable

from sqlalchemy.orm import Session

_session_factory: ContextVar[Callable[[], Session] | None] = ContextVar(
    "sync_session_factory", default=None
)
_current_session: ContextVar[Session | None] = ContextVar("current_sync_session", default=None)


class CurrentSessionContext:
    """Sessão síncrona lazy: cria na primeira chamada a `.get()`."""

    @staticmethod
    def set_factory(factory: Callable[[], Session]) -> None:
        _session_factory.set(factory)

    @staticmethod
    def get() -> Session | None:
        existing = _current_session.get()
        if existing is not None:
            return existing

        factory = _session_factory.get()
        if factory is None:
            return None

        session = factory()
        _current_session.set(session)
        return session

    @staticmethod
    def clear() -> None:
        _current_session.set(None)
        _session_factory.set(None)
