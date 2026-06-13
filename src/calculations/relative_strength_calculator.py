"""
Relative Strength Calculator

Purpose:
    Compares Indian sector returns against global sector returns.

GILI v2 Formula:
    Excess Relative Strength = Indian Sector Return - Global Sector Return

Current periods:
    1-month, 3-month, and 6-month returns.

Composite formula:
    Relative_Strength_Raw =
        0.30 * Excess_RS_1M
        + 0.40 * Excess_RS_3M
        + 0.30 * Excess_RS_6M

Input:
    1. Return summary DataFrame created by return_calculator.py
    2. Sector config loaded from config/sectors.json
    3. GILI settings loaded from config/gili_settings.json

Output:
    data/relative_strength_summary.csv
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
# 3. Default Settings
# ============================================================

DEFAULT_RELATIVE_STRENGTH_PERIOD_WEIGHTS = {
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


def get_relative_strength_period_weights(
    gili_settings: dict | None = None,
) -> dict:
    """
    Get relative strength period weights from config.

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
        .get("relative_strength", DEFAULT_RELATIVE_STRENGTH_PERIOD_WEIGHTS)
    )


# ============================================================
# 5. Name Helpers
# ============================================================

def clean_name_for_file(value: str) -> str:
    """
    Convert text into a simple filename-safe value.

    This must match the naming style used by market_data_collector.py.
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
    """
    clean_sector_name = clean_name_for_file(sector_name)

    return f"{region}_{clean_sector_name}"


# ============================================================
# 6. Sector Helpers
# ============================================================

def is_sector_enabled(sector_details: dict) -> bool:
    """
    Check whether a sector is enabled.

    Backward-compatible behavior:
        If 'enabled' is missing, treat sector as enabled.
    """
    return sector_details.get("enabled", True)


# ============================================================
# 7. Input Validation
# ============================================================

def validate_return_summary(return_summary: pd.DataFrame) -> None:
    """
    Validate that the return summary has the columns needed for
    relative strength calculations.
    """
    required_columns = ["Symbol"] + list(RETURN_COLUMNS_BY_PERIOD.values())

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
    Validate enabled sectors.

    Disabled sectors are ignored.
    """
    failures = {}

    for sector_name, sector_details in sector_config.items():
        if not is_sector_enabled(sector_details):
            continue

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
# 8. Return Summary Row Selection
# ============================================================

def get_symbol_return_row(
    return_summary: pd.DataFrame,
    symbol_name: str,
) -> pd.Series:
    """
    Get one row from the return summary for a symbol.
    """
    matching_rows = return_summary[
        return_summary["Symbol"] == symbol_name
    ]

    if matching_rows.empty:
        raise ValueError(f"Missing return summary row for symbol: {symbol_name}")

    return matching_rows.iloc[0]


# ============================================================
# 9. Excess Relative Strength Calculation
# ============================================================

def calculate_excess_return(
    india_return: float,
    global_return: float,
) -> float | None:
    """
    Calculate excess return.

    Formula:
        Excess Return = Indian Sector Return - Global Sector Return
    """
    if pd.isna(india_return) or pd.isna(global_return):
        return None

    return india_return - global_return


def calculate_weighted_relative_strength_raw(
    result: dict,
    period_weights: dict,
) -> float | None:
    """
    Calculate weighted excess relative strength.
    """
    weighted_value = 0.0

    for period_label, weight in period_weights.items():
        excess_column = f"Excess_RS_{period_label}"
        excess_value = result.get(excess_column)

        if excess_value is None or pd.isna(excess_value):
            return None

        weighted_value += weight * excess_value

    return weighted_value


def calculate_relative_strength_for_sector(
    sector_name: str,
    sector_details: dict,
    return_summary: pd.DataFrame,
    period_weights: dict,
) -> dict:
    """
    Calculate excess relative strength for one sector.
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

    for period_label, return_column in RETURN_COLUMNS_BY_PERIOD.items():
        india_return = india_row[return_column]
        global_return = global_row[return_column]

        excess_return = calculate_excess_return(
            india_return=india_return,
            global_return=global_return,
        )

        result[f"India_Return_{period_label}"] = india_return
        result[f"Global_Return_{period_label}"] = global_return
        result[f"Excess_RS_{period_label}"] = excess_return

    relative_strength_raw = calculate_weighted_relative_strength_raw(
        result=result,
        period_weights=period_weights,
    )

    result["Relative_Strength_Raw"] = relative_strength_raw

    # Temporary compatibility column.
    # Current gili_calculator.py still reads Relative_Strength_Composite.
    # We will update gili_calculator.py in the next milestone.
    result["Relative_Strength_Composite"] = relative_strength_raw

    return result


# ============================================================
# 10. Relative Strength Summary Workflow
# ============================================================

def calculate_relative_strength_summary(
    return_summary: pd.DataFrame,
    sector_config: dict,
) -> pd.DataFrame:
    """
    Calculate excess relative strength summary for all enabled sectors.
    """
    print("Calculating relative strength summary...")

    validate_return_summary(return_summary)
    validate_sector_config(sector_config)

    gili_settings = load_gili_settings()

    period_weights = get_relative_strength_period_weights(gili_settings)

    results = []

    for sector_name, sector_details in sector_config.items():
        if not is_sector_enabled(sector_details):
            print(f"Skipping disabled sector in relative strength: {sector_name}")
            continue

        result = calculate_relative_strength_for_sector(
            sector_name=sector_name,
            sector_details=sector_details,
            return_summary=return_summary,
            period_weights=period_weights,
        )

        results.append(result)

        print(
            f"Calculated excess relative strength for {sector_name}: "
            f"{format_relative_strength(result['Relative_Strength_Raw'])}"
        )

    relative_strength_summary = pd.DataFrame(results)

    relative_strength_summary = relative_strength_summary.sort_values(
        by="Relative_Strength_Raw",
        ascending=False,
        na_position="last",
    )

    return relative_strength_summary


# ============================================================
# 11. Formatting Helpers
# ============================================================

def format_relative_strength(value: float | None) -> str:
    """
    Format relative strength value for terminal display.
    """
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:.2%}"


# ============================================================
# 12. CSV Saving
# ============================================================

def save_relative_strength_summary(
    relative_strength_summary: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Save relative strength summary to a CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    relative_strength_summary.to_csv(output_path, index=False)

    print(f"Saved relative strength summary to {output_path}")

    return output_path