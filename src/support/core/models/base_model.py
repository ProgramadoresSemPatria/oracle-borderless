"""BaseModel — DeclarativeBase compartilhado por todos os Models SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class BaseModel(DeclarativeBase):
    """Base declarativa única do projeto. `metadata` é o target do Alembic."""
