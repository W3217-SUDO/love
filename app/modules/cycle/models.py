from datetime import date as date_t
from datetime import datetime
from datetime import time as time_t
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Period(Base):
    """One row per menstrual period."""
    __tablename__ = "periods"
    __table_args__ = (
        UniqueConstraint("user_id", "start_date", name="uq_periods_user_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    start_date: Mapped[date_t] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date_t | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )


class CycleSettings(Base):
    """Per-user cycle prediction configuration."""
    __tablename__ = "cycle_settings"
    __table_args__ = (
        CheckConstraint("mode IN ('auto', 'manual')", name="ck_cycle_settings_mode"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    avg_cycle_length: Mapped[int] = mapped_column(Integer, nullable=False, default=28)
    avg_period_length: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="auto")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )


class BbtReading(Base):
    """One basal body temperature reading per user per day."""
    __tablename__ = "bbt_readings"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_bbt_user_date"),
        CheckConstraint(
            "temp_c BETWEEN 35.00 AND 38.00",
            name="ck_bbt_temp_range",
        ),
        CheckConstraint(
            "method IS NULL OR method IN ('oral','vaginal','axillary','wrist','other')",
            name="ck_bbt_method",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    date: Mapped[date_t] = mapped_column(Date, nullable=False)
    temp_c: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    measure_time: Mapped[time_t | None] = mapped_column(Time, nullable=True)
    method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
