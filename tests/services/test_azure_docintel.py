from pathlib import Path

import pytest

from src.config import SettingsManager
from src.services import get_docintel_client
from src.services.azure_docintel import minimal_pdf


@pytest.mark.integration
def test_begin_analyze_document():
    settings = SettingsManager.get_instance()
    with Path(Path(__file__).parent.parent / "test_empty.pdf").open("rb") as fp:
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


@pytest.mark.integration
def test_begin_analyze_document_with_bytes():
    settings = SettingsManager.get_instance()
    doc_bytes = minimal_pdf()
    
    client = get_docintel_client(settings)
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        analyze_request=doc_bytes,
        content_type="application/octet-stream",
    )
    result = poller.result()
    assert result is not None
    assert len(result.pages) > 0
