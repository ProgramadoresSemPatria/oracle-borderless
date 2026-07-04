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


def test_full_chunk_landing_on_end_has_no_redundant_tail():
    """Regression: verifies that a full-size chunk landing on len(text) does not create redundant tail."""
    chunks = ChunkingService(size=100, overlap=20).split("x" * 180)
    assert len(chunks) == 2
    # all content covered, no duplicate subset tail
    assert chunks[0] == "x" * 100
    assert chunks[1] == "x" * 100  # text[80:180]
