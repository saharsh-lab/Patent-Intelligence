"""answers the user stopped

The chat's Stop button (2026-10-22) keeps what was written so far as a run with status
"stopped", so the run status check allows it.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_agent_runs_valid_status"), "agent_runs", type_="check")
    op.create_check_constraint(
        op.f("ck_agent_runs_valid_status"),
        "agent_runs",
        "status IN ('running', 'succeeded', 'insufficient_evidence', 'failed', 'stopped')",
    )


def downgrade() -> None:
    op.execute("UPDATE agent_runs SET status = 'failed' WHERE status = 'stopped'")
    op.drop_constraint(op.f("ck_agent_runs_valid_status"), "agent_runs", type_="check")
    op.create_check_constraint(
        op.f("ck_agent_runs_valid_status"),
        "agent_runs",
        "status IN ('running', 'succeeded', 'insufficient_evidence', 'failed')",
    )
