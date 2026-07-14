"""KnowledgeCurationPolicy — decide o que do Notion pode entrar na base.

Domain Service puro (sem I/O, sem infra). Aplica a regra inegociável nº 4:
o oráculo só responde a partir de conhecimento aprovado — nada de dados
pessoais nem de trackers operacionais.

A fronteira de curadoria é estrutural: no workspace do Notion, todo dado
pessoal e todo tracker operacional vive como **linha de banco de dados**
(`parent = data_source/database`), enquanto o conhecimento real (SOPs,
processos, guias, editoriais) são **páginas-documento** (`parent =
page/workspace`). Logo, a proteção primária é: só páginas-documento entram;
linhas de banco nunca. Uma denylist conservadora de títulos serve como
defesa em profundidade contra páginas-documento que apenas embrulham um
tracker.

Roda ANTES de buscar o conteúdo: recebe metadados leves (que o `search` do
MCP já devolve) e evita até o fetch de material indevido.
"""

import re
from dataclasses import dataclass

# Tipos de parent do Notion que representam páginas-documento (conteúdo real).
_DOCUMENT_PARENTS = frozenset({"page_id", "workspace"})

# Tipos de parent que representam linha de banco — nunca ingerir.
_DATABASE_PARENTS = frozenset({"data_source_id", "database_id"})

# Defesa em profundidade: páginas-documento cujo título indica tracker/PII
# ou ruído (embeds de banco, placeholders). Conservador de propósito.
_TITLE_DENYLIST = (
    re.compile(r"\bbacklog\b", re.IGNORECASE),
    re.compile(r"\bonboarding control\b", re.IGNORECASE),
    re.compile(r"\bsprints?\b", re.IGNORECASE),
    re.compile(r"\bbanco de (fotos|v[íi]deos)\b", re.IGNORECASE),
    re.compile(r"^\s*date:\s", re.IGNORECASE),
)


@dataclass(frozen=True)
class NotionPageRef:
    """Metadados leves de um item do Notion (nível de resultado do `search`)."""

    object_type: str  # "page" | "data_source" | "database"
    parent_type: str  # "page_id" | "workspace" | "data_source_id" | ...
    title: str


class KnowledgeCurationPolicy:
    """Decide se um item do Notion é conhecimento aprovado ingerível."""

    def should_ingest(self, ref: NotionPageRef) -> bool:
        return self.reject_reason(ref) is None

    def reject_reason(self, ref: NotionPageRef) -> str | None:
        """Retorna o motivo da rejeição, ou ``None`` se o item é ingerível."""
        if ref.object_type != "page":
            return "não é página (data_source/database não são documentos)"
        if ref.parent_type in _DATABASE_PARENTS:
            return "linha de banco (tracker/PII operacional) — parent é data source"
        if ref.parent_type not in _DOCUMENT_PARENTS:
            return f"parent não-documental ({ref.parent_type!r})"
        title = (ref.title or "").strip()
        if not title:
            return "página sem título"
        for pattern in _TITLE_DENYLIST:
            if pattern.search(title):
                return f"título casa denylist de tracker/PII ({pattern.pattern!r})"
        return None
