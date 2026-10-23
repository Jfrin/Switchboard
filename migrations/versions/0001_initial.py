"""initial schema

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sender", sa.String(320), nullable=False),
        sa.Column("subject", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("parsed", sa.JSON, nullable=True),
        sa.Column("enrichment", sa.JSON, nullable=True),
        sa.Column("decision", sa.JSON, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "routing_decisions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("lead_id", sa.String(36), sa.ForeignKey("leads.id"), nullable=False, index=True),
        sa.Column("rep", sa.String(64), nullable=False),
        sa.Column("rule", sa.String(128), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "round_robin_state",
        sa.Column("team", sa.String(64), primary_key=True),
        sa.Column("counter", sa.Integer, nullable=False),
    )
    op.create_table(
        "enrichment_cache",
        sa.Column("domain", sa.String(255), primary_key=True),
        sa.Column("data", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("enrichment_cache")
    op.drop_table("round_robin_state")
    op.drop_table("routing_decisions")
    op.drop_table("leads")
