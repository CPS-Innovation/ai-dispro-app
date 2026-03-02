# python
import pytest
from unittest.mock import patch

from src.config import SettingsManager
from src.database import init_session_manager, init_database
from src.services import save_blob
from src.analysis import AnalysisOrchestrator
from src.analysis.tasks import AnalysisTask
from src.analysis.workers import (
    EchoWorker,
    SimpleLLMWorker,
    LLMWorker,
    LangchainWorker,
)

from src.repositories import (
    CaseRepository,
    DocumentRepository,
    VersionRepository,
    ExperimentRepository,
    SectionRepository
)
from src.models import Section


@pytest.fixture(scope="class")
def db_initialized():
    init_session_manager()  # Ensure DB is initialized
    init_database()  # Ensure tables are created
    yield


@pytest.fixture(scope="class")
def settings():
    return SettingsManager.get_instance()


@pytest.fixture
def mock_task() -> AnalysisTask:
    return AnalysisTask(
        task_id="mockup_task",
        worker_class=EchoWorker,
        worker_config={
            "content": "This is a static analysis result.",
            "justification": "Static justification.",
            "self_confidence": 0.01,
        },
        save_results=False,
    )


class TestAnalysisOrchestrator:
    """Tests for AnalysisOrchestrator."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_call_analyze_with_mock(self, mock_task, db_initialized, settings, mock_db_session):
        """Test analyze_section method."""

        # Setup
        case_repo = CaseRepository(mock_db_session)
        case = case_repo.create(urn="01TS1234567", finalised=False)

        doc_repo = DocumentRepository(mock_db_session)
        doc = doc_repo.create(case_id=case.id, original_file_name="test.pdf")

        version_repo = VersionRepository(mock_db_session)
        version = version_repo.create(document_id=doc.id)

        section_repo = SectionRepository(mock_db_session)

        content = "This is a test section content for analysis."
        redacted_content = "This is a [REDACTED] section content for analysis."

        settings = SettingsManager.get_instance()
        container_name = settings.storage.blob_container_name_section
        blob_name = "test_analyse_with_mock/test_analyze_section.txt"
        save_blob(
            container_name=container_name,
            blob_name=blob_name,
            data=content.encode('utf-8'),
        )

        section: Section = section_repo.create(
            version_id=version.id, 
            document_id=doc.id, 
            content_blob_container=container_name,
            content_blob_name=blob_name,
            redacted_content=redacted_content)
        mock_db_session.commit()

        orchestrator = AnalysisOrchestrator(tasks=[mock_task])

        class _SessionCtx:
            """Simple context manager to return the provided session."""

            def __init__(self, session):
                self.session = session

            def __enter__(self):
                return self.session

            def __exit__(self, exc_type, exc, tb):
                return False

        with patch("src.analysis.orchestrator.get_session", return_value=_SessionCtx(mock_db_session)):
            with patch("src.analysis.orchestrator.load_blob", return_value=content.encode("utf-8")):
                with patch.object(orchestrator, "analyze", return_value="mocked_analysis_job") as mock_analyze:
                    analysis_job = orchestrator.analyze_section(section_id=section.id)

                    assert mock_analyze.call_count == 1
                    call_kwargs = mock_analyze.call_args.kwargs
                    assert call_kwargs["text"] == content
                    assert call_kwargs["section_id"] == section.id
                    assert analysis_job == "mocked_analysis_job"

    @pytest.mark.parametrize("tasks", [
        [AnalysisTask(
            task_id="test_staticworker_task",
            worker_class=EchoWorker,
            worker_config={
                "content": "This is a static analysis result.",
                "justification": "Static justification.",
                "self_confidence": 0.01,
            },
            save_results=False,
        )],
        [AnalysisTask(
            task_id="test_simplellmworker_task",
            worker_class=SimpleLLMWorker,
            worker_config={
                "prompt_template": """
                    Return the first word from {{text}} 
                    in the following JSON format: 
                    {\"content\": \"<word>\", \"justification\": \"<explanation>\", \"self_confidence\": 0.9}
                    """,
            },
            save_results=False,
        )],
        [AnalysisTask(
            task_id="test_llmworker_task",
            worker_class=LLMWorker,
            worker_config={
                "theme_id": "tst-theme-01",
                "pattern_id": "tst-pattern-01",
            },
            save_results=False,
        )],
        [AnalysisTask(
            task_id="test_langchainworker_task",
            worker_class=LangchainWorker,
            worker_config={
                "prompt_template_id": 0,
                "pattern_id": "TEST",
            },
            save_results=False,
        )],
    ])
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_call_analyze(self, tasks, db_initialized, settings, db_session):
        """Test analyze_section method."""

        # Setup
        case_repo = CaseRepository(db_session)
        case = case_repo.create(urn="01TS1234567", finalised=False)

        doc_repo = DocumentRepository(db_session)
        doc = doc_repo.create(case_id=case.id, original_file_name="test.pdf")

        version_repo = VersionRepository(db_session)
        version = version_repo.create(document_id=doc.id)

        experiment_repo = ExperimentRepository(db_session)
        experiment = experiment_repo.upsert(id="TST-EXP-test_call_analyze")

        section_repo = SectionRepository(db_session)

        settings = SettingsManager.get_instance()
        content = settings.test.section_content
        redacted_content = settings.test.section_content

        container_name = settings.storage.blob_container_name_section
        blob_name = settings.test.blob_name
        save_blob(
            container_name=container_name,
            blob_name=blob_name,
            data=content.encode('utf-8'),
        )

        section: Section = section_repo.create(
            version_id=version.id, 
            document_id=doc.id, 
            experiment_id=experiment.id,
            content_blob_container=container_name,
            content_blob_name=blob_name,
            redacted_content=redacted_content)
        db_session.commit()

        orchestrator = AnalysisOrchestrator(tasks=tasks)

        analysis_job = orchestrator.analyze_section(section_id=section.id)

        assert analysis_job.id