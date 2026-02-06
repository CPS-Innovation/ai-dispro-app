import pytest

from src.config import SettingsManager
from src.services import get_blob_service_client


@pytest.mark.integration
def test_list_containers():
    settings = SettingsManager.get_instance()
    client = get_blob_service_client(settings)
    containers = client.list_containers()
    containers = list(containers)
    assert len(containers) > 0