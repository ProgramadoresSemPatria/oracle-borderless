"""Citation — value object de fonte citável. Domínio puro (sem infra)."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Citation:
    """Uma fonte atribuída a uma resposta do oráculo."""

    source_type: Literal["notion", "web"]
    title: str
    url: str
    snippet: str
    page_id: str | None = None

    def is_notion(self) -> bool:
        return self.source_type == "notion"
