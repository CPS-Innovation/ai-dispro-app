from src.config import SettingsManager

from src.repositories import (
    CaseRepository,
    DocumentRepository,
    PromptTemplateRepository,
    EventRepository,
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

def test_prompt_template_repository_create(db_session):
    """Test PromptTemplate repository create."""
    repo = PromptTemplateRepository(db_session)
    settings = SettingsManager.get_instance()
    pt = repo.create(
        template="Hello {name}",
        agent="test_agent",
        theme=settings.test.theme,
        pattern=settings.test.pattern,
        version=0.1,
    )
    db_session.commit()

    assert pt.template == "Hello {name}"
    assert pt.version == 0.1
    assert pt.id is not None

    retrieved = repo.get_by_id(pt.id)
    assert retrieved is not None
    assert retrieved.template == "Hello {name}"
    assert retrieved.id == pt.id

    # Delete the template
    db_session.delete(pt)
    db_session.commit()


def test_prompt_template_repository_upsert(db_session):
    """Test PromptTemplate repository upsert."""
    repo = PromptTemplateRepository(db_session)
    settings = SettingsManager.get_instance()
    
    # First upsert - should create
    pt1 = repo.upsert_by(
        template="Original template",
        theme=settings.test.theme,
        pattern=settings.test.pattern,
        agent="test_agent",
        version=0.1,
    )
    db_session.commit()
    id1 = pt1.id

    # Second upsert with same unique fields - should update
    pt2 = repo.upsert_by(
        template="Updated template",
        theme=settings.test.theme,
        pattern=settings.test.pattern,
        agent="test_agent",
        version=0.1,
    )
    db_session.commit()

    assert pt2.id == id1
    assert pt2.template == "Updated template"

    # Cleanup
    db_session.delete(pt2)
    db_session.commit()


def test_event_repository_log(db_session):
    """Test Event repository log."""
    repo = EventRepository(db_session)
    event = repo.log(
        event_type="test",
        actor_id="0",
        action="test",
        object_type="test",
        object_id="0",
    )
    db_session.commit()

    assert event.id is not None
    assert event.event_type == "test"
    assert event.actor_id == "0"
    assert event.action == "test"
    assert event.object_type == "test"
    assert event.object_id == "0"

    # Cleanup
    db_session.delete(event)
    db_session.commit()