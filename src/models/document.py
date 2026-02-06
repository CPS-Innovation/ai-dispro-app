from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .case import Case
    from .version import Version

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()

class Document(Base):
    """Document linked to a case."""

    __tablename__ = _settings.storage.table_name_documents

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign key to Case
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_settings.storage.table_name_cases}.id"), nullable=False, index=True
    )

    original_file_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cms_doc_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    doc_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_extension: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    case: Mapped["Case"] = relationship(
        "Case", 
        foreign_keys=[case_id],
        back_populates="documents"
    )
    versions: Mapped[list["Version"]] = relationship(
        "Version",
        back_populates="document",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id='{self.id}', case_id='{self.case_id}', filename='{self.original_file_name}')>"
