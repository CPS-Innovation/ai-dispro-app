from __future__ import annotations

import json
from typing import Dict

from loguru import logger
import requests

from .azure_key_vault import get_secret
from ..config import SettingsManager


class CMSClient:
    """Client for interacting with DDEI API endpoints."""

    def __init__(self) -> None:
        """Initialize the instance."""
        self.settings = SettingsManager.get_instance()

        self.function_key = get_secret(self.settings.cms.api_key_secret_name)
        self.username = get_secret(self.settings.cms.username_secret_name)
        self.password = get_secret(self.settings.cms.password_secret_name)
            
        self.base_url = self.settings.cms.endpoint.rstrip("/")
        self.cms_auth_values = None
        self.token = None
        # Log the configuration
        logger.info(f"CMS base url: {self.base_url}")
        logger.info("CMS function key length: {}", len(self.function_key))
        logger.info("CMS username length: {}", len(self.username))
        logger.info("CMS password length: {}", len(self.password))


    def authenticate(self) -> bool:
        """Authenticate with the API and store auth values.

        Returns:
            bool: True if authentication successful, False otherwise

        """
        url = f"{self.base_url}/authenticate"
        headers = {
            "x-functions-key": self.function_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept":  "application/json",
        }
        payload = {
            "username": self.username,
            "password": self.password,
        }

        try:
            response = requests.post(
                url,
                data=payload,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()

            auth_data = response.json()
            self.cms_auth_values = json.dumps(auth_data)
            self.token = auth_data.get("Token")

            logger.info("Authentication successful")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            return False


    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        if not self.cms_auth_values:
            raise ValueError("Not authenticated. Call authenticate() first.")

        return {
            "Cms-Auth-Values": self.cms_auth_values,
            "x-functions-key": self.function_key,
            "Content-Type": "application/json",
        }

    def get_urn_from_case_id(self, case_id: int) -> str | None:
        """Get URN from case ID."""

        url = f"{self.base_url}/cases/{case_id}/summary"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            urn = data.get("urn", None)

            if urn:
                logger.info(f"Found URN: {urn}")
                return urn
            logger.warning("No URN found in response")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get URN: {e}")
            return None

    def get_case_id_from_urn(self, urn: str) -> int | None:
        """Get case ID from URN."""
        url = f"{self.base_url}/urns/{urn}/case-identifiers"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            if len(data) > 0:
                case_id = data[0].get("id") if isinstance(data[0], dict) else None
            else:
                case_id = None

            if case_id:
                logger.info(f"Found case ID: {case_id}")
                return case_id
            logger.warning("No case ID found in response")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get case ID: {e}")
            return None

    def get_case_summary(self, case_id: int) -> dict | None:
        """Get case summary information for a given case ID."""
        url = f"{self.base_url}/cases/{case_id}/summary"
        headers = self._get_headers()
        keys = ["urn", "finalised", "areaId", "unitId", "registrationDate"]

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            response_data = {key: data.get(key, None) for key in keys}
            return response_data

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get case finalised status: {e}")
            return None
    
    def get_case_defendants(
            self,
            case_id: int,
            include_charges: bool = True,
        ) -> list | None:
        """Get defendants for a case ID."""

        url = f"{self.base_url}/cases/{case_id}/defendants"
        headers = self._get_headers()
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            defendants = response.json()

            if defendants:
                ans = []
                for defendant in defendants:
                    defendant_data = {
                        "id": defendant.get("id"),
                        "case_id": case_id,
                        "dob": defendant.get("dob", None),
                        "ethnicity": defendant.get("personalDetail", {}).get("ethnicity", None),
                        "gender": defendant.get("personalDetail", {}).get("gender", None),
                        "charges": []
                    }
                    if not include_charges:
                        ans.append(defendant_data)
                        continue
                    charges = defendant.get("charges", None)
                    if charges is None or len(charges) == 0:
                        charges = defendant.get("proposedCharges", None)
                    for charge in charges or []:
                        charge_data = {
                            "id": charge.get("id"),
                            "defendant_id": defendant.get("id"),
                            "code": charge.get("code"),
                            "description": charge.get("description"),
                            "latest_verdict": charge.get("latestVerdict", None),
                        }
                        defendant_data["charges"].append(charge_data)
                    ans.append(defendant_data)
                logger.info(f"Found metadata for case ID: {case_id}")
                return ans
            logger.warning("No defendants found in response")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get metadata: {e}")
            return None

    def list_case_documents(self, case_id: int) -> list | None:
        """List all documents for a case."""
        url = f"{self.base_url}/cases/{case_id}/documents/cwa"
        headers = self._get_headers()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            documents = response.json()
            logger.info(f"Found {len(documents)} documents")

            return documents

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list documents: {e}")
            return None

    def download_data(self, case_id: int, document_id: int, version_id: int) -> requests.Response:
        """Download a document directly from the API."""
        url = f"{self.base_url}/cases/{case_id}/documents/{document_id}/versions/{version_id}"
        headers = self._get_headers()

        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        return response
