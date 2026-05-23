from datetime import date as date_t
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('private', 'shared')",
            name="ck_diary_visibility",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    date: Mapped[date_t] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(16), nullable=False, default="shared",
        server_default="shared",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(),
        nullable=False,
    )


class DiaryMedia(Base):
    __tablename__ = "diary_media"
    __table_args__ = (
        PrimaryKeyConstraint("diary_id", "media_id", name="pk_diary_media"),
    )

    diary_id: Mapped[int] = mapped_column(
        ForeignKey("diary_entries.id", ondelete="CASCADE"), nullable=False,
    )
    media_id: Mapped[int] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
