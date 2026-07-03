"""Model de tracking de execução de jobs — base da idempotência do scheduler."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.support.core.mixins import HasUUID
from src.support.core.models.base_model import BaseModel


class JobExecution(BaseModel, HasUUID):
    """Registro de uma execução de job — evita re-execução concorrente/duplicada."""

    __tablename__ = "job_executions"

    job_name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
