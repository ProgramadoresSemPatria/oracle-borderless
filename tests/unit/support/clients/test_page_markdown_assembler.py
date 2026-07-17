import pytest

from src.support.clients.notion.page_markdown_assembler import PageMarkdownAssembler


class FakeNotion:
    """Árvore fake: id -> (markdown, truncated, [child_ids])."""

    def __init__(self, tree: dict[str, tuple[str, bool, list[str]]]):
        self.tree = tree
        self.markdown_calls: list[str] = []
        self.children_calls: list[str] = []

    async def fetch_markdown(self, block_id: str) -> tuple[str, bool]:
        self.markdown_calls.append(block_id)
        md, truncated, _ = self.tree[block_id]
        return md, truncated

    async def list_child_ids(self, block_id: str) -> list[str]:
        self.children_calls.append(block_id)
        return self.tree[block_id][2]


def _assembler(fake: FakeNotion, **kw) -> PageMarkdownAssembler:
    return PageMarkdownAssembler(fake.fetch_markdown, fake.list_child_ids, **kw)


@pytest.mark.asyncio
async def test_returns_markdown_directly_when_not_truncated():
    fake = FakeNotion({"page": ("# Título\nconteúdo completo.", False, [])})
    out = await _assembler(fake).assemble("page")
    assert out == "# Título\nconteúdo completo."
    assert fake.children_calls == []  # não desceu nos filhos


@pytest.mark.asyncio
async def test_assembles_children_in_order_when_truncated():
    fake = FakeNotion({
        "page": ("TRUNCADO", True, ["a", "b"]),
        "a": ("## Seção A\ntexto A.", False, []),
        "b": ("## Seção B\ntexto B.", False, []),
    })
    out = await _assembler(fake).assemble("page")
    assert out == "## Seção A\ntexto A.\n\n## Seção B\ntexto B."


@pytest.mark.asyncio
async def test_recurses_into_truncated_child():
    fake = FakeNotion({
        "page": ("TRUNCADO", True, ["a"]),
        "a": ("TRUNCADO", True, ["a1", "a2"]),
        "a1": ("neto 1.", False, []),
        "a2": ("neto 2.", False, []),
    })
    out = await _assembler(fake).assemble("page")
    assert out == "neto 1.\n\nneto 2."


@pytest.mark.asyncio
async def test_respects_max_depth_keeping_partial_markdown():
    fake = FakeNotion({
        "page": ("TRUNCADO", True, ["a"]),
        "a": ("markdown parcial de a.", True, ["a1"]),
        "a1": ("nunca alcançado.", False, []),
    })
    out = await _assembler(fake, max_depth=1).assemble("page")
    # parou em profundidade 1: usa o markdown (parcial) do próprio filho truncado
    assert out == "markdown parcial de a."
    assert "a1" not in fake.markdown_calls


@pytest.mark.asyncio
async def test_skips_blank_child_markdown():
    fake = FakeNotion({
        "page": ("TRUNCADO", True, ["a", "b", "c"]),
        "a": ("texto A.", False, []),
        "b": ("   ", False, []),
        "c": ("texto C.", False, []),
    })
    out = await _assembler(fake).assemble("page")
    assert out == "texto A.\n\ntexto C."
