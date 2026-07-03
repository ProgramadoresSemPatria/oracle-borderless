"""ContextVar da request HTTP atual (e, quando a auth existir, do usuário)."""

from contextvars import ContextVar
from typing import Any

_current_request: ContextVar[Any | None] = ContextVar("current_request", default=None)
_current_user: ContextVar[Any | None] = ContextVar("current_user", default=None)


class CurrentRequestContext:
    """Acesso à request atual de qualquer lugar da aplicação."""

    @staticmethod
    def set_request(request: Any) -> None:
        _current_request.set(request)

    @staticmethod
    def get_request() -> Any | None:
        return _current_request.get()

    @staticmethod
    def set_user(user: Any) -> None:
        # Auth é ponto em aberto — o slot já existe para quando for definida.
        _current_user.set(user)

    @staticmethod
    def get_user() -> Any | None:
        return _current_user.get()

    @staticmethod
    def clear() -> None:
        _current_request.set(None)
        _current_user.set(None)
