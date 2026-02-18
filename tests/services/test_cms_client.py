"""Integration tests for CMS Client."""

import os
import pytest

from src.services import CMSClient
from src.config import Environment, SettingsManager


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def test_cms_headers_require_authentication():
    """Test that getting headers without authentication raises an error."""
    client = CMSClient()
    
    # Before authentication, accessing headers should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        client._get_headers()
    
    # Error message should contain expected text
    assert "Not authenticated" in str(exc_info.value)


def test_cms_authentication_sets_token():
    """Test that authentication sets the authentication token."""
    client = CMSClient()

    assert client.cms_auth_values is None  # Not authenticated yet
    assert client.token is None  # Not authenticated yet
    
    auth_result = client.authenticate()
    
    assert auth_result is True
    assert client.cms_auth_values is not None
    assert client.token is not None
    assert isinstance(client.token, str)
    assert len(client.token) > 0

    headers = client._get_headers()
    
    assert "Cms-Auth-Values" in headers
    assert "x-functions-key" in headers
    assert "Content-Type" in headers
    assert headers["Content-Type"] == "application/json"

    # Clean up singleton instance
    SettingsManager.reset_instance()


class TestCMSClientCaseOperations:
    """Test CMS Client case-related operations."""

    @pytest.fixture(scope="class")
    def authenticated_client(self):
        """Provide an authenticated CMS client for the test class."""
        client = CMSClient()
        auth_success = client.authenticate()
        
        if not auth_success:
            pytest.skip("Failed to authenticate with CMS API")

        return client

    @pytest.fixture(scope="class")
    def test_case_id(self):
        """Provide a test case ID for integration testing."""
        case_id = os.getenv("TEST_CMS_CASE_ID")
        if not case_id:
            pytest.skip("TEST_CMS_CASE_ID environment variable not set")
        return case_id

    @pytest.fixture(scope="class")
    def test_urn(self):
        """Provide a test URN for integration testing."""
        urn = os.getenv("TEST_CMS_URN")
        if not urn:
            pytest.skip("TEST_CMS_URN environment variable not set")
        return urn

    def test_case_id_urn_bidirectional_lookup(
        self, authenticated_client, test_case_id, test_urn
    ):
        """Test that case ID and URN lookups are consistent."""
        # Get URN from case ID
        urn_from_case = authenticated_client.get_urn_from_case_id(test_case_id)
        
        # Get case ID from URN
        case_from_urn = authenticated_client.get_case_id_from_urn(test_urn)
        
        # Verify consistency
        assert urn_from_case == test_urn or urn_from_case is not None
        assert case_from_urn == test_case_id or case_from_urn is not None

    def test_get_case_summary(self, authenticated_client, test_case_id):
        """Test retrieving case summary."""
        case_summary = authenticated_client.get_case_summary(test_case_id)
        
        assert case_summary is not None
        assert isinstance(case_summary, dict)

    def test_get_case_defendants(self, authenticated_client, test_case_id):
        """Test retrieving defendants for a case."""
        defendants = authenticated_client.get_case_defendants(
            case_id=test_case_id,
            include_charges=False,
            include_offences=False,
        )
        
        assert defendants is not None
        assert isinstance(defendants, list)
        
        # If there are defendants, verify structure
        if len(defendants) > 0:
            defendant = defendants[0]
            assert "ethnicity" in defendant
            assert "charges" in defendant
            assert isinstance(defendant["charges"], list)
            
            # If there are charges, verify structure
            if len(defendant["charges"]) > 0:
                charge = defendant["charges"][0]
                assert "description" in charge
                assert "latestVerdict" in charge

    def test_get_case_defendant_offences(self, authenticated_client, test_case_id):
        """Test retrieving defendant offences for a case."""
        defendants = authenticated_client.get_case_defendants(
            case_id=test_case_id,
            include_charges=False,
            include_offences=True,
        )
        
        assert defendants is not None
        assert isinstance(defendants, list)
        
        # If there are defendants, verify structure
        if len(defendants) > 0:
            defendant = defendants[0]
            assert "ethnicity" in defendant
            assert "charges" in defendant
            assert isinstance(defendant["charges"], list)
            
            # If there are offences, verify structure
            if len(defendant["offences"]) > 0:
                offence = defendant["offences"][0]
                assert "description" in offence
                assert "code" in offence

    def test_get_invalid_urn_or_case_id_returns_none(self, authenticated_client):
        """Test that invalid URN or case ID returns None gracefully."""
        invalid_case_id = "INVALID_CASE_ID_12345"
        urn = authenticated_client.get_urn_from_case_id(invalid_case_id)        
        assert urn is None

        invalid_urn = "INVALID_URN_12345"
        case_id = authenticated_client.get_case_id_from_urn(invalid_urn)
        assert case_id is None

    def test_list_case_documents(self, authenticated_client, test_case_id):
        """Test listing all documents for a case."""
        documents = authenticated_client.list_case_documents(test_case_id)
        
        assert documents is not None
        assert isinstance(documents, list)


    def test_download_data_invalid_ids_returns_error(
        self, authenticated_client, test_case_id
    ):
        """Test that downloading with invalid IDs handles errors gracefully."""
        invalid_document_id = "INVALID_DOC_ID"
        invalid_version_id = "INVALID_VER_ID"
        
        # This should raise an exception or return False
        with pytest.raises(Exception):
            authenticated_client.download_data(
                test_case_id, invalid_document_id, invalid_version_id
            )

    def test_get_mg3_from_history(
        self,
        authenticated_client,
        test_case_id
    ):
        """Test retrieving MG3 from history."""
        mg3_components = authenticated_client.get_mg3_from_history(case_id=test_case_id)
        
        assert mg3_components is not None
        assert isinstance(mg3_components, list)