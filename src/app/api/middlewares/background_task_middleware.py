"""Disponibiliza um BackgroundTasks acessível de qualquer camada via contexto."""

from starlette.background import BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.support.core.context import BackgroundTaskContext


class BackgroundTaskMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tasks = BackgroundTasks()
        BackgroundTaskContext.set(tasks)
        try:
            response = await call_next(request)
            # Anexa as tasks acumuladas à resposta, se houver.
            if tasks.tasks:
                response.background = tasks
            return response
        finally:
            BackgroundTaskContext.clear()
