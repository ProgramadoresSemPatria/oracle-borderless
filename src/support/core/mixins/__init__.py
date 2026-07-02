"""Mixins de persistência reutilizáveis pelos Models."""

from src.support.core.mixins.apply_relations import ApplyRelations
from src.support.core.mixins.has_timestamps import HasTimestamps
from src.support.core.mixins.has_uuid import HasUUID

__all__ = ["ApplyRelations", "HasTimestamps", "HasUUID"]
