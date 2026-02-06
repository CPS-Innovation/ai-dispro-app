from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .defendant import Defendant

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()

class Charge(Base):
    """Charge against defendant entity."""

    __tablename__ = _settings.storage.table_name_charges

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign key to Defendant
    defendant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_settings.storage.table_name_defendants}.id"), nullable=False, index=True
    )

    code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_verdict: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relationships
    defendant: Mapped["Defendant"] = relationship(
        "Defendant",
        foreign_keys=[defendant_id],
        back_populates="charges",
    )

    def __repr__(self) -> str:
        return f"<Charge(id='{self.id}', defendant_id='{self.defendant_id}')>"
