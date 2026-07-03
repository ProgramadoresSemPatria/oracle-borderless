from src.domain.documents.services.chunking_service import ChunkingService


def test_empty_text_yields_no_chunks():
    assert ChunkingService(size=100, overlap=10).split("   ") == []


def test_short_text_is_single_chunk():
    assert ChunkingService(size=100, overlap=10).split("abc") == ["abc"]


def test_long_text_splits_with_overlap():
    text = "x" * 250
    chunks = ChunkingService(size=100, overlap=20).split(text)
    assert len(chunks) == 3
    assert all(len(c) <= 100 for c in chunks)
    # overlap: chunk[1] começa 80 chars após o início do chunk[0]
    assert chunks[1].startswith("x")
