from src.domain.documents.services.notion_markup_cleaner import NotionMarkupCleaner

cleaner = NotionMarkupCleaner()


def test_plain_text_is_unchanged():
    text = "## Título\nUm parágrafo normal com **negrito** e [link](https://x).\n\n## Outro\nMais texto."
    assert cleaner.clean(text) == text


def test_removes_callout_wrapper_keeps_inner_text():
    out = cleaner.clean('<callout icon="▶️" color="gray_bg">\nConteúdo do callout.\n</callout>')
    assert "<callout" not in out and "</callout>" not in out
    assert "Conteúdo do callout." in out


def test_unwraps_colored_span():
    assert cleaner.clean('Olá <span color="red">#NOME</span>!') == "Olá #NOME!"


def test_strips_toggle_suffix_from_heading():
    assert cleaner.clean('## Etapa 1 {toggle="true"}') == "## Etapa 1"


def test_removes_empty_block_and_unknown_tags():
    out = cleaner.clean('Texto.\n<empty-block/>\n<unknown url="x" alt="breadcrumb"/>\nFim.')
    assert "empty-block" not in out
    assert "unknown" not in out
    assert "Texto." in out and "Fim." in out


def test_br_becomes_newline():
    assert cleaner.clean("linha1<br>linha2") == "linha1\nlinha2"


def test_table_cells_become_lines():
    table = (
        '<table header-row="true">\n<tr>\n<td>**Código**</td>\n<td>SOP-01</td>\n</tr>\n</table>'
    )
    out = cleaner.clean(table)
    assert "<table" not in out and "<td>" not in out and "<tr>" not in out
    assert "**Código**" in out
    assert "SOP-01" in out


def test_collapses_excess_blank_lines():
    assert cleaner.clean("a\n\n\n\n\nb") == "a\n\nb"


def test_preserves_headings_and_lists():
    text = "## Regras\n1. Primeira\n2. Segunda\n- bullet"
    assert cleaner.clean(text) == text
