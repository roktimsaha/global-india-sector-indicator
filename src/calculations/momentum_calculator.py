"""
Momentum Calculator

Purpose:
    Calculates a weighted momentum score using 1-month, 3-month,
    and 6-month returns.

Formula:
    Momentum = 0.5 * Return_1M + 0.3 * Return_3M + 0.2 * Return_6M

Input:
    Return summary DataFrame created by return_calculator.py

Output:
    data/momentum_summary.csv

Designed for:
    Phase 2 of the Global India Sector Leadership Indicator project.
"""


# ============================================================
# 1. Imports
# ============================================================

from pathlib import Path

import pandas as pd


# ============================================================
# 2. Momentum Settings
# ============================================================

MOMENTUM_WEIGHTS = {
    "Return_1M": 0.50,
    "Return_3M": 0.30,
    "Return_6M": 0.20,
}


# ============================================================
# 3. Input Validation
# ============================================================

def validate_return_summary(return_summary: pd.DataFrame) -> None:
    """
    Validate that the return summary has the columns required for momentum.

    Args:
        return_summary (pd.DataFrame): Return summary table.

    Raises:
        ValueError: If required columns are missing.
    """
    required_columns = [
        "Symbol",
        "Return_1M",
        "Return_3M",
        "Return_6M",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in return_summary.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Return summary is missing required columns: {missing_columns}"
        )


# ============================================================
# 4. Single Row Momentum Calculation
# ============================================================

def calculate_momentum_for_row(row: pd.Series) -> float | None:
    """
    Calculate momentum for one symbol.

    Args:
        row (pd.Series): One row from the return summary table.

    Returns:
        float | None: Weighted momentum value as a decimal.
    """
    required_values = [
        row["Return_1M"],
        row["Return_3M"],
        row["Return_6M"],
    ]

    if any(pd.isna(value) for value in required_values):
        return None

    momentum = (
        MOMENTUM_WEIGHTS["Return_1M"] * row["Return_1M"]
        + MOMENTUM_WEIGHTS["Return_3M"] * row["Return_3M"]
        + MOMENTUM_WEIGHTS["Return_6M"] * row["Return_6M"]
    )

    return momentum


# ============================================================
# 5. Momentum Summary Calculation
# ============================================================

def calculate_momentum_summary(return_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate momentum score for all symbols.

    Args:
        return_summary (pd.DataFrame): Return summary table.

    Returns:
        pd.DataFrame: Momentum summary table.
    """
    print("Calculating momentum summary...")

    validate_return_summary(return_summary)

    momentum_summary = return_summary.copy()

    momentum_summary["Momentum"] = momentum_summary.apply(
        calculate_momentum_for_row,
        axis=1,
    )

    momentum_summary = momentum_summary.sort_values(
        by="Momentum",
        ascending=False,
        na_position="last",
    )

    for _, row in momentum_summary.iterrows():
        print(
            f"Calculated momentum for {row['Symbol']}: "
            f"{format_momentum(row['Momentum'])}"
        )

    return momentum_summary


# ============================================================
# 6. Formatting Helpers
# ============================================================

def format_momentum(value: float | None) -> str:
    """
    Format momentum value for terminal display.

    Args:
        value (float | None): Momentum value as decimal.

    Returns:
        str: Human-readable percentage.
    """
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2%}"


# ============================================================
# 7. CSV Saving
# ============================================================

def save_momentum_summary(
    momentum_summary: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Save momentum summary to a CSV file.

    Args:
        momentum_summary (pd.DataFrame): Momentum summary table.
        output_path (Path): Output CSV path.

    Returns:
        Path: Saved output path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    momentum_summary.to_csv(output_path, index=False)

    print(f"Saved momentum summary to {output_path}")

    return output_path