import pytest
from unittest.mock import patch, MagicMock
from azure.core.exceptions import ResourceNotFoundError

from src.services import get_secret
from src.config import SettingsManager


@pytest.mark.integration
def test_get_secret():
    settings = SettingsManager.get_instance()
    value = get_secret(settings.cms.username_secret_name)
    assert isinstance(value, str)

@pytest.mark.unit
class TestGetSecret:
    """Tests for get_secret function."""

    @pytest.mark.unit
    @pytest.mark.parametrize("secret_name, secret_value", [
        ("test-secret", "my-secret-value"),
        ("  test-secret-with-whitespace  ", "my-secret-value"),
        ("complex-secret", "special!@#$%^&*()_+-=[]{}|;':,.<>?secret"),
        ("empty-secret", "")
    ])
    @patch("src.services.azure_key_vault.get_credentials")
    def test_get_secret_success(self, mock_get_creds, secret_name, secret_value):
        """Test successful secret retrieval from Key Vault."""
        # Setup mocks
        mock_settings = MagicMock()
        mock_settings.azure.key_vault_url = "https://test-vault.vault.azure.net/"
        
        mock_credential = MagicMock()
        mock_get_creds.return_value = mock_credential
        
        mock_secret_value = secret_value
        mock_secret = MagicMock()
        mock_secret.value = mock_secret_value
        
        with patch(
            "src.services.azure_key_vault.SecretClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_secret.return_value = mock_secret
            
            result = get_secret(
                secret_name=secret_name, settings=mock_settings)
            
            assert result == mock_secret_value
            mock_client_class.assert_called_once_with(
                vault_url="https://test-vault.vault.azure.net/",
                credential=mock_credential,
            )
            mock_client.get_secret.assert_called_once_with(secret_name)
            mock_get_creds.assert_called_once()

    @patch("src.services.azure_key_vault.get_credentials")
    def test_get_secret_not_found(self, mock_get_creds):
        """Test that ResourceNotFoundError is re-raised when secret doesn't exist."""
        mock_settings = MagicMock()
        mock_settings.azure.key_vault_url = "https://test-vault.vault.azure.net/"
        
        mock_credential = MagicMock()
        mock_get_creds.return_value = mock_credential
        
        with patch(
            "src.services.azure_key_vault.SecretClient"
        ) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_client.get_secret.side_effect = ResourceNotFoundError(
                "Secret not found"
            )
            
            with pytest.raises(ResourceNotFoundError):
                get_secret(secret_name="non-existent-secret", settings=mock_settings)
