import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_conversation_tables_exist(db_session):
    for table in ("conversations", "messages"):
        r = await db_session.execute(text("SELECT to_regclass(:t)"), {"t": table})
        assert r.scalar_one() is not None
