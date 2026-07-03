"""Model de tracking de seeds executadas — garante idempotência das seeds."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.support.core.mixins import HasUUID
from src.support.core.models.base_model import BaseModel


class SeedExecution(BaseModel, HasUUID):
    """Registra cada seed já rodada. Já rodou? Pula na próxima vez."""

    __tablename__ = "seeds_executions"

    seed_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
