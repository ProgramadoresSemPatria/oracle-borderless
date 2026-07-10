"""Executa uma coroutine num escopo de sessão async própria — para trabalho fora
do ciclo de request (ex.: persistir a resposta do oráculo depois que o streaming
SSE termina, quando a sessão do request já foi comitada e limpa).

Mesma mecânica de Job.execute()/Commands/Seeds: abre AsyncSessionLocal, popula o
contexto, comita, limpa. Os repositórios continuam lendo a sessão via
CurrentAsyncSessionContext.get() — sem criar sessão eles próprios (regra 3)."""

from typing import Awaitable, Callable, TypeVar

from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.database import AsyncSessionLocal

T = TypeVar("T")


async def run_in_async_session(fn: Callable[[], Awaitable[T]]) -> T:
    async with AsyncSessionLocal() as session:
        CurrentAsyncSessionContext.set(session)
        try:
            result = await fn()
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
        finally:
            CurrentAsyncSessionContext.clear()
