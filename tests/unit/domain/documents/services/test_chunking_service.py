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


# --- heading-aware ---

def _section(name: str) -> str:
    return f"## {name}\n" + ("palavra " * 12).strip() + "."


def test_splits_at_heading_boundaries_never_mid_content():
    text = "\n".join(_section(n) for n in ("Alpha", "Beta", "Gamma"))
    chunks = ChunkingService(size=250, overlap=20).split(text)
    assert len(chunks) >= 2
    # cada chunk começa num heading e termina em fim de sentença (nunca no meio)
    assert all(c.startswith("## ") for c in chunks)
    assert all(c.endswith(".") for c in chunks)


def test_small_sections_are_packed_together_under_size():
    text = "\n".join(_section(n) for n in ("Alpha", "Beta", "Gamma"))
    chunks = ChunkingService(size=250, overlap=20).split(text)
    assert all(len(c) <= 250 for c in chunks)
    # todas as seções preservadas na saída
    joined = "\n".join(chunks)
    assert "## Alpha" in joined and "## Beta" in joined and "## Gamma" in joined


def test_heading_stays_with_its_body():
    text = _section("Sozinha")
    chunks = ChunkingService(size=500, overlap=20).split(text)
    assert len(chunks) == 1
    assert chunks[0].startswith("## Sozinha\n")


def test_large_section_falls_back_to_paragraph_split():
    para = ("frase de tamanho medio aqui. " * 6).strip()  # ~170 chars
    text = "## Grande\n" + "\n\n".join([para, para, para])
    chunks = ChunkingService(size=250, overlap=20).split(text)
    assert len(chunks) >= 2
    assert all(len(c) <= 250 for c in chunks)
    assert chunks[0].startswith("## Grande")
    # corta em fim de parágrafo/sentença, nunca no meio de palavra
    assert all(c.rstrip().endswith(".") for c in chunks)
