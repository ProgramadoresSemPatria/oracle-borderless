from src.support.agent.ports import AgentMessage, AgentStreamChunk


def test_text_chunk_defaults():
    c = AgentStreamChunk(type="text", text="olá")
    assert c.text == "olá" and c.citations == []


def test_sources_chunk_carries_citations():
    from src.domain.shared.value_objects.citation import Citation

    c = AgentStreamChunk(type="sources", citations=[Citation("web", "T", "u", "s")])
    assert c.type == "sources" and len(c.citations) == 1


def test_agent_message():
    m = AgentMessage(role="user", content="oi")
    assert m.role == "user"
