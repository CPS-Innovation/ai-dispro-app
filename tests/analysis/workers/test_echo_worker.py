import pytest

from src.analysis.workers import EchoWorker
from src.models import AnalysisResult


@pytest.mark.unit
def test_worker_returns_configured_result():
    config = {
        "content": "echo content",
        "justification": "because",
        "self_confidence": "0.42",
    }

    worker = EchoWorker(config=config, save_results=False)

    results = worker.analyze(
        text="ignored text",
        experiment_id="exp_1",
        section_id=1,
        analysis_job_id=123,
    )

    assert isinstance(results, list)
    assert len(results) == 1

    result = results[0]
    assert isinstance(result, AnalysisResult)
    assert result.content == "echo content"
    assert result.justification == "because"
    assert result.analysis_job_id == 123
    assert result.experiment_id == "exp_1"
    assert result.self_confidence == float("0.42")
