from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()


class Event(Base):
    """Event model for audit."""

    __tablename__ = _settings.storage.table_name_events

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    experiment_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<Event(id='{self.id}')>"
