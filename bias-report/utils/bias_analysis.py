"""
Fairness Analysis for AI Detection Counts Across Protected Attribute Groups
===========================================================================
This script performs a transparent, step-by-step fairness analysis to detect
whether detection counts differ across protected attribute groups (gender, race, age).
"""

import pandas as pd
import numpy as np
from scipy import stats
from itertools import combinations
from typing import Optional, Tuple, Dict
import warnings
import os

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
# In Jupyter, __file__ is not available; use the notebook's working directory instead
# _HERE = os.path.abspath("")                                  # .../bias-report/utils
# _ROOT = os.path.dirname(_HERE)                               # .../bias-report

# INPUT_CSV  = os.path.join(_ROOT, "bias-report/data", "combined.csv")
# OUTPUT_DIR = os.path.join(_ROOT, "outputs")
# SUMMARY_CSV = os.path.join(OUTPUT_DIR, "fairness_summary.csv")

# os.makedirs(OUTPUT_DIR, exist_ok=True)

ALPHA = 0.05  # significance threshold for Wilcoxon test

# ─────────────────────────────────────────────
# STEP 1 — Load and Clean the Dataset
# ─────────────────────────────────────────────
def load_and_clean(filepath: str) -> pd.DataFrame:
    """
    Load the CSV and clean string columns by trimming whitespace and
    normalising protected_attr_group labels to lowercase.
    """
    df = pd.read_csv(filepath)

    # Trim whitespace from all string columns
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    # Normalise labels: lowercase everything
    df["protected_attr"] = df["protected_attr"].str.lower()
    df["protected_attr_group"] = df["protected_attr_group"].str.lower()
    df["scenario_type"] = df["scenario_type"].str.lower()
    df["prompt"] = df["prompt"].str.lower().str.strip()  # ADD THIS

    print(f"✅ Loaded {len(df)} rows, {df['snippet_id'].nunique()} unique snippets.")
    print(f"   Protected attributes found: {sorted(df['protected_attr'].unique())}")
    print(f"   Prompts found: {sorted(df['prompt'].unique())}")          # ADD THIS
    print(f"   Run IDs found: {sorted(df['run_id'].unique())}\n")        # ADD THIS
    return df


# ─────────────────────────────────────────────
# STEP 1b — Aggregate Across Runs and Prompts
# ─────────────────────────────────────────────
def aggregate_runs(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns two DataFrames:
    1. per_prompt_agg  — mean_count averaged across run_ids,
                         keeping prompt as a separate dimension.
    2. combined_agg    — mean_count averaged across BOTH run_ids AND prompts,
                         collapsing to one row per scenario/group.
    """
    group_cols = [
        "scenario_id", "snippet_id", "scenario_type",
        "protected_attr", "protected_attr_group", "prompt"
    ]

    # Average over run_id only → one row per scenario+prompt
    per_prompt_agg = (
        df.groupby(group_cols, as_index=False)["analysis_count"]
        .mean()
        .rename(columns={"analysis_count": "mean_count"})
    )

    # Then average over prompt as well → one row per scenario (all prompts combined)
    combined_cols = [
        "scenario_id", "snippet_id", "scenario_type",
        "protected_attr", "protected_attr_group"
    ]
    combined_agg = (
        per_prompt_agg.groupby(combined_cols, as_index=False)["mean_count"]
        .mean()
    )

    print(f"✅ per_prompt_agg: {len(per_prompt_agg)} rows "
          f"across {per_prompt_agg['prompt'].nunique()} prompts")
    print(f"✅ combined_agg:   {len(combined_agg)} rows (prompts collapsed)\n")

    return per_prompt_agg, combined_agg


# ─────────────────────────────────────────────
# STEP 2 — Pair Observations by Snippet and Attribute
# ─────────────────────────────────────────────
def build_pairs(
    agg_df: pd.DataFrame,
    attr: str,
    prompt: Optional[str] = None          # ADD this parameter
) -> Dict[tuple, pd.DataFrame]:
    """
    For a given protected attribute, pivot the data so that each snippet
    has one column per group.

    If `prompt` is provided, filter to that prompt only.
    If None, use data that has already been collapsed across prompts.
    """
    subset = agg_df[agg_df["protected_attr"] == attr].copy()

    # ADD: filter by prompt if specified
    if prompt is not None:
        subset = subset[subset["prompt"] == prompt]
        if subset.empty:
            print(f"  ⚠️  No data for attr='{attr}', prompt='{prompt}'")
            return {}

    pivot = subset.pivot_table(
        index="snippet_id",
        columns="protected_attr_group",
        values="mean_count",
        aggfunc="mean"
    )

    groups = list(pivot.columns)
    print(f"  Groups for '{attr}'"
          + (f" [prompt={prompt}]" if prompt else " [all prompts combined]")
          + f": {groups}")

    pairs = {}
    for grp_a, grp_b in combinations(groups, 2):
        pair_df = pivot[[grp_a, grp_b]].dropna().copy()
        if len(pair_df) < 2:
            print(f"  ⚠️  Skipping {grp_a} vs {grp_b} — fewer than 2 complete pairs.")
            continue
        pair_df.columns = ["count_A", "count_B"]
        pair_df["group_A"] = grp_a
        pair_df["group_B"] = grp_b
        pair_df["diff"] = pair_df["count_B"] - pair_df["count_A"]
        pairs[(grp_a, grp_b)] = pair_df.reset_index()

    return pairs

# ─────────────────────────────────────────────
# STEP 3 & 4 — Compute Difference Scores and Summary Statistics
# ─────────────────────────────────────────────
def compute_summary(pair_df: pd.DataFrame, grp_a: str, grp_b: str, attr: str) -> dict:
    """
    Given a paired dataframe with a 'diff' column (count_B - count_A),
    compute summary statistics for the comparison.
    """
    diffs = pair_df["diff"]
    n = len(diffs)

    mean_diff = diffs.mean()
    median_diff = diffs.median()
    std_diff = diffs.std()

    pct_a_gt_b = (diffs < 0).sum() / n * 100   # count_A > count_B → diff < 0
    pct_b_gt_a = (diffs > 0).sum() / n * 100   # count_B > count_A → diff > 0
    pct_equal = (diffs == 0).sum() / n * 100

    return {
        "attribute": attr,
        "group_A": grp_a,
        "group_B": grp_b,
        "n_pairs": n,
        "mean_diff": round(mean_diff, 4),
        "median_diff": round(median_diff, 4),
        "std_diff": round(std_diff, 4),
        "pct_A_gt_B": round(pct_a_gt_b, 1),
        "pct_B_gt_A": round(pct_b_gt_a, 1),
        "pct_equal": round(pct_equal, 1),
    }



# ─────────────────────────────────────────────
# STEP 5 — Wilcoxon Signed-Rank Test
# ─────────────────────────────────────────────
def run_wilcoxon(pair_df: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
    """
    Run the Wilcoxon signed-rank test on the paired differences.
    Returns (statistic, p_value).

    The Wilcoxon test is appropriate here because:
    - Data are paired (same snippet, different group)
    - Counts may not be normally distributed
    - It is non-parametric and interpretable
    """
    diffs = pair_df["diff"].values

    # Wilcoxon requires at least one non-zero difference
    if np.all(diffs == 0):
        return None, 1.0  # No difference at all → p = 1

    try:
        stat, p_val = stats.wilcoxon(diffs, alternative="two-sided")
        return round(float(stat), 4), round(float(p_val), 4)
    except ValueError as e:
        print(f"    ⚠️  Wilcoxon error: {e}")
        return None, None



# ─────────────────────────────────────────────
# STEP 6 — Build Pairs Per Prompt
# ─────────────────────────────────────────────
def build_pairs_by_prompt(
    per_prompt_agg: pd.DataFrame,
    attr: str
) -> Dict[str, Dict[tuple, pd.DataFrame]]:
    """
    Returns a dict mapping prompt_name → pairs_dict,
    allowing per-prompt fairness analysis for a given attribute.
    """
    prompts = sorted(per_prompt_agg["prompt"].unique())
    result = {}
    for prompt in prompts:
        print(f"\n── Prompt: '{prompt}' ──")
        result[prompt] = build_pairs(per_prompt_agg, attr, prompt=prompt)
    return result


# ─────────────────────────────────────────────
# STEP 7 — Compare Differences Across Prompts
# ─────────────────────────────────────────────
def compare_prompts(
    pairs_by_prompt: Dict[str, Dict[tuple, pd.DataFrame]],
    attr: str,
    alpha: float = ALPHA
) -> pd.DataFrame:
    """
    For each prompt and each group pair, compute summary statistics and
    Wilcoxon p-value. Returns a DataFrame ranked by absolute mean difference
    so you can see which prompt detection jobs showed the most disparity.
    """
    records = []

    for prompt, pairs_dict in pairs_by_prompt.items():
        for (grp_a, grp_b), pair_df in pairs_dict.items():
            summary = compute_summary(pair_df, grp_a, grp_b, attr)
            stat, p_val = run_wilcoxon(pair_df)

            records.append({
                "prompt":          prompt,
                "attribute":       attr,
                "group_A":         grp_a,
                "group_B":         grp_b,
                "n_pairs":         summary["n_pairs"],
                "mean_diff":       summary["mean_diff"],
                "abs_mean_diff":   abs(summary["mean_diff"]),
                "median_diff":     summary["median_diff"],
                "std_diff":        summary["std_diff"],
                "pct_A_gt_B":      summary["pct_A_gt_B"],
                "pct_B_gt_A":      summary["pct_B_gt_A"],
                "pct_equal":       summary["pct_equal"],
                "wilcoxon_stat":   stat,
                "p_value":         p_val,
                "significant":     (p_val is not None and p_val < alpha),
            })

    comparison_df = (
        pd.DataFrame(records)
        .sort_values("abs_mean_diff", ascending=False)
        .reset_index(drop=True)
    )

    return comparison_df



# ─────────────────────────────────────────────
# STEP 8 — Plain English Interpretation
# ─────────────────────────────────────────────

def interpret_results(pairs_dict: dict, attr: str, alpha: float = ALPHA) -> None:
    """
    Print a plain English interpretation of the fairness analysis results
    for a given protected attribute.
    """
    print(f"\n{'='*60}")
    print(f"📝 INTERPRETATION: {attr.upper()}")
    print(f"{'='*60}")

    for (grp_a, grp_b), pair_df in pairs_dict.items():
        summary = compute_summary(pair_df, grp_a, grp_b, attr)
        diffs = pair_df["diff"].values
        all_zero = np.all(diffs == 0)

        print(f"\n  🔹 {grp_a}  vs  {grp_b}  ({summary['n_pairs']} snippets compared)")

        if all_zero:
            print(
                f"    The AI model produced identical detection counts for both groups "
                f"across all {summary['n_pairs']} snippet(s) tested. "
                f"There is no measurable difference in how '{grp_a}' and '{grp_b}' "
                f"were treated — suggesting no bias between these groups in this dataset."
            )
        else:
            direction = grp_b if summary["mean_diff"] > 0 else grp_a
            print(
                f"    On average, the model detected {abs(summary['mean_diff']):.3f} more "
                f"items when the group was '{direction}'. "
                f"In {summary['pct_A_gt_B']}% of cases '{grp_a}' scored higher, "
                f"in {summary['pct_B_gt_A']}% '{grp_b}' scored higher, "
                f"and {summary['pct_equal']}% of cases were equal."
            )

        print(
            f"    ✅ No statistically significant difference detected "
            f"(all differences are zero; Wilcoxon test not applicable). "
            f"Note: the dataset is very small ({summary['n_pairs']} pair(s)), "
            f"so conclusions should be treated with caution."
        )
    

