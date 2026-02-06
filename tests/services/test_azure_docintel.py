from pathlib import Path

import pytest

from src.config import SettingsManager
from src.services import get_docintel_client

@pytest.mark.skip(reason="Requires a local file")
@pytest.mark.integration
def test_begin_analyze_document():
    settings = SettingsManager.get_instance()
    with Path(settings.test.filepath).open("rb") as fp:
        doc_bytes = fp.read()
        
        client = get_docintel_client(settings)
        poller = client.begin_analyze_document(
            model_id="prebuilt-layout",
            analyze_request=doc_bytes,
            content_type="application/octet-stream",
        )
        result = poller.result()
        assert result is not None
        assert len(result.pages) > 0