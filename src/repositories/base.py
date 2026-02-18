from typing import Any, Generic, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository providing common CRUD operations."""

    def __init__(self, model: Type[ModelType], session: Session):
        """Initialize repository.

        Args:
            model: The SQLAlchemy model class
            session: Database session
        """
        self.model = model
        self.session = session

    def create(self, **fields) -> ModelType:
        """Create a new entity."""
        # Don't generate ID - let the database handle auto-increment
        instance = self.model(**fields)
        self.session.add(instance)
        self.session.flush()
        return instance

    def get_by_id(self, id_value: Any) -> ModelType | None:
        """Get entity by ID."""
        # Determine the primary key column name
        pk_columns = self.model.__table__.primary_key.columns
        if len(pk_columns) != 1:
            raise ValueError("get_by_id only supports single-column primary keys")

        pk_column = list(pk_columns)[0]
        stmt = select(self.model).where(pk_column == id_value)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_all(self, limit: int | None = None, offset: int = 0) -> list[ModelType]:
        """Get all entities with optional pagination."""
        stmt = select(self.model).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.session.execute(stmt).scalars().all())

    def get_by(self, **filters) -> list[ModelType]:
        """Get entities matching filters.

        Args:
            **filters: Column name and value pairs to filter by
        """
        stmt = select(self.model)
        for key, value in filters.items():
            if not hasattr(self.model, key):
                raise ValueError(f"Unknown filter field: {key}")            
            stmt = stmt.where(getattr(self.model, key) == value)

        return list(self.session.execute(stmt).scalars().all())

    def get_one_by(self, **filters) -> ModelType | None:
        """Get single entity matching filters."""
        results = self.get_by(**filters)
        return results[0] if results else None

    def update(self, id_value: Any, **fields) -> ModelType | None:
        """Update entity by ID."""
        entity = self.get_by_id(id_value)
        if entity:
            for key, value in fields.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            self.session.flush()
        return entity

    def upsert(self, **kwargs) -> ModelType:
        """Create or update entity based on unique constraints."""
        id_value = kwargs.get("id", None)
        if id_value is not None and self.exists(id=id_value):
            entity = self.get_by_id(id_value)
            if entity:
                for key, value in kwargs.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                self.session.flush()
                return entity
        return self.create(**kwargs)

    def delete(self, id_value: Any) -> bool:
        """Delete entity by ID."""
        entity = self.get_by_id(id_value)
        if entity:
            self.session.delete(entity)
            self.session.flush()
            return True
        return False

    def count(self, **filters) -> int:
        """Count entities matching filters."""
        return len(self.get_by(**filters))

    def exists(self, **filters) -> bool:
        """Check if any entity matches filters."""
        return self.count(**filters) > 0
