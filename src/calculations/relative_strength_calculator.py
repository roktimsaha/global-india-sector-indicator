"""
Relative Strength Calculator

Purpose:
    Compares Indian sector returns against global sector returns.

Formula:
    Relative Strength = India Sector Return / Global Sector Return

Current periods:
    1-month, 3-month, and 6-month returns.

Composite formula:
    Relative Strength Composite =
        0.5 * Relative_Strength_1M
        + 0.3 * Relative_Strength_3M
        + 0.2 * Relative_Strength_6M

Input:
    1. Return summary DataFrame created by return_calculator.py
    2. Sector config loaded from config/sectors.json

Output:
    data/relative_strength_summary.csv

Designed for:
    Phase 2 of the Global India Sector Leadership Indicator project.
"""


# ============================================================
# 1. Imports
# ============================================================

from pathlib import Path

import pandas as pd


# ============================================================
# 2. Relative Strength Settings
# ============================================================

RETURN_COLUMNS = [
    "Return_1M",
    "Return_3M",
    "Return_6M",
]

RELATIVE_STRENGTH_WEIGHTS = {
    "Relative_Strength_1M": 0.50,
    "Relative_Strength_3M": 0.30,
    "Relative_Strength_6M": 0.20,
}


# ============================================================
# 3. Name Helpers
# ============================================================

def clean_name_for_file(value: str) -> str:
    """
    Convert text into a simple filename-safe value.

    This must match the naming style used by market_data_collector.py.

    Example:
        "Financial Services" becomes "Financial_Services"
    """
    return (
        value.strip()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("&", "and")
    )


def build_sector_symbol_name(region: str, sector_name: str) -> str:
    """
    Build the symbol name used inside returns_summary.csv.

    Examples:
        INDIA_Technology
        GLOBAL_Technology
        INDIA_Banking
        GLOBAL_Banking

    Args:
        region (str): INDIA or GLOBAL.
        sector_name (str): Sector name from config.

    Returns:
        str: Symbol name used in return summary.
    """
    clean_sector_name = clean_name_for_file(sector_name)

    return f"{region}_{clean_sector_name}"


# ============================================================
# 4. Input Validation
# ============================================================

def validate_return_summary(return_summary: pd.DataFrame) -> None:
    """
    Validate that the return summary has the columns needed for
    relative strength calculations.

    Args:
        return_summary (pd.DataFrame): Return summary table.

    Raises:
        ValueError: If required columns are missing.
    """
    required_columns = ["Symbol"] + RETURN_COLUMNS

    missing_columns = [
        column for column in required_columns
        if column not in return_summary.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Return summary is missing required columns: {missing_columns}"
        )


def validate_sector_config(sector_config: dict) -> None:
    """
    Validate that each sector has Indian and global symbols.

    Args:
        sector_config (dict): Loaded sector configuration.

    Raises:
        ValueError: If any sector is missing required fields.
    """
    failures = {}

    for sector_name, sector_details in sector_config.items():
        missing_fields = []

        if "india_symbol" not in sector_details:
            missing_fields.append("india_symbol")

        if "global_symbol" not in sector_details:
            missing_fields.append("global_symbol")

        if missing_fields:
            failures[sector_name] = missing_fields

    if failures:
        raise ValueError(f"Sector config is missing required fields: {failures}")


# ============================================================
# 5. Return Summary Row Selection
# ============================================================

def get_symbol_return_row(
    return_summary: pd.DataFrame,
    symbol_name: str,
) -> pd.Series:
    """
    Get one row from the return summary for a symbol.

    Args:
        return_summary (pd.DataFrame): Return summary table.
        symbol_name (str): Symbol name, for example INDIA_Technology.

    Returns:
        pd.Series: Matching return summary row.

    Raises:
        ValueError: If the symbol is not found.
    """
    matching_rows = return_summary[
        return_summary["Symbol"] == symbol_name
    ]

    if matching_rows.empty:
        raise ValueError(f"Missing return summary row for symbol: {symbol_name}")

    return matching_rows.iloc[0]


# ============================================================
# 6. Relative Strength Calculation
# ============================================================

def calculate_relative_strength_value(
    india_return: float,
    global_return: float,
) -> float | None:
    """
    Calculate one relative strength value.

    Formula:
        India Return / Global Return

    Args:
        india_return (float): Indian sector return.
        global_return (float): Global sector return.

    Returns:
        float | None: Relative strength value, or None if not calculable.
    """
    if pd.isna(india_return) or pd.isna(global_return):
        return None

    if global_return == 0:
        return None

    return india_return / global_return


def calculate_weighted_relative_strength(result: dict) -> float | None:
    """
    Calculate weighted relative strength composite score.

    Args:
        result (dict): Result dictionary for one sector.

    Returns:
        float | None: Weighted relative strength composite.
    """
    values = [
        result[column]
        for column in RELATIVE_STRENGTH_WEIGHTS
    ]

    if any(value is None or pd.isna(value) for value in values):
        return None

    weighted_value = sum(
        RELATIVE_STRENGTH_WEIGHTS[column] * result[column]
        for column in RELATIVE_STRENGTH_WEIGHTS
    )

    return weighted_value


def calculate_relative_strength_for_sector(
    sector_name: str,
    sector_details: dict,
    return_summary: pd.DataFrame,
) -> dict:
    """
    Calculate relative strength for one sector.

    Args:
        sector_name (str): Sector name from config.
        sector_details (dict): Sector details from config.
        return_summary (pd.DataFrame): Return summary table.

    Returns:
        dict: Relative strength result for one sector.
    """
    india_symbol_name = build_sector_symbol_name(
        region="INDIA",
        sector_name=sector_name,
    )

    global_symbol_name = build_sector_symbol_name(
        region="GLOBAL",
        sector_name=sector_name,
    )

    india_row = get_symbol_return_row(
        return_summary=return_summary,
        symbol_name=india_symbol_name,
    )

    global_row = get_symbol_return_row(
        return_summary=return_summary,
        symbol_name=global_symbol_name,
    )

    result = {
        "Sector": sector_name,
        "India_Symbol": sector_details["india_symbol"],
        "Global_Symbol": sector_details["global_symbol"],
        "India_Return_Symbol": india_symbol_name,
        "Global_Return_Symbol": global_symbol_name,
    }

    for return_column in RETURN_COLUMNS:
        period_label = return_column.replace("Return_", "")

        india_return = india_row[return_column]
        global_return = global_row[return_column]

        relative_strength = calculate_relative_strength_value(
            india_return=india_return,
            global_return=global_return,
        )

        result[f"India_Return_{period_label}"] = india_return
        result[f"Global_Return_{period_label}"] = global_return
        result[f"Relative_Strength_{period_label}"] = relative_strength

    result["Relative_Strength_Composite"] = calculate_weighted_relative_strength(
        result
    )

    return result


# ============================================================
# 7. Relative Strength Summary Workflow
# ============================================================

def calculate_relative_strength_summary(
    return_summary: pd.DataFrame,
    sector_config: dict,
) -> pd.DataFrame:
    """
    Calculate relative strength summary for all configured sectors.

    Args:
        return_summary (pd.DataFrame): Return summary table.
        sector_config (dict): Loaded sector configuration.

    Returns:
        pd.DataFrame: Relative strength summary table.
    """
    print("Calculating relative strength summary...")

    validate_return_summary(return_summary)
    validate_sector_config(sector_config)

    results = []

    for sector_name, sector_details in sector_config.items():
        result = calculate_relative_strength_for_sector(
            sector_name=sector_name,
            sector_details=sector_details,
            return_summary=return_summary,
        )

        results.append(result)

        print(
            f"Calculated relative strength for {sector_name}: "
            f"{format_relative_strength(result['Relative_Strength_Composite'])}"
        )

    relative_strength_summary = pd.DataFrame(results)

    relative_strength_summary = relative_strength_summary.sort_values(
        by="Relative_Strength_Composite",
        ascending=False,
        na_position="last",
    )

    return relative_strength_summary


# ============================================================
# 8. Formatting Helpers
# ============================================================

def format_relative_strength(value: float | None) -> str:
    """
    Format relative strength value for terminal display.

    Args:
        value (float | None): Relative strength value.

    Returns:
        str: Human-readable value.
    """
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2f}x"


# ============================================================
# 9. CSV Saving
# ============================================================

def save_relative_strength_summary(
    relative_strength_summary: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Save relative strength summary to a CSV file.

    Args:
        relative_strength_summary (pd.DataFrame): Relative strength summary.
        output_path (Path): Output CSV path.

    Returns:
        Path: Saved output path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    relative_strength_summary.to_csv(output_path, index=False)

    print(f"Saved relative strength summary to {output_path}")

    return output_path