"""per-user data and chat conversations

- documents.owner_id, queries.owner_id: which user (in the separate auth database) owns
  them; NULL in single-user mode and for experiment runs.
- Duplicate detection becomes per owner: two users uploading the same file get their
  own copies (before, the second user would have received the first user's document).
  NULLS NOT DISTINCT keeps de-duplication working when there is no owner.
- conversations: chat threads; their messages are queries with this conversation_id.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_documents_owner_id"), "documents", ["owner_id"], unique=False)
    op.drop_constraint(op.f("uq_documents_content_sha256"), "documents", type_="unique")
    op.execute(
        "ALTER TABLE documents ADD CONSTRAINT uq_documents_owner_id_content_sha256 "
        "UNIQUE NULLS NOT DISTINCT (owner_id, content_sha256)"
    )
    op.add_column("queries", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_queries_owner_id"), "queries", ["owner_id"], unique=False)

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("document_ids", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversations")),
    )
    op.create_index(op.f("ix_conversations_owner_id"), "conversations", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_conversations_owner_id"), table_name="conversations")
    op.drop_table("conversations")
    op.drop_index(op.f("ix_queries_owner_id"), table_name="queries")
    op.drop_column("queries", "owner_id")
    op.execute("ALTER TABLE documents DROP CONSTRAINT uq_documents_owner_id_content_sha256")
    op.create_unique_constraint(op.f("uq_documents_content_sha256"), "documents", ["content_sha256"])
    op.drop_index(op.f("ix_documents_owner_id"), table_name="documents")
    op.drop_column("documents", "owner_id")
