"""Serve a UI web mínima do oráculo. Pública (protegida por Cloudflare Access na borda)."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

public_router = APIRouter(tags=["Web"])
_INDEX = Path(__file__).resolve().parents[2] / "web" / "index.html"


@public_router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(_INDEX.read_text(encoding="utf-8"))
