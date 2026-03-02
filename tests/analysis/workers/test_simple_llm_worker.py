import pytest
from textwrap import dedent
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.analysis.workers import SimpleLLMWorker
from src.models import AnalysisResult


@pytest.mark.unit
def test_worker_parses_model_response(monkeypatch):
    # Prepare fake settings with ai_foundry.deployment_name
    fake_settings = SimpleNamespace(ai_foundry=SimpleNamespace(deployment_name="test-deploy"))

    # Build response object
    response_json = '{"analysis_results":[{"content":"llm content","justification":"llm justification","categories":["catA"],"self_confidence":0.77}]}'
    message = SimpleNamespace(content=response_json)
    choice = SimpleNamespace(message=message)
    fake_response = SimpleNamespace(choices=[choice])

    # Create mock llm client with the right call chain
    mock_llm_client = MagicMock()
    mock_llm_client.chat.completions.create.return_value = fake_response

    # Patch get_settings and get_llm_client used in the module
    
    # Patch SettingsManager.get_instance, token provider and AzureChatOpenAI
    monkeypatch.setattr("src.analysis.workers.langchain_worker.SettingsManager.get_instance", lambda: fake_settings)
    monkeypatch.setattr("src.analysis.workers.simple_llm_worker.get_llm_client", lambda settings: mock_llm_client)

    worker = SimpleLLMWorker(
        config={"prompt_template": "Prompt: {{ contextText }}", "pattern_id": "TEST-PATTERN"},
        save_results=False,
    )

    results = worker.analyze(
        text="ignored",
        experiment_id="TEST-EXP",
        section_id=11,
        analysis_job_id=22,
    )

    assert isinstance(results, list)
    assert len(results) == 1

    res = results[0]
    assert isinstance(res, AnalysisResult)
    assert res.content == "llm content"
    assert res.justification == "llm justification"
    assert res.pattern_id == "TEST-PATTERN"
    assert res.category_id == "catA"
    assert res.self_confidence == pytest.approx(0.77)
    assert res.analysis_job_id == 22
    assert res.experiment_id == "TEST-EXP"

@pytest.mark.integration
def test_worker():
    # This test requires actual Azure AI Foundry settings to be set in environment variables
    prompt_template = dedent("""
        Classify the first word in the following text based on language:
        {{ contextText }}
        Return a JSON with {
            "analysis_results": [{
                "content": string the word,
                "justification": string, why this language was selected,
                "categories": [list of selected languages],
                "self_confidence": float (0.0-1.0)
            }]
    }""")
    worker = SimpleLLMWorker(
        config={
            "prompt_template": prompt_template,
            "theme_id": "TEST-THEME",
            "pattern_id": "TEST-PATTERN",
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
        assert res.pattern_id == "TEST-PATTERN"
        assert isinstance(res.content, str)
        assert isinstance(res.justification, str)
        assert isinstance(res.category_id, str)
        assert 0.0 <= res.self_confidence <= 1.0