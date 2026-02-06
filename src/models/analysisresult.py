from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.experiment import Experiment

if TYPE_CHECKING:
    from .analysisjob import AnalysisJob

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()


class AnalysisResult(Base):
    """Result of an analysis."""

    __tablename__ = _settings.storage.table_name_analysisresults

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)

    # Foreign keys
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey(f"{_settings.storage.table_name_experiments}.id"), nullable=False, index=True
    )
    analysis_job_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{_settings.storage.table_name_analysisjobs}.id"), nullable=False, index=True
    )
    
    prompt_template_id: Mapped[str | None] = mapped_column(
        String(50), 
        nullable=True,
    )

    theme_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    pattern_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[str | None] = mapped_column(Text, nullable=True, index=True)
    self_confidence: Mapped[float | None] = mapped_column(nullable=True)
    is_witness: Mapped[bool | None] = mapped_column(nullable=True)
    rewritten_phrase: Mapped[str | None] = mapped_column(Text, nullable=True)
    rewritten_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    defence_verdict: Mapped[str | None] = mapped_column(String(50), nullable=True)
    defence_pattern: Mapped[str | None] = mapped_column(String(100), nullable=True)
    defence_argument: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_final_verdict: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewer_confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    reviewer_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    analysis_job: Mapped["AnalysisJob"] = relationship(
        "AnalysisJob",
        foreign_keys=[analysis_job_id],
        back_populates="analysis_job_results"
    )
    experiment: Mapped["Experiment"] = relationship(
        "Experiment",
        foreign_keys=[experiment_id],
        back_populates="analysis_job_results"
    )

    def __repr__(self) -> str:
        return f"<AnalysisResult(id='{self.id}', analysis_job_id='{self.analysis_job_id}')>"
