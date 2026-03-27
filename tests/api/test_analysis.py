import pytest
from unittest.mock import MagicMock, patch

from src.api.analysis import analysis


class TestAnalysisEndpoint:
    """Tests for the analysis API endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analysis(self):
        """Test successful analysis of a section."""
        mock_analysis_job = MagicMock()
        mock_analysis_job.experiment_id = "TST-EXP-test_analysis"
        mock_analysis_job.id = 42
        mock_analysis_job.task_ids = ["task-1", "task_id"]

        mock_orchestrator = MagicMock()
        mock_orchestrator.analyze_section.return_value = mock_analysis_job

        with patch("src.api.analysis.init_session_manager") as mock_init_session, \
             patch("src.api.analysis.init_database") as mock_init_db, \
             patch("src.api.analysis.AnalysisOrchestrator", return_value=mock_orchestrator):
            result = await analysis(section_ids=[0])

        mock_init_session.assert_called_once()
        mock_init_db.assert_called_once()
        mock_orchestrator.analyze_section.assert_called_once_with(section_id=0, task_ids=None)

        # Verify all expected keys are present
        expected_keys = {"experiment_id", "section_id", "analysis_job_id", "task_ids", "correlation_id"}
        assert set(result["analysis"][0].keys()) == expected_keys

        assert result["analysis"][0]["experiment_id"] == "TST-EXP-test_analysis"
        assert result["analysis"][0]["section_id"] == 0
        assert result["analysis"][0]["analysis_job_id"] == 42
        
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_analysis_handles_empty_tasks(self):
        """Test that analysis handles jobs with no tasks."""
        mock_analysis_job = MagicMock()
        mock_analysis_job.experiment_id = "exp-123"
        mock_analysis_job.id = 42
        mock_analysis_job.task_ids = []

        mock_orchestrator = MagicMock()
        mock_orchestrator.analyze_section.return_value = mock_analysis_job

        with patch("src.api.analysis.init_session_manager"), \
             patch("src.api.analysis.init_database"), \
             patch("src.api.analysis.AnalysisOrchestrator", return_value=mock_orchestrator):
            result = await analysis(section_ids=[0])

        assert result["analysis"][0]


class TestAnalysisIntegration:
    """Integration tests for the analysis API endpoint."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_analysis(self):
        from src.config import SettingsManager
        settings = SettingsManager.get_instance()
        result = await analysis(
            section_ids=[settings.test.section_id],
            task_ids=['combined-age-appropriate'],
        )

        assert result["analysis"][0]["section_id"] == settings.test.section_id
        assert "analysis_job_id" in result["analysis"][0]
        assert len(result["analysis"]) > 0
        assert len(result["analysis"][0]["task_ids"]) > 0