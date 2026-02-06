from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .experiment import Experiment
    from .section import Section
    from .analysisresult import AnalysisResult

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()

class AnalysisJob(Base):
    """Analysis job for a content section."""

    __tablename__ = _settings.storage.table_name_analysisjobs

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign keys
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey(f"{_settings.storage.table_name_experiments}.id"), nullable=False, index=True
    )
    section_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_settings.storage.table_name_sections}.id"), nullable=False, index=True
    )

    task_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # Relationships
    section: Mapped["Section"] = relationship(
        "Section",
        foreign_keys=[section_id],
        back_populates="analysis_jobs",
    )
    experiment: Mapped["Experiment"] = relationship(
        "Experiment",
        foreign_keys=[experiment_id],
        back_populates="analysis_jobs",
    )
    analysis_job_results: Mapped[list["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="analysis_job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AnalysisJob(id='{self.id}', section_id='{self.section_id}')>"
