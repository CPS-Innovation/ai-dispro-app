import pandas as pd
from pathlib import Path

def get_prompts(path: str = "./data/prompts.xlsx") -> list[str]:
    """
    Loads an Excel file containing a column called 'prompts'
    and returns it as a list of strings.

    Parameters
    ----------
    path : str
        File path to the Excel file. Defaults to ./data/prompt.xlsx

    Returns
    -------
    list[str]
        A list of prompt strings suitable for looping.
    """

    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Could not find Excel file at: {file_path}")

    # Load Excel
    df = pd.read_excel(file_path, engine="openpyxl")

    for col in ("prompt", "prompt_name"):
        # Validate expected column
        if col not in df.columns:
            raise KeyError("Excel file must contain a column named '{col}'.")

    df = df[["prompt_name", "prompt"]].dropna(subset=["prompt"])

    # Return as dict
    return df.to_dict(orient="records")