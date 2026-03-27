import asyncio
from datetime import datetime, timezone
from typing import Any
import json

from tenacity import retry, stop_after_attempt, wait_fixed
from loguru import logger
from openai import AzureOpenAI
from jinja2 import Environment
from pydantic import BaseModel

from ..config import SettingsManager
from .tasks import DEFAULT_TASKS, AnalysisTask
from .base_worker import AnalysisWorker
from ..models import (
    PromptTemplate,
    Version,
    Section,
    Experiment,
    AnalysisJob,
    AnalysisResult,
)
from ..repositories import (
    EventRepository,
    PromptTemplateRepository,
    VersionRepository,
    SectionRepository,
    ExperimentRepository,
    AnalysisJobRepository,
)
from ..database import get_session
from ..services import load_blob, save_blob, get_llm_client
from .utils import is_valid_subset
from .models import ExtractionResult


class AnalysisOrchestrator:
    """Orchestrator for managing analysis workflows."""

    settings: SettingsManager
    task_dict: dict[str, AnalysisTask]
    event_repo: EventRepository | None
    correlation_id: str | None

    def __init__(
        self,
        tasks: list[AnalysisTask] | None = None,
        event_repo: EventRepository | None = None,
        correlation_id: str | None = None,
    ):
        """Initialize the orchestrator."""
        self.settings = SettingsManager.get_instance()
        task_list = list(tasks or DEFAULT_TASKS)
        self.task_dict = {t.task_id: t for t in task_list}
        logger.info(f"Initialized AnalysisOrchestrator with {len(self.task_dict)} tasks")
        self.event_repo = event_repo
        self.correlation_id = correlation_id


    def extract_section(
        self,
        version_id: int,
        experiment_id: str | None = None,
    ) -> ExtractionResult:
        """Extract a section from a document."""

        result: ExtractionResult = ExtractionResult(success=False)

        self._log(
            event_type="extraction",
            action="version_load_begin",
            object_type="version",
            object_id=version_id,
            experiment_id=experiment_id,
        )
        with get_session() as session:
            version_repo = VersionRepository(session)
            version: Version = version_repo.get_by_id(version_id)

        parsing_result = load_blob(
            container_name=version.parsed_blob_container,
            blob_name=version.parsed_blob_name,
        )
        # convert bytes to dict
        parsing_result = json.loads(parsing_result.decode("utf-8"))
        result.version_ids = [version_id]
        self._log(
            event_type="extraction",
            action="version_load_end",
            object_type="version",
            object_id=version_id,
            experiment_id=experiment_id,
        )

        # Extract sections
        self._log(
            event_type="extraction",
            action="section_extraction_begin",
            object_type="version",
            object_id=version.id,
            experiment_id=experiment_id,
        )
        try:
            sections_data = self._extract_sections(
                parsing_result=parsing_result,
                version_id=version.id,
            )
        except Exception as e:
            logger.error(f"Error extracting sections for version {version_id}: {e}")
            self._log(
                event_type="extraction",
                action="section_extraction_failure",
                object_type="version",
                object_id=f"{version_id}:{e}",
                experiment_id=experiment_id,
                source="orchestrator",
            )
            result.error = str(e)
            return result
        self._log(
            event_type="extraction",
            action="section_extraction_end",
            object_type="version",
            object_id=version.id,
            experiment_id=experiment_id,
        )
        
        # Store sections
        with get_session() as session:
            experiment_repo = ExperimentRepository(session)
            if experiment_id is not None:
                experiment: Experiment = experiment_repo.upsert(id=experiment_id)
            else:
                experiment: Experiment = experiment_repo.create()

            section_repo = SectionRepository(session)
            
            section_ids = []
            for section_data in sections_data:

                # Redact section content
                self._log(
                    event_type="extraction",
                    action="section_redaction_begin",
                    object_type="version",
                    object_id=version.id,
                    experiment_id=experiment_id,
                )
                raw_content = section_data.get("content")
                try:
                    redacted_content = self._redact_content(
                        content=raw_content,
                        version_id=version.id,
                    )
                except Exception as e:
                    logger.error(f"Error redacting content for version {version_id}: {e}")
                    self._log(
                        event_type="extraction",
                        action="content_redaction_failure",
                        object_type="version",
                        object_id=f"{version_id}:{e}",
                        experiment_id=experiment_id,
                        source="orchestrator",
                    )
                    result.error = f"Redaction failed: {e}"
                    return result
                self._log(
                    event_type="extraction",
                    action="section_redaction_end",
                    object_type="version",
                    object_id=version.id,
                    experiment_id=experiment_id,
                )
                
                # Create section record (create id)
                self._log(
                    event_type="extraction",
                    action="section_store_begin",
                    object_type="section",
                    experiment_id=experiment.id,
                )
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
                section_ids.append(section.id)
                self._log(
                    event_type="extraction",
                    action="section_store_end",
                    object_type="section",
                    object_id=section.id,
                    experiment_id=experiment.id,
                )
        
        result.section_ids = section_ids
        result.success = True
        return result


    def analyze_section(
        self,
        section_id: int,
        task_ids: list[str] | None = None,
        experiment_id: str | None = None,
    ) -> AnalysisJob:
        """Analyze a section by its ID."""
        # Fetch section content from database
        with get_session() as session:
            section_repo = SectionRepository(session)
            section: Section = section_repo.get_by_id(section_id)
            if not section:
                raise ValueError(f"Section {section_id} not found")
            experiment_id = experiment_id or section.experiment_id
            experiment_repo = ExperimentRepository(session)
            experiment_repo.upsert(id=experiment_id)
        
        # use redacted section content
        text = section.redacted_content

        # Run analysis    
        return self.analyze(
            text=text,
            experiment_id=experiment_id,
            section_id=section_id,
            task_ids=task_ids,
        )


    def analyze(
        self,
        text: str,
        experiment_id: str,
        section_id: int,
        task_ids: list[str] | None = None,
    ) -> AnalysisJob:
        """Analyze a section with specified tasks."""
        # Determine which tasks to run
        tasks_to_run = []
        if task_ids:
            tasks_to_run = [self.task_dict[tid] for tid in task_ids if tid in self.task_dict]
        else:
            tasks_to_run = list(self.task_dict.values())
        
        # Create analysis job
        with get_session() as session:
            job_repo = AnalysisJobRepository(session)
            analysis_job: AnalysisJob = job_repo.create(
                section_id=section_id,
                experiment_id=experiment_id,
                task_ids=','.join([t.task_id for t in tasks_to_run]),
            )
            session.add(analysis_job)
            session.commit()
            session.refresh(analysis_job)
            logger.info(f"Created AnalysisJob {analysis_job.id} for section {section_id}")
        
        # Run tasks
        try:
            self._log(
                action="analysis_job_begin",
                object_type="analysis_job",
                object_id=str(analysis_job.id),
                experiment_id=experiment_id,
            )
            self._run_tasks_sequentially( 
               text=text,
               experiment_id=experiment_id,
               section_id=section_id,
               analysis_job_id=analysis_job.id, 
               tasks=tasks_to_run
            )   
        except Exception as e:
            logger.error(f"Error analyzing section {section_id}: {e}")
            self._log(
                action="analysis_job_failure",
                object_type="analysis_job",
                object_id=f"{analysis_job.id}:{e}",
                experiment_id=experiment_id,
            )
            raise

        self._log(
            action="analysis_job_success",
            object_type="analysis_job",
            object_id=str(analysis_job.id),
            experiment_id=experiment_id,
        )
        return analysis_job


    def _run_tasks_sequentially(
        self,
        text: str,
        experiment_id: str,
        section_id: int,
        analysis_job_id: int,
        tasks: list[AnalysisTask],
    ) -> None:
        """Run tasks sequentially.
        
        Args:
            text: Content to analyze
            experiment_id: ID of the experiment
            section_id: ID of the section
            analysis_job_id: ID of the analysis job
            tasks: List of tasks to execute
        """
        logger.info(
            f"Starting analysis for section {section_id} in experiment {experiment_id}"
        )
        
        for task in tasks:
            try:

                self._log(
                    actor_id=task.worker_class.__name__,
                    action="analysis_task_begin",
                    object_type="analysis_task",
                    object_id=task.task_id,
                    experiment_id=experiment_id,
                )
                # Instantiate worker
                worker: AnalysisWorker = task.worker_class(
                    config=task.worker_config,
                    save_results=task.save_results
                )
                
                # Execute analysis
                logger.info(f"Running task {task.task_id} for job {analysis_job_id}")
                analysis_results: list[AnalysisResult] = worker.analyze(
                   text=text,
                   experiment_id=experiment_id,
                   section_id=section_id,
                   analysis_job_id=analysis_job_id,
                )
                self._log(
                    actor_id=task.worker_class.__name__,
                    action="analysis_task_success",
                    object_type="analysis_task:result_count",
                    object_id=f"{task.task_id}:{len(analysis_results)}",
                    experiment_id=experiment_id,
                )
                
            except Exception as e:
                logger.error(f"Error running task {task.task_id}: {e}")
                self._log(
                    actor_id=task.worker_class.__name__,
                    action="analysis_task_failure",
                    object_type="analysis_task:error_message",
                    object_id=f"{task.task_id}:{e}",
                    experiment_id=experiment_id,
                )
                raise


    def _run_tasks_parallel(
        self,
        text: str,
        experiment_id: str,
        section_id: int,
        analysis_job_id: int,
        tasks: list[AnalysisTask],
    ) -> None:
        """Run tasks in parallel.

        Uses Asyncio, ie. this is single thread, single process. 
        It uses an event loop to run many tasks concurrently by switching between them 
        when one task is waiting (for example, waiting for LLM inference).
        It is best for I/O-bound workloads along with high-concurrency workloads.
        
        Args:
            text: Content to analyze
            experiment_id: ID of the experiment
            section_id: ID of the section
            analysis_job_id: ID of the analysis job
            tasks: List of tasks to execute
        """
        logger.info(
            f"Starting analysis for section {section_id} in experiment {experiment_id}"
        )

        # Create event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create async tasks
        futures = []
        for task in tasks:
            future = loop.create_task(
                self._run_single_task(
                    text,
                    experiment_id,
                    section_id,
                    analysis_job_id,
                    task,
                )
            )
            futures.append(future)
        
        # Run all tasks
        try:
            loop.run_until_complete(asyncio.gather(*futures))
        finally:
            loop.close()


    async def _run_single_task(
        self,
        text: str,
        experiment_id: str,
        section_id: int,
        analysis_job_id: int,
        task: AnalysisTask,
    ) -> None:
        """Run a single analysis task.
        
        Args:
            text: Content to analyze
            experiment_id: ID of the experiment
            section_id: ID of the section
            analysis_job_id: ID of the analysis job
            task: Task definition to execute
        """
        try:
            # Instantiate worker
            worker: AnalysisWorker = task.worker_class(
                config=task.worker_config,
                save_results=task.save_results
            )
            
            # Execute analysis
            logger.info(f"Running task {task.task_id} for job {analysis_job_id}")
            worker.analyze(
               text=text,
               experiment_id=experiment_id,
               section_id=section_id,
               analysis_job_id=analysis_job_id,
            )
            
        except Exception as e:
            logger.error(f"Error running task {task.task_id}: {e}")
            raise


    def _extract_sections(
        self,
        parsing_result: dict,
        version_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Extract sections"""
        logger.debug("Extracting sections with Azure AI Foundry")
    
        with get_session() as session:
            prompt_template_repo: PromptTemplateRepository = PromptTemplateRepository(session)
            prompt_template: PromptTemplate = prompt_template_repo.get_last_version_by(agent="section_extractor")
            if prompt_template is None:
                raise ValueError("No prompt template found for agent 'section_extractor'")
            self._log(
                event_type="extraction",
                action="section_extraction_prompt",
                object_type="prompt_template",
                object_id=prompt_template.id,
            )
            logger.debug(f"Section extraction prompt.id: {prompt_template.id}")
        
        template = Environment(autoescape=True).from_string(source=prompt_template.template)
        parsing_result_content = parsing_result.get("content", "")
        compiled_prompt = template.render(contextText=parsing_result_content)
        
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
                max_output_tokens=16000,
                truncation="auto",
            )
            try:
                sections_data = response.output_parsed
            except Exception as e:
                logger.error(f"Error parsing section extraction response for version {version_id}: {e}")
                sections_data = json.loads(response.output_text + '"]')
            if sections_data.narratives is None or len(sections_data.narratives) == 0:
                logger.warning("No sections extracted from document")
                return []
            logger.debug(f"Extracted {len(sections_data.narratives)} sections")
            return sections_data.narratives

        
        # Convert to list of dicts and validate each
        try:
            extracted_sections = __extract(compiled_prompt, llm_client)
        except Exception as e:
            cause = e.last_attempt.exception() if hasattr(e, "last_attempt") else e
            logger.exception(f"Section extraction failed with exception: {cause}")
            self._log(
                event_type="extraction",
                action="section_extraction_failure",
                object_type="version",
                object_id=f"{version_id}:{cause}",
                source="llm",
            )
            raise cause
        
        result = []
        for idx, content in enumerate(extracted_sections):
            self._log(
                event_type="extraction",
                action="section_validation_begin",
                object_type="version",
                object_id=f"{version_id}/{idx}",
            )
            is_valid = is_valid_subset(
                text=parsing_result_content,
                subset=content,
            )
            self._log(
                event_type="extraction",
                action=f"section_validation_{'success' if is_valid else 'failure'}",
                object_type="version",
                object_id=f"{version_id}/{idx}",
            )
            if not is_valid:
                logger.warning(f"Extracted section {idx} content failed subset validation, skipping")
                continue
            result.append({"content": content})

        return result

    def _redact_content(
            self,
            content: str,
            version_id: str | None = None,
        ) -> str:
        """Redact UK and Northern Ireland Personally Identifiable Information (PII) from content."""
        
        with get_session() as session:
            prompt_template_repo: PromptTemplateRepository = PromptTemplateRepository(session)
            prompt_template: PromptTemplate = prompt_template_repo.get_last_version_by(agent="redactor")
            if prompt_template is None:
                raise ValueError("No prompt template found for agent 'redactor'")
            self._log(
                event_type="extraction",
                action="content_redaction_prompt",
                object_type="prompt_template",
                object_id=prompt_template.id,
            )
            logger.debug(f"Content redaction prompt.id: {prompt_template.id}")
        
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
                max_output_tokens=16000,
                truncation="auto",
            )
            try:
                redacted_text = response.output_parsed.redacted_text
            except Exception as e:
                logger.error(f"Error parsing redacted content response for version {version_id}: {e}")
                redacted_text = json.loads(response.output_text + '"}').get("redacted_text", "")
            return redacted_text
        
        try:
            redacted_content = _redact(llm_client, compiled_prompt)
        except Exception as e:
            self._log(
                event_type="extraction",
                action="content_redaction_failure",
                object_type="version",
                object_id=version_id,
                source="llm",
            )
            cause = e.last_attempt.exception() if hasattr(e, "last_attempt") else e
            logger.exception(f"Content redaction failed with exception: {cause}")
            raise cause
        
        return redacted_content

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
                event_type=event_type or "analysis",
                actor_id=actor_id or "analysis.orchestrator",
                action=action,
                object_type=object_type,
                object_id=str(object_id) if object_id is not None else None,
                experiment_id=experiment_id,
                correlation_id=correlation_id or self.correlation_id,
                source=source or self.__class__.__name__,
                created_at=datetime.now(timezone.utc),
            )
