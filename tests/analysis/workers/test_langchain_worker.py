import pytest
from types import SimpleNamespace
from contextlib import contextmanager

from src.analysis.workers import LangchainWorker
from src.models import AnalysisResult


@pytest.mark.unit
def test_worker_parses_model_response(monkeypatch):
    # Fake settings
    fake_settings = SimpleNamespace(ai_foundry=SimpleNamespace(endpoint="ep", deployment_name="dep", api_version="v"))

    # Fake prompt template returned by repository
    fake_prompt_template = SimpleNamespace(template="Prompt: {{ contextText }}")

    # Fake model JSON response
    response_json = '{"analysis_results":[{"content":"lc content","justification":"llm just","categories":["catX"],"self_confidence":0.33}]}'

    # Fake AzureChatOpenAI replacement
    class FakeAzureChatOpenAI:
        def __init__(self, *args, **kwargs):
            pass

        def invoke(self, messages):
            return SimpleNamespace(content=response_json)

    # Patch SettingsManager.get_instance, token provider and AzureChatOpenAI
    monkeypatch.setattr("src.analysis.workers.langchain_worker.SettingsManager.get_instance", lambda: fake_settings)
    monkeypatch.setattr("src.analysis.workers.langchain_worker.get_token_provider", lambda scopes=None: "token")
    monkeypatch.setattr("src.analysis.workers.langchain_worker.AzureChatOpenAI", FakeAzureChatOpenAI)

    # Patch get_session to a context manager that yields a dummy session
    @contextmanager
    def fake_get_session():
        yield SimpleNamespace()

    monkeypatch.setattr("src.analysis.workers.langchain_worker.get_session", fake_get_session)

    # Patch PromptTemplateRepository to return our fake template
    class FakePromptTemplateRepository:
        def __init__(self, session):
            pass

        def get_by_id(self, _id):
            return fake_prompt_template

    monkeypatch.setattr("src.analysis.workers.langchain_worker.PromptTemplateRepository", FakePromptTemplateRepository)

    # Instantiate worker with prompt_template_id that will be looked up
    worker = LangchainWorker(
        config={
            "prompt_template_id": 1,
            "theme_id": "TST-THEME-1",
            "pattern_id": "TST-PATTERN-1",
        },
        save_results=False,
    )

    results = worker.analyze(
        text="ignored text",
        experiment_id="EXP-1",
        section_id=7,
        analysis_job_id=55,
    )

    assert isinstance(results, list)
    assert len(results) == 1

    res = results[0]
    assert isinstance(res, AnalysisResult)
    assert res.content == "lc content"
    assert res.justification == "llm just"
    assert res.theme_id == "TST-THEME-1"
    assert res.pattern_id == "TST-PATTERN-1"
    assert res.category_id == "catX"
    assert res.self_confidence == pytest.approx(0.33)
    assert res.analysis_job_id == 55
    assert res.experiment_id == "EXP-1"
