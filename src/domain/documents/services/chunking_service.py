"""ChunkingService — segmenta texto para embeddings, consciente da estrutura.

Puro, sem I/O. Estratégia (ver ADR-0008):

1. Quebra o texto em **seções** por heading markdown (`#`..`######`); o
   preâmbulo antes do primeiro heading é uma seção.
2. **Empacota** seções consecutivas num chunk até `size` — assim headings
   ficam com seu corpo e os cortes caem em fronteira de seção, não no meio
   de palavra.
3. Seção maior que `size` cai para split por **parágrafo**; parágrafo ainda
   maior que `size` cai para janela de caractere com `overlap` (último
   recurso, também usado para texto sem nenhum heading).

Espera texto já limpo pelo NotionMarkupCleaner.
"""

import re

from src.support.core.settings import settings

_HEADING_SPLIT = re.compile(r"(?m)^(?=#{1,6}\s)")
_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")


class ChunkingService:
    def __init__(self, size: int | None = None, overlap: int | None = None) -> None:
        self.size = size if size is not None else settings.RAG_CHUNK_SIZE
        self.overlap = overlap if overlap is not None else settings.RAG_CHUNK_OVERLAP
        if self.overlap >= self.size:
            raise ValueError("overlap deve ser menor que size")

    def split(self, text: str) -> list[str]:
        text = (text or "").strip()
        if not text:
            return []

        sections = [s.strip() for s in _HEADING_SPLIT.split(text) if s.strip()]
        chunks: list[str] = []
        buffer = ""
        for section in sections:
            if len(section) > self.size:
                if buffer:
                    chunks.append(buffer)
                    buffer = ""
                chunks.extend(self._split_oversized(section))
            elif not buffer:
                buffer = section
            elif len(buffer) + 2 + len(section) <= self.size:
                buffer = f"{buffer}\n\n{section}"
            else:
                chunks.append(buffer)
                buffer = section
        if buffer:
            chunks.append(buffer)
        return chunks

    def _split_oversized(self, section: str) -> list[str]:
        """Seção maior que size: empacota por parágrafo; parágrafo grande
        demais vai para janela de caractere."""
        chunks: list[str] = []
        buffer = ""
        for paragraph in (p.strip() for p in _PARAGRAPH_SPLIT.split(section) if p.strip()):
            if len(paragraph) > self.size:
                if buffer:
                    chunks.append(buffer)
                    buffer = ""
                chunks.extend(self._char_window(paragraph))
            elif not buffer:
                buffer = paragraph
            elif len(buffer) + 2 + len(paragraph) <= self.size:
                buffer = f"{buffer}\n\n{paragraph}"
            else:
                chunks.append(buffer)
                buffer = paragraph
        if buffer:
            chunks.append(buffer)
        return chunks

    def _char_window(self, text: str) -> list[str]:
        """Último recurso: janela fixa com overlap (texto atômico sem
        fronteira natural, ou texto sem heading algum)."""
        step = self.size - self.overlap
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.size, len(text))
            chunks.append(text[start:end])
            if end >= len(text):
                break
            start += step
        return chunks
