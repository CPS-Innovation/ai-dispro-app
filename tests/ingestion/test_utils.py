import pytest

from src.ingestion.utils import is_document_supported


@pytest.mark.unit
@pytest.mark.parametrize("raw_doc_data, expected", [
    ({
            "id": "MG3.pdf",
            "presentationTitle": "MG3",
            "originalFileName": "MG3.pdf",
            "cmsDocCategory": "MGForm",
            "type": "MG3",
            "mimeType": "application/pdf",
    }, True),
    ({
            "id": "MG3.docx",
            "presentationTitle": "MG3",
            "originalFileName": "MG3.docx",
            "cmsDocCategory": "MGForm",
            "type": "MG3",
            "mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }, True),
    ({
            "id": "MGForm",
            "presentationTitle": "MG3",
            "originalFileName": "MG3.pdf",
            "cmsDocCategory": "MGForm",
            "type": "MG 3",
            "mimeType": "application/pdf",
    }, True),
    ({
            "id": "MG3 (with Schedule of Charges)",
            "presentationTitle": "MG3",
            "originalFileName": "MG3.pdf",
            "cmsDocCategory": "MGForm",
            "type": "MG3 (with Schedule of Charges)",
            "mimeType": "application/pdf",
    }, True),
    ({
            "id": "Review",
            "presentationTitle": "MG3",
            "originalFileName": "MG3.pdf",
            "cmsDocCategory": "Review",
            "type": "MG3",
            "mimeType": "application/pdf",
    }, True),
    ({
            "id": "ERR - Unsupported category",
            "presentationTitle": "foo",
            "originalFileName": "foo.pdf",
            "cmsDocCategory": "ERR",
            "type": "MG3",
            "mimeType": "application/pdf",
    }, False),
    ({
            "id": "ERR - Unsupported type",
            "presentationTitle": "foo",
            "originalFileName": "foo.pdf",
            "cmsDocCategory": "MGForm",
            "type": "ERR",
            "mimeType": "application/pdf",
    }, False),
    ({
            "id": "ERR - Unsupported MIME type",
            "presentationTitle": "foo",
            "originalFileName": "foo.txt",
            "cmsDocCategory": "MGForm",
            "type": "MG3",
            "mimeType": "ERR",
    }, False),
])
def test_supported_cms_doc_categories_filter(raw_doc_data, expected):
    """Test that only supported CMS doc categories are processed."""

    assert is_document_supported(raw_doc_data=raw_doc_data) == expected
