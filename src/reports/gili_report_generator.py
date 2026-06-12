"""
GILI Report Generator

Purpose:
    Creates a human-readable text report from the GILI ranking table.

Input:
    GILI summary DataFrame created by gili_calculator.py

Output:
    data/gili_report.txt

Designed for:
    Phase 3 of the Global India Sector Leadership Indicator project.
"""


# ============================================================
# 1. Imports
# ============================================================

from datetime import datetime
from pathlib import Path

import pandas as pd


# ============================================================
# 2. Formatting Helpers
# ============================================================

def format_number(value: float, decimals: int = 2) -> str:
    """
    Format a numeric value for report display.
    """
    if pd.isna(value):
        return "N/A"

    return f"{value:.{decimals}f}"


def format_percent(value: float) -> str:
    """
    Format a decimal value as a percentage.

    Example:
        0.20 becomes 20.00%
    """
    if pd.isna(value):
        return "N/A"

    return f"{value:.2%}"


# ============================================================
# 3. Input Validation
# ============================================================

def validate_gili_summary(gili_summary: pd.DataFrame) -> None:
    """
    Validate that the GILI summary has the columns needed for reporting.
    """
    required_columns = [
        "Rank",
        "Sector",
        "GILI_Score",
        "Relative_Strength_Score",
        "Momentum_Score",
        "Currency_Score",
        "Relative_Strength_Weight",
        "Momentum_Weight",
        "Currency_Weight_Effective",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in gili_summary.columns
    ]

    if missing_columns:
        raise ValueError(
            f"GILI summary is missing required report columns: {missing_columns}"
        )


# ============================================================
# 4. Report Section Builders
# ============================================================

def build_report_header() -> list[str]:
    """
    Build the report header section.
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return [
        "Global India Sector Leadership Indicator Report",
        "=" * 48,
        f"Generated at: {generated_at}",
        "",
    ]


def build_weight_section(gili_summary: pd.DataFrame) -> list[str]:
    """
    Build the component weight section.
    """
    first_row = gili_summary.iloc[0]

    return [
        "Component Weights",
        "-" * 17,
        f"Relative Strength: {format_percent(first_row['Relative_Strength_Weight'])}",
        f"Momentum:          {format_percent(first_row['Momentum_Weight'])}",
        f"Currency:          {format_percent(first_row['Currency_Weight_Effective'])}",
        "",
    ]


def build_ranking_section(gili_summary: pd.DataFrame) -> list[str]:
    """
    Build the sector ranking section.
    """
    lines = [
        "Sector Ranking",
        "-" * 14,
    ]

    ranked_summary = gili_summary.sort_values("Rank")

    for _, row in ranked_summary.iterrows():
        lines.extend(
            [
                (
                    f"Rank {int(row['Rank'])}: {row['Sector']} "
                    f"- GILI {format_number(row['GILI_Score'])}"
                ),
                (
                    f"  Relative Strength Score: "
                    f"{format_number(row['Relative_Strength_Score'])}"
                ),
                f"  Momentum Score:          {format_number(row['Momentum_Score'])}",
                f"  Currency Score:          {format_number(row['Currency_Score'])}",
                "",
            ]
        )

    return lines


def build_methodology_section() -> list[str]:
    """
    Build a simple methodology explanation.
    """
    return [
        "Methodology",
        "-" * 11,
        "GILI is calculated from three normalized component scores:",
        "1. Relative Strength Score",
        "2. Momentum Score",
        "3. Currency Score",
        "",
        "Each enabled component is normalized to a 0-100 scale.",
        "Disabled components receive a 0% effective weight.",
        "If enabled-weight normalization is active, remaining enabled weights",
        "are automatically rebalanced to total 100%.",
        "",
    ]


# ============================================================
# 5. Main Report Workflow
# ============================================================

def build_gili_text_report(gili_summary: pd.DataFrame) -> str:
    """
    Build the full GILI text report.

    Args:
        gili_summary (pd.DataFrame): Final GILI ranking table.

    Returns:
        str: Human-readable report text.
    """
    validate_gili_summary(gili_summary)

    report_lines = []

    report_lines.extend(build_report_header())
    report_lines.extend(build_weight_section(gili_summary))
    report_lines.extend(build_ranking_section(gili_summary))
    report_lines.extend(build_methodology_section())

    return "\n".join(report_lines)


def save_gili_text_report(
    gili_summary: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Save the GILI text report to a file.

    Args:
        gili_summary (pd.DataFrame): Final GILI ranking table.
        output_path (Path): Output text file path.

    Returns:
        Path: Saved report path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_text = build_gili_text_report(gili_summary)

    output_path.write_text(report_text, encoding="utf-8")

    print(f"Saved GILI text report to {output_path}")

    return output_path