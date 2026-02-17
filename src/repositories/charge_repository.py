from sqlalchemy.orm import Session

from ..models import Charge
from .base import BaseRepository


class ChargeRepository(BaseRepository[Charge]):
    """Repository for Charge operations."""

    def __init__(self, session: Session):
        super().__init__(Charge, session)
