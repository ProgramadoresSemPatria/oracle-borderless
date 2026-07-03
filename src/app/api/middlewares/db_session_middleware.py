"""Abre a sessão async (e factory sync lazy) por request, comita/rollback ao fim."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.support.core.context import CurrentAsyncSessionContext, CurrentSessionContext
from src.support.core.database import AsyncSessionLocal, SessionLocal


class DBSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        async with AsyncSessionLocal() as async_session:
            CurrentAsyncSessionContext.set(async_session)
            CurrentSessionContext.set_factory(SessionLocal)

            try:
                response = await call_next(request)
                await async_session.commit()
                sync_session = CurrentSessionContext.get() if _sync_touched() else None
                if sync_session is not None:
                    sync_session.commit()
                return response
            except Exception:
                await async_session.rollback()
                raise
            finally:
                sync_session = _peek_sync()
                if sync_session is not None:
                    sync_session.close()
                CurrentSessionContext.clear()
                CurrentAsyncSessionContext.clear()


def _sync_touched() -> bool:
    """A sessão sync só existe se alguém a acessou durante a request."""
    return _peek_sync() is not None


def _peek_sync():
    # Import local para evitar acoplar o módulo ao detalhe interno do contexto.
    from src.support.core.context.current_db_session_context import _current_session

    return _current_session.get()
