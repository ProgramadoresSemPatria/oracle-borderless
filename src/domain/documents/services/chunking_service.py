"""ChunkingService — divide texto em chunks com overlap. Puro, sem I/O."""

from src.support.core.settings import settings


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
        if len(text) <= self.size:
            return [text]

        step = self.size - self.overlap
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + self.size, len(text))
            chunks.append(text[start:end])
            if end >= len(text):  # reached end of text, stop
                break
            start += step
        return chunks
