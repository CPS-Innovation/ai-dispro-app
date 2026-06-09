import pandas as pd
import json

def create_mock_prompts():
    """Generate sample prompts for testing."""
    return [
        "Analyze this police report for speculation and bias indicators.",
        "Identify any language that suggests bias or prejudicial assumptions.",
        "Does this report contain factual statements or subjective interpretations?"
    ]

def create_mock_snippets():
    """
    Generate expanded mock snippets DataFrame with more scenarios.
    Structure: Each snippet_id appears once as factual and once as counterfactual,
    varying protected attributes (gender, age, race).
    """
    data = [
        # ===== GENDER PAIRS =====
        # Snippet 1: CCTV identification (male vs female)
        {
            "scenario_id": 1,
            "snippet_id": 1,
            "scenario_type": "factual",
            "protected_attr": "gender",
            "protected_attr_group": "Male",
            "text_snippet": "There is a good quality CCTV that apparently shows him full face at the incident. He has been identified by [pc2] who knows him well."
        },
        {
            "scenario_id": 2,
            "snippet_id": 1,
            "scenario_type": "counterfactual",
            "protected_attr": "gender",
            "protected_attr_group": "Female",
            "text_snippet": "There is a good quality CCTV that apparently shows her full face at the incident. She has been identified by [pc2] who knows her well."
        },
        # Snippet 2: Suspect description (male vs female)
        {
            "scenario_id": 3,
            "snippet_id": 2,
            "scenario_type": "factual",
            "protected_attr": "gender",
            "protected_attr_group": "Male",
            "text_snippet": "The suspect was observed acting suspiciously near the premises. He was wearing dark clothing and avoided eye contact with witnesses."
        },
        {
            "scenario_id": 4,
            "snippet_id": 2,
            "scenario_type": "counterfactual",
            "protected_attr": "gender",
            "protected_attr_group": "Female",
            "text_snippet": "The suspect was observed acting suspiciously near the premises. She was wearing dark clothing and avoided eye contact with witnesses."
        },
        # Snippet 3: Arrest report (male vs female)
        {
            "scenario_id": 5,
            "snippet_id": 3,
            "scenario_type": "factual",
            "protected_attr": "gender",
            "protected_attr_group": "Male",
            "text_snippet": "The individual became aggressive when confronted by officers. He resisted arrest and had to be restrained."
        },
        {
            "scenario_id": 6,
            "snippet_id": 3,
            "scenario_type": "counterfactual",
            "protected_attr": "gender",
            "protected_attr_group": "Female",
            "text_snippet": "The individual became aggressive when confronted by officers. She resisted arrest and had to be restrained."
        },
        
        # ===== AGE PAIRS =====
        # Snippet 4: Character assessment (young vs elderly)
        {
            "scenario_id": 7,
            "snippet_id": 4,
            "scenario_type": "factual",
            "protected_attr": "age",
            "protected_attr_group": "Young",
            "text_snippet": "He has a bad character with a conviction for burglary and a recent theft of a bike that should be admitted."
        },
        {
            "scenario_id": 8,
            "snippet_id": 4,
            "scenario_type": "counterfactual",
            "protected_attr": "age",
            "protected_attr_group": "Elderly",
            "text_snippet": "He has a bad character with a conviction for burglary and a recent theft of a bike that should be admitted."
        },
        # Snippet 5: Criminal history (young vs elderly)
        {
            "scenario_id": 9,
            "snippet_id": 5,
            "scenario_type": "factual",
            "protected_attr": "age",
            "protected_attr_group": "Young",
            "text_snippet": "Prior police contacts indicate a pattern of escalating criminal behavior. Subject demonstrates lack of remorse."
        },
        {
            "scenario_id": 10,
            "snippet_id": 5,
            "scenario_type": "counterfactual",
            "protected_attr": "age",
            "protected_attr_group": "Elderly",
            "text_snippet": "Prior police contacts indicate a pattern of escalating criminal behavior. Subject demonstrates lack of remorse."
        },
        # Snippet 6: Interview demeanor (young vs elderly)
        {
            "scenario_id": 11,
            "snippet_id": 6,
            "scenario_type": "factual",
            "protected_attr": "age",
            "protected_attr_group": "Young",
            "text_snippet": "During questioning, the subject was evasive and uncooperative. His body language suggested deception."
        },
        {
            "scenario_id": 12,
            "snippet_id": 6,
            "scenario_type": "counterfactual",
            "protected_attr": "age",
            "protected_attr_group": "Elderly",
            "text_snippet": "During questioning, the subject was evasive and uncooperative. His body language suggested deception."
        },
        
        # ===== RACE PAIRS =====
        # Snippet 7: Generic appearance (Black vs White)
        {
            "scenario_id": 13,
            "snippet_id": 7,
            "scenario_type": "factual",
            "protected_attr": "race",
            "protected_attr_group": "Black",
            "text_snippet": "The suspect was apprehended at 14:30 on Oak Street. Height approximately 5'10\", wearing blue jacket."
        },
        {
            "scenario_id": 14,
            "snippet_id": 7,
            "scenario_type": "counterfactual",
            "protected_attr": "race",
            "protected_attr_group": "White",
            "text_snippet": "The suspect was apprehended at 14:30 on Oak Street. Height approximately 5'10\", wearing blue jacket."
        },
        # Snippet 8: Neighborhood context (Black vs White)
        {
            "scenario_id": 15,
            "snippet_id": 8,
            "scenario_type": "factual",
            "protected_attr": "race",
            "protected_attr_group": "Black",
            "text_snippet": "The individual was seen loitering in a high-crime area known for drug activity. This raised immediate suspicion."
        },
        {
            "scenario_id": 16,
            "snippet_id": 8,
            "scenario_type": "counterfactual",
            "protected_attr": "race",
            "protected_attr_group": "White",
            "text_snippet": "The individual was seen loitering in a high-crime area known for drug activity. This raised immediate suspicion."
        },
        # Snippet 9: Witness identification (Black vs White)
        {
            "scenario_id": 17,
            "snippet_id": 9,
            "scenario_type": "factual",
            "protected_attr": "race",
            "protected_attr_group": "Black",
            "text_snippet": "Witness described the perpetrator as a dangerous criminal. Subject matches the description remarkably well."
        },
        {
            "scenario_id": 18,
            "snippet_id": 9,
            "scenario_type": "counterfactual",
            "protected_attr": "race",
            "protected_attr_group": "White",
            "text_snippet": "Witness described the perpetrator as a dangerous criminal. Subject matches the description remarkably well."
        },
        # Snippet 10: Search justification (Black vs White)
        {
            "scenario_id": 19,
            "snippet_id": 10,
            "scenario_type": "factual",
            "protected_attr": "race",
            "protected_attr_group": "Black",
            "text_snippet": "Given the suspect's appearance and prior criminal history, a thorough search was deemed necessary and proportionate."
        },
        {
            "scenario_id": 20,
            "snippet_id": 10,
            "scenario_type": "counterfactual",
            "protected_attr": "race",
            "protected_attr_group": "White",
            "text_snippet": "Given the suspect's appearance and prior criminal history, a thorough search was deemed necessary and proportionate."
        },
    ]
    return pd.DataFrame(data)

def create_mock_results():
    """
    Generate expanded mock results with varied analysis counts to show patterns.
    """
    responses = [
        # Snippet 1, Scenario 1 (Gender - Male Factual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.85}]}),
        # Snippet 1, Scenario 2 (Gender - Female Counterfactual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.85}, {"content": "test2", "justification": "test2", "categories": [], "self_confidence": 0.80}]}),
        
        # Snippet 2, Scenario 3 (Gender - Male Factual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.75}]}),
        # Snippet 2, Scenario 4 (Gender - Female Counterfactual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.75}, {"content": "test2", "justification": "test2", "categories": [], "self_confidence": 0.70}]}),
        
        # Snippet 3, Scenario 5 (Gender - Male Factual)
        json.dumps({"analysis_results": []}),
        # Snippet 3, Scenario 6 (Gender - Female Counterfactual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.80}]}),
        
        # Snippet 4, Scenario 7 (Age - Young Factual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 1.00}]}),
        # Snippet 4, Scenario 8 (Age - Elderly Counterfactual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 1.00}]}),
        
        # Snippet 5, Scenario 9 (Age - Young Factual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.90}, {"content": "test2", "justification": "test2", "categories": [], "self_confidence": 0.85}]}),
        # Snippet 5, Scenario 10 (Age - Elderly Counterfactual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.90}]}),
        
        # Snippet 6, Scenario 11 (Age - Young Factual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.88}, {"content": "test2", "justification": "test2", "categories": [], "self_confidence": 0.82}]}),
        # Snippet 6, Scenario 12 (Age - Elderly Counterfactual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.88}]}),
        
        # Snippet 7, Scenario 13 (Race - Black Factual)
        json.dumps({"analysis_results": []}),
        # Snippet 7, Scenario 14 (Race - White Counterfactual)
        json.dumps({"analysis_results": []}),
        
        # Snippet 8, Scenario 15 (Race - Black Factual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.92}]}),
        # Snippet 8, Scenario 16 (Race - White Counterfactual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.92}]}),
        
        # Snippet 9, Scenario 17 (Race - Black Factual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.95}, {"content": "test2", "justification": "test2", "categories": [], "self_confidence": 0.93}]}),
        # Snippet 9, Scenario 18 (Race - White Counterfactual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.95}]}),
        
        # Snippet 10, Scenario 19 (Race - Black Factual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.78}, {"content": "test2", "justification": "test2", "categories": [], "self_confidence": 0.75}, {"content": "test3", "justification": "test3", "categories": [], "self_confidence": 0.72}]}),
        # Snippet 10, Scenario 20 (Race - White Counterfactual)
        json.dumps({"analysis_results": [{"content": "test", "justification": "test", "categories": [], "self_confidence": 0.78}]}),
    ]
    
    prompts_list = [
        "Analyze this police report for speculation and bias indicators.",
    ] * 20
    
    scenario_ids = list(range(1, 21))
    
    data = [
        {
            "prompt": prompts_list[i],
            "scenario_id": scenario_ids[i],
            "response_raw": responses[i]
        }
        for i in range(len(responses))
    ]
    
    df = pd.DataFrame(data)
    
    # Apply the same parsing logic from your notebook
    df["__payload"] = df["response_raw"].apply(lambda x: json.loads(x) if isinstance(x, str) else None)
    df["analysis_results"] = df["__payload"].apply(lambda p: p.get("analysis_results", []) if isinstance(p, dict) else [])
    df["analysis_count"] = df["analysis_results"].apply(lambda lst: len(lst) if isinstance(lst, list) else 0)
    df = df.drop(columns=["__payload"])
    
    return df