import re
from typing import Any

from loguru import logger

SUPPORTED_CMS_DOC_CATEGORIES: list[str] = [
    "Review",
    "MGForm",
]
SUPPORTED_DOC_TYPES: list[str] = [
    "MG 3",
    "MG3",
    "MG3 (with Schedule of Charges)",
]
SUPPORTED_MIME_TYPES: list[str] = [
    "application/pdf", # .pdf
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
]

def is_document_supported(
        raw_doc_data: dict[str, Any],
    ) -> bool:
    """Check if document is supported based on category, type and mime type."""
    ans = False
    presentation_title = raw_doc_data.get("presentationTitle", "")
    original_file_name = raw_doc_data.get("originalFileName", "")
    if presentation_title is not None and re.search(r'M\s*G\s*3(?!\s*A)\b', presentation_title, re.IGNORECASE):
        ans = True  # accept by name
    elif original_file_name is not None and re.search(r'M\s*G\s*3(?!\s*A)\b', original_file_name, re.IGNORECASE):
        ans = True  # accept by name
    elif raw_doc_data["cmsDocCategory"] not in SUPPORTED_CMS_DOC_CATEGORIES:
        logger.debug(f"Skip {raw_doc_data['id']} '{presentation_title}'. Reason: unsupported category {raw_doc_data['cmsDocCategory']}")
        ans = False 
    elif raw_doc_data["type"] not in SUPPORTED_DOC_TYPES:
        logger.debug(f"Skip {raw_doc_data['id']} '{presentation_title}'. Reason: unsupported type {raw_doc_data.get('type')}")
        ans = False
    
    # only PDF and DOCX are supported
    if raw_doc_data["mimeType"] not in SUPPORTED_MIME_TYPES:
        logger.debug(f"Skip {raw_doc_data['id']} '{presentation_title}'. Reason: unsupported mime type {raw_doc_data.get('mimeType')}")
        ans = False
    
    return ans
