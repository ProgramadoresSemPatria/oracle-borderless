import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_vector_extension_and_tables_exist(db_session):
    ext = await db_session.execute(text("SELECT 1 FROM pg_extension WHERE extname='vector'"))
    assert ext.scalar_one() == 1

    for table in ("documents", "document_chunks"):
        r = await db_session.execute(text("SELECT to_regclass(:t)"), {"t": table})
        assert r.scalar_one() is not None
