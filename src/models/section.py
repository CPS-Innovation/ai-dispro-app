from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .version import Version
    from .experiment import Experiment
    from .analysisjob import AnalysisJob

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()


class Section(Base):
    """Relevant section of a document version."""

    __tablename__ = _settings.storage.table_name_sections

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign keys
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey(f"{_settings.storage.table_name_experiments}.id"), nullable=False, index=True
    )
    version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_settings.storage.table_name_versions}.id"), nullable=False, index=True
    )

    document_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    content_blob_container: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    content_blob_name: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    redacted_content: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relationships
    version: Mapped["Version"] = relationship(
        "Version",
        foreign_keys=[version_id],
        back_populates="sections",
    )
    experiment: Mapped["Experiment"] = relationship(
        "Experiment",
        foreign_keys=[experiment_id],
        back_populates="sections",
    )
    analysis_jobs: Mapped[list["AnalysisJob"]] = relationship(
        "AnalysisJob",
        back_populates="section",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Section(id='{self.id}', version_id='{self.version_id}')>"
