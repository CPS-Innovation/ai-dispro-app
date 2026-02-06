from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..config import SettingsManager
from ..database.base import Base

_settings = SettingsManager.get_instance()


class PromptTemplate(Base):
    """Prompt template model."""

    __tablename__ = _settings.storage.table_name_prompt_templates

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    
    template: Mapped[str] = mapped_column(String(10000), nullable=False, default="")
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    agent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(128), nullable=True)
    pattern: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    def __repr__(self) -> str:
        return f"<PromptTemplate(id='{self.id}', name='{self.name}')>"
