from datetime import date as date_t
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class HealthMetric(Base):
    """One health metric reading per user, date, type, and source."""
    __tablename__ = "health_metrics"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "date",
            "metric_type",
            "source",
            name="uq_health_metrics_user_date_type_source",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    date: Mapped[date_t] = mapped_column(Date, nullable=False, index=True)
    metric_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual", server_default="manual",
    )
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )
