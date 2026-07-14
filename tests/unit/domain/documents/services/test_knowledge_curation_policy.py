from src.domain.documents.services.knowledge_curation_policy import (
    KnowledgeCurationPolicy,
    NotionPageRef,
)

policy = KnowledgeCurationPolicy()


def _doc(title: str, parent_type: str = "page_id") -> NotionPageRef:
    return NotionPageRef(object_type="page", parent_type=parent_type, title=title)


def test_sop_document_page_is_ingested():
    ref = _doc("SOP-GM-06 — Nomenclatura de Campanhas")
    assert policy.should_ingest(ref) is True
    assert policy.reject_reason(ref) is None


def test_editorial_document_page_is_ingested():
    assert policy.should_ingest(_doc("Editorial YouTube — Visão & Princípios")) is True


def test_workspace_parented_page_is_ingested():
    assert policy.should_ingest(_doc("Programs", parent_type="workspace")) is True


def test_database_row_is_rejected():
    """Toda linha de banco (tracker/PII) é rejeitada, mesmo com título inocente."""
    row = NotionPageRef(object_type="page", parent_type="data_source_id", title="Lucas Ferreira")
    assert policy.should_ingest(row) is False
    assert "linha de banco" in policy.reject_reason(row)


def test_data_source_object_is_rejected():
    ds = NotionPageRef(object_type="data_source", parent_type="database_id", title="Growth Sprint")
    assert policy.should_ingest(ds) is False


def test_onboarding_control_title_rejected_defense_in_depth():
    assert policy.should_ingest(_doc("New Onboarding Control")) is False


def test_backlog_wrapper_page_rejected():
    assert policy.should_ingest(_doc("Backlog Platform")) is False


def test_photo_bank_rejected():
    assert policy.should_ingest(_doc("📸 Banco de Fotos Curado")) is False


def test_date_placeholder_page_rejected():
    assert policy.should_ingest(_doc("Date: DD/mmm de 2026 (1)")) is False


def test_untitled_page_rejected():
    assert policy.should_ingest(_doc("   ")) is False


def test_block_parented_fragment_rejected():
    assert policy.should_ingest(_doc("sub-página", parent_type="block_id")) is False
