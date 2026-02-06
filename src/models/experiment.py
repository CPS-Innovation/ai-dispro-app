from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .section import Section
    from .analysisjob import AnalysisJob
    from .analysisresult import AnalysisResult

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()

class Experiment(Base):
    """Experiment model representing a run."""

    __tablename__ = _settings.storage.table_name_experiments

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4()), index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    sections: Mapped[list["Section"]] = relationship(
        "Section",
        back_populates="experiment",
        cascade="all, delete-orphan"
    )
    analysis_jobs: Mapped[list["AnalysisJob"]] = relationship(
        "AnalysisJob",
        back_populates="experiment",
        cascade="all, delete-orphan"
    )
    analysis_job_results: Mapped[list["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="experiment",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Experiment(id='{self.id}')>"
