import pytest
import inspect
from dataclasses import fields
from unittest.mock import patch, AsyncMock

from src.database import init_session_manager, init_database
from src.config import SettingsManager
from src.ingestion.orchestrator import IngestionOrchestrator
from src.ingestion.models import IngestionResult, TriggerType


@pytest.fixture(scope="class")
def db_initialized():
    init_session_manager()  # Ensure DB is initialized
    init_database()  # Ensure tables are created
    yield

@pytest.fixture(scope="class")
def settings():
    return SettingsManager.get_instance()


class TestIngestion:
    """Tests for IngestionOrchestrator initialization."""

    @pytest.mark.regression
    def test_class_structure(self):
        """Test that class structure is correct."""

        # Verify TriggerType enum
        assert hasattr(TriggerType, 'URN')
        assert hasattr(TriggerType, 'BLOB_NAME')
        assert hasattr(TriggerType, 'FILEPATH')
        
        # Verify IngestionResult structure by checking dataclass fields
        ingestion_result_fields = {f.name for f in fields(IngestionResult)}
        assert 'success' in ingestion_result_fields
        assert 'error' in ingestion_result_fields
        assert 'case_id' in ingestion_result_fields
        assert 'document_ids' in ingestion_result_fields

        # Verify ingest method signature
        sig = inspect.signature(IngestionOrchestrator.ingest)
        params = list(sig.parameters.keys())
        assert 'trigger_type' in params
        assert 'value' in params
        assert 'experiment_id' in params

    @pytest.mark.regression
    def test_initialization(self):
        """Test that orchestrator initializes correctly."""
        orchestrator = IngestionOrchestrator()
        assert orchestrator is not None
        assert orchestrator.settings is not None
        assert hasattr(orchestrator, 'supportedCMSDocCategories')
        assert hasattr(orchestrator, 'supportedDocTypes')
        assert hasattr(orchestrator, 'supportedMimeTypes')

    @pytest.mark.regression
    def test_supported_formats(self):
        """Test that supported formats are correctly defined."""
        orchestrator = IngestionOrchestrator()
        
        # Verify supported CMS doc categories
        assert "MGForm" in orchestrator.supportedCMSDocCategories
        
        # Verify supported doc types
        assert "MG 3" in orchestrator.supportedDocTypes or "MG3" in orchestrator.supportedDocTypes
        
        # Verify supported MIME types
        assert "application/pdf" in orchestrator.supportedMimeTypes
        assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in orchestrator.supportedMimeTypes

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_route_to_urn_handler(self):
        """Test that URN trigger routes to correct handler."""
        orchestrator = IngestionOrchestrator()
        
        with patch.object(orchestrator, '_ingest_from_urn', new_callable=AsyncMock) as mock_urn:
            mock_urn.return_value = IngestionResult(success=True)
            
            result = await orchestrator.ingest(
                trigger_type=TriggerType.URN,
                value="TEST_URN",
            )
            
            mock_urn.assert_called_once()
            assert result.success is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_route_to_blob_handler(self):
        """Test that blob trigger routes to correct handler."""
        orchestrator = IngestionOrchestrator()
        
        with patch.object(orchestrator, '_ingest_from_blob_name', new_callable=AsyncMock) as mock_blob:
            mock_blob.return_value = IngestionResult(success=True)
            
            result = await orchestrator.ingest(
                trigger_type=TriggerType.BLOB_NAME,
                value="test-blob.pdf",
            )
            
            mock_blob.assert_called_once()
            assert result.success is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_route_to_filepath_handler(self):
        """Test that filepath trigger routes to correct handler."""
        orchestrator = IngestionOrchestrator()
        
        with patch.object(orchestrator, '_ingest_from_filepath', new_callable=AsyncMock) as mock_filepath:
            mock_filepath.return_value = IngestionResult(success=True)
            
            result = await orchestrator.ingest(
                trigger_type=TriggerType.FILEPATH,
                value="/path/to/file.pdf",
            )
            
            mock_filepath.assert_called_once()
            assert result.success is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_trigger_type(self):
        """Test handling of unknown trigger type."""
        orchestrator = IngestionOrchestrator()
        
        result = await orchestrator.ingest(
            trigger_type="INVALID",  # type: ignore
            value="test",
        )
        
        assert result.success is False
        assert "Unknown trigger type" in result.error

    @pytest.mark.unit
    def test_supported_cms_doc_categories_filter(self):
        """Test that only supported CMS doc categories are processed."""
        orchestrator = IngestionOrchestrator()
        
        documents = [
            {"cmsDocCategory": "MGForm", "type": "MG3", "mimeType": "application/pdf"},
            {"cmsDocCategory": "Other", "type": "MG3", "mimeType": "application/pdf"},
            {"cmsDocCategory": "MGForm", "type": "MG3", "mimeType": "application/pdf"},
        ]
        
        # Count documents that would be processed
        filtered = [
            doc for doc in documents
            if doc["cmsDocCategory"] in orchestrator.supportedCMSDocCategories
        ]
        
        assert len(filtered) == 2

    @pytest.mark.unit
    def test_supported_doc_types_filter(self):
        """Test that only supported doc types are processed."""
        orchestrator = IngestionOrchestrator()
        
        documents = [
            {"cmsDocCategory": "MGForm", "type": "MG3", "mimeType": "application/pdf"},
            {"cmsDocCategory": "MGForm", "type": "MG1", "mimeType": "application/pdf"},
            {"cmsDocCategory": "MGForm", "type": "MG 3", "mimeType": "application/pdf"},
        ]
        
        # Count documents that would be processed
        filtered = [
            doc for doc in documents
            if doc["type"] in orchestrator.supportedDocTypes
        ]
        
        assert len(filtered) >= 1  # At least MG3 or MG 3

    @pytest.mark.unit
    def test_supported_mime_types_filter(self):
        """Test that only supported MIME types are processed."""
        orchestrator = IngestionOrchestrator()
        
        documents = [
            {"cmsDocCategory": "MGForm", "type": "MG3", "mimeType": "application/pdf"},
            {"cmsDocCategory": "MGForm", "type": "MG3", "mimeType": "text/plain"},
            {"cmsDocCategory": "MGForm", "type": "MG3", "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
        ]
        
        # Count documents that would be processed
        filtered = [
            doc for doc in documents
            if doc["mimeType"] in orchestrator.supportedMimeTypes
        ]
        
        assert len(filtered) == 2  # PDF and DOCX

class TestIngestionIntegration:

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ingest_urn(self, db_initialized, settings):
        ingestion_orchestrator = IngestionOrchestrator()
        result = await ingestion_orchestrator.ingest(
            trigger_type=TriggerType.URN,
            value=settings.test.cms_urn,
            experiment_id="TST-EXP-Ingestion-URN",
        )
        assert result.success

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ingest_blob(self, db_initialized, settings):
        ingestion_orchestrator = IngestionOrchestrator()
        result = await ingestion_orchestrator.ingest(
            trigger_type=TriggerType.BLOB_NAME,
            value=settings.test.blob_name,
            experiment_id="TST-EXP-Ingestion-BLOB_NAME",
        )
        assert result.success

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ingest_file(self, db_initialized, settings):
        ingestion_orchestrator = IngestionOrchestrator()
        result = await ingestion_orchestrator.ingest(
            trigger_type=TriggerType.FILEPATH,
            value=settings.test.filepath,
            experiment_id="TST-EXP-Ingestion-FILEPATH",
        )
        assert result.success
