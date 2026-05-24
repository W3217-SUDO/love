"""create push subscriptions

Revision ID: 0013_push_subscriptions
Revises: 0012_import_jobs
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_push_subscriptions"
down_revision: Union[str, Sequence[str], None] = "0012_import_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("keys_json", sa.JSON(), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("fail_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("disabled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_push_subscriptions_endpoint"),
        "push_subscriptions",
        ["endpoint"],
        unique=True,
    )
    op.create_index(
        op.f("ix_push_subscriptions_user_id"),
        "push_subscriptions",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_push_subscriptions_user_id"), table_name="push_subscriptions")
    op.drop_index(op.f("ix_push_subscriptions_endpoint"), table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
