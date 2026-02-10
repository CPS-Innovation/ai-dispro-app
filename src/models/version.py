from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .section import Section
    from .document import Document

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()


class Version(Base):
    """Document version entity."""

    __tablename__ = _settings.storage.table_name_versions

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign key to Document
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_settings.storage.table_name_documents}.id"), nullable=False, index=True
    )

    source_blob_container: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_blob_name: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    parsed_blob_container: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    parsed_blob_name: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        foreign_keys=[document_id],
        back_populates="versions",
    )
    sections: Mapped[list["Section"]] = relationship(
        "Section",
        back_populates="version",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Version(id='{self.id}', document_id='{self.document_id}')>"
