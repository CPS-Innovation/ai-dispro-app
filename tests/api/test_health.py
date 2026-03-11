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

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_returns_error_for_unknown_route(self):
        mock_settings = MagicMock()
        mock_settings.validate.return_value = []

        with patch("src.api.health.SettingsManager.get_instance", return_value=mock_settings):
            result = await health(route="nonexistent")

        assert result["status"] == "error"
        assert "nonexistent" in result["error"]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_postgres_success(self):
        mock_settings = MagicMock()
        mock_settings.validate.return_value = []
        mock_session_manager = MagicMock()
        mock_session_manager.engine = MagicMock()
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["table1", "table2"]
        mock_session_manager.session.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_session_manager.session.return_value.__exit__ = MagicMock(return_value=False)

        with patch("src.api.health.SettingsManager.get_instance", return_value=mock_settings), \
             patch("src.database.init_session_manager"), \
             patch("src.api.health.inspect", return_value=mock_inspector), \
             patch("src.database.session.get_session_manager", return_value=mock_session_manager), \
             patch("src.api.health.verify_schema", return_value={"status": "ok"}):
            result = await health(route="postgres")

        assert result["status"] == "success"
        assert "postgres" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_blob_success(self):
        mock_settings = MagicMock()
        mock_settings.validate.return_value = []
        mock_client = MagicMock()
        mock_client.list_containers.return_value = [MagicMock(), MagicMock()]

        with patch("src.api.health.SettingsManager.get_instance", return_value=mock_settings), \
             patch("src.services.get_blob_service_client", return_value=mock_client):
            result = await health(route="blob")

        assert result["status"] == "success"
        assert "blob" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_llm_success(self):
        mock_settings = MagicMock()
        mock_settings.validate.return_value = []
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="six"))]

        with patch("src.api.health.SettingsManager.get_instance", return_value=mock_settings), \
             patch("src.services.get_llm_client", return_value=mock_client):
            result = await health(route="llm")

        assert result["status"] == "success"
        assert "llm" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_docintel_success(self):
        mock_settings = MagicMock()
        mock_settings.validate.return_value = []
        mock_client = MagicMock()
        mock_client.begin_analyze_document.return_value.result.return_value.pages = [MagicMock()]

        with patch("src.api.health.SettingsManager.get_instance", return_value=mock_settings), \
             patch("src.services.azure_docintel.minimal_pdf", return_value=b"fakepdf"), \
             patch("src.services.get_docintel_client", return_value=mock_client):
            result = await health(route="docintel")

        assert result["status"] == "success"
        assert "docintel" in result

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_keyvault_success(self):
        mock_settings = MagicMock()
        mock_settings.validate.return_value = []
        mock_settings.cms.username_secret_name = "my-secret"

        with patch("src.api.health.SettingsManager.get_instance", return_value=mock_settings), \
             patch("src.services.get_secret", return_value="secret-value"):
            result = await health(route="keyvault")

        assert result["status"] == "success"
        assert "keyvault" in result

