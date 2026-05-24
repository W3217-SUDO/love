"""create health metrics

Revision ID: 0010_health_metrics
Revises: 0009_user_settings
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0010_health_metrics"
down_revision: Union[str, Sequence[str], None] = "0009_user_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "health_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("metric_type", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="manual", nullable=False),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "date",
            "metric_type",
            "source",
            name="uq_health_metrics_user_date_type_source",
        ),
    )
    op.create_index(op.f("ix_health_metrics_user_id"), "health_metrics", ["user_id"])
    op.create_index(op.f("ix_health_metrics_date"), "health_metrics", ["date"])
    op.create_index(op.f("ix_health_metrics_metric_type"), "health_metrics", ["metric_type"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_health_metrics_metric_type"), table_name="health_metrics")
    op.drop_index(op.f("ix_health_metrics_date"), table_name="health_metrics")
    op.drop_index(op.f("ix_health_metrics_user_id"), table_name="health_metrics")
    op.drop_table("health_metrics")
