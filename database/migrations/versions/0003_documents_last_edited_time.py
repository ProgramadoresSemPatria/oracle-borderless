"""documents.last_edited_time (sync incremental do Notion)

Revision ID: 0003_documents_last_edited_time
Revises: 0002_conversations
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_documents_last_edited_time"
down_revision = "0002_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("last_edited_time", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "last_edited_time")
