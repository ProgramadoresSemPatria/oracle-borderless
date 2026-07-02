"""Rota de health check — pública (sem auth)."""

from fastapi import APIRouter

public_router = APIRouter(tags=["Health"])


@public_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
