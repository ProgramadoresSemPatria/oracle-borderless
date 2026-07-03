"""Mixin para eager load dinâmico de relacionamentos por dot-notation."""

from typing import Any

from sqlalchemy.orm import selectinload


class ApplyRelations:
    """Permite montar opções de eager load a partir de nomes em dot-notation.

    Uso:
        query = query.options(*DocumentModel.build_load_options(["messages", "source.owner"]))
    """

    @classmethod
    def build_load_options(cls, relations: list[str] | None) -> list[Any]:
        """Constrói `selectinload` encadeado para cada caminho de relacionamento."""
        if not relations:
            return []

        options: list[Any] = []
        for path in relations:
            parts = path.split(".")
            current_model: Any = cls
            loader = None
            for part in parts:
                attr = getattr(current_model, part, None)
                if attr is None:
                    break
                loader = selectinload(attr) if loader is None else loader.selectinload(attr)
                related = getattr(attr.property, "mapper", None)
                current_model = related.class_ if related is not None else current_model
            if loader is not None:
                options.append(loader)
        return options
