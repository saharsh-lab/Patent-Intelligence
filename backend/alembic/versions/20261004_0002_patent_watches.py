"""patent watches (monitoring)

Adds `patent_watches` (saved searches) and `watch_hits` (new publications they found).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patent_watches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("keywords", sa.Text(), server_default="", nullable=False),
        sa.Column("cpc", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("reference_document_id", sa.Uuid(), nullable=True),
        sa.Column("import_top", sa.Integer(), server_default="3", nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("since", sa.Date(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["reference_document_id"],
            ["documents.id"],
            name=op.f("fk_patent_watches_reference_document_id_documents"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patent_watches")),
    )
    op.create_index(op.f("ix_patent_watches_owner_id"), "patent_watches", ["owner_id"], unique=False)
    op.create_table(
        "watch_hits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("watch_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("publication_number", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("applicants", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("imported_patent_id", sa.Uuid(), nullable=True),
        sa.Column("seen", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("found_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["imported_patent_id"],
            ["patents.id"],
            name=op.f("fk_watch_hits_imported_patent_id_patents"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["watch_id"],
            ["patent_watches.id"],
            name=op.f("fk_watch_hits_watch_id_patent_watches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_watch_hits")),
        sa.UniqueConstraint("watch_id", "publication_number", name=op.f("uq_watch_hits_watch_id_publication_number")),
    )
    op.create_index(op.f("ix_watch_hits_watch_id"), "watch_hits", ["watch_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_watch_hits_watch_id"), table_name="watch_hits")
    op.drop_table("watch_hits")
    op.drop_index(op.f("ix_patent_watches_owner_id"), table_name="patent_watches")
    op.drop_table("patent_watches")
