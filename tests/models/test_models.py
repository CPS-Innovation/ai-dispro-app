import pytest
from datetime import datetime, date

from src.models import (
    Case,
    Defendant,
    Charge,
    Document,
    Version,
    Experiment,
    Section,
    AnalysisJob,
    AnalysisResult,
)


@pytest.mark.integration
def test_create_case(db_session):
    """Test Case creation linked to URN."""

    # Verify critical attributes
    assert hasattr(Case, '__tablename__')
    assert hasattr(Case, 'urn')
    assert hasattr(Case, 'id')
    assert hasattr(Case, 'finalised')

    # Create Case
    case = Case(
        urn="01TS0000001",
        finalised=False,
        area_id=1,
        unit_id=1,
        registration_date=date(2024, 1, 1),
    )
    db_session.add(case)
    db_session.commit()

    # Verify
    retrieved = db_session.query(Case).filter_by(urn="01TS0000001").first()
    assert retrieved is not None
    assert retrieved.finalised is False
    assert retrieved.area_id == 1
    assert retrieved.unit_id == 1
    assert retrieved.urn == "01TS0000001"
    
    # Clean up
    db_session.delete(retrieved)
    db_session.commit()


@pytest.mark.integration
def test_create_defendant(db_session):
    """Test Defendant creation."""

    # Verify critical attributes
    assert hasattr(Defendant, '__tablename__')
    assert hasattr(Defendant, 'id')
    assert hasattr(Defendant, 'case_id')
    
    # Create Case
    case = Case(urn="01TS0000002", finalised=False)
    db_session.add(case)
    db_session.commit()

    # Create Defendant
    defendant = Defendant(
        case_id=case.id,
        dob=date(1990, 1, 1),
        gender="Male",
        ethnicity="White",
    )
    db_session.add(defendant)
    db_session.commit()

    # Verify
    retrieved = db_session.query(Defendant).filter_by(case_id=case.id).first()
    assert retrieved is not None
    assert retrieved.gender == "Male"
    assert retrieved.case.urn == "01TS0000002"
    
    # Clean up
    for item in [retrieved, case]:
        db_session.delete(item)
    db_session.commit()


@pytest.mark.integration
def test_create_charge(db_session):
    """Test Charge creation."""
    # Create Case, and Defendant
    case = Case(urn="01TS0000003", finalised=False)
    db_session.add(case)
    db_session.commit()
    defendant = Defendant(case_id=case.id)
    db_session.add(defendant)
    db_session.commit()

    # Create Charge
    charge = Charge(
        defendant_id=defendant.id,
        description="Theft",
        latest_verdict=datetime(2024, 6, 1),
    )
    db_session.add(charge)
    db_session.commit()

    # Verify
    retrieved = db_session.query(Charge).filter_by(defendant_id=defendant.id).first()
    assert retrieved is not None
    assert retrieved.description == "Theft"
    assert retrieved.defendant.case.urn == "01TS0000003"
    
    # Clean up
    for item in [retrieved, charge, defendant, case]:
        db_session.delete(item)
    db_session.commit()


@pytest.mark.integration
def test_create_document(db_session):
    """Test Document creation."""

    # Verify critical attributes
    assert hasattr(Document, '__tablename__')
    assert hasattr(Document, 'id')
    assert hasattr(Document, 'case_id')

    # Create Case
    case = Case(urn="01TS0000004", finalised=False)
    db_session.add(case)
    db_session.commit()

    # Create Document
    document = Document(
        case_id=case.id,
        original_file_name="test_empty.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
    )
    db_session.add(document)
    db_session.commit()

    # Verify
    retrieved = db_session.query(Document).filter_by(case_id=case.id).first()
    assert retrieved is not None
    assert retrieved.original_file_name == "test_empty.pdf"
    assert retrieved.case.urn == "01TS0000004"
    
    # Clean up
    for item in [retrieved, document, case]:
        db_session.delete(item)
    db_session.commit()


@pytest.mark.integration
def test_create_version(db_session):
    """Test Version creation."""
    # Create URN, Case, and Document
    case = Case(urn="01TS0000005", finalised=False)
    db_session.add(case)
    db_session.commit()
    document = Document(case_id=case.id, original_file_name="test.pdf")
    db_session.add(document)
    db_session.commit()

    # Create Version
    version = Version(document_id=document.id)
    db_session.add(version)
    db_session.commit()

    # Verify
    retrieved = db_session.query(Version).filter_by(document_id=document.id).first()
    assert retrieved is not None

    # Clean up
    for item in [retrieved, version, document, case]:
        db_session.delete(item)
    db_session.commit()


@pytest.mark.integration
def test_create_experiment(db_session):
    """Test Experiment creation."""
    # Create Experiment
    experiment = Experiment()
    db_session.add(experiment)
    db_session.commit()

    # Verify
    retrieved = db_session.query(Experiment).filter_by(id=experiment.id).first()
    assert retrieved is not None
    assert retrieved.id == experiment.id

    # Clean up
    db_session.delete(retrieved)
    db_session.commit()


@pytest.mark.integration
def test_create_section(db_session):
    """Test Section creation."""
    # Create full hierarchy
    case = Case(urn="01TS0000006", finalised=False)
    db_session.add(case)
    db_session.commit()
    document = Document(case_id=case.id, original_file_name="test.pdf")
    db_session.add(document)
    db_session.commit()
    version = Version(document_id=document.id)
    db_session.add(version)
    db_session.commit()
    experiment = Experiment()
    db_session.add(experiment)
    db_session.commit()

    # Create Section
    section = Section(
        version_id=version.id, experiment_id=experiment.id, redacted_content="Section content"
    )
    db_session.add(section)
    db_session.commit()

    # Verify
    retrieved = db_session.query(Section).filter_by(version_id=version.id).first()
    assert retrieved is not None
    assert retrieved.redacted_content == "Section content"
    assert retrieved.version_id == version.id
    assert retrieved.experiment_id == experiment.id

    # Clean up
    for item in [retrieved, section, experiment, version, document, case]:
        db_session.delete(item)
    db_session.commit()


@pytest.mark.integration
def test_create_analysis_job(db_session):
    """Test AnalysisJob creation."""
    # Create full hierarchy
    case = Case(urn="01TS0000007", finalised=False)
    db_session.add(case)
    db_session.commit()
    document = Document(case_id=case.id, original_file_name="test.pdf")
    db_session.add(document)
    db_session.commit()
    version = Version(document_id=document.id)
    db_session.add(version)
    db_session.commit()
    experiment = Experiment()
    db_session.add(experiment)
    db_session.commit()
    section = Section(version_id=version.id, experiment_id=experiment.id, redacted_content="Content")
    db_session.add(section)
    db_session.commit()

    # Create AnalysisJob
    job = AnalysisJob(section_id=section.id, experiment_id=experiment.id)
    db_session.add(job)
    db_session.commit()

    # Verify
    retrieved = db_session.query(AnalysisJob).filter_by(section_id=section.id).first()
    assert retrieved is not None
    assert retrieved.experiment_id == experiment.id

    # Clean up
    for item in [retrieved, job, section, experiment, version, document, case]:
        db_session.delete(item)
    db_session.commit()


@pytest.mark.integration
def test_create_analysis_result(db_session):
    """Test AnalysisResult creation."""
    # Create full hierarchy
    case = Case(urn="01TS0000008", finalised=False)
    db_session.add(case)
    db_session.commit()
    document = Document(case_id=case.id, original_file_name="test.pdf")
    db_session.add(document)
    db_session.commit()
    version = Version(document_id=document.id)
    db_session.add(version)
    db_session.commit()
    experiment = Experiment()
    db_session.add(experiment)
    db_session.commit()
    section = Section(version_id=version.id, experiment_id=experiment.id, redacted_content="Content")
    db_session.add(section)
    db_session.commit()
    analysis_job = AnalysisJob(section_id=section.id, experiment_id=experiment.id)
    db_session.add(analysis_job)
    db_session.commit()

    # Create Result
    result = AnalysisResult(
        analysis_job_id=analysis_job.id,
        experiment_id=experiment.id,
        content="Analysis result content",
        justification="Because reasons",
    )
    db_session.add(result)
    db_session.commit()

    # Verify
    retrieved = (
        db_session.query(AnalysisResult).filter_by(analysis_job_id=analysis_job.id).first()
    )
    assert retrieved is not None
    assert retrieved.analysis_job_id == analysis_job.id
    assert retrieved.experiment_id == experiment.id
    assert retrieved.content == "Analysis result content"
    assert retrieved.justification == "Because reasons"

    # Clean up
    for item in [retrieved, analysis_job, section, experiment, version, document, case]:
        db_session.delete(item)
    db_session.commit()


@pytest.mark.integration
def test_cascade_delete_case(db_session):
    """Test that deleting a case cascades to defendants and documents."""
    # Create full structure
    case = Case(urn="01TS0000009", finalised=False)
    db_session.add(case)
    db_session.commit()
    defendant = Defendant(case_id=case.id)
    db_session.add(defendant)
    db_session.commit()
    document = Document(case_id=case.id, original_file_name="test.pdf")
    db_session.add(document)
    db_session.commit()

    case_id = case.id
    defendant_id = defendant.id
    document_id = document.id

    # Delete case
    db_session.delete(case)
    db_session.commit()

    # Verify cascaded deletes
    assert db_session.query(Case).filter_by(id=case_id).first() is None
    assert db_session.query(Defendant).filter_by(id=defendant_id).first() is None
    assert db_session.query(Document).filter_by(id=document_id).first() is None
