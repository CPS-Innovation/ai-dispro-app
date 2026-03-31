import pytest

from src.analysis.workers import LangGraphWorker
from src.database import init_session_manager, get_session
from src.config import SettingsManager


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
