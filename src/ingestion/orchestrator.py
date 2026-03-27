import json
import uuid
from datetime import datetime, timezone
from typing import Any
from pathlib import Path
from contextlib import contextmanager

from tenacity import retry, stop_after_attempt, wait_fixed
from loguru import logger

from azure.ai.documentintelligence import (  # type: ignore[import]
    AnalyzeDocumentLROPoller,
    DocumentIntelligenceClient,
)

from azure.ai.documentintelligence.models import AnalyzeResult  # type: ignore[import]

from ..config import SettingsManager
from ..database import get_session
from ..repositories import (
    CaseRepository,
    DefendantRepository,
    ChargeRepository,
    OffenceRepository,
    DocumentRepository,
    VersionRepository,
    EventRepository,
)
from ..models import (
    Case,
    Defendant,
    Document,
    Version,
)
from ..services import (
    CMSClient,
    get_docintel_client,
    load_blob,
    save_blob,
)
from .models import IngestionResult, TriggerType
from .utils import is_document_supported

class IngestionOrchestrator:
    """Orchestrates the ingestion pipeline."""


    settings: SettingsManager
    event_repo: EventRepository | None
    correlation_id: str | None
    doc_intel: DocumentIntelligenceClient | None

    def __init__(
            self,
            event_repo: EventRepository | None = None,
            correlation_id: str | None = None,
        ) -> None:
        """Initialize ingestion orchestrator with service dependencies."""
        self.settings = SettingsManager.get_instance()
        self.event_repo = event_repo
        self.correlation_id = correlation_id
        self.doc_intel = get_docintel_client()
        logger.info("Ingestion orchestrator initialized")

    async def ingest(
            self, 
            trigger_type: TriggerType,
            value: str | list[str],
            experiment_id: str | None = None,
        ) -> IngestionResult:
        """Execute complete ingestion pipeline."""
        logger.info(f"Starting ingestion: trigger_type={trigger_type}, value={value}, experiment_id={experiment_id}")
        
        # Route to appropriate handler based on trigger type
        if trigger_type == TriggerType.URN:
            cms_client = CMSClient()
            
            with self._log_step(
                action="mds_auth_request",
                object_type="mds",
                experiment_id=experiment_id,
            ):
                if not cms_client.authenticate():
                    logger.error("MDS authentication failed")
                    raise Exception("MDS authentication failed")
            return await self._ingest_from_urn(urn=value, cms_client=cms_client, experiment_id=experiment_id)
        elif trigger_type == TriggerType.BLOB_NAME:
            return await self._ingest_from_blob_name(blob_name=value, experiment_id=experiment_id)
        elif trigger_type == TriggerType.FILEPATH:
            return await self._ingest_from_filepath(filepath=value, experiment_id=experiment_id)
        else:
            raise Exception(f"Unknown trigger type: {trigger_type}")

    async def _ingest_from_urn(
            self,
            urn: str,
            cms_client: CMSClient,
            experiment_id: str | None = None,
        ) -> IngestionResult:
        """Ingest from CMS using URN (complete CMS flow)."""
        logger.info(f"Ingesting from URN {urn}")

        # Get case id
        with self._log_step(
            action="mds_case_id_request",
            object_type="urn",
            object_id=urn,
            experiment_id=experiment_id,
        ):
            case_id = cms_client.get_case_id_from_urn(urn)
            if case_id is None:
                logger.error(f"URN {urn}: No case found")
                raise Exception(f"URN {urn}: No case found")
            
        case_data = {
            "urn": urn,
            "id": case_id,  # external CMS ID used as pk
        }   
        logger.debug(f"URN {urn} Case {case_id}: Case ID retrieved ")
        
        # Get case summary
        with self._log_step(
            action="mds_case_summary_request",
            object_type="case",
            object_id=case_id,
            experiment_id=experiment_id,
        ):
            case_summary = cms_client.get_case_summary(case_id)
            if case_summary is None:
                logger.error(f"URN {urn} Case {case_id}: No case summary")
                raise Exception(f"URN {urn} Case {case_id}: No case summary")   
        
        case_data.update(self._case_summary_to_dict(case_summary))
        logger.debug(f"URN {urn} Case {case_id}: Case summary retrieved")

        # Get raw documents from CMS
        with self._log_step(
            action="mds_document_list_request",
            object_type="case",
            object_id=case_id,
            experiment_id=experiment_id,
        ):
            raw_documents_data = cms_client.list_case_documents(case_id=case_id)
            if raw_documents_data is None:
                logger.warning(f"URN {urn} Case {case_id}: No document data")
                raise Exception(f"URN {urn} Case {case_id}: No document data")
            
        logger.debug(f"URN {urn} Case {case_id}: Number of documents: {len(raw_documents_data) if raw_documents_data else 0}")
        selected_documents_data = []
        for idx, raw_doc_data in enumerate(raw_documents_data or []):
            logger.debug(f"URN {urn} Case {case_id} Document {idx}: {raw_doc_data.get('presentationTitle')} {raw_doc_data.get('originalFileName')} ({raw_doc_data.get('cmsDocCategory')}:{raw_doc_data.get('type')})")
            if not is_document_supported(raw_doc_data=raw_doc_data):
                continue
            
            # Convert raw to internal document data format
            doc_data = self._document_to_dict(raw_doc_data)
            doc_data["case_id"] = case_id  # ensure case_id is included

            # Get raw documents from CMS
            self._log(
                action="mds_document_data_request",
                object_type="version",
                object_id=doc_data["version_id"],
                experiment_id=experiment_id,
            )
            document_data = cms_client.download_data(
                case_id=case_id,
                document_id=doc_data["id"],
                version_id=doc_data["version_id"],
            )
            self._log(
                action=f"mds_document_data_{'success' if document_data is not None else 'failure'}",
                object_type="version",
                object_id=doc_data["version_id"],
                experiment_id=experiment_id,
            )
            if document_data is None:
                logger.error(f"URN {urn} Case {case_id} Document {doc_data['id']} v{doc_data['version_id']}: Failed to retrieve document content. Skipping document.")
                continue

            doc_data["data"] = document_data

            # Add to selected documents if data is retrieved successfully
            selected_documents_data.append(doc_data)

        if not selected_documents_data:
            logger.warning(f"URN {urn} Case {case_id}: No document selected")
            return IngestionResult(
                success=False,
                error=f"URN {urn} Case {case_id}: No document selected",
            )
        
        logger.debug(
            f"URN {urn} Case {case_id}: Selected documents for ingestion ({len(selected_documents_data)} in total): " +
            '; '.join([f"{doc['id']} v{doc['version_id']} ({doc['original_file_name']}, {doc['cms_doc_category']}, {doc['doc_type']}, {doc['mime_type']})" for doc in selected_documents_data])
        )

        # Get defendants and charges from CMS
        self._log(
            action="mds_case_defendants_request",
            object_type="case",
            object_id=case_id,
            experiment_id=experiment_id,
        )
        defendants_data = cms_client.get_case_defendants(
            case_id=case_id,
            include_charges=True,
            include_offences=True,
        )
        self._log(
            action=f"mds_case_defendants_{'success' if defendants_data is not None else 'failure'}",
            object_type="case",
            object_id=case_id,
            experiment_id=experiment_id,
        )
        logger.debug(f"URN {urn} Case {case_id}: Number of defendants: {len(defendants_data)}")
        for def_idx, def_data in enumerate(defendants_data):
            charges = def_data.get("charges", [])
            offences = def_data.get("offences", [])
            logger.debug(f"URN {urn} Case {case_id} Defendant {def_idx}: {len(charges)} charges and {len(offences)} offences")
        # Store case data and process documents
        result = await self._store_and_process_case(
            case_data,
            defendants_data,
            selected_documents_data,
            experiment_id,
        )
        
        return result

    async def _ingest_from_blob_name(
            self,
            blob_name: str,
            experiment_id: str | None = None,
        ) -> IngestionResult:
        """Ingest from blob storage name."""
        logger.info(f"Ingesting from blob name: {blob_name}")

        with get_session() as session:
            # Store minimal case
            case_repo = CaseRepository(session)
            case: Case = case_repo.upsert(urn="01BL0000001") # Plaholder URN 
            
            # Store document reference
            doc_repo = DocumentRepository(session)
            document: Document = doc_repo.upsert(
                case_id=case.id,
                original_file_name=Path(blob_name).name,
            )

            # Store version reference
            version_repo = VersionRepository(session)
            version: Version = version_repo.upsert(
                document_id=document.id,
                source_blob_container=self.settings.storage.blob_container_name_source,
                source_blob_name=blob_name,
            )
        
        # Parse and process document
        result = await self._process_version(
            version=version,
            experiment_id=experiment_id,
        )
        
        result.case_ids.append(case.id)
        
        return result

    async def _ingest_from_filepath(
            self,
            filepath: str,
            experiment_id: str | None = None,
        ) -> IngestionResult:
        """Ingest from local filepath."""
        logger.info(f"Ingesting from filepath: {filepath}")
        
        # Read document from file system
        try:
            with open(filepath, "rb") as f:
                document_content = f.read()
        except Exception as e:
            return IngestionResult(success=False, error=f"Failed to read file: {e}")
        
        # Store to blob storage first
        blob_name = f"FILEPATH/{Path(filepath).name}"
        save_blob(
            container_name=self.settings.storage.blob_container_name_source,
            blob_name=blob_name,
            data=document_content,
        )
        
        return await self._ingest_from_blob_name(
            blob_name=blob_name,
            experiment_id=experiment_id,
        )

    # ========== Processing Methods ==========

    async def _store_and_process_case(
        self,
        case_data: dict[str, Any],
        defendants_data: list[dict[str, Any]],
        documents_data: list[dict[str, Any]],
        experiment_id: str | None,
    ) -> IngestionResult:
        """Store data and process documents."""
        result = IngestionResult(success=True) 

        case: Case = await self._store_case(
            case_data=case_data,
            experiment_id=experiment_id,
        )
        result.case_ids = [case.id]
        
        await self._store_defendants(
            defendants_data=defendants_data,
            experiment_id=experiment_id,
        )

        documents_data = await self._upload_document_blobs(
            case=case,
            documents_data=documents_data,
            experiment_id=experiment_id,
        )

        # Store documents and versions
        versions: list[Version] = await self._store_documents(
            case=case,
            documents_data=documents_data,
            experiment_id=experiment_id,
        )
        
        # Parse each document
        for version in versions:
            doc_result = await self._process_version(
                version=version,
                experiment_id=experiment_id,
            )            
            if doc_result.success:
                result.document_ids.extend(doc_result.document_ids)
                result.version_ids.extend(doc_result.version_ids)
            else:
                logger.warning(f"Document processing failed: doc_id={version.document_id}, error={doc_result.error}")
        
        return result

    async def _store_case(
        self,
        case_data: dict[str, Any],
        experiment_id: str | None,
    ) -> Case:
        """Store case data."""
        with get_session() as session:
            with self._log_step(
                action="case_data_storage",
                object_type="case",
                object_id=case_data.get("id", None),
                experiment_id=experiment_id,
            ):
                case_repo = CaseRepository(session)
                case: Case = case_repo.upsert(**case_data)

        return case


    async def _store_defendants(
        self,
        defendants_data: list[dict[str, Any]],
        experiment_id: str | None,
    ) -> list[Defendant]:
        """Store defendants, charges, and offences."""
        defendants: list[Defendant] = []
        with get_session() as session:
            defendant_repo = DefendantRepository(session)
            charge_repo = ChargeRepository(session)
            offence_repo = OffenceRepository(session)
            
            for defendant_data in defendants_data:

                with self._log_step(
                    action="defendant_data_storage",
                    object_type="defendant",
                    object_id=defendant_data.get("id", None),
                    experiment_id=experiment_id,
                ):
                    charges_data = defendant_data.pop("charges", [])
                    offences_data = defendant_data.pop("offences", [])
                    
                    defendant: Defendant = defendant_repo.upsert(**defendant_data)
                    defendants.append(defendant)
                    
                    # Store charges
                    for charge_data in charges_data:
                        charge_data["defendant_id"] = defendant.id
                        charge_repo.upsert(**charge_data)
            
                    # Store offences
                    for offence_data in offences_data:
                        offence_data["defendant_id"] = defendant.id
                        offence_repo.upsert(**offence_data)
        return defendants

    async def _upload_document_blobs(
        self,
        case: Case,
        documents_data: list[dict[str, Any]],
        experiment_id: str | None,
    ) -> list[dict[str, Any]]:
        """Upload document content to blob storage and update document data with blob references."""  
        # Store each document
        for doc_data in documents_data:

            self._log(
                action="document_content_store_begin",
                object_type="version",
                object_id=doc_data.get("version_id", None),
                experiment_id=experiment_id,
            )
            if doc_data.get("id") is None:
                doc_data["id"] = uuid.uuid4().int
            if doc_data.get("version_id") is None:
                doc_data["version_id"] = uuid.uuid4().int

            # Upload file content to Blob Storage
            container_name = self.settings.storage.blob_container_name_source
            blob_name = f"{experiment_id or 'None'}/{case.id}/{doc_data['id']}_{doc_data['version_id']}{doc_data['file_extension']}"
            save_blob(
                container_name=container_name,
                blob_name=blob_name,
                data=doc_data['data'],
            )
            doc_data['source_blob_container'] = container_name
            doc_data['source_blob_name'] = blob_name
            
            self._log(
                action="document_content_store_end",
                object_type="version",
                object_id=doc_data.get("version_id", None),
                experiment_id=experiment_id,
            )
        return documents_data

    async def _store_documents(
        self,
        case: Case,
        documents_data: list[dict[str, Any]],
        experiment_id: str | None,
    ) -> list[Version]:
        """Store document and version data."""
        versions: list[Version] = []
        with get_session() as session:
            doc_repo = DocumentRepository(session)
            version_repo = VersionRepository(session)
            for doc_data in documents_data:
                self._log(
                    action="document_record_store_begin",
                    object_type="document",
                    object_id=doc_data.get("id", None),
                    experiment_id=experiment_id,
                )
                document = doc_repo.upsert(
                    id=doc_data.get("id", None),
                    case_id=case.id,
                    presentation_title=doc_data.get("presentation_title", None),
                    original_file_name=doc_data.get("original_file_name", None),
                    cms_doc_category=doc_data.get("cms_doc_category", None),
                    doc_type=doc_data.get("doc_type", None),
                    file_extension=doc_data.get("file_extension", None),
                    mime_type=doc_data.get("mime_type", None),
                )
                version = version_repo.upsert(
                    id=doc_data.get("version_id", None),
                    document_id=document.id,
                    source_blob_container=doc_data.get("source_blob_container", None),
                    source_blob_name=doc_data.get("source_blob_name", None),
                )
                versions.append(version)
                self._log(
                    action="document_record_store_end",
                    object_type="document",
                    object_id=doc_data.get("id", None),
                    experiment_id=experiment_id,
                )
        return versions

    async def _process_version(
        self,
        version: Version,
        experiment_id: str | None,
    ) -> IngestionResult:
        """Parse document and extract sections."""
        result = IngestionResult(success=True)
        
        # Download file from Blob Storage
        content = load_blob(
            container_name=version.source_blob_container,
            blob_name=version.source_blob_name,
        )
            
        # Parse file content
        self._log(
            action="document_parse_begin",
            object_type="version",
            object_id=version.id,
            experiment_id=experiment_id,
        )
        parsing_result = self._parse_document(content)
        self._log(
            action="document_parse_end",
            object_type="version",
            object_id=version.id,
            experiment_id=experiment_id,
        )

        # Store parsed content on Blob Storage
        self._log(
            action="parsed_content_storage_begin",
            object_type="version",
            object_id=version.id,
            experiment_id=experiment_id,
        )
        container_name = self.settings.storage.blob_container_name_processed
        blob_name = f"{version.source_blob_name}.json"
        save_blob(
            container_name=container_name,
            blob_name=blob_name,
            data=json.dumps(parsing_result.as_dict(), indent=2).encode("utf-8"),
        )
        self._log(
            action="parsed_content_storage_end",
            object_type="version",
            object_id=version.id,
            experiment_id=experiment_id,
        )

        # Update version
        with get_session() as session:
            version_repo = VersionRepository(session)
            version_repo.upsert(
                id=version.id,
                parsed_blob_container=container_name,
                parsed_blob_name=blob_name,
            )
        
        result.document_ids.append(version.document_id)
        result.version_ids.append(version.id)
        
        return result

    def _parse_document(
            self,
            content: bytes,
        ) -> AnalyzeResult:
        """Parse document content using Azure Document Intelligence."""

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
        def __parse(doc_intel: DocumentIntelligenceClient, content: bytes) -> AnalyzeResult:
            """Parse document using Azure Document Intelligence."""
            poller: AnalyzeDocumentLROPoller = doc_intel.begin_analyze_document(
                model_id="prebuilt-layout",
                body=content,
                content_type="application/octet-stream",
                # try content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            logger.debug(f"Poller status: {poller.status()}")
            # Wait for the analysis to complete
            parsing_result: AnalyzeResult = poller.result()
            return parsing_result

        try:
            parsing_result: AnalyzeResult = __parse(self.doc_intel, content)
        except Exception as e:
            self._log(
                action="document_parse_failure",
                object_type="version",
                object_id=None,
                source="DocumentIntelligenceClient",
            )
            cause = e.last_attempt.exception() if hasattr(e, "last_attempt") else e
            logger.exception(f"Document parsing failed with exception: {cause}")
            raise cause
        
        return parsing_result


    def _case_summary_to_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Convert raw CMS case summary data to internal format."""
        return {
            "finalised": data.get("finalised", None),
            "area_id": data.get("areaId", None),
            "area_name": data.get("areaName", None),
            "unit_id": data.get("unitId", None),
            "unit_name": data.get("unitName", None),
            "registration_date": data.get("registrationDate", None),
        }
    

    def _document_to_dict(
            self,
            data: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert raw CMS document data to internal format."""
        return {
            "id": data.get("id"),
            "version_id": data.get("versionId"),
            "presentation_title": data.get("presentationTitle"),
            "original_file_name": data.get("originalFileName"),
            "cms_doc_category": data.get("cmsDocCategory"),
            "doc_type": data.get("type"),
            "file_extension": Path(data.get("originalFileName", "")).suffix,
            "mime_type": data.get("mimeType"),
        }

    def _log(
        self, *,
        event_type: str | None = None,
        actor_id: str | None = None,
        action: str,
        object_type: str,
        object_id: str | None = None,
        experiment_id: str | None = None,
        correlation_id: str | None = None,
        source: str | None = None,
        ) -> None:
        """Log."""

        if self.event_repo:
            self.event_repo.log(
                event_type=event_type or "ingestion",
                actor_id=actor_id or "ingestion.orchestrator",
                action=action,
                object_type=object_type,
                object_id=str(object_id) if object_id is not None else None,
                experiment_id=experiment_id,
                correlation_id=correlation_id or self.correlation_id,
                source=source or self.__class__.__name__,
                created_at=datetime.now(timezone.utc),
            )

    @contextmanager
    def _log_step(
        self,
        action: str,
        object_type: str,
        object_id=None,
        experiment_id=None,
    ):
        """Context manager for logging the start and end of a processing step, as well as any failure."""
        self._log(action=f"{action}_begin", object_type=object_type, object_id=object_id, experiment_id=experiment_id)
        try:
            yield
            self._log(action=f"{action}_end", object_type=object_type, object_id=object_id, experiment_id=experiment_id)
        except Exception:
            self._log(action=f"{action}_failure", object_type=object_type, object_id=object_id, experiment_id=experiment_id)
            raise
