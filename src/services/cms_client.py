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
        logger.info("CMS username: {}", self.username)
        logger.info("CMS password length: {}", len(self.password))


    async def authenticate(self) -> bool:
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
            response = requests.post(url, data=payload, headers=headers)
            response.raise_for_status()

            auth_data = response.json()
            self.cms_auth_values = json.dumps(auth_data)
            self.token = auth_data.get("Token")

            logger.info("Authentication successful")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            return False


    async def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        if not self.cms_auth_values:
            raise ValueError("Not authenticated. Call authenticate() first.")

        return {
            "Cms-Auth-Values": self.cms_auth_values,
            "x-functions-key": self.function_key,
            "Content-Type": "application/json",
        }

    async def get_urn_from_case_id(self, case_id: int) -> str | None:
        """Get URN from case ID."""

        url = f"{self.base_url}/cases/{case_id}/summary"
        headers = await self._get_headers()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            urn = data.get("urn", None)

            if urn:
                logger.info(f"Found URN: {urn}")
                return urn
            logger.warning("No URN found in response")
            logger.warning(f"Response data: {data}")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get URN: {e}")
            return None

    async def get_case_id_from_urn(self, urn: str) -> int | None:
        """Get case ID from URN."""
        url = f"{self.base_url}/urns/{urn}/case-identifiers"
        headers = await self._get_headers()

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
            logger.warning(f"Response data: {data}")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get case ID: {e}")
            return None

    async def get_case_summary(self, case_id: int) -> dict | None:
        """Check if a case is finalised."""
        url = f"{self.base_url}/cases/{case_id}/summary"
        headers = await self._get_headers()
        keys = ["urn", "finalised", "areaId", "unitId", "registrationDate"]

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            response_data = {key: data.get(key, None) for key in keys}

            logger.warning(f"Response data: {response_data}")
            return response_data

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get case finalised status: {e}")
            return None
    
    async def get_case_defendants(
            self,
            case_id: int,
            include_charges: bool = True,
        ) -> list | None:
        """Get defendants for a case ID."""

        url = f"{self.base_url}/cases/{case_id}/defendants"
        headers = await self._get_headers()
        
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
            logger.warning("No metadata found in response")
            logger.warning(f"Response data: {defendants}")
            return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get metadata: {e}")
            return None

    async def list_case_documents(self, case_id: int) -> list | None:
        """List all documents for a case."""
        url = f"{self.base_url}/cases/{case_id}/documents/cwa"
        headers = await self._get_headers()

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            documents = response.json()
            logger.info(f"Found {len(documents)} documents")

            return documents

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list documents: {e}")
            return None


    async def upload_document(
            self,
            case_id: int,
            document_type: int,
            content_type: str,
            file_name: str,
            file_content: bytes,
            file_subject: str,
            file_description: str,
        ) -> bool:
        """Upload a document directly via the API."""
        url = f"{self.base_url}/cases/{case_id}/document/{document_type}"
        headers = await self._get_headers()
        payload = {
            "documentType": "Mg3",
            "caseId": case_id,
            "contentType": content_type,
            "fileName": file_name,
            "fileContent": file_content,
            "fileSubject": file_subject,
            "fileDescription": file_description,
        }

        try:
            response = requests.post(url, data=payload, headers=headers)
            response.raise_for_status()

            logger.info(f"Document uploaded (Type: {document_type})")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload document: {e}")
            return False


    async def download_data(self, case_id: int, document_id: int, version_id: int) -> bytes:
        """Download a document directly from the API."""
        url = f"{self.base_url}/cases/{case_id}/documents/{document_id}/versions/{version_id}"
        headers = await self._get_headers()

        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()
        return response

    async def download_document(self, case_id: int, document_id: int, version_id: int, output_filename: str | None = None) -> bool:
        """Download a document directly from the API.

        Args:
            case_id: The case ID
            document_id: The document ID
            version_id: The version ID
            output_filename: Path to save the downloaded file (optional, will use Content-Disposition if not provided)

        Returns:
            bool: True if successful, False otherwise

        """
        url = f"{self.base_url}/cases/{case_id}/documents/{document_id}/versions/{version_id}"
        headers = await self._get_headers()

        try:
            response = requests.get(url, headers=headers, stream=True)
            response.raise_for_status()

            # If no filename provided, try to get it from Content-Disposition header
            if not output_filename:
                content_disp = response.headers.get("Content-Disposition", "")
                if "filename=" in content_disp:
                    parts = content_disp.split("filename=")
                    if len(parts) > 1:
                        filename = parts[1].split(";")[0].strip('"\'')
                        output_filename = filename
                    else:
                        output_filename = f"document_{document_id}.pdf"
                else:
                    output_filename = f"document_{document_id}.pdf"

            # Write the file
            with open(output_filename, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            content_type = response.headers.get("Content-Type", "unknown")
            logger.info(f"Document downloaded to: {output_filename} (Type: {content_type})")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download document: {e}")
            return False
