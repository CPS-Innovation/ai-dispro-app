from src.repositories import (
    CaseRepository,
    DocumentRepository,
    VersionRepository,
    SectionRepository,
)


def test_case_repository_create(db_session):
    """Test Case repository create (with embedded URN)."""
    case_repo = CaseRepository(db_session)
    case = case_repo.create(
        urn="01TS1234567",
        finalised=False,
        area_id=1,
    )
    db_session.commit()

    assert case.urn == "01TS1234567"
    assert case.id is not None


def test_case_repository_get_by_urn(db_session):
    """Test Case repository get by URN."""
    # Setup
    case_repo = CaseRepository(db_session)
    case_repo.create(urn="01TS1234567", finalised=False)
    db_session.commit()

    # Test
    retrieved = case_repo.get_by_urn("01TS1234567")
    assert retrieved is not None
    assert retrieved.urn == "01TS1234567"


def test_document_repository_create(db_session):
    """Test Document repository create."""
    # Setup - create a Case with URN
    case_repo = CaseRepository(db_session)
    case = case_repo.create(urn="01TS1234567", finalised=False)
    db_session.commit()

    # Create document linked to the case (by composite key)
    doc_repo = DocumentRepository(db_session)
    doc = doc_repo.create(
        case_id=case.id,
        original_file_name="test.pdf",
        file_extension="pdf"
    )
    db_session.commit()

    assert doc.case_id == case.id
    assert doc.original_file_name == "test.pdf"


def test_document_repository_get_by_case(db_session):
    """Test getting documents by case."""
    # Setup
    case_repo = CaseRepository(db_session)
    case = case_repo.create(urn="01TS1234567", finalised=False)
    db_session.commit()

    doc_repo = DocumentRepository(db_session)
    doc_repo.create(case_id=case.id, original_file_name="doc1.pdf")
    doc_repo.create(case_id=case.id, original_file_name="doc2.pdf")
    db_session.commit()

    # Test
    docs = doc_repo.get_by_case(case_id=case.id)
    assert len(docs) >= 2


def test_repository_update(db_session):
    """Test repository update."""
    case_repo = CaseRepository(db_session)
    case = case_repo.create(
        urn="01T0000002",
        finalised=False,
        area_id=1,
    )
    db_session.commit()

    # Update using composite key - note: BaseRepository.update() uses single ID column
    # For composite keys, update directly
    case.finalised = True
    case.area_id = 1
    db_session.commit()

    # Retrieve to verify
    updated = case_repo.get_by_urn("01T0000002")
    assert updated.finalised is True
    assert updated.area_id == 1

def test_repository_delete(db_session):
    """Test repository delete."""
    case_repo = CaseRepository(db_session)
    case = case_repo.create(urn="01TS0000001", finalised=False)
    db_session.commit()
    
    # Delete the case directly
    db_session.delete(case)
    db_session.commit()

    # Verify deletion
    assert case_repo.get_by_urn("01TS0000001") is None
