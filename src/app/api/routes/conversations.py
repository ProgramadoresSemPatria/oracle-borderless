"""Rota do oráculo — pública no nível da app (protegida por Cloudflare Access na borda)."""

from fastapi import APIRouter

from src.app.api.controllers.conversation_controller import ConversationController

public_router = APIRouter(prefix="/conversations", tags=["Conversations"])
public_router.post("/ask")(ConversationController.ask)
