"""Popula o CurrentRequestContext com a request atual."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.support.core.context import CurrentRequestContext


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        CurrentRequestContext.set_request(request)
        try:
            return await call_next(request)
        finally:
            CurrentRequestContext.clear()
