from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Media(Base):
    """A single uploaded file (image or PDF). Files live under UPLOAD_DIR;
    DB row stores metadata. PDF support comes in M2 — M1 only handles images."""
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # "image" | "pdf"
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_path: Mapped[str] = mapped_column(String(255), nullable=False)
    thumb_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preview_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exif_taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # GPS stripped from this row; we don't store it for now.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("owner_id", "sha256", name="uq_media_owner_sha256"),
        CheckConstraint("kind IN ('image', 'pdf')", name="ck_media_kind"),
    )
