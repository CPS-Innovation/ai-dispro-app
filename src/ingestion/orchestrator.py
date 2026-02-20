import json
import uuid
from datetime import datetime, timezone

from tenacity import retry, stop_after_attempt, wait_fixed
from typing import Any
from pathlib import Path

from loguru import logger
from openai import AzureOpenAI
from pydantic import BaseModel
from jinja2 import Environment
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
    ExperimentRepository,
    SectionRepository,
    PromptTemplateRepository,
    EventRepository,
)
from ..models import (
    Case,
    Defendant,
    Charge,
    Offence,
    Document,
    Version,
    Experiment,
    Section,
)
from ..services import (
    CMSClient,
    get_docintel_client,
    load_blob,
    save_blob,
    get_llm_client,
)
from .models import IngestionResult, TriggerType
from .utils import is_valid_subset


class IngestionOrchestrator:
    """Orchestrates the ingestion pipeline."""

    supportedCMSDocCategories: list[str] = [
        "Review",
        "MGForm",
    ]
    supportedDocTypes: list[str] = [
        "MG 3",
        "MG3",
        "MG3 (with Schedule of Charges)",
    ]
    supportedMimeTypes: list[str] = [
        "application/pdf", # .pdf
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
    ]
    event_repo: EventRepository | None
    correlation_id: str | None

    def __init__(
            self,
            event_repo: EventRepository | None = None,
            correlation_id: str | None = None,
        ) -> None:
        """Initialize ingestion orchestrator with service dependencies."""
        self.settings = SettingsManager.get_instance()
        self.event_repo = event_repo
        self.correlation_id = correlation_id
        logger.info("Ingestion orchestrator initialized")

    async def ingest(
            self, 
            trigger_type: TriggerType,
            value: str,
            experiment_id: str | None = None,
        ) -> IngestionResult:
        """Execute complete ingestion pipeline."""
        logger.info(
            "Starting ingestion: trigger_type={}, value={}, experiment_id={}",
            trigger_type,
            value,
            experiment_id,
        )
        
        try:
            # Route to appropriate handler based on trigger type
            if trigger_type in [TriggerType.URN, TriggerType.URN_LIST]:
                cms_client = CMSClient()
                self._log(
                    action="CMS_AUTH_REQUEST",
                    object_type="CMS",
                    object_id=None,
                )
                
                is_auth_successful = cms_client.authenticate()
                
                if not is_auth_successful:
                    logger.error("CMS authentication failed")
                    return IngestionResult(
                        success=False,
                        error="CMS authentication failed",
                    )

                self._log(
                    action="CMS_TOKEN_ISSUED",
                    object_type="CMS",
                    object_id=None,
                )

                if trigger_type == TriggerType.URN:
                    return await self._ingest_from_urn(value=value, cms_client=cms_client, experiment_id=experiment_id)
                elif trigger_type == TriggerType.URN_LIST:
                    overall_result = IngestionResult(success=True)
                    for urn in value:
                        result = await self._ingest_from_urn(value=urn.strip(), cms_client=cms_client, experiment_id=experiment_id)
                        if not result.success:
                            overall_result.success = False
                            overall_result.error = f"One or more URNs failed ingestion. Latest error: {result.error}"
                        else:
                            overall_result.case_ids.extend(result.case_ids or [])
                            overall_result.document_ids.extend(result.document_ids or [])
                            overall_result.version_ids.extend(result.version_ids or [])
                            overall_result.section_ids.extend(result.section_ids or [])
                    return overall_result
            
            elif trigger_type == TriggerType.BLOB_NAME:
                return await self._ingest_from_blob_name(value=value, experiment_id=experiment_id)
            elif trigger_type == TriggerType.FILEPATH:
                return await self._ingest_from_filepath(value=value, experiment_id=experiment_id)
            else:
                return IngestionResult(
                    success=False,
                    error=f"Unknown trigger type: {trigger_type}"
                )
                
        except Exception as e:
            logger.exception("Ingestion failed with exception")
            return IngestionResult(success=False, error=str(e))

    async def _ingest_from_urn(
            self,
            value: str,
            cms_client: CMSClient,
            experiment_id: str | None = None,
        ) -> IngestionResult:
        """Ingest from CMS using URN (complete CMS flow)."""
        urn = value
        logger.info("Ingesting from URN: {}", urn)

        # Get case
        self._log(
            action="CMS_METADATA_REQUEST",
            object_type="URN",
            object_id=urn,
        )

        case_id = cms_client.get_case_id_from_urn(urn)
        case_data = {
            "urn": urn,
            "id": case_id,
        }   
        logger.debug("Retrieved case ID {} for URN {}", case_id, urn)
        
        # Get case summary         
        case_summary = cms_client.get_case_summary(case_id)
        if case_summary:
            case_data["finalised"] = case_summary.get("finalised", None)
            case_data["area_id"] = case_summary.get("areaId", None)
            case_data["area_name"] = case_summary.get("areaName", None)
            case_data["unit_id"] = case_summary.get("unitId", None)
            case_data["unit_name"] = case_summary.get("unitName", None)
            case_data["registration_date"] = case_summary.get("registrationDate", None)
        logger.debug("Case info retrieved: case_id={}", case_id)

        # Get raw documents from CMS
        documents_data = cms_client.list_case_documents(case_id=case_id)
        logger.debug("Case {} has {} documents", case_id, len(documents_data) if documents_data else 0)
        selected_documents_data = []
        for doc_idx, doc_data in enumerate(documents_data or []):
            logger.debug("Document {}: {} ({}:{})", doc_idx, doc_data.get("originalFileName"), doc_data.get("cmsDocCategory"), doc_data.get("type"))
            if doc_data["cmsDocCategory"] not in self.supportedCMSDocCategories:
                logger.debug("Skipping '{}'. Reason: non-MGForm document {}", doc_data.get("originalFileName"), doc_data.get("id"))
                continue
            if doc_data["type"] not in self.supportedDocTypes:
                logger.debug("Skipping '{}'. Reason: non-MG3 document {}", doc_data.get("originalFileName"), doc_data.get("id"))
                continue
            if doc_data["mimeType"] not in self.supportedMimeTypes:
                logger.debug("Skipping '{}'. Reason: unsupported mime type document {}", doc_data.get("originalFileName"), doc_data.get("id"))
                continue
            selected_documents_data.append(doc_data)
            # Get raw documents from CMS
            self._log(
                action="CMS_DOCUMENTS_REQUEST",
                object_type="version",
                object_id=doc_data["versionId"],
            )
            document_data = cms_client.download_data(
                case_id=case_id,
                document_id=doc_data["id"],
                version_id=doc_data["versionId"],
            )
            doc_data["data"] = document_data

        if not selected_documents_data:
            logger.warning("No document selected for case {}", case_id)
            return IngestionResult(
                success=False,
                error=f"No document selected for case {case_id}",
            )
        
        logger.debug(
            "Selected documents for ingestion ({} in total): {}", 
            len(selected_documents_data),
            '; '.join([f"{doc['id']} v{doc['versionId']} ({doc['originalFileName']}, {doc['cmsDocCategory']}, {doc['type']}, {doc['mimeType']})" for doc in selected_documents_data]),
        )

        # Get defendants and charges from CMS
        defendants_data = cms_client.get_case_defendants(
            case_id=case_id,
            include_charges=True,
            include_offences=True,
        )
        logger.debug("Case {} has {} defendants", case_id, len(defendants_data))
        for def_idx, def_data in enumerate(defendants_data):
            charges = def_data.get("charges", [])
            offences = def_data.get("offences", [])
            logger.debug("Defendant {} has {} charges and {} offences", def_idx, len(charges), len(offences))

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
            value: str,
            experiment_id: str | None = None,
        ) -> IngestionResult:
        """Ingest from blob storage name."""
        blob_name = value
        logger.info("Ingesting from blob name: {}", blob_name)

        with get_session() as session:
            # Store minimal case
            case_repo = CaseRepository(session)
            case: Case = case_repo.upsert(urn="01BL0000001")
            
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
            value: str,
            experiment_id: str | None = None,
        ) -> IngestionResult:
        """Ingest from local filepath."""
        filepath = value
        logger.info("Ingesting from filepath: {}", filepath)
        
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
            value=blob_name,
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

        with get_session() as session:
            # Store case
            case_repo = CaseRepository(session)
            case: Case = case_repo.upsert(**case_data)
            result.case_id = case.id
            
            # Store defendants and charges
            defendant_repo = DefendantRepository(session)
            charge_repo = ChargeRepository(session)
            offence_repo = OffenceRepository(session)
            
            for defendant_data in defendants_data:
                charges_data = defendant_data.pop("charges", [])
                offences_data = defendant_data.pop("offences", [])
                
                defendant: Defendant = defendant_repo.upsert(**defendant_data)
                
                # Store charges
                for charge_data in charges_data:
                    charge_data["defendant_id"] = defendant.id
                    charge_repo.upsert(**charge_data)
        
                # Store offences
                for offence_data in offences_data:
                    offence_data["defendant_id"] = defendant.id
                    offence_repo.upsert(**offence_data)
        
        # Store each document
        versions: list[Version] = []
        for doc_data in documents_data:

            if doc_data.get("id") is None:
                doc_data["id"] = uuid.uuid4().int
            if doc_data.get("versionId") is None:
                doc_data["versionId"] = uuid.uuid4().int

            # Upload file content to Blob Storage
            container_name = self.settings.storage.blob_container_name_source
            blob_name = f"{experiment_id}/{case.id}/{doc_data['id']}_{doc_data['versionId']}{doc_data['fileExtension']}"
            save_blob(
                container_name=container_name,
                blob_name=blob_name,
                data=doc_data['data'],
            )
            doc_data['source_blob_container'] = container_name
            doc_data['source_blob_name'] = blob_name

        # Store documents and versions
        with get_session() as session:
            doc_repo = DocumentRepository(session)
            version_repo = VersionRepository(session)
            # Store documents and versions
            for doc_data in documents_data:
                document = doc_repo.upsert(
                    id=doc_data.get("id", None),
                    case_id=case.id,
                    cms_doc_category=doc_data.get("cms_doc_category"),
                    original_file_name=doc_data.get("original_file_name", "document"),
                    doc_type=doc_data.get("doc_type"),
                    file_extension=doc_data.get("file_extension"),
                    mime_type=doc_data.get("mime_type"),
                )
                version = version_repo.upsert(
                    id=doc_data.get("versionId", None),
                    document_id=document.id,
                    source_blob_container=doc_data.get("source_blob_container", None),
                    source_blob_name=doc_data.get("source_blob_name", None),
                )
                versions.append(version)
        
        # Parse each document
        for version in versions:

            doc_result = await self._process_version(
                version=version,
                experiment_id=experiment_id,
            )
            
            if doc_result.success:
                result.document_ids.extend(doc_result.document_ids)
                result.version_ids.extend(doc_result.version_ids)
                result.section_ids.extend(doc_result.section_ids)
            else:
                logger.warning(
                    "Document processing failed: doc_id={}, error={}",
                    version.document_id,
                    doc_result.error,
                )
        
        return result

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
            action="DOCUMENT_PARSE_REQUEST",
            object_type="version",
            object_id=version.id,
        )
        parsing_result = self._parse_document(content)

        # Store parsed content back to Blob Storage
        container_name = self.settings.storage.blob_container_name_processed
        blob_name = f"{version.source_blob_name}.json"
        save_blob(
            container_name=container_name,
            blob_name=blob_name,
            data=json.dumps(parsing_result.as_dict(), indent=2).encode("utf-8"),
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
        
        # Extract sections
        self._log(
            action="SECTION_EXTRACTION_REQUEST",
            object_type="version",
            object_id=version.id,
        )
        sections_data = self._extract_sections(parsing_result=parsing_result)
        
        # Store sections
        with get_session() as session:
            
            experiment_repo = ExperimentRepository(session)
            if experiment_id is not None:
                experiment: Experiment = experiment_repo.upsert(id=experiment_id)
            else:
                experiment: Experiment = experiment_repo.create()

            section_repo = SectionRepository(session)
            
            for section_data in sections_data:
                raw_content = section_data.get("content")
                redacted_content = self._redact_content(raw_content)
                # Create section record (create id)
                section: Section = section_repo.upsert(
                    version_id=version.id,
                    document_id=version.document_id,
                    experiment_id=experiment.id,
                    redacted_content=redacted_content,
                    created_at=datetime.now(timezone.utc),
                )
                # Save section content to Blob Storage
                content_blob_name = f"{experiment.id}/{version.id}/{section.id}.txt"
                save_blob(
                    container_name=self.settings.storage.blob_container_name_section,
                    blob_name=content_blob_name,
                    data=section_data.get("content", "").encode("utf-8"),
                )
                # Update section with blob info
                section_repo.update(
                    id_value=section.id,
                    content_blob_container=self.settings.storage.blob_container_name_section,
                    content_blob_name=content_blob_name,
                )
                result.section_ids.append(section.id)
        
        return result

    def _parse_document(self, content: bytes) -> AnalyzeResult:
        """Parse document content using Azure Document Intelligence."""

        doc_intel: DocumentIntelligenceClient = get_docintel_client()

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
        def __parse(doc_intel: DocumentIntelligenceClient, content: bytes) -> AnalyzeResult:
            """Parse document using Azure Document Intelligence."""
            poller: AnalyzeDocumentLROPoller = doc_intel.begin_analyze_document(
                model_id="prebuilt-layout",
                analyze_request=content,
                content_type="application/octet-stream",
                # try content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            logger.debug("Poller status: {}", poller.status())
            # Wait for the analysis to complete
            parsing_result: AnalyzeResult = poller.result()
            return parsing_result

        parsing_result: AnalyzeResult = __parse(doc_intel, content)
        return parsing_result

    def _extract_sections(
        self, parsing_result: AnalyzeResult
    ) -> list[dict[str, Any]]:
        """Extract sections"""
        logger.debug("Extracting sections with Azure AI Foundry")
    
        with get_session() as session:
            prompt_template_repo: PromptTemplateRepository = PromptTemplateRepository(session)
            prompt_template = prompt_template_repo.get_last_version_by(agent="section_extractor")
            if prompt_template is None:
                raise ValueError("No prompt template found for agent 'section_extractor'")
        
        template = Environment(autoescape=True).from_string(source=prompt_template.template)
        context_text = parsing_result.get("content", "")
        compiled_prompt = template.render(contextText=context_text)
        
        llm_client = get_llm_client()

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
        def __extract(
            compiled_prompt: str,
            llm_client: AzureOpenAI,
        ) -> Any:
            """Extract sections using Azure AI Foundry."""
            class SectionContent(BaseModel):
                narratives: list[str] | None = None

            # responses.parse() expects model gpt-4o (or newer), API version: 2025-03-01-preview (or newer)
            response = llm_client.responses.parse(
                model=self.settings.ai_foundry.deployment_name,
                input=[{"role": "user", "content": compiled_prompt}],
                text_format=SectionContent,
                temperature=0.0,
            )
            sections_data = response.output_parsed
            if sections_data.narratives is None or len(sections_data.narratives) == 0:
                logger.warning("No sections extracted from document")
                return []
            logger.debug("Extracted {} sections", len(sections_data.narratives))
            return sections_data.narratives
        
        # Convert to list of dicts and validate each
        extracted_sections = __extract(compiled_prompt, llm_client)
        result = []
        for idx, content in enumerate(extracted_sections):
            is_valid = is_valid_subset(
                text=context_text,
                subset=content,
            )
            if not is_valid:
                logger.warning("Extracted section {} content failed subset validation, skipping", idx)
                continue
            result.append({"content": content})

        return result

    def _redact_content(self, content: str) -> str:
        """Redact UK and Northern Ireland Personally Identifiable Information (PII) from content."""
        
        with get_session() as session:
            prompt_template_repo: PromptTemplateRepository = PromptTemplateRepository(session)
            prompt_template = prompt_template_repo.get_last_version_by(agent="redactor")
            if prompt_template is None:
                raise ValueError("No prompt template found for agent 'redactor'")
        
        template = Environment(autoescape=True).from_string(source=prompt_template.template)
        compiled_prompt = template.render(contextText=content)

        llm_client = get_llm_client()

        @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
        def _redact(llm_client: AzureOpenAI, compiled_prompt: str) -> str:
            """Redact PII from content using Azure AI Foundry."""
            class RedactedContent(BaseModel):
                redacted_text: str
            
            response = llm_client.responses.parse(
                model=self.settings.ai_foundry.deployment_name,
                input=[{"role": "user", "content": compiled_prompt}],
                text_format=RedactedContent,
                temperature=0.0,
            )
            redacted_text = response.output_parsed.redacted_text
            return redacted_text
        
        return _redact(llm_client, compiled_prompt)
    
    def _log(
        self, *,
        event_type: str | None = None,
        actor_id: str | None = None,
        action: str,
        object_type: str,
        object_id: str | None = None,
        correlation_id: str | None = None,
        source: str | None = None,
        ) -> None:
        """Log."""
        if self.event_repo:
            self.event_repo.log(
                event_type=event_type or "INGESTION",
                actor_id=actor_id or "INGESTION_ORCHESTRATOR",
                action=action,
                object_type=object_type,
                object_id=str(object_id) if object_id is not None else None,
                correlation_id=correlation_id or self.correlation_id,
                source=source or self.__class__.__name__,
            )
