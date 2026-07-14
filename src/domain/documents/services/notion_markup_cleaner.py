"""NotionMarkupCleaner — normaliza o markdown do Notion antes do chunking.

Domain Service puro (sem I/O). O `retrieve-page-markdown` do MCP devolve
sintaxe pseudo-HTML própria do Notion (`<callout>`, `<span color>`,
`{toggle}`, `<table>`, `<empty-block/>`, `<br>`, breadcrumbs `<unknown/>`)
que polui embeddings e não agrega significado. Este cleaner remove esses
wrappers **preservando** o markdown de verdade (headings, listas, negrito,
links) — o que o ChunkingService heading-aware usa para segmentar.

É no-op em texto sem markup do Notion.
"""

import re

# Tags self-closing sem valor semântico.
_SELF_CLOSING = re.compile(r"<(empty-block|unknown)\b[^>]*/?>", re.IGNORECASE)
# Wrappers estruturais de tabela/callout — remove a tag, mantém o conteúdo.
_STRUCT_TAGS = re.compile(r"</?(callout|table|tr|td|th|thead|tbody)\b[^>]*>", re.IGNORECASE)
# Span colorido: mantém só o texto interno.
_SPAN = re.compile(r"</?span\b[^>]*>", re.IGNORECASE)
# Sufixo {toggle="..."} em headings/linhas.
_TOGGLE = re.compile(r"\s*\{toggle=\"[^\"]*\"\}")
# Quebra de linha explícita.
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
# 3+ linhas em branco viram uma só linha em branco.
_BLANK_LINES = re.compile(r"\n{3,}")


class NotionMarkupCleaner:
    """Remove sintaxe custom do Notion mantendo o markdown semântico."""

    def clean(self, text: str) -> str:
        if not text:
            return text
        out = _BR.sub("\n", text)
        out = _SELF_CLOSING.sub("", out)
        out = _STRUCT_TAGS.sub("", out)
        out = _SPAN.sub("", out)
        out = _TOGGLE.sub("", out)
        # remove linhas que ficaram vazias após tirar wrappers
        out = "\n".join(line.rstrip() for line in out.split("\n"))
        out = _BLANK_LINES.sub("\n\n", out)
        return out.strip("\n")
