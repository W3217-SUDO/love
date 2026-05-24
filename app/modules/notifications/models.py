from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    keys_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fail_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False,
    )
