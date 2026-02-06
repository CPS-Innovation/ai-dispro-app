from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models.
    
    It is not allowed to use 'DeclarativeBase' directly as a declarative base class.
    """

    def to_dict(self) -> dict:
        mapper = inspect(self).mapper
        return {column.key: getattr(self, column.key) for column in mapper.columns}
