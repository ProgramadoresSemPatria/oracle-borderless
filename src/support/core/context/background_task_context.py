"""ContextVar de BackgroundTasks da request atual (FastAPI)."""

from contextvars import ContextVar
from typing import Any

_background_tasks: ContextVar[Any | None] = ContextVar("background_tasks", default=None)


class BackgroundTaskContext:
    """Acesso ao objeto BackgroundTasks da request, de qualquer camada."""

    @staticmethod
    def set(tasks: Any) -> None:
        _background_tasks.set(tasks)

    @staticmethod
    def get() -> Any | None:
        return _background_tasks.get()

    @staticmethod
    def clear() -> None:
        _background_tasks.set(None)
