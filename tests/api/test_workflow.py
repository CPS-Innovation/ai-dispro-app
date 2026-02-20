"""Unit tests for the workflow API module."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.api.workflow import workflow


class TestWorkflowEndpoint:
    """Tests for the workflow API endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_workflow_success_single_section(self):
        """Test successful workflow with single section."""
        mock_ingestion_result = {
            "status": "success",
            "section_ids": ["section-1"],
            "experiment_id": "exp-123",
            "correlation_id": None,
            "error": None,
            "success": True,
        }
        # Make it behave like a dict with .get() and .success attribute
        mock_ingestion = MagicMock()
        mock_ingestion.success = True
        mock_ingestion.get.side_effect = lambda key, default=None: mock_ingestion_result.get(key, default)

        mock_analysis_result = {
            "status": "success",
            "experiment_id": "exp-123",
            "correlation_id": None,
            "section_id": "section-1",
            "analysis_job_id": "job-1",
            "tasks": [],
            "success": True,
        }
        mock_analysis = MagicMock()
        mock_analysis.success = True
        mock_analysis.get.side_effect = lambda key, default=None: mock_analysis_result.get(key, default)

        with patch("src.api.workflow.init_session_manager") as mock_init_session, \
             patch("src.api.workflow.init_database") as mock_init_db, \
             patch("src.api.workflow.ingestion", new_callable=AsyncMock, return_value=mock_ingestion) as mock_ing, \
             patch("src.api.workflow.analysis", new_callable=AsyncMock, return_value=mock_analysis):
            result = await workflow(
                trigger_type="blob",
                value="test-path",
                experiment_id="exp-123",
            )

        mock_init_session.assert_called_once()
        mock_init_db.assert_called_once()
        mock_ing.assert_called_once_with(
            trigger_type="blob",
            value="test-path",
            experiment_id="exp-123",
            correlation_id=None,
        )

        expected_keys = {"status", "experiment_id", "sections", "analysis_job_ids", "correlation_id"}
        assert set(result.keys()) == expected_keys

        assert result["status"] == "success"
        assert result["experiment_id"] == "exp-123"
        assert len(result["sections"]) == 1
        assert len(result["analysis_job_ids"]) == 1


class TestWorkflowIntegration:
    """Integration tests for the workflow API endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow(self):
        from src.config.settings_manager import SettingsManager
        settings = SettingsManager.get_instance()
        result = await workflow(
            trigger_type="blob_name",
            value=settings.test.blob_name,
            experiment_id="TST-EXP-API-Workflow-BLOB_NAME",
            task_ids=['theme1-appropriateness'],
            correlation_id="TST-CORR-API-Workflow-BLOB_NAME",
        )

        assert result["status"] == "success"
        assert len(result["sections"]) > 0
        assert len(result["analysis_job_ids"]) > 0