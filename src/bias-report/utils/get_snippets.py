import ast
from pathlib import Path
import pandas as pd


REQUIRED_COLUMNS = [
    "scenario_id",
    "case_id",
    "snippet_id",
    "scenario_type",
    "protected_attr",
    "protected_attr_group",
    "protected_value",
    "text_snippet",
    "change_summary",
]


def _to_list(value):
    """
    Convert a cell value to a Python list.
    Handles:
      - actual lists
      - empty cells
      - JSON-like / Python-like list strings
      - any other value -> wrapped in a list
    """
    if isinstance(value, list):
        return value
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return []
        try:
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except Exception:
            # Not parseable — return string as single-item list
            return [s]
    # Fallback for any edge cases
    return [value]


def get_snippets(path: str = "./data/senarios.xlsx", sheet_name=0) -> pd.DataFrame:
    """
    Loads snippet data from an Excel file and returns a clean DataFrame.

    The returned DataFrame includes:
        scenario_id
        case_id
        snippet_id
        scenario_type
        protected_attr
        protected_attr_group
        protected_value
        text_snippet
        change_summary (as a list)

    Parameters
    ----------
    path : str
        Path to the Excel file. Defaults to ../data/snippets.xlsx.
    sheet_name : int or str
        Excel sheet index or name.

    Returns
    -------
    pandas.DataFrame
        A cleaned DataFrame with 'change_summary' normalized to a list.
    """

    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Could not find Excel file at: {file_path}")

    # Load Excel
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")

    # Ensure required columns exist
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(
            "Excel file is missing required columns: "
            + ", ".join(missing)
            + f". Columns present: {list(df.columns)}"
        )

    # Keep only required columns
    df = df[REQUIRED_COLUMNS].copy()

    # Normalize change_summary column
    df["change_summary"] = df["change_summary"].apply(_to_list)

    # Ensure text-like fields have None instead of NaN
    text_cols = [
        "scenario_type",
        "protected_attr",
        "protected_attr_group",
        "protected_value",
        "text_snippet",
    ]
    for col in text_cols:
        df[col] = df[col].where(~df[col].isna(), None)

    return df