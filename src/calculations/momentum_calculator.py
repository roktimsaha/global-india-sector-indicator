"""
Momentum Calculator

Purpose:
    Calculates weighted momentum using 1-month, 3-month, and 6-month returns.

GILI v2 Formula:
    Momentum_Raw =
        0.30 * Return_1M
        + 0.40 * Return_3M
        + 0.30 * Return_6M

Input:
    Return summary DataFrame created by return_calculator.py

Output:
    data/momentum_summary.csv
"""


# ============================================================
# 1. Imports
# ============================================================

from pathlib import Path
import json

import pandas as pd


# ============================================================
# 2. Project Paths
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]
GILI_SETTINGS_PATH = ROOT_DIR / "config" / "gili_settings.json"


# ============================================================
# 3. Default Momentum Settings
# ============================================================

DEFAULT_MOMENTUM_PERIOD_WEIGHTS = {
    "1M": 0.30,
    "3M": 0.40,
    "6M": 0.30,
}

RETURN_COLUMNS_BY_PERIOD = {
    "1M": "Return_1M",
    "3M": "Return_3M",
    "6M": "Return_6M",
}


# ============================================================
# 4. Settings Loading
# ============================================================

def load_gili_settings(settings_path: Path = GILI_SETTINGS_PATH) -> dict:
    """
    Load GILI settings from config/gili_settings.json.
    """
    if not settings_path.exists():
        return {}

    with settings_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_momentum_period_weights(
    gili_settings: dict | None = None,
) -> dict:
    """
    Get momentum period weights from config.

    Falls back to:
        1M = 0.30
        3M = 0.40
        6M = 0.30
    """
    if gili_settings is None:
        gili_settings = load_gili_settings()

    return (
        gili_settings
        .get("period_weights", {})
        .get("momentum", DEFAULT_MOMENTUM_PERIOD_WEIGHTS)
    )


# ============================================================
# 5. Input Validation
# ============================================================

def validate_return_summary(return_summary: pd.DataFrame) -> None:
    """
    Validate that the return summary has the columns required for momentum.
    """
    required_columns = [
        "Symbol",
        *RETURN_COLUMNS_BY_PERIOD.values(),
    ]

    missing_columns = [
        column for column in required_columns
        if column not in return_summary.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Return summary is missing required columns: {missing_columns}"
        )


def validate_period_weights(period_weights: dict) -> None:
    """
    Validate configured momentum period weights.
    """
    required_periods = list(RETURN_COLUMNS_BY_PERIOD.keys())

    missing_periods = [
        period for period in required_periods
        if period not in period_weights
    ]

    if missing_periods:
        raise ValueError(
            f"Momentum period weights are missing periods: {missing_periods}"
        )

    for period, weight in period_weights.items():
        if period not in required_periods:
            raise ValueError(f"Unsupported momentum period: {period}")

        if not isinstance(weight, int | float):
            raise ValueError(
                f"Momentum weight for {period} must be numeric."
            )

        if weight < 0:
            raise ValueError(
                f"Momentum weight for {period} cannot be negative."
            )

    total_weight = sum(period_weights.values())

    if total_weight <= 0:
        raise ValueError("Momentum period weights must total more than zero.")


# ============================================================
# 6. Single Row Momentum Calculation
# ============================================================

def calculate_momentum_for_row(
    row: pd.Series,
    period_weights: dict,
) -> float | None:
    """
    Calculate momentum for one symbol.

    Args:
        row (pd.Series): One row from the return summary table.
        period_weights (dict): Period weights from GILI settings.

    Returns:
        float | None: Weighted momentum value as a decimal.
    """
    momentum = 0.0

    for period_label, weight in period_weights.items():
        return_column = RETURN_COLUMNS_BY_PERIOD[period_label]
        return_value = row[return_column]

        if pd.isna(return_value):
            return None

        momentum += weight * return_value

    return momentum


# ============================================================
# 7. Momentum Summary Calculation
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

    gili_settings = load_gili_settings()

    period_weights = get_momentum_period_weights(gili_settings)

    validate_period_weights(period_weights)

    print(
        "Using momentum period weights: "
        f"1M={period_weights['1M']:.2%}, "
        f"3M={period_weights['3M']:.2%}, "
        f"6M={period_weights['6M']:.2%}"
    )

    momentum_summary = return_summary.copy()

    momentum_summary["Momentum_Raw"] = momentum_summary.apply(
        calculate_momentum_for_row,
        axis=1,
        period_weights=period_weights,
    )

    # Temporary compatibility column.
    # Current gili_calculator.py still reads Momentum.
    # We will update gili_calculator.py in a later milestone.
    momentum_summary["Momentum"] = momentum_summary["Momentum_Raw"]

    momentum_summary = momentum_summary.sort_values(
        by="Momentum_Raw",
        ascending=False,
        na_position="last",
    )

    for _, row in momentum_summary.iterrows():
        print(
            f"Calculated momentum for {row['Symbol']}: "
            f"{format_momentum(row['Momentum_Raw'])}"
        )

    return momentum_summary


# ============================================================
# 8. Formatting Helpers
# ============================================================

def format_momentum(value: float | None) -> str:
    """
    Format momentum value for terminal display.
    """
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2%}"


# ============================================================
# 9. CSV Saving
# ============================================================

def save_momentum_summary(
    momentum_summary: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Save momentum summary to a CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    momentum_summary.to_csv(output_path, index=False)

    print(f"Saved momentum summary to {output_path}")

    return output_path