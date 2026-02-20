import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
from contextlib import contextmanager

from src.analysis.workers import LLMWorker
from src.models import AnalysisResult
from src.database import init_session_manager


@pytest.mark.unit
@pytest.mark.parametrize("experiment_id", [
    "TST-EXP-test_worker_parses_model_response",]
)
def test_worker_parses_model_response(monkeypatch, experiment_id):
    # Fake settings
    fake_settings = SimpleNamespace(ai_foundry=SimpleNamespace(deployment_name="test-deploy"))

    # Fake model JSON response
    response_json = '{"analysis_results":[{"content":"llm content","justification":"just","categories":["cat1"],"self_confidence":0.5}]}'

    # Fake response structure returned by the SDK
    message = SimpleNamespace(content=response_json)
    choice = SimpleNamespace(message=message)
    fake_response = SimpleNamespace(choices=[choice])

    # Mock LLM client
    mock_llm_client = MagicMock()
    mock_llm_client.chat.completions.create.return_value = fake_response

    # Patch SettingsManager.get_instance, token provider and AzureChatOpenAI
    monkeypatch.setattr("src.analysis.workers.langchain_worker.SettingsManager.get_instance", lambda: fake_settings)
    monkeypatch.setattr("src.analysis.workers.llm_worker.get_llm_client", lambda settings: mock_llm_client)

    @contextmanager
    def fake_get_session():
        yield SimpleNamespace()

    monkeypatch.setattr("src.analysis.workers.llm_worker.get_session", fake_get_session)

    class FakePromptTemplateRepository:
        def __init__(self, session):
            pass

        def get_last_version_by(self, **filters):
            return SimpleNamespace(id=0, template="Prompt: {{ contextText }}")

    monkeypatch.setattr("src.analysis.workers.llm_worker.PromptTemplateRepository", FakePromptTemplateRepository)

    worker = LLMWorker(
        config={
            "theme_id": 'theme1',
            "pattern_id": "not_fact"
        },
        save_results=False,
    )

    results = worker.analyze(
        text="ignored",
        experiment_id=experiment_id,
        section_id=3,
        analysis_job_id=44,
    )

    assert isinstance(results, list)
    assert len(results) == 1

    res = results[0]
    assert isinstance(res, AnalysisResult)
    assert res.content == "llm content"
    assert res.justification == "just"
    assert res.pattern_id == "not_fact"
    assert res.category_id == "cat1"
    assert res.self_confidence == pytest.approx(0.5)
    assert res.analysis_job_id == 44
    assert res.experiment_id == experiment_id

@pytest.mark.integration
def test_worker():
    # This test requires actual Azure AI Foundry settings to be set in environment variables
    init_session_manager()

    worker = LLMWorker(
        config={
            "theme_id": 'tst-theme-01',
            "pattern_id": "tst-pattern-01",
        },
        save_results=False,
    )

    test_text = "The quick brown fox jumps over the lazy dog."

    results = worker.analyze(
        text=test_text,
        experiment_id="TEST-EXP",
        section_id=11,
        analysis_job_id=22,
    )

    assert isinstance(results, list)
    assert len(results) > 0  # Expecting at least one result

    for res in results:
        assert isinstance(res, AnalysisResult)
        assert res.analysis_job_id == 22
        assert res.experiment_id == "TEST-EXP"
        assert res.pattern_id == "tst-pattern-01"
        assert isinstance(res.content, str)
        assert isinstance(res.justification, str)
        assert isinstance(res.category_id, str)
        assert 0.0 <= res.self_confidence <= 1.0