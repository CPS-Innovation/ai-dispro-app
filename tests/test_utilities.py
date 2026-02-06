from typing import List
from unittest.mock import MagicMock


class DatabaseSessionMockBuilder:
    """Builder for creating mocked database sessions."""

    def __init__(self):
        """Initialize the mock builder."""
        self.mock = MagicMock()
        self._configure_defaults()

    def _configure_defaults(self):
        """Configure default mock behaviors."""
        self.mock.add = MagicMock()
        self.mock.commit = MagicMock()
        self.mock.rollback = MagicMock()
        self.mock.query = MagicMock()

    def with_query_result(self, model_class, result):
        """Configure query to return specific result."""
        query_mock = MagicMock()
        query_mock.filter.return_value.first.return_value = result
        self.mock.query.return_value = query_mock
        return self

    def with_query_all_results(self, model_class, results: List):
        """Configure query to return multiple results."""
        query_mock = MagicMock()
        query_mock.filter.return_value.all.return_value = results
        self.mock.query.return_value = query_mock
        return self

    def with_commit_error(self, error_message: str = "Commit failed"):
        """Configure commit to fail."""
        self.mock.commit = MagicMock(side_effect=Exception(error_message))
        return self

    def build(self):
        """Build and return the mock."""
        return self.mock
