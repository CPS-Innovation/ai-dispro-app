from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .defendant import Defendant
    from .document import Document

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()

class Case(Base):
    """Case with URN."""

    __tablename__ = _settings.storage.table_name_cases

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    
    # URN is indexed for fast lookup
    urn: Mapped[str] = mapped_column(String(255), primary_key=False, index=True)


    finalised: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    area_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    defendants: Mapped[list["Defendant"]] = relationship(
        "Defendant",
        back_populates="case",
        cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="case",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Case(urn='{self.urn}', id='{self.id}', finalised={self.finalised})>"
