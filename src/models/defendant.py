from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .case import Case
    from .charge import Charge

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()

class Defendant(Base):
    """Defendant (Person in a case) entity."""

    __tablename__ = _settings.storage.table_name_defendants

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign key to Case
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_settings.storage.table_name_cases}.id"), nullable=False, index=True
    )

    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case",
        foreign_keys=[case_id],
        back_populates="defendants"
    )
    charges: Mapped[list["Charge"]] = relationship(
        "Charge",
        back_populates="defendant",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Defendant(id='{self.id}', case_id='{self.case_id}')>"
