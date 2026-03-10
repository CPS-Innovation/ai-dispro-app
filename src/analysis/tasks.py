from dataclasses import dataclass
from typing import Type

from .base_worker import AnalysisWorker
from .workers import LLMWorker, LangGraphWorker

@dataclass
class AnalysisTask:
    """Definition of an analysis task."""

    task_id: str
    worker_class: Type[AnalysisWorker]  # Worker class to use
    save_results: bool = True
    worker_config: dict | None = None

    def __hash__(self):
        """Make task hashable."""
        return hash(self.task_id)


# Default analysis tasks
DEFAULT_TASKS = []
for (task_id, theme_id, pattern_id, worker_class) in [
    # ('theme1-appropriateness',  'theme1', 'appropriateness', LangGraphWorker),
    # ('theme1-emotional',        'theme1', 'emotional', LangGraphWorker),
    # ('theme1-judgemental',      'theme1', 'judgemental', LangGraphWorker),
    # ('theme1-not_fact',         'theme1', 'not_fact', LangGraphWorker),
    # ('theme1-relevant',         'theme1', 'relevant', LangGraphWorker),
    # ('theme1-tropes_context',   'theme1', 'tropes_context', LangGraphWorker),
    # ('theme1-tropes_grounded',  'theme1', 'tropes_grounded', LangGraphWorker),

    # ('theme2-adultification',   'theme2', 'adultification', LangGraphWorker),
    # ('theme2-judgemental',      'theme2', 'judgemental', LangGraphWorker),
    # ('theme2-probative',        'theme2', 'probative', LangGraphWorker),
    # ('theme2-risk',             'theme2', 'risk', LangGraphWorker),
    # ('theme2-tropes',           'theme2', 'tropes', LangGraphWorker),
    # ('theme2-victim',           'theme2', 'victim', LangGraphWorker),

    ('combined-age-appropriate',  'combined', 'age-appropriate', LangGraphWorker),
    ('combined-emotionally neutral', 'combined', 'emotionally neutral', LangGraphWorker),
    ('combined-character',          'combined', 'character', LangGraphWorker),
    ('combined-fact-based',         'combined', 'fact-based', LangGraphWorker),
    ('combined-non-judgemental',    'combined', 'non-judgemental', LangGraphWorker),
    ('combined-offence-appropriate','combined', 'offence-appropriate', LangGraphWorker),
    ('combined-probative',  'combined', 'probative', LangGraphWorker),
    ('combined-risk-proportionate',  'combined', 'risk-proportionate', LangGraphWorker),
    ('combined-victim-appropriate',  'combined', 'victim-appropriate', LangGraphWorker),
]:
    DEFAULT_TASKS.append(
        AnalysisTask(
            task_id=task_id,
            worker_class=worker_class,
            worker_config={
                "theme_id": theme_id,
                "pattern_id": pattern_id,
            },
            save_results=True,
    ))
