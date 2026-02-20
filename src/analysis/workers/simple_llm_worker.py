import json
from typing import Any

from loguru import logger
from jinja2 import Environment
from openai import AzureOpenAI

from ...config import SettingsManager
from ..base_worker import AnalysisWorker
from ...models import AnalysisResult
from ...services import get_llm_client


class SimpleLLMWorker(AnalysisWorker):
    """Worker that uses LLM."""

    llm_client: AzureOpenAI
    deployment_name: str
    prompt_template: str | None
    theme_id: str | None
    pattern_id: str | None

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        save_results: bool = True,
    ):
        """Initialize the worker."""
        super().__init__(config, save_results)
        self.prompt_template = self.config.get("prompt_template")
        self.theme_id = self.config.get("theme_id", None)
        self.pattern_id = self.config.get("pattern_id", None)
        settings = SettingsManager.get_instance()
        self.deployment_name = settings.ai_foundry.deployment_name
        self.llm_client = get_llm_client(settings)

    def analyze(
        self,
        text: str,
        experiment_id: str,
        section_id: int,
        analysis_job_id: int,
    ) -> list[AnalysisResult]:
        """Execute LLM analysis on section content.
        
        Args:
            text: The text content to analyze
            experiment_id: The experiment ID
            section_id: The section ID
            analysis_job_id: The analysis job ID
            
        Returns:
            List of AnalysisResult instances
        """
        logger.info(f"Analyzing section {section_id} with analysis job {analysis_job_id}")
        
        # Build prompt from template
        prompt_template_str = self.prompt_template
        if prompt_template_str is None:
            raise ValueError("Prompt template is not provided.")
        prompt_template = Environment(autoescape=True).from_string(source=prompt_template_str)
        compiled_prompt = prompt_template.render(contextText=text)
        
        # Call LLM
        try:
            response = self._call_model(compiled_prompt)
            
            # Parse results
            parsed_results = self._parse_response(response)
            
            # Create AnalysisResult instances
            results = []
            for result_data in parsed_results:
                result = AnalysisResult(
                    analysis_job_id=analysis_job_id,
                    experiment_id=experiment_id,
                    prompt_template_id=None,
                    content=result_data.get("content", ""),
                    justification=result_data.get("justification", ""),
                    theme_id=self.theme_id,
                    pattern_id=self.pattern_id,
                    category_id=', '.join(result_data.get("categories", [])),
                    self_confidence=float(result_data.get("self_confidence", 0.0)),
                )
                results.append(result)
            
            logger.info(f"Found {len(results)} results for section {section_id}")
            
            if self.save_results:
                self.save_results_to_db(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing section {section_id}: {str(e)}")
            raise

    def _call_model(self, prompt: str) -> str:
        """Call the LLM API."""
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = self.llm_client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
        
        return response.choices[0].message.content

    def _parse_response(self, response: str) -> list[dict[str, Any]]:
        """Parse JSON response from LLM."""
        # Extract JSON from response
        response_text = response.strip()
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        
        if start_idx == -1 or end_idx == 0:
            logger.warning("No JSON found in response")
            return []
        
        json_str = response_text[start_idx:end_idx]
        
        try:
            parsed = json.loads(json_str)
            return parsed.get("analysis_results", [])
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return []
