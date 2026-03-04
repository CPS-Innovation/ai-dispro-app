import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.api import ingestion
from src.config import SettingsManager
from src.ingestion import IngestionResult
from src.repositories import EventRepository


class TestIngestionEndpoint:
    """Tests for the ingestion API endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_ingestion_success(self):
        """Test successful document ingestion."""
        mock_result = IngestionResult(
            success=True,
            section_ids=["section-1", "section-2"],
            error=None,
        )
        mock_orchestrator = MagicMock()
        mock_orchestrator.ingest = AsyncMock(return_value=mock_result)
        
        with patch("src.api.ingestion.init_session_manager") as mock_init_session, \
             patch("src.api.ingestion.init_database") as mock_init_db, \
             patch("src.api.ingestion.IngestionOrchestrator", return_value=mock_orchestrator) as mock_ingest:
            result = await ingestion(
                trigger_type="blob_name",
                value="test-blob-path",
                experiment_id="exp-123",
            )
        
        mock_init_session.assert_called_once()
        mock_init_db.assert_called_once()
        mock_ingest.assert_called_once()

        expected_keys = {"status", "section_ids", "experiment_id", "correlation_id", "error"}
        assert set(result.keys()) == expected_keys

        assert result["status"] == "success"
        assert result["section_ids"] == ["section-1", "section-2"]
        assert result["experiment_id"] == "exp-123"
        assert result["error"] is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_ingestion_failure(self):
        """Test ingestion failure returns error status."""
        mock_result = IngestionResult(
            success=False,
            section_ids=[],
            error="Failed to process document",
        )
        mock_orchestrator = MagicMock()
        mock_orchestrator.ingest = AsyncMock(return_value=mock_result)

        with patch("src.api.ingestion.init_session_manager"), \
             patch("src.api.ingestion.init_database"), \
             patch("src.api.ingestion.IngestionOrchestrator", return_value=mock_orchestrator):
            result = await ingestion(
                trigger_type="blob_name",
                value="invalid-path",
                experiment_id="exp-456",
            )

        assert result["status"] == "error"
        assert result["section_ids"] == []
        assert result["error"] == "Failed to process document"


class TestIngestionIntegration:
    """Integration tests for the ingestion API endpoint."""

    settings = SettingsManager.get_instance()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ingestion_with_urn(self):
        result = await ingestion(
            trigger_type="urn",
            value=self.settings.test.cms_urn,
            experiment_id="TST-EXP-API-Ingestion-URN",
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ingestion_with_urn_list(self):
        result = await ingestion(
            trigger_type="urn_list",
            value=[self.settings.test.cms_urn],
            experiment_id="TST-EXP-API-Ingestion-URN_LIST",
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ingestion_with_blob(self):
        settings = SettingsManager.get_instance()
        result = await ingestion(
            trigger_type="blob_name",
            value=settings.test.blob_name,
            experiment_id="TST-EXP-API-Ingestion-BLOB_NAME",
        )
        assert result["status"] == "success"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_ingestion_with_local_file(self):
        settings = SettingsManager.get_instance()
        result = await ingestion(
            trigger_type="filepath",
            value=settings.test.filepath,
            experiment_id="TST-EXP-API-Ingestion-FILEPATH",
        )
        assert result["status"] == "success"