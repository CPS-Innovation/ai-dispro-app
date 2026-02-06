from loguru import logger
from sqlalchemy.orm import Session

from ..models import PromptTemplate
from .base import BaseRepository


class PromptTemplateRepository(BaseRepository[PromptTemplate]):
    """Repository for PromptTemplate operations."""

    def __init__(self, session: Session):
        super().__init__(PromptTemplate, session)

    def get_by_id(self, id: str) -> PromptTemplate | None:
        """Get prompt template by ID."""
        return self.get_one_by(id=id)
    
    def get_last_version_by(
            self,
            **filters
        ) -> PromptTemplate | None:
        """Get the latest version of a prompt template matching the given filters."""
        records = self.get_by(**filters)
        if not records:
            return None
        
        # Return the record with the highest version number
        return max(records, key=lambda record: record.version)
    
    def upsert_by(
        self,
        template: str,
        theme: str,
        pattern: str,
        agent: str,
        version: str,
    ) -> PromptTemplate:
        """Upsert a prompt template by its unique fields."""
        prompt_templates = self.get_by(
            theme=theme,
            pattern=pattern,
            agent=agent,
            version=version,
        )
        if prompt_templates:
            if len(prompt_templates) > 1:
                raise ValueError("Multiple prompt templates found with the same unique fields")
            existing = prompt_templates[0]
            logger.info(f"Existing prompt template found with ID {existing.id}, updating it")
            self.update(id_value=existing.id, template=template)
            return existing

        logger.info("No existing prompt template found, creating a new one")
        return self.create(
            theme=theme,
            pattern=pattern,
            agent=agent,
            version=str(version or "0.1"),
            template=template,
        )
