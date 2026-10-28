import pytest
import json

from src.analysis.workers import LangGraphWorker
from src.database import init_session_manager, get_session
from src.config import SettingsManager
from unittest.mock import MagicMock, patch
from src.models import AnalysisJob

from src.repositories import (
    CaseRepository,
    DocumentRepository,
    VersionRepository,
    SectionRepository,
    DefendantRepository,
    AnalysisJobRepository
)

@pytest.mark.integration
@pytest.mark.parametrize(("experiment_id", "save_results"), [
    (
         "TST-EXP-test_langgraph_worker",
         True,
    )
])
def test_worker(experiment_id, save_results):

    init_session_manager()

    worker = LangGraphWorker(
        config={
            "theme_id": "theme1",
            "pattern_id": "not_fact",
        },
        save_results=save_results,
    )

    if save_results:

         with get_session() as session:
            from src.repositories import (
                ExperimentRepository,
                AnalysisJobRepository,
                SectionRepository,
                VersionRepository,
                DocumentRepository,
                CaseRepository,
            )
            CaseRepository(session).upsert(id=1, urn="01TS0000008")
            DocumentRepository(session).upsert(id=1, case_id=1)
            VersionRepository(session).upsert(id=1, document_id=1)
            ExperimentRepository(session).upsert(id=experiment_id)
            SectionRepository(session).upsert(id=29, version_id=1, experiment_id=experiment_id, redacted_content="Content")
            AnalysisJobRepository(session).upsert(id=0, section_id=29, experiment_id=experiment_id)
    
    settings_manager = SettingsManager.get_instance()
    results = worker.analyze(
        text=settings_manager.test.section_content,
        experiment_id=experiment_id,
        section_id=29,
        analysis_job_id=0,
    )

    assert isinstance(results, list)
    assert len(results) >= 1


@pytest.mark.integration
@pytest.mark.parametrize(("experiment_id", "theme", "pattern", "save_results"), [
    ("TST-EXP-test_langgraph_worker", "combined", "age-appropriate", False),
    ("TST-EXP-test_langgraph_worker", "combined", "emotionally neutral", False),
    ("TST-EXP-test_langgraph_worker", "combined", "character", False),
    ("TST-EXP-test_langgraph_worker", "combined", "grounded in evidence", False),
    ("TST-EXP-test_langgraph_worker", "combined", "non-judgemental", False),
    ("TST-EXP-test_langgraph_worker", "combined", "offence-appropriate", False),
    ("TST-EXP-test_langgraph_worker", "combined", "probative", False),
    ("TST-EXP-test_langgraph_worker", "combined", "risk-proportionate", False),
    ("TST-EXP-test_langgraph_worker", "combined", "victim-appropriate", False),
])
def test_reviewer_flip_rate(experiment_id, theme, pattern, save_results):

    init_session_manager()

    worker = LangGraphWorker(
        config={
            "theme_id": theme,
            "pattern_id": pattern,
        },
        save_results=save_results,
    )

    settings_manager = SettingsManager.get_instance()
    results = worker.analyze(
        text=settings_manager.test.section_content,
        experiment_id=experiment_id,
        section_id=29,
        analysis_job_id=0,
    )

    assert isinstance(results, list)

@pytest.mark.integration
@pytest.mark.parametrize(
    "is_youth, categories, expected_count",
    [
        (False, ["Adultification"], 0),
        (True, ["Adultification"], 1),
        (False, ["VictimBlaming"], 1),
    ],
)
def test_critic_filters_adultification(
    mock_db_session,
    is_youth,
    categories,
    expected_count,
):
    # Setup
    case_repo = CaseRepository(mock_db_session)
    case = case_repo.create(urn="01TS1234567", finalised=False)

    defendant_repo = DefendantRepository(mock_db_session)
    defendant = defendant_repo.create(case_id=case.id, youth=is_youth)

    doc_repo = DocumentRepository(mock_db_session)
    document = doc_repo.create(case_id=case.id, original_file_name="test.pdf")

    version_repo = VersionRepository(mock_db_session)
    version = version_repo.create(document_id=document.id)

    section_repo = SectionRepository(mock_db_session)
    section = section_repo.create(version_id=version.id, document_id=document.id)

    analysis_job_repo = AnalysisJobRepository(mock_db_session)
    analysis_job = analysis_job_repo.create(section_id=section.id)

    # Set up relationships used by _critic
    case.defendants = [defendant]
    document.case = case
    version.document = document
    section.version = version
    analysis_job.section = section

    mock_db_session.get.return_value = analysis_job
    mock_db_session.commit()

    worker = LangGraphWorker.__new__(LangGraphWorker)
    worker.theme_id = "combined"
    worker.pattern_id = "test"
    worker.critic_prompt_template = MagicMock()
    worker.critic_prompt_template.template = "{{ contextText }}"

    class _SessionCtx:
        """Simple context manager to return the provided session."""

        def __init__(self, session):
            self.session = session

        def __enter__(self):
            return self.session

        def __exit__(self, exc_type, exc, tb):
            return False

    critic_response = {
        "analysis_results": [
            {
                "content": "test",
                "categories": categories,
                "justification": "test",
                "self_confidence": "0.9",
            }
        ]
    }

    state = {
        "text_": "test",
        "pattern_": "test",
        "analysis_job_id": analysis_job.id,
        "references": [],
        "results": [],
    }

    with patch("src.analysis.workers.langgraph_worker.get_session", return_value=_SessionCtx(mock_db_session)), \
         patch.object(worker, "_call_model", return_value=json.dumps(critic_response)):
        result = worker._critic(state)

    mock_db_session.get.assert_called_once_with(
        AnalysisJob,
        analysis_job.id,
    )

    assert len(result["references"]) == expected_count