from typing import List, Optional, Tuple
import pandas as pd
from openai import AzureOpenAI  # make sure you have: pip install openai>=1.0.0
import os
from dotenv import load_dotenv
import json
import re



load_dotenv()
AZURE_AI_FOUNDRY_API_KEY = os.getenv("AZURE_AI_FOUNDRY_API_KEY")
AZURE_AI_FOUNDRY_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
AZURE_AI_FOUNDRY_API_VERSION = os.getenv("AZURE_AI_FOUNDRY_API_VERSION")
AZURE_AI_FOUNDRY_DEPLOYMENT_NAME = os.getenv("AZURE_AI_FOUNDRY_DEPLOYMENT_NAME")




def run_prompts_over_snippets(
    prompts: List[dict],
    snippets_df: pd.DataFrame,
    print_responses: bool,
    run_id: str
) -> pd.DataFrame:

    """
    For each prompt p in `prompts` and each row in `snippets_df`, combine:
        prompt_and_snippet = f"{p}{joiner}{row.text_snippet}"
    then send to Azure OpenAI and collect responses.

    Returns a DataFrame with:
        prompt, scenario_id, case_id, snippet_id, text_snippet, prompt_and_snippet, response
    """


    if not isinstance(snippets_df, pd.DataFrame):
        raise TypeError("snippets_df must be a pandas DataFrame")

    # Ensure required column exists
    if "text_snippet" not in snippets_df.columns:
        raise KeyError("snippets_df must contain a 'text_snippet' column")

    # Validate prompt in dicts
    for i, p in enumerate(prompts):
        if not isinstance(p, dict):
            raise TypeError(f"Each item in prompts must be a dict, got {type(p)}")
        for key in ("prompt_name", "prompt"):
            if key not in p:
                raise KeyError(f"Prompt dict at index '{i}' is missing required '{key}'")

    client = AzureOpenAI(
        api_key= AZURE_AI_FOUNDRY_API_KEY,
        api_version=AZURE_AI_FOUNDRY_API_VERSION,
        azure_endpoint=AZURE_AI_FOUNDRY_ENDPOINT
    )

    records = []

    joiner = "\n\n"

    # Use .itertuples for speed and attribute-style access
    for p in prompts:
        p_name = str(p["prompt_name"]).strip()
        p_clean = str(p["prompt"]).strip()

        for row in snippets_df.itertuples(index=False):
            # Safely get text_snippet and identifiers, even if columns are missing
            text_snippet: Optional[str] = getattr(row, "text_snippet", None)
            text_snippet = "" if text_snippet is None or pd.isna(text_snippet) else str(text_snippet)

            prompt_and_snippet = f"{p_clean}{joiner}{text_snippet}"
            
            
            
            response = client.chat.completions.create(
                model=AZURE_AI_FOUNDRY_DEPLOYMENT_NAME,  # Azure deployment name
                messages=[
                    {"role": "system", "content": "You are an AI assistant"},
                    {"role": "user", "content": prompt_and_snippet},
                ],
                temperature=0.0,
                max_tokens=4096,
                stream=False
            )


            answer = response.choices[0].message.content if response.choices else ""

            if print_responses:
                print(answer)

            
            # Context identifiers
            scenario_id = getattr(row, "scenario_id", None)
           
         
            # Append one sentinel row indicating no results
            records.append({
                "run_id":run_id,
                "prompt_name":p_name,
                "prompt": p_clean,
                "scenario_id": scenario_id,
                "response_raw": answer,        # keep raw JSON for auditing
            })
        


    return pd.DataFrame.from_records(records)
        

def _strip_code_fences(s: str) -> str:
    """Remove markdown code fences from a string."""
    s = s.strip()
    if s.startswith("```"):
        # remove a leading fence with optional language tag
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s, count=1, flags=re.DOTALL)
        # remove trailing fence if present
        s = re.sub(r"\s*```$", "", s, count=1)
    return s.strip()


def _extract_first_json_object(s: str) -> str:
    """Return the substring containing the first balanced JSON object, or raise."""
    s = s.strip()
    start = s.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response (missing '{').")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
    raise ValueError("Unbalanced JSON braces in response.")


def parse_payload(raw) -> dict:
    """
    Convert a cell (string or dict) to a Python dict.
    - If dict -> return as-is
    - If string -> strip code fences, try json.loads
      - If extra prose present, extract only the first JSON object and parse that
    - On any parse error -> return None
    """
    if pd.isna(raw):
        return None
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None

    text = _strip_code_fences(raw)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            obj_str = _extract_first_json_object(text)
            return json.loads(obj_str)
        except Exception:
            return None


def extract_analysis_results(payload) -> list:
    """
    From a parsed payload (dict/None), return the list in 'analysis_results',
    or [] if missing/wrong type.
    """
    if not isinstance(payload, dict):
        return []
    results = payload.get("analysis_results", [])
    return results if isinstance(results, list) else []


def parse_response_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse raw API responses and extract analysis counts.
    
    Args:
        df: DataFrame with 'response_raw' column from API responses
        
    Returns:
        DataFrame with added 'analysis_count' column
    """
    if "response_raw" not in df.columns:
        raise KeyError("DataFrame must contain 'response_raw' column")
    
    # Parse JSON payloads
    df["__payload"] = df["response_raw"].apply(parse_payload)
    
    # Extract analysis results list
    df["analysis_results"] = df["__payload"].apply(extract_analysis_results)
    
    # Count analysis results
    df["analysis_count"] = df["analysis_results"].apply(
        lambda lst: len(lst) if isinstance(lst, list) else 0
    )
    
    # Drop helper column
    df = df.drop(columns=["__payload"])
    
    return df


def join_with_snippets(results_df: pd.DataFrame, snippets_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge API results with snippet metadata.
    
    Args:
        results_df: DataFrame from parse_response_data() with 'scenario_id'
        snippets_df: DataFrame with snippet metadata (scenario_id, snippet_id, etc.)
        
    Returns:
        Merged DataFrame with all columns
    """
    if "scenario_id" not in results_df.columns:
        raise KeyError("Results DataFrame must contain 'scenario_id' column")
    if "scenario_id" not in snippets_df.columns:
        raise KeyError("Snippets DataFrame must contain 'scenario_id' column")
    
    joined = results_df.merge(
        snippets_df,
        on=["scenario_id"],
        how="left"
    )
    
    return joined


def simplify_joined_results(joined_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract only the essential columns needed for bias analysis.
    
    Args:
        joined_df: DataFrame from join_with_snippets()
        
    Returns:
        Simplified DataFrame with columns for bias analysis
    """
    cols_to_keep = [
        "scenario_id",
        "snippet_id",
        "scenario_type",
        "protected_attr",
        "protected_attr_group",
        "prompt_name",
        "run_id",
        "analysis_count"
    ]
    
    # Verify all required columns exist
    missing = [col for col in cols_to_keep if col not in joined_df.columns]
    if missing:
        raise KeyError(f"Missing required columns: {missing}")
    
    simplified = joined_df[cols_to_keep].copy()
    
    return simplified


def postprocess_analysis_results(
    results_df: pd.DataFrame,
    snippets_df: pd.DataFrame,
    save_to_csv: str = None
) -> pd.DataFrame:
    """
    Complete post-processing pipeline: parse responses, join with snippets, simplify.
    
    This function orchestrates the entire pipeline from raw API responses to
    simplified data ready for bias analysis.
    
    Args:
        results_df: DataFrame from Azure OpenAI API with 'response_raw' column
        snippets_df: DataFrame with snippet metadata
        save_to_csv: Optional path to save simplified results to CSV
        
    Returns:
        Simplified DataFrame ready for bias analysis
        
    Example:
        >>> from utils.run_dispro_analysis import postprocess_analysis_results
        >>> from utils.get_snippets import get_snippets
        >>> results_df = run_prompts_over_snippets(prompts, snippets, False)
        >>> snippets = get_snippets()
        >>> simplified = postprocess_analysis_results(
        ...     results_df,
        ...     snippets,
        ...     save_to_csv="simplified_joined_results.csv"
        ... )
    """
    print("Step 1: Parsing response payloads...")
    parsed_df = parse_response_data(results_df)
    print(f"  ✓ Parsed {len(parsed_df)} responses")
    print(parsed_df.head(2))
    
    print("\nStep 2: Joining with snippet metadata...")
    joined_df = join_with_snippets(parsed_df, snippets_df)
    print(f"  ✓ Joined {len(joined_df)} rows")
    print(joined_df.head(2))
    
    print("\nStep 3: Simplifying to essential columns...")
    simplified_df = simplify_joined_results(joined_df)
    print(f"  ✓ Simplified to {len(simplified_df)} rows × {len(simplified_df.columns)} columns")
    print(f"  Columns: {list(simplified_df.columns)}")
    
    if save_to_csv:
        simplified_df.to_csv(save_to_csv, index=False)
        print(f"\n✓ Saved to: {save_to_csv}")
    
    return simplified_df