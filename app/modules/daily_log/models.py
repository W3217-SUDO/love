from datetime import date as date_t
from datetime import datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DailyEntry(Base):
    """One row per user per day; parent for the day's tags."""
    __tablename__ = "daily_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_daily_entries_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    date: Mapped[date_t] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )


class DailyTag(Base):
    """A single tag (Flo-style label) attached to a DailyEntry."""
    __tablename__ = "daily_tags"
    __table_args__ = (
        UniqueConstraint(
            "entry_id", "category", "tag_key",
            name="uq_daily_tags_entry_category_key",
        ),
        Index("ix_daily_tags_tag_key", "tag_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("daily_entries.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    tag_key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
