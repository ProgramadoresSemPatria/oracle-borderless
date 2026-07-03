"""Traduz exceções de domínio em respostas HTTP. Registrado no main.py."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.support.core.exceptions import (
    DomainConflictError,
    DomainError,
    NotFoundError,
    UnauthorizedDomainError,
    ValidationError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Mapeia cada exceção de domínio para um status HTTP."""

    @app.exception_handler(NotFoundError)
    async def _not_found(request: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DomainConflictError)
    async def _conflict(request: Request, exc: DomainConflictError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def _validation(request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(UnauthorizedDomainError)
    async def _unauthorized(request: Request, exc: UnauthorizedDomainError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(DomainError)
    async def _domain(request: Request, exc: DomainError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})
