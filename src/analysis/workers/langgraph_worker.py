import json
from typing import List, Dict, TypedDict, Annotated, Any
import operator
from hashlib import md5

from loguru import logger
from jinja2 import Environment
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from tenacity import retry, stop_after_attempt, wait_fixed

from ...config import SettingsManager
from ...database import get_session
from ...repositories import PromptTemplateRepository
from ..base_worker import AnalysisWorker
from ...models import AnalysisResult, PromptTemplate
from ...services import get_token_provider


class State(TypedDict):
    text_: str
    pattern_: str
    references: Annotated[list, operator.add]
    results: Annotated[list, operator.add]


class ReferenceState(TypedDict):
    """State data."""
    hash_id: str
    content: str
    categories: list[str]
    justification: str
    self_confidence: str
    text: str
    pattern: str
    is_witness_response: str | None
    rewrite_response: dict | None
    defence_response: dict | None
    reviewer_response: dict | None
    results: Annotated[list, operator.add]


class LangGraphWorker(AnalysisWorker):
    """Worker that uses a LangGraph-like client and prompt repository."""

    llm_client: AzureChatOpenAI
    deployment_name: str
    theme_id: str
    pattern_id: str

    critic_prompt_template: PromptTemplate
    is_witness_prompt_template: PromptTemplate
    rewrite_prompt_template: PromptTemplate
    defence_prompt_template: PromptTemplate
    reviewer_prompt_template: PromptTemplate

    def __init__(
        self,
        config: Dict[str, Any] | None = None,
        save_results: bool = True,
    ):
        super().__init__(config, save_results)
        
        self.theme_id = self.config.get("theme_id")
        self.pattern_id = self.config.get("pattern_id")

        with get_session() as session:
            prompt_template_repo = PromptTemplateRepository(session)
            self.critic_prompt_template = prompt_template_repo.get_last_version_by(
                theme=self.theme_id,
                pattern=self.pattern_id,
                agent="critic",
            )
            self.is_witness_prompt_template = prompt_template_repo.get_last_version_by(
                agent="is_witness",
            )
            self.rewrite_prompt_template = prompt_template_repo.get_last_version_by(
                agent="rewrite",
            )
            self.defence_prompt_template = prompt_template_repo.get_last_version_by(
                theme=self.theme_id,
                pattern=self.pattern_id,
                agent="defence", 
            )
            self.reviewer_prompt_template = prompt_template_repo.get_last_version_by(
                agent="reviewer",
            )

        settings = SettingsManager.get_instance()
        token_provider = get_token_provider(
            scopes="https://cognitiveservices.azure.com/.default",
        )
        self.llm_client = AzureChatOpenAI(
            azure_endpoint=settings.ai_foundry.endpoint,
            azure_deployment=settings.ai_foundry.deployment_name,
            openai_api_version=settings.ai_foundry.api_version,
            azure_ad_token_provider=token_provider,
        )

    def analyze(
        self,
        text: str,
        experiment_id: str,
        section_id: int,
        analysis_job_id: int,
    ) -> List[AnalysisResult]:
        logger.info(f"Analyzing section {section_id} with analysis job {analysis_job_id} (LangGraph)")

        try:
            initial_state: State = self._build_initial_state(
                text=text,
                pattern=self.pattern_id,
            )
            graph: StateGraph = self._build_graph()

            @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
            def _invoke(state: State) -> State:
                return graph.invoke(state)

            graph_results = _invoke(initial_state)
            parsed_results = self._parse_results(graph_results)

            results: List[AnalysisResult] = []
            for result_data in parsed_results:
                result = AnalysisResult(
                    analysis_job_id=analysis_job_id,
                    experiment_id=experiment_id,
                    prompt_template_id=str(self.critic_prompt_template.id),
                    theme_id=self.theme_id,
                    pattern_id=self.pattern_id,
                    content=result_data.get("content", ""),
                    justification=result_data.get("justification", ""),
                    category_id=', '.join(result_data.get("categories", [])),
                    self_confidence=float(result_data.get("self_confidence", 0.0)),
                    is_witness=result_data.get("is_witness"),
                    rewritten_phrase=result_data.get("rewritten_phrase"),
                    rewritten_explanation=result_data.get("rewritten_explanation"),
                    defence_verdict=result_data.get("defence_verdict"),
                    defence_pattern=result_data.get("defence_pattern"),
                    defence_argument=result_data.get("defence_argument"),
                    reviewer_final_verdict=result_data.get("reviewer_final_verdict"),
                    reviewer_confidence_score=float(result_data.get("reviewer_confidence_score", 0.0)),
                    reviewer_reasoning=result_data.get("reviewer_reasoning"),
                )
                results.append(result)

            logger.info(f"Found {len(results)} results for section {section_id} (LangGraph)")

            if self.save_results:
                self.save_results_to_db(results)

            return results

        except Exception as e:
            logger.error(f"Error analyzing section {section_id}: {str(e)}")
            raise

    def _build_initial_state(
            self,
            text: str,
            pattern: str
        ) -> State:
        
        return State(
            text_=text,
            pattern_=pattern,
            references=[],
            results=[],
        )
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""

        # Define subgraph
        # START
        # ├── is_witness ─ END
        # ├── rewrite ─ END
        # └── defence - reviewer - END
        sub_builder = StateGraph(ReferenceState)
        sub_builder.add_node("is_witness", self._is_witness)
        sub_builder.add_node("rewrite", self._rewrite)
        sub_builder.add_node("defence", self._defence)
        sub_builder.add_node("reviewer", self._reviewer)

        sub_builder.add_edge(START, "is_witness")
        sub_builder.add_edge(START, "rewrite")
        sub_builder.add_edge(START, "defence")
        sub_builder.add_edge("defence", "reviewer")
        sub_builder.add_edge("reviewer", END)
        sub_builder.add_edge("is_witness", END)
        sub_builder.add_edge("rewrite", END)

        sub_graph = sub_builder.compile()
        
        # Define main graph
        # START
        # └── critic ─ [subgraph for r in references] - END
        builder = StateGraph(State)
        builder.add_node("critic", self._critic)
        builder.add_node("subgraph", sub_graph)
        
        # Fan-Out: Start to critic
        builder.add_edge(START, "critic")
        
        # Dynamic Fan-Out: Connect generator to workers via conditional edge
        def map_items(state: State):
            """Map each reference to a Send object for the subgraph worker.
            
            "Conditional edge" logic returns a Send objects for each item
            """
            return [
                Send(
                    "subgraph",  # Target node (our subgraph)
                    {
                        "text": state["text_"],
                        "pattern": state["pattern_"],
                        **item,
                    },  # The initial state for the worker
                )
                for item in state["references"]
            ]
        
        builder.add_conditional_edges(
            "critic",
            map_items,
            ["subgraph"],  # Expected destination
        )

        # Fan-In: The worker results are automatically reduced into 'results'
        # because of the operator.add annotation in MainState.
        builder.add_edge("subgraph", END)

        return builder.compile()
    
    def _parse_results(self, graph_results: State) -> List[dict]:
        """Parse the final results from the graph execution."""
        references = graph_results["references"]
        results = graph_results["results"]
        for reference in references:
            hash_id = reference["hash_id"]
            for result in results:
                if result.get("hash_id") == hash_id:
                    reference.update(result)

        return references

    def _call_model(self, prompt: str) -> str:
        """Call the LLM API."""
        messages = [HumanMessage(content=prompt)]
        response = self.llm_client.invoke(messages)
        return response.content

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _critic(self, state: State) -> dict:
        """Invoke the critic prompt to get references."""
        text = state["text_"]
        prompt_template = Environment(autoescape=True).from_string(
            source=self.critic_prompt_template.template
        )
        compiled_prompt = prompt_template.render(contextText=text)
        critic_response_content = self._call_model(compiled_prompt)
        logger.debug("critic invoked")
        if '"analysis_results": []' in critic_response_content:
            return {"references": []}
        critic_response_content_json = json.loads(
            critic_response_content.replace("```json", "").replace("```", "").strip()
        )
        critic_response_content_json_hashed = [
            {"hash_id": md5(i["content"].encode()).hexdigest(), **i}
            for i in critic_response_content_json["analysis_results"]
        ]
        return {"references": critic_response_content_json_hashed}

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _is_witness(self, reference_state: ReferenceState) -> ReferenceState:
        """Identify if the phrase is a witness statement."""
        text = reference_state["text"]
        prompt_template = Environment(autoescape=True).from_string(
            source=self.is_witness_prompt_template.template
        )
        complied_prompt = prompt_template.render(
            police_report=text,
            phrase=reference_state["content"]
        )
        is_witness_response_content = self._call_model(complied_prompt)
        is_witness_response_content_clean = json.loads(
            is_witness_response_content.replace("```json", "").replace("```", "").strip()
        )
        logger.debug("is_witness invoked")
        return {
            "results": [
                {
                    "hash_id": reference_state["hash_id"],
                    "is_witness": is_witness_response_content_clean["response"]
                }
            ]
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _rewrite(self, reference_state: ReferenceState) -> ReferenceState:
        """Rewrite the phrase for clarity."""
        text = reference_state["text"]
        prompt_template = Environment(autoescape=True).from_string(
            source=self.rewrite_prompt_template.template
        )
        compiled_prompt = prompt_template.render(
            police_report=text,
            phrase=reference_state["content"],
            justification=reference_state["justification"],
            pattern=reference_state["pattern"],
        )
        rewrite_response_content = self._call_model(compiled_prompt)
        rewrite_response_content_clean = json.loads(
            rewrite_response_content.replace("```json", "").replace("```", "").strip()
        )
        logger.debug("rewrite invoked")
        return {
            "results": [
                {
                    "hash_id": reference_state["hash_id"],
                    "rewritten_phrase": rewrite_response_content_clean["rewritten_phrase"],
                    "rewritten_explanation": rewrite_response_content_clean["explanation"],
                }
            ]
        }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _defence(self, reference_state: ReferenceState) -> ReferenceState:
        """Generate a defence argument for the phrase."""
        text = reference_state["text"]
        prompt_template = Environment(autoescape=True).from_string(
            source=self.defence_prompt_template.template
        )
        compiled_prompt = prompt_template.render(
            police_report=text,
            phrase=reference_state["content"],
            pattern=reference_state["pattern"],
            justification=reference_state["justification"],
        )
        defence_response_content = self._call_model(compiled_prompt)
        defence_response_content_clean = json.loads(
            defence_response_content.replace("```json", "").replace("```", "").strip()
        )
        logger.debug("defence invoked")
        return {"defence_response": defence_response_content_clean}
    
    def _reviewer(self, reference_state: ReferenceState) -> ReferenceState:
        """Review the defence argument for the phrase."""
        text = reference_state["text"]
        prompt_template = Environment(autoescape=True).from_string(
            source=self.reviewer_prompt_template.template
        )
        compiled_prompt = prompt_template.render(
            police_report=text,
            phrase=reference_state["content"],
            pattern=reference_state["pattern"],
            justification=reference_state["justification"],
            defence_argument=reference_state["defence_response"]["argument"],
            defence_verdict=reference_state["defence_response"]["verdict"],
            defence_pattern=reference_state["defence_response"]["pattern"],
        )
        reviewer_response_content = self._call_model(compiled_prompt)
        reviewer_response_content_clean = json.loads(
            reviewer_response_content.replace("```json", "").replace("```", "")
        )
        logger.debug("reviewer invoked")
        return {
            "results": [
                {
                    "hash_id": reference_state["hash_id"],
                    "defence_verdict": reference_state["defence_response"]["verdict"],
                    "defence_pattern": reference_state["defence_response"]["pattern"],
                    "defence_argument": reference_state["defence_response"]["argument"],
                    "reviewer_final_verdict": reviewer_response_content_clean["final_verdict"],
                    "reviewer_confidence_score": reviewer_response_content_clean["self_confidence_score"],
                    "reviewer_reasoning": reviewer_response_content_clean["reasoning"],
                },
            ]
        }
