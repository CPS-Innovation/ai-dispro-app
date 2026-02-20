import pytest
from unittest.mock import MagicMock, patch

from src.api.health import health


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_returns_success_when_settings_valid(self):
        """Test health returns success when settings are valid and no route specified."""
        mock_settings = MagicMock()
        mock_settings.validate.return_value = []

        with patch("src.api.health.SettingsManager.get_instance", return_value=mock_settings):
            result = await health(route=None)

        assert result["status"] == "success"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_returns_error_when_settings_invalid(self):
        """Test health returns error when settings validation fails."""
        mock_settings = MagicMock()
        mock_settings.validate.return_value = ["Missing required setting: X"]

        with patch("src.api.health.SettingsManager.get_instance", return_value=mock_settings):
            result = await health(route=None)

        assert result["status"] == "error"
        assert "errors" in result
        assert "Missing required setting: X" in result["errors"]

