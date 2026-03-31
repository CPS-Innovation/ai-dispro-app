# ─────────────────────────────────────────────
# STEP 9 — Generate PDF Bias Report
# ─────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from datetime import datetime
from utils.bias_analysis import (compute_summary, run_wilcoxon)
import pandas as pd
from typing import Dict
from pathlib import Path
import os

# PDF_DIR = Path(__file__).resolve().parent / "outputs"
# PDF_DIR.mkdir(parents=True, exist_ok=True)
# PDF_PATH = str(f"./{PDF_DIR}/dispro_bias_report.pdf")
ALPHA = 0.05


def generate_bias_report(
    df: pd.DataFrame,
    gender_pairs: Dict[tuple, pd.DataFrame],
    age_pairs: Dict[tuple, pd.DataFrame],
    race_pairs: Dict[tuple, pd.DataFrame],
    gender_prompt_comparison: pd.DataFrame,
    age_prompt_comparison: pd.DataFrame,
    race_prompt_comparison: pd.DataFrame,
    output_dir: str,
) -> str:

    output_path =  os.path.join(output_dir, "dispro_summary_report.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2.5 * cm, leftMargin=2.5 * cm,
        topMargin=1.5 * cm,   bottomMargin=2.5 * cm,
    )

    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle", parent=base_styles["Title"],
        fontSize=28, textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=10, alignment=TA_CENTER, fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", parent=base_styles["Normal"],
        fontSize=13, textColor=colors.HexColor("#4a4a8a"),
        spaceAfter=8, alignment=TA_CENTER, fontName="Helvetica-Oblique",
    )
    date_style = ParagraphStyle(
        "DateStyle", parent=base_styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#888888"),
        spaceAfter=20, alignment=TA_CENTER,
    )
    section_heading_style = ParagraphStyle(
        "SectionHeading", parent=base_styles["Heading1"],
        fontSize=16, textColor=colors.HexColor("#1a1a2e"),
        spaceBefore=12, spaceAfter=8, fontName="Helvetica-Bold", borderPad=4,
    )
    sub_heading_style = ParagraphStyle(
        "SubHeading", parent=base_styles["Heading2"],
        fontSize=13, textColor=colors.HexColor("#4a4a8a"),
        spaceBefore=12, spaceAfter=6, fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "BodyText", parent=base_styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#2c2c2c"),
        spaceAfter=8, leading=16, alignment=TA_JUSTIFY,
    )
    index_style = ParagraphStyle(
        "IndexItem", parent=base_styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=5, leftIndent=20, leading=18,
    )
    note_style = ParagraphStyle(
        "NoteStyle", parent=base_styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#666666"),
        spaceAfter=6, leading=14, leftIndent=10, fontName="Helvetica-Oblique",
    )
    card_title_style = ParagraphStyle(
        "CardTitle", parent=base_styles["Normal"],
        fontSize=11, textColor=colors.white,
        spaceAfter=4, alignment=TA_CENTER, fontName="Helvetica-Bold",
    )
    card_body_style = ParagraphStyle(
        "CardBody", parent=base_styles["Normal"],
        fontSize=8, textColor=colors.white,
        spaceAfter=4, alignment=TA_CENTER, leading=12,
    )
    bullet_style = ParagraphStyle(
        "BulletStyle", parent=base_styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#2c2c2c"),
        spaceAfter=6, leading=16, leftIndent=20, bulletIndent=10,
    )

    # ── Inner helpers ────────────────────────

    def _divider(color="#cccccc", thickness=0.5):
        return HRFlowable(
            width="100%", thickness=thickness,
            color=colors.HexColor(color), spaceAfter=10, spaceBefore=4,
        )

    def _make_table(data, col_widths=None):
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  9),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1),
             [colors.HexColor("#f5f5fa"), colors.white]),
            ("FONTSIZE",      (0, 1), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        return t

    def _bias_detected(pairs_dict: Dict) -> bool:
        """Return True if any group pair shows a non-zero mean difference."""
        return any(
            compute_summary(pdf, ga, gb, "")["mean_diff"] != 0
            for (ga, gb), pdf in pairs_dict.items()
        )

    def _significant_bias(pairs_dict: Dict) -> bool:
        """Return True if any group pair has a statistically significant result."""
        for _, pdf in pairs_dict.items():
            _, p = run_wilcoxon(pdf)
            if p is not None and p < ALPHA:
                return True
        return False

    def _key_findings_overview(gender_pairs, age_pairs, race_pairs):
        els = []
        els.append(Paragraph("Key Findings Overview", section_heading_style))
        els.append(_divider())
        els.append(Paragraph(
            "This section summarises the top-level findings from our counterfactual bias testing across "
            "gender, age and race. The table uses a traffic-light colour system to show whether any differences "
            "were observed and how confident we can be in those findings. Each comparison lists the mean difference "
            "in outputs across the counterfactual pairs, along with the associated p-value.  ",
            body_style
        ))
        els.append(Spacer(1, 0.4 * cm))

        # ── Status logic ─────────────────────
        def _status(pairs_dict):
            if _significant_bias(pairs_dict):
                return (
                    "SIGNIFICANT BIAS DETECTED",
                    colors.HexColor("#c0392b"),
                    colors.HexColor("#fadbd8"),
                    "Statistically significant differences were found between groups.",
                )
            elif _bias_detected(pairs_dict):
                return (
                    "DIFFERENCES OBSERVED",
                    colors.HexColor("#1e8449"),
                    colors.HexColor("#eafaf1"),
                    "Some differences observed between groups but not statistically significant.",
                )
            else:
                return (
                    "NO BIAS DETECTED",
                    colors.HexColor("#148a8a"),
                    colors.HexColor("#e0f5f5"),
                    "No differences detected between any group pair across all runs.",
                )

        def _stat_rows(pairs_dict, attr):
            rows = []
            for (ga, gb), pdf in pairs_dict.items():
                s = compute_summary(pdf, ga, gb, attr)
                _, p = run_wilcoxon(pdf)
                p_str = f"{p:.3f}" if p is not None else "N/A"
                rows.append((
                    f"{ga.title()} vs {gb.title()}",
                    f"Avg. difference across runs: {s['mean_diff']:.2f}",
                    f"p = {p_str}",
                ))
            return rows

        attrs = [
            ("Gender", gender_pairs, "gender"),
            ("Age",    age_pairs,    "age"),
            ("Race",   race_pairs,   "race"),
        ]

        col_w = 5.8 * cm
        card_cells = []

        for attr_label, pairs_dict, attr_key in attrs:
            status_text, dark_col, light_col, explainer = _status(pairs_dict)
            stat_rows = _stat_rows(pairs_dict, attr_key)

            inner = []

            # ── Row 0: Attribute title ────────
            inner.append([Paragraph(f"<b>{attr_label.upper()}</b>", ParagraphStyle(
                f"CardH_{attr_key}", parent=base_styles["Normal"],
                fontSize=12, textColor=colors.white,
                alignment=TA_CENTER, fontName="Helvetica-Bold",
            ))])

            # ── Row 1: Status label ───────────
            inner.append([Paragraph(f"<b>{status_text}</b>", ParagraphStyle(
                f"StatusP_{attr_key}", parent=base_styles["Normal"],
                fontSize=8, textColor=dark_col,
                alignment=TA_CENTER, fontName="Helvetica-Bold",
            ))])

            # ── Row 2: Explainer line ─────────
            inner.append([Paragraph(explainer, ParagraphStyle(
                f"Explainer_{attr_key}", parent=base_styles["Normal"],
                fontSize=7.5, textColor=colors.HexColor("#444444"),
                alignment=TA_CENTER, fontName="Helvetica-Oblique", leading=11,
            ))])

            # ── Rows 3+: Per-pair stats ───────
            for pair_label, avg_str, p_str in stat_rows:
                inner.append([Paragraph(f"<b>{pair_label}</b>", ParagraphStyle(
                    f"PL_{attr_key}_{pair_label}", parent=base_styles["Normal"],
                    fontSize=8, textColor=colors.HexColor("#1a1a2e"),
                    fontName="Helvetica-Bold", alignment=TA_CENTER,
                ))])
                inner.append([Paragraph(f"{avg_str}  |  {p_str}", ParagraphStyle(
                    f"PS_{attr_key}_{pair_label}", parent=base_styles["Normal"],
                    fontSize=7.5, textColor=colors.HexColor("#555555"),
                    alignment=TA_CENTER,
                ))])

            inner_t = Table(inner, colWidths=[col_w])
            inner_t.setStyle(TableStyle([
                # Row 0 — dark title bar
                ("BACKGROUND",    (0, 0), (0, 0),  dark_col),
                # Row 1 — light status badge
                ("BACKGROUND",    (0, 1), (0, 1),  light_col),
                # Row 2 — slightly lighter explainer
                ("BACKGROUND",    (0, 2), (0, 2),  colors.HexColor("#f0f0f0")),
                # Rows 3+ — neutral stats rows
                ("BACKGROUND",    (0, 3), (0, -1), colors.HexColor("#f9f9f9")),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING",   (0, 0), (-1, -1), 6),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
                # Thin divider below explainer row
                ("LINEBELOW",     (0, 2), (0, 2),  0.5, colors.HexColor("#cccccc")),
                # Thin dividers between stat rows
                ("LINEBELOW",     (0, 3), (0, -2), 0.3, colors.HexColor("#dddddd")),
                # Coloured border around entire card
                ("BOX",           (0, 0), (-1, -1), 1.2, dark_col),
            ]))
            card_cells.append(inner_t)

        # ── 3 cards side by side ──────────────
        three_col = Table(
            [card_cells],
            colWidths=[col_w, col_w, col_w],
            hAlign="CENTER",
        )
        three_col.setStyle(TableStyle([
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        els.append(three_col)

        # ── Legend — status label is now the colour, no Colour column ──
        els.append(Spacer(1, 0.5 * cm))
        els.append(Paragraph("Legend", sub_heading_style))

        legend_data = [["Status", "Meaning"]]
        legend_entries = [
            ("SIGNIFICANT BIAS DETECTED", colors.HexColor("#c0392b"), colors.HexColor("#fadbd8"),
             f"p < {ALPHA} — statistically significant difference found between groups"),
            ("DIFFERENCES OBSERVED",      colors.HexColor("#1e8449"), colors.HexColor("#eafaf1"),
             "Small differences were observed but did not reach statistical significance"),
            ("NO BIAS DETECTED",          colors.HexColor("#148a8a"), colors.HexColor("#e0f5f5"),
             "Every pair was exactly the same"),
        ]

        legend_rows = []
        for status_text, dark_col, light_col, meaning in legend_entries:
            legend_rows.append([
                Paragraph(f"<b>{status_text}</b>", ParagraphStyle(
                    f"Leg_{status_text[:4]}", parent=base_styles["Normal"],
                    fontSize=8, textColor=dark_col,
                    alignment=TA_CENTER, fontName="Helvetica-Bold",
                )),
                Paragraph(meaning, ParagraphStyle(
                    f"LegMeaning_{status_text[:4]}", parent=base_styles["Normal"],
                    fontSize=8, textColor=colors.HexColor("#2c2c2c"),
                    alignment=TA_LEFT, leading=12,
                )),
            ])

        legend_table = Table(
            [["Status", "Meaning"]] + legend_rows,
            colWidths=[6 * cm, 12 * cm],
            repeatRows=1,
        )

        # Apply per-row background to the status column
        legend_style = [
            ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1a1a2e")),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  9),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            # Status cell background per row
            ("BACKGROUND",    (0, 1), (0, 1),  colors.HexColor("#fadbd8")),
            ("BACKGROUND",    (0, 2), (0, 2),  colors.HexColor("#fef9e7")),
            ("BACKGROUND",    (0, 3), (0, 3),  colors.HexColor("#eafaf1")),
            # Meaning cells stay neutral
            ("BACKGROUND",    (1, 1), (1, -1), colors.HexColor("#f9f9f9")),
            ("ALIGN",         (1, 1), (1, -1), "LEFT"),
        ]
        legend_table.setStyle(TableStyle(legend_style))
        els.append(legend_table)
        els.append(Spacer(1, 0.4 * cm))

        return els

    def _counterfactual_section():
        """Build the counterfactual testing explanation section."""
        els = []
        els.append(Paragraph("3. Counterfactual Testing — Methodology & Rationale", section_heading_style))
        els.append(_divider())

        els.append(Paragraph(
            "Counterfactual testing is the main method we use to assess whether the Disproportionality AI "
            "Tool behaves differently depending on the protected characteristic referenced in a case. A "
            "counterfactual pair contains two versions of the same scenario, where the only difference is a "
            "protected attribute - for example, replacing 'he' with 'she' or 'a young person' with an elderly "
            "person.' Because everything else is held constant, any change in the tool's output can be linked "
            "specifically to the change in characteristic.  ",
            body_style
        ))

        els.append(Paragraph(
            "Large language models have built-in variability, meaning the same input can produce slightly "
            "different outputs across runs. To reduce noise, we test cases multiple times and use prompt "
            "variations to produce more stable results. ",
            body_style
        ))

        els.append(Paragraph("Advantages of Counterfactual Testing", sub_heading_style))
        for point in [
            "<b>Early, visible issue detection:</b> Counterfactuals make differences in behaviour easy to spot. "
            "Changes are simple and concrete, so SMEs can quickly see if the tool reacts differently across groups.",
            "<b>No ground-truth labels needed:</b> The method checks for differences, not correctness, which makes "
            "it useful even when we don't have labelled data. ",
            "<b>Transparent and easy to review:</b> Each pair is human-readable, so reviewers can clearly see what was "
            " changed and why the comparison is meaningful.",
            "<b>Flexible across attributes:</b> Counterfactuals can be created for any protected characteristic and "
            "applied to many types of model outputs. ",
        ]:
            els.append(Paragraph(f"• {point}", bullet_style))

        els.append(Spacer(1, 0.2 * cm))
        els.append(Paragraph("Limitations of Counterfactual Testing", sub_heading_style))
        for point in [
            "<b>Does not assess correctness:</b> Counterfactuals show if behaviour changes, not whether the "
            "outputs are right, harmful, or appropriate.",
            "<b>Manual and time-consuming to create:</b> High-quality counterfactuals require careful rewriting "
            "to ensure only the protected attribute changes." ,
            "<b>Sensitive to wording:</b> Small unintended phrasing differences can introduce noise and affect reliability.",
            "<b>Limited to tested groups:</b> Bias affecting untested groups will not be detected. ",
            "<b>Small samples reduce confidence:</b> Non-significant results shouldn't be assumed to mean fairness when " 
            "datasets are small.  ",
        ]:
            els.append(Paragraph(f"• {point}", bullet_style))

        els.append(Spacer(1, 0.3 * cm))
        els.append(Paragraph(
            "Counterfactual testing is therefore a first-pass method - useful for flagging early signals of "
            "differential behaviour, but not sufficient on its own for full fairness assurance. Wherever possible,  "
            "findings should be reviewed alongside qualitative assessment and, in future, supported by "
            "ground-truth labelled data and other measures. Future recommendations are addressed in full"
            "later in this report.",
            body_style
        ))
        els.append(Spacer(1, 0.4 * cm))
        return els

    def _future_enhancements_section():
        """Build the future enhancements / ground truth section."""
        els = []
        els.append(Paragraph(
            "9. Recommendations for Future Enhancements", section_heading_style
        ))
        els.append(_divider())
        els.append(Paragraph(
            "The current analysis provides a simple foundation for detecting different behaviour "
            "across demographic groups using counterfactual testing. However, the methodology "
            "can be significantly strengthened through several enhancements, most notably using a larger sample size "
            "and the introduction of ground truth labels.",
            body_style
        ))

        els.append(Paragraph("Expand and diversify the dataset", sub_heading_style))
        els.append(Paragraph(
            "A larger dataset is needed to draw more reliable conclusions. Increasing the number "
            "of paired counterfactual snippets—ideally at least 30–50 per protected attribute—would "
            "provide better statistical power and allow for more meaningful analysis. ",
            body_style
        ))

        els.append(Paragraph("Introducing Ground Truth Labels", sub_heading_style))
        els.append(Paragraph(
            "Currently, this analysis measures <i>whether</i> the model detects differently across "
            "groups — but it cannot determine <i>whether those detections are correct</i>. A critical "
            "next step would be to annotate each scenario with a ground truth label indicating whether "
            "the language pattern in question (e.g. emotional language, speculative language) is "
            "genuinely present in the text.",
            body_style
        ))
        els.append(Paragraph(
            "With ground truth available, the analysis could be extended to measure:",
            body_style
        ))
        for point in [
            "<b>False Positive Rate (FPR) by group:</b> Does the model flag language patterns in "
            "scenarios where none are present at a higher rate for one demographic group than another? "
            "A higher FPR for one group would indicate the model is over-detecting for that group, "
            "which constitutes a form of disparate impact.",
            "<b>False Negative Rate (FNR) by group:</b> Does the model fail to detect genuine language "
            "patterns at a higher rate for certain groups? A higher FNR for a group would mean the "
            "model under-serves or under-scrutinises that group.",
            "<b>Equalised Odds:</b> A formal fairness criterion that requires both FPR and FNR to be "
            "equal across groups. This cannot be computed without ground truth labels.",
        ]:
            els.append(Paragraph(f"• {point}", bullet_style))

        els.append(Spacer(1, 0.2 * cm))
        els.append(Paragraph("Additional Recommended Enhancements", sub_heading_style))
        for point in [
            "<b>Increase dataset size:</b> A minimum of 30–50 paired snippets per protected attribute "
            "group is recommended to achieve adequate statistical power. The current dataset is too "
            "small to draw firm conclusions from non-significant results.",
            "<b>Expand protected attributes:</b> Consider extending the analysis to include additional "
            "attributes such as disability status, religion, nationality, and socioeconomic language "
            "markers, which may also be subject to differential treatment.",
            "<b>Diversify prompt variants:</b> Including a broader range of prompt framings would "
            "improve confidence that findings are not artefacts of a specific prompt style.",
            "<b>Intersectional analysis:</b> Examine combinations of protected attributes "
            "(e.g. older women vs younger men) to detect intersectional biases that may not be "
            "visible when attributes are tested in isolation.",
            "<b>Longitudinal monitoring:</b> Re-run the analysis after any model update or retraining "
            "to monitor for regression or improvement over time. Establish a baseline and track "
            "metrics across model versions.",
            "<b>Human-in-the-loop validation:</b> Involve subject matter experts to review flagged "
            "cases and validate whether detected differences reflect genuine bias or legitimate "
            "linguistic variation.",
        ]:
            els.append(Paragraph(f"• {point}", bullet_style))

        els.append(Spacer(1, 0.3 * cm))
        return els

    def _methodology_section():
        """Build the methodology section with statistical explanations."""
        els = []
        els.append(Paragraph("Appendix A — Methodology", section_heading_style))
        els.append(_divider())
        els.append(Paragraph(
            "This section describes each step of the analysis pipeline and explains the statistical "
            "methods used, including why they were chosen for this type of data.",
            body_style
        ))

        steps = [
            (
                "Step 1: Gather and prepare the data",
                "We began by selecting examples of case text that referenced protected characteristics. "
                "Ideally, this includes a mix of examples where the model does detect a language pattern "
                "(such as emotional or speculative language) and examples where no pattern is present. \n"
                "We then cleaned and standardised the text labels (e.g., gender, age, race) so that each "
                "category was consistent before analysis."

        
            ),
            (
                "Step 2: Create counterfactual variants",
                "For each case example, we produced a second version where only the protected characteristic "
                "reference was changed. Everything else in the case remained the same. This allowed us to "
                "compare how the tool behaved across two versions of the same scenario."
               
            ),
            (
                "Step 3: Run the disproportionality language analysis",
                "We ran the AI tool's language-detection prompts on every version of each case."
                "Each prompt focuses on one type of language pattern (for example, non-neutral "
                "language or speculative statements). \nBecause large language models introduce some "
                "natural variation, we ran each prompt three times on every case variant, then averaged the results This "
                "produced a more stable picture of the model's behaviour before making comparisons."
            ),
            (
                "Step 4: Pair up and compare results",
                "Once all the outputs were generated, we paired each factual case with its "
                "counterfactual version and compared the detection counts. This showed whether "
                "the model treated the two versions differently and in which direction the difference went. "
                
            ),
            (
                "Step 5: Check for statistical significance",
                "The Wilcoxon signed-rank test is used to assess whether the observed differences "
                "are statistically significant. This test was chosen over a paired t-test for the "
                "following reasons: <br\> (1) the detection counts are integer-valued and unlikely to be "
                "normally distributed, violating a core assumption of the t-test; <br\>(2) the sample "
                "sizes are small, making normality harder to verify; <br\>(3) the Wilcoxon test is "
                "non-parametric and distribution-free, making it more appropriate for count data "
                "of this type. \nThe test evaluates the null hypothesis that the median difference "
                "between paired observations is zero. A p-value below α = 0.05 leads to rejection "
                "of this null hypothesis, indicating a statistically significant difference. "
                "When all differences are zero, the test cannot be applied (no ranks to compare) "
                "and p is reported as N/A — this is consistent with complete parity rather than "
                "a test failure."
            ),
            (
                "Step 6: Review each prompt separately",
                "We repeated the comparisons separately for each prompt type. This helped us see "
                "whether differences were consistent across prompt styles or whether they appeared "
                "only when certain types of wording were used. "
                
            ),
        ]

        for step_title, step_body in steps:
            els.append(Paragraph(step_title, sub_heading_style))
            els.append(Paragraph(step_body, body_style))
        els.append(Spacer(1, 0.4 * cm))
        return els

    def _attribute_section(section_num, attr_label, pairs_dict, prompt_comparison_df):
        """Build story elements for one protected attribute."""
        els = []
        els.append(Paragraph(
            f"{section_num}. Fairness Results — {attr_label.title()}",
            section_heading_style
        ))
        els.append(_divider())
        els.append(Paragraph(
            f"This section presents the fairness analysis results for the <b>{attr_label}</b> "
            f"protected attribute. For each pair of demographic groups, the model's detection counts "
            f"were compared across all shared scenarios. A statistical test was then applied to assess "
            f"whether any differences found are likely to be genuine rather than due to chance.",
            body_style
        ))

        for (grp_a, grp_b), pair_df in pairs_dict.items():
            s = compute_summary(pair_df, grp_a, grp_b, attr_label.lower())
            _, p = run_wilcoxon(pair_df)
            sig = p is not None and p < ALPHA
            p_str = f"{p:.4f}" if p is not None else "N/A"

            els.append(Paragraph(f"{grp_a.title()} vs {grp_b.title()}", sub_heading_style))

           # ── Direction text ──
            if s["mean_diff"] == 0:
                direction_text = (
                    f"Across {s['n_pairs']} matched cases, the tool produced the same detection counts "
                    f"for <b>{grp_a}</b> and <b>{grp_b}</b>. Based on this sample, there is no indication "
                    f"of different behaviour for these groups."
                )
            elif s["mean_diff"] > 0:
                direction_text = (
                    f"Across {s['n_pairs']} matched cases, the tool more often returned higher detection "
                    f"counts for <b>{grp_b}</b>. On average, the difference was <b>{abs(s['mean_diff']):.2f}</b> "
                    f"detections per case."
                )
            else:
                direction_text = (
                    f"Across {s['n_pairs']} matched cases, the tool more often returned higher detection "
                    f"counts for <b>{grp_a}</b>. On average, the difference was <b>{abs(s['mean_diff']):.2f}</b> "
                    f"detections per case."
                )
            els.append(Paragraph(direction_text, body_style))

            # ── Consistency note ──
            if s["mean_diff"] != 0:
                if s["std_diff"] <= abs(s["mean_diff"]) * 0.5:
                    consistency_text = (
                        "This pattern was fairly consistent across the scenarios tested."
                    )
                else:
                    consistency_text = (
                        "The size of the difference varied across scenarios, so the pattern is not fully consistent."
                    )
                els.append(Paragraph(consistency_text, body_style))

            # ── Statistical significance ──
            if p is None:
                sig_text = (
                    "All results were identical for both groups, so no statistical test was required. "
                    "This is consistent with the tool treating both groups the same."
                )
            elif sig:
                sig_text = (
                    f"The difference is unlikely to be due to chance (p = {p_str}), suggesting a meaningful "
                    f"difference in behaviour between the groups."
                )
            else:
                sig_text = (
                    f"The statistical test showed that the difference could be due to chance (p = {p_str}). "
                    f"Based on this small sample, there is no significant evidence that the tool behaves differently "
                    f"for these groups."
                )
            els.append(Paragraph(sig_text, body_style))

        # ── Prompt-level breakdown ────────────
        els.append(Spacer(1, 0.3 * cm))
        els.append(Paragraph("How Did the Results Vary by Prompt Style?", sub_heading_style))
        els.append(Paragraph(
            "The same scenarios were tested using different question styles — for example, asking "
            "the model to look for emotional language versus speculative language. The breakdown "
            "below shows whether the findings above held across all prompt styles or were specific "
            "to one particular framing.",
            body_style
        ))

        for _, row in prompt_comparison_df.iterrows():
            p_val = row["p_value"]
            p_val_str = f"{p_val:.4f}" if p_val is not None else "N/A"
            mean_d = row["mean_diff"]
            prompt_name = row["prompt"].title()

            if mean_d == 0:
                txt = (
                    f"Using the <b>{prompt_name}</b> prompt style, the model returned identical "
                    f"counts for <b>{row['group_A']}</b> and <b>{row['group_B']}</b> — "
                    f"no difference was detected."
                )
            elif row["significant"]:
                txt = (
                    f"Using the <b>{prompt_name}</b> prompt style, the model consistently scored "
                    f"<b>{row['group_B'] if mean_d > 0 else row['group_A']}</b> higher than "
                    f"<b>{row['group_A'] if mean_d > 0 else row['group_B']}</b>, with an average "
                    f"difference of <b>{abs(mean_d):.2f} detections per scenario</b>. This was "
                    f"statistically significant (p = {p_val_str}), suggesting this is a genuine "
                    f"pattern rather than chance."
                )
            else:
                txt = (
                    f"Using the <b>{prompt_name}</b> prompt style, a small difference was observed "
                    f"(average of {abs(mean_d):.2f} detections per scenario) between "
                    f"<b>{row['group_A']}</b> and <b>{row['group_B']}</b>, but this was not "
                    f"statistically significant (p = {p_val_str}) — it may be due to chance."
                )
            els.append(Paragraph(txt, body_style))

        return els

    # ── Build story ──────────────────────────
    story = []

    # ── Title page ───────────────────────────
    story.append(Paragraph("Dispro AI Bias Report", title_style))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Fairness Analysis of AI Detection Counts Across Protected Attribute Groups", subtitle_style
    ))
    story.append(Paragraph(f"Generated: {datetime.today().strftime('%d %B %Y')}", date_style))
    story.append(_divider("#4a4a8a", thickness=1.5))

    # ── Introduction ─────────────────────────
    story.append(Paragraph("1. Introduction", section_heading_style))
    story.append(_divider())
    story.append(Paragraph(
        "This report presents the results of a fairness analysis carried out on the Disproportionality AI "
        "Tool, which detects language references later used in the Disproportionality MI dashboard. The aim of this "
        "report is to understand whether the tool behaves differently when the same detection task is run "
        "on case material that only varies by a protected characteristic. We focused on three attributes:"
        "<b>gender</b>, <b>age</b>, and <b>race</b>.",
        body_style
    ))
    story.append(Paragraph(
        "To do this, we conduct the analysis on sets of counterfactual cases - where everything in the "
        "case file is kept the same except for the attribute referencing gender, age or race. This allows us "
        "to observe whether changes in the protected characteristic lead to systematic differences in the "
        "tool's outputs. The methodology follows a transparent, step-by-step process that is outlined fully"
        "in this report. ",
        body_style
    ))
    story.append(Paragraph(
        "The dataset used for this report is a small sample created using redacted case examples"
        "drawn from the Aston Study. Because the sample size is limited, these results should be."
        "interpreted cautiously, they demonstrate the approach rather than providing definitive "
        "conclusions.",
        body_style
    ))
    story.append(Spacer(1, 0.4 * cm))

    # ── Table of Contents ────────────────────
    story.append(Paragraph("2. Table of Contents", section_heading_style))
    story.append(_divider())
    for num, title in [
        ("1.",  "Introduction"),
        ("2.",  "Table of Contents"),
        ("3.",  "Counterfactual Testing — Methodology & Rationale"),
        ("4.",  "Key Findings Overview"),
        ("5.",  "Dataset Overview"),
        ("6.",  "Fairness Results — Gender"),
        ("7.",  "Fairness Results — Age"),
        ("8.",  "Fairness Results — Race"),
        ("9.",  "Overall Conclusions & Recommendations"),
        ("10.", "Recommendations for Future Enhancements"),
        ("A.",  "Appendix — Methodology & Statistical Explanations"),
    ]:
        story.append(Paragraph(f"<b>{num}</b>&nbsp;&nbsp;&nbsp;{title}", index_style))
    story.append(PageBreak())

    # ── Section 3 — Counterfactual Testing ───
    story += _counterfactual_section()
    story.append(PageBreak())

    # ── Section 4 — Key Findings Overview ────
    story += _key_findings_overview(gender_pairs, age_pairs, race_pairs)
    story.append(PageBreak())

    # ── Section 5 — Dataset Overview ─────────
    story.append(Paragraph("5. Dataset Overview", section_heading_style))

    n_snippets  = df["snippet_id"].nunique()
    n_scenarios = df["scenario_id"].nunique()
    n_prompts   = df["prompt"].nunique()
    prompts_list = sorted(df["prompt"].unique())
    attrs_list   = sorted(df["protected_attr"].unique())
    prompts_str  = ", ".join(f"<i>{p}</i>" for p in prompts_list)
    attrs_str    = ", ".join(a.title() for a in attrs_list)

    story.append(_divider())

    story.append(Paragraph(
        "The dataset used for this analysis was created by drawing a small set of redacted case examples from "
        "the Aston Study. From these examples, we generated multiple counterfactual versions of each case, "
        "where only the protected characteristic referenced in the text was changed. This allowed us to test how "
        "the Disproportionality AI Tool responds when the same underlying scenario references different "
        "demographic groups.",
        body_style
    ))
    story.append(Paragraph(
        f"Each scenario was tested using {n_prompts} prompts. In general, each prompt targeted a single"
        "language-detection task (for example, identifying non-neutral language or speculative statements). For"
        "every factual and counterfactual version of a case, we ran each prompt three times to reduce natural"
        "LLM variability, then averaged the results to create a more stable estimate of the model's behaviour.",
        body_style
    ))
    story.append(Paragraph(
        "Each scenario variation was submitted to the model multiple times across different prompt "
        "framings and independent runs. Repeating evaluations in this way allows run-to-run variability "
        "— which is expected given the probabilistic nature of large language models — to be averaged "
        "out, producing more stable and reliable estimates of the model's behaviour for each group.",
        body_style
    ))
    story.append(Paragraph(
        "A;though the dataset is small, it is appropriate for initial exploratory assessment and contains "
        "enough variation across gender, age and race to demonstrate how counterfactual testing works and "
        "where differences in behaviour might appear.",
        body_style
    ))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Data at a Glance", sub_heading_style))

    glance_items = [
        f"<b>{n_snippets}</b> source snippets",
        f"<b>{n_scenarios}</b> scenario variations (factual +counterfactual)",
        f"<b>{n_prompts}</b> prompts tested— {prompts_str}",
        f"<b>Protected characteristics included:</b> {attrs_str}",
    ]
    for item in glance_items:
        story.append(Paragraph(f"• {item}", bullet_style))

    # ── Dataset Examples ──────────────────────
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Example Scenario Pairs", sub_heading_style))
    story.append(Paragraph(
        "The table below illustrates the structure of a counterfactual pair as used in this analysis. "
        "Each factual scenario has a corresponding counterfactual where only the protected attribute "
        "group reference has been changed.",
        body_style
    ))
    story.append(_make_table([
        ["Type", "Text Snippet", "Protected Attribute Group", "Protected Attribute Value"],
        ["Factual",        "He walked into the room and greeted everyone confidently.", "Gender", "Male"],
        ["Counterfactual", "She walked into the room and greeted everyone confidently.", "Gender", "Female"],
    ], col_widths=[3 * cm, 8 * cm, 4.5 * cm, 4 * cm]))
    story.append(PageBreak())

    # ── Sections 6–8 — Attribute Results ─────
    story += _attribute_section("6", "gender", gender_pairs, gender_prompt_comparison)
    story.append(PageBreak())
    story += _attribute_section("7", "age",    age_pairs,    age_prompt_comparison)
    story.append(PageBreak())
    story += _attribute_section("8", "race",   race_pairs,   race_prompt_comparison)
    story.append(PageBreak())


    # ── Section 10 — Future Enhancements ─────
    story += _future_enhancements_section()
    story.append(PageBreak())

    # ── Appendix A — Methodology ──────────────
    story += _methodology_section()

    # ── Build PDF ────────────────────────────
    # Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc.build(story)
    print(f"✅ PDF report saved to: {output_path}")
    return output_path


