import pytest

from src.config import SettingsManager
from src.services import get_llm_client

@pytest.mark.integration
def test_chat_completions_create():
    settings = SettingsManager.get_instance()
    client = get_llm_client(settings)
    response = client.chat.completions.create(
        model=settings.ai_foundry.deployment_name,
        messages=[{"role": "user", "content": "1 + two + tree = ? Be concise."}],
        temperature=0.0,
    )
    answer = response.choices[-1].message.content
    assert "6" in answer