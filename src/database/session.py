from contextlib import contextmanager
from typing import Generator, Literal

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from ..config import SettingsManager
from .base import Base
from ..services.azure_postgresql import get_connection_string

# TODO: singleton pattern instead of global variable

class SessionManager:
    """Manages database sessions and engine lifecycle."""

    _engine: Engine
    _session_factory: sessionmaker

    def __init__(
        self,
        connection_string: str | None = None,
    ):
        """Initialize session manager."""
        if connection_string:
            self._engine = create_engine(connection_string)
        else:
            # Load from SettingsManager
            settings = SettingsManager.get_instance()
            self._engine = create_engine(
                get_connection_string(settings),
                pool_size=settings.database.pool_size,
                max_overflow=settings.database.max_overflow,
                echo=settings.database.echo,
            )

        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @property
    def engine(self) -> Engine:
        """Get the database engine."""
        return self._engine

    def create_all(self):
        """Create all tables in the database."""
        Base.metadata.create_all(self._engine)

    def truncate_table(self, table_name: str):
        """Truncate a specific table in the database."""
        with self.get_session() as session:
            if table_name not in Base.metadata.tables:
                raise ValueError(f"Unknown or unauthorized table name: {table_name!r}")
            quoted_table_name = self._engine.dialect.identifier_preparer.quote(table_name)
            sttmt = "TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE;".format(
                table_name=quoted_table_name
            )
            session.execute(text(sttmt))
            session.commit()

    def grant_access(
            self,
            object_name: str,
            grantee: str,
            operations: list[str],
            object_type: Literal["TABLE", "SEQUENCE"] = "TABLE",
     ) -> None:
        """Grant access to a specific table for a given role or user."""
        operations = ', '.join(operations)
        sttmnt = "GRANT {operations} ON {object_type} {object_name} TO {grantee};".format_map({
            "operations": operations,
            "object_type": object_type,
            "object_name": object_name,
            "grantee": grantee,
        })
        with self.get_session() as session:
            session.execute(text(sttmnt))
            session.commit()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope around a series of operations."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """Get a new database session."""
        return self._session_factory()

    def close(self):
        """Close the engine and cleanup resources."""
        self._engine.dispose()


# Global session manager instance
_session_manager: SessionManager | None = None


def init_session_manager(
    connection_string: str | None = None,
) -> SessionManager:
    """Initialize the global database session manager."""
    global _session_manager
    _session_manager = SessionManager(
        connection_string=connection_string
    )
    return _session_manager


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    if _session_manager is None:
        raise RuntimeError(
            "Database not initialized. Call init_session_manager() first or set environment variables."
        )
    return _session_manager


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session as a context manager.

    Usage:
        with get_session() as session:
            # Use session
            pass
    """
    manager = get_session_manager()
    with manager.session() as session:
        yield session
