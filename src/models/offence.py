from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .defendant import Defendant

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()


class Offence(Base):
    """Offence of defendant entity."""

    __tablename__ = _settings.storage.table_name_offences

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign key to Defendant
    defendant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_settings.storage.table_name_defendants}.id"), nullable=False, index=True
    )

    code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relationships
    defendant: Mapped["Defendant"] = relationship(
        "Defendant",
        foreign_keys=[defendant_id],
        back_populates="offences",
    )

    def __repr__(self) -> str:
        return f"<Offence(id='{self.id}', defendant_id='{self.defendant_id}')>"