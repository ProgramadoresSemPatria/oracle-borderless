"""Mixin de PK UUID v7."""

from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7


class HasUUID:
    """Adiciona PK `uuid` gerada com UUID v7 (`uuid6.uuid7`)."""

    uuid: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
