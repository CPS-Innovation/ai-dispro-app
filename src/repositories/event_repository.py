from sqlalchemy.orm import Session

from ..models import Event
from .base import BaseRepository

DEFAULT_SOURCE = 'cps-ai'


class EventRepository(BaseRepository[Event]):
    """Repository for Event operations."""

    def __init__(self, session: Session):
        super().__init__(Event, session)
    
    def log(
        self, 
        event_type: str,
        actor_id: str,
        action: str,
        object_type: str,
        object_id: str,
        correlation_id: str | None = None,
        source: str | None = DEFAULT_SOURCE,
        ) -> Event:
        """Get all results for an analysis job."""
        return self.create(
            source=source,
            event_type=event_type,
            actor_id=actor_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            correlation_id=correlation_id,
        )
