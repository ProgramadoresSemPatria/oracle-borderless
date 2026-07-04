from src.domain.shared.value_objects.citation import Citation


def test_citation_is_frozen_and_equatable():
    a = Citation(source_type="notion", title="Regras", url="https://n/1", snippet="...", page_id="p1")
    b = Citation(source_type="notion", title="Regras", url="https://n/1", snippet="...", page_id="p1")
    assert a == b


def test_notion_citation_flag():
    c = Citation(source_type="notion", title="T", url="u", snippet="s", page_id="p1")
    assert c.is_notion() is True


def test_web_citation_flag():
    c = Citation(source_type="web", title="T", url="u", snippet="s")
    assert c.is_notion() is False
