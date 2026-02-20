import asyncio
from loguru import logger

from .tasks import DEFAULT_TASKS, AnalysisTask
from .base_worker import AnalysisWorker
from ..models import AnalysisJob, Section
from ..repositories import (
    AnalysisJobRepository,
    SectionRepository,
    EventRepository,
    ExperimentRepository,
)
from ..database import get_session
from ..services import load_blob


class AnalysisOrchestrator:
    """Orchestrator for managing analysis workflows."""

    task_dict: dict[str, AnalysisTask]
    event_repo: EventRepository | None
    correlation_id: str | None

    def __init__(
        self,
        tasks: list[AnalysisTask] | None = DEFAULT_TASKS,
        event_repo: EventRepository | None = None,
        correlation_id: str | None = None,
    ):
        """Initialize the orchestrator."""
        self.task_dict = {t.task_id: t for t in tasks}
        logger.info(f"Initialized AnalysisOrchestrator with {len(self.task_dict)} tasks")
        self.event_repo = event_repo
        self.correlation_id = correlation_id

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
        
        # Load section content from blob storage
        text = load_blob(
            container_name=section.content_blob_container,
            blob_name=section.content_blob_name,
        ).decode("utf-8")

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
        self._log(
            action="ANALYSIS_JOB_BEGIN",
            object_type="ANALYSIS_JOB",
            object_id=str(analysis_job.id),
        )
        try:
            self._run_tasks_sequentially( 
               text=text,
               experiment_id=experiment_id,
               section_id=section_id,
               analysis_job_id=analysis_job.id, 
               tasks=tasks_to_run
            )
                
        except Exception as e:
            logger.error(f"Error analyzing section {section_id}: {e}")
            raise
            
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
                    action="ANALYSIS_TASK_BEGIN",
                    object_type="ANALYSIS_TASK",
                    object_id=task.task_id,
                )
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
                event_type=event_type or "ANALYSIS_ORCHESTRATION",
                actor_id=actor_id or "ANALYSIS_ORCHESTRATOR",
                action=action,
                object_type=object_type,
                object_id=str(object_id) if object_id is not None else None,
                correlation_id=correlation_id or self.correlation_id,
                source=source or self.__class__.__name__,
            )
