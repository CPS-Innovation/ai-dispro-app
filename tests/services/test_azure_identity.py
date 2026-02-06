"""Unit tests for Azure identity credential management.

Tests cover:
- Credential initialization
- Credential caching via LRU cache
- Proper configuration of allowed authentication sources
"""

import pytest
from unittest.mock import patch, MagicMock
from azure.identity import DefaultAzureCredential

from src.services.azure_identity import get_credentials


class TestGetCredentials:
    """Tests for get_credentials function."""

    @pytest.mark.unit
    def test_get_credentials_caching(self):
        """Test that credentials are cached via LRU cache."""
        # Clear the cache first
        get_credentials.cache_clear()
        
        with patch(
            "src.services.azure_identity.DefaultAzureCredential"
        ) as mock_credential_class:
            mock_instance = MagicMock(spec=DefaultAzureCredential)
            mock_credential_class.return_value = mock_instance
            
            # Get initial cache info
            initial_info = get_credentials.cache_info()
            assert initial_info.hits == 0
            assert initial_info.misses == 0

            # First call (cache miss)
            result1 = get_credentials()
            assert result1 is mock_instance
            info1 = get_credentials.cache_info()
            assert info1.misses == 1

            # Second call (cache hit)
            result2 = get_credentials()
            assert result2 is mock_instance
            info2 = get_credentials.cache_info()
            assert info2.hits == 1
            assert info2.misses == 1

            # Verify it was called with correct configuration
            call_kwargs = mock_credential_class.call_args[1]
            
            # Should allow CLI and managed identity
            for key in ["exclude_cli_credential", "exclude_managed_identity_credential"]:
                assert call_kwargs[key] is False

            # Should return the same instance
            assert result1 is result2
            # Should only be called once (cached)
            mock_credential_class.assert_called_once()

    def test_get_credentials_cache_clear(self):
        """Test that cache can be cleared properly."""
        get_credentials.cache_clear()
        
        with patch(
            "src.services.azure_identity.DefaultAzureCredential"
        ) as mock_credential_class:
            mock_instance1 = MagicMock(spec=DefaultAzureCredential)
            mock_instance2 = MagicMock(spec=DefaultAzureCredential)
            mock_credential_class.side_effect = [mock_instance1, mock_instance2]
            
            # First call
            result1 = get_credentials()
            assert result1 is mock_instance1
            
            # Clear cache
            get_credentials.cache_clear()
            
            # Second call should create a new instance
            result2 = get_credentials()
            assert result2 is mock_instance2
            assert result1 is not result2
            assert mock_credential_class.call_count == 2

    def test_get_credentials_thread_safety(self):
        """Test that cached credentials work in multi-threaded scenarios."""
        import threading
        
        get_credentials.cache_clear()
        
        with patch(
            "src.services.azure_identity.DefaultAzureCredential"
        ) as mock_credential_class:
            mock_instance = MagicMock(spec=DefaultAzureCredential)
            mock_credential_class.return_value = mock_instance
            
            results = []
            
            def call_get_credentials():
                results.append(get_credentials())
            
            threads = [threading.Thread(target=call_get_credentials) for _ in range(5)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            
            # All threads should get the same cached instance
            assert all(r is mock_instance for r in results)
            assert len(results) == 5
            
            # Check cache stats after threaded calls
            # Should have 1 miss (first call) and 4 hits (remaining 4 threads)
            info1 = get_credentials.cache_info()
            assert info1.misses == 1
            assert info1.hits == 4
   
            # Call again (another cache hit)
            get_credentials()
            info2 = get_credentials.cache_info()
            assert info2.misses == 1
            assert info2.hits == 5


    def teardown_method(self):
        """Clean up cache after each test."""
        get_credentials.cache_clear()
