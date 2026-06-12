"""
GILI Calculator

Purpose:
    Calculates the Global India Sector Leadership Indicator score.

Default formula:
    GILI =
        0.50 * Relative Strength Score
        + 0.30 * Momentum Score
        + 0.20 * Currency Score

Configurable behavior:
    Components can be enabled or disabled in:

        config/gili_settings.json

    Example:
        Disable currency impact by setting:
            "currency": {
                "enabled": false,
                "weight": 0.20
            }

    If normalize_enabled_weights is true, enabled component weights are
    automatically rebalanced to total 1.0.

Designed for:
    Phase 3 of the Global India Sector Leadership Indicator project.
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
# 3. GILI Settings
# ============================================================

DEFAULT_GILI_SETTINGS = {
    "components": {
        "relative_strength": {
            "enabled": True,
            "weight": 0.50,
        },
        "momentum": {
            "enabled": True,
            "weight": 0.30,
        },
        "currency": {
            "enabled": True,
            "weight": 0.20,
        },
    },
    "normalize_enabled_weights": True,
}

COMPONENT_COLUMN_MAP = {
    "relative_strength": "Relative_Strength_Score",
    "momentum": "Momentum_Score",
    "currency": "Currency_Score",
}

USDINR_SYMBOL_NAME = "USDINR"


# ============================================================
# 4. Name Helpers
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


def build_india_return_symbol_name(sector_name: str) -> str:
    """
    Build the Indian sector symbol name used inside momentum_summary.csv.

    Example:
        Technology becomes INDIA_Technology
    """
    clean_sector_name = clean_name_for_file(sector_name)

    return f"INDIA_{clean_sector_name}"


# ============================================================
# 5. GILI Settings Loading
# ============================================================

def load_gili_settings(settings_path: Path = GILI_SETTINGS_PATH) -> dict:
    """
    Load GILI component settings.

    If config/gili_settings.json does not exist, default settings are used.
    """
    if not settings_path.exists():
        return DEFAULT_GILI_SETTINGS

    with settings_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_gili_settings(gili_settings: dict) -> None:
    """
    Validate the GILI settings file.
    """
    if "components" not in gili_settings:
        raise ValueError("GILI settings must contain a 'components' section.")

    components = gili_settings["components"]

    required_components = [
        "relative_strength",
        "momentum",
        "currency",
    ]

    missing_components = [
        component for component in required_components
        if component not in components
    ]

    if missing_components:
        raise ValueError(
            f"GILI settings missing components: {missing_components}"
        )

    enabled_count = 0

    for component_name in required_components:
        component_settings = components[component_name]

        if "enabled" not in component_settings:
            raise ValueError(
                f"GILI component '{component_name}' is missing 'enabled'."
            )

        if "weight" not in component_settings:
            raise ValueError(
                f"GILI component '{component_name}' is missing 'weight'."
            )

        if component_settings["enabled"]:
            enabled_count += 1

        if component_settings["weight"] < 0:
            raise ValueError(
                f"GILI component '{component_name}' weight cannot be negative."
            )

    if enabled_count == 0:
        raise ValueError("At least one GILI component must be enabled.")


def get_effective_component_weights(gili_settings: dict) -> dict:
    """
    Return final component weights after applying enabled/disabled settings.

    If normalize_enabled_weights is true:
        Enabled weights are rebalanced so they total 1.0.
    """
    validate_gili_settings(gili_settings)

    components = gili_settings["components"]

    effective_weights = {}

    for component_name, component_settings in components.items():
        if component_settings["enabled"]:
            effective_weights[component_name] = component_settings["weight"]
        else:
            effective_weights[component_name] = 0.0

    normalize_enabled_weights = gili_settings.get(
        "normalize_enabled_weights",
        True,
    )

    if normalize_enabled_weights:
        total_enabled_weight = sum(effective_weights.values())

        if total_enabled_weight == 0:
            raise ValueError("Enabled GILI component weights total zero.")

        effective_weights = {
            component_name: weight / total_enabled_weight
            for component_name, weight in effective_weights.items()
        }

    return effective_weights


# ============================================================
# 6. Input Validation
# ============================================================

def validate_relative_strength_summary(
    relative_strength_summary: pd.DataFrame,
) -> None:
    """
    Validate required relative strength columns.
    """
    required_columns = [
        "Sector",
        "Relative_Strength_Composite",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in relative_strength_summary.columns
    ]

    if missing_columns:
        raise ValueError(
            "Relative strength summary is missing required columns: "
            f"{missing_columns}"
        )


def validate_momentum_summary(momentum_summary: pd.DataFrame) -> None:
    """
    Validate required momentum columns.
    """
    required_columns = [
        "Symbol",
        "Momentum",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in momentum_summary.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Momentum summary is missing required columns: {missing_columns}"
        )


def validate_sector_config(sector_config: dict) -> None:
    """
    Validate that each sector has the fields needed for GILI.
    """
    failures = {}

    for sector_name, sector_details in sector_config.items():
        missing_fields = []

        if "india_symbol" not in sector_details:
            missing_fields.append("india_symbol")

        if "global_symbol" not in sector_details:
            missing_fields.append("global_symbol")

        if "currency_weight" not in sector_details:
            missing_fields.append("currency_weight")

        if missing_fields:
            failures[sector_name] = missing_fields

    if failures:
        raise ValueError(f"Sector config is missing required fields: {failures}")


# ============================================================
# 7. Data Lookup Helpers
# ============================================================

def get_momentum_for_symbol(
    momentum_summary: pd.DataFrame,
    symbol_name: str,
) -> float:
    """
    Get momentum value for one symbol from momentum_summary.
    """
    matching_rows = momentum_summary[
        momentum_summary["Symbol"] == symbol_name
    ]

    if matching_rows.empty:
        raise ValueError(f"Missing momentum row for symbol: {symbol_name}")

    return matching_rows.iloc[0]["Momentum"]


def get_relative_strength_for_sector(
    relative_strength_summary: pd.DataFrame,
    sector_name: str,
) -> float:
    """
    Get relative strength composite value for one sector.
    """
    matching_rows = relative_strength_summary[
        relative_strength_summary["Sector"] == sector_name
    ]

    if matching_rows.empty:
        raise ValueError(
            f"Missing relative strength row for sector: {sector_name}"
        )

    return matching_rows.iloc[0]["Relative_Strength_Composite"]


# ============================================================
# 8. Normalization
# ============================================================

def normalize_to_0_100(values: pd.Series) -> pd.Series:
    """
    Normalize a numeric series to a 0-100 scale.

    Formula:
        normalized = ((value - min_value) / (max_value - min_value)) * 100

    If all values are equal, every valid value receives a neutral score of 50.
    """
    numeric_values = pd.to_numeric(values, errors="coerce")

    min_value = numeric_values.min()
    max_value = numeric_values.max()

    if pd.isna(min_value) or pd.isna(max_value):
        return numeric_values

    if max_value == min_value:
        return numeric_values.apply(
            lambda value: 50 if not pd.isna(value) else None
        )

    return ((numeric_values - min_value) / (max_value - min_value)) * 100


# ============================================================
# 9. Currency Impact Calculation
# ============================================================

def calculate_currency_impact(
    usdinr_momentum: float,
    currency_weight: float,
) -> float | None:
    """
    Calculate raw currency impact for one sector.

    Logic:
        If USDINR is rising, export-oriented sectors benefit more.
        The sector currency_weight controls how much each sector is affected.
    """
    if pd.isna(usdinr_momentum) or pd.isna(currency_weight):
        return None

    return usdinr_momentum * currency_weight


# ============================================================
# 10. GILI Row Preparation
# ============================================================

def build_gili_base_rows(
    relative_strength_summary: pd.DataFrame,
    momentum_summary: pd.DataFrame,
    sector_config: dict,
) -> pd.DataFrame:
    """
    Build raw GILI input rows before normalization.

    Each row represents one sector.
    """
    usdinr_momentum = get_momentum_for_symbol(
        momentum_summary=momentum_summary,
        symbol_name=USDINR_SYMBOL_NAME,
    )

    rows = []

    for sector_name, sector_details in sector_config.items():
        india_return_symbol_name = build_india_return_symbol_name(sector_name)

        relative_strength = get_relative_strength_for_sector(
            relative_strength_summary=relative_strength_summary,
            sector_name=sector_name,
        )

        momentum = get_momentum_for_symbol(
            momentum_summary=momentum_summary,
            symbol_name=india_return_symbol_name,
        )

        currency_weight = sector_details["currency_weight"]

        currency_impact = calculate_currency_impact(
            usdinr_momentum=usdinr_momentum,
            currency_weight=currency_weight,
        )

        rows.append(
            {
                "Sector": sector_name,
                "India_Symbol": sector_details["india_symbol"],
                "Global_Symbol": sector_details["global_symbol"],
                "India_Return_Symbol": india_return_symbol_name,
                "Relative_Strength_Raw": relative_strength,
                "Momentum_Raw": momentum,
                "USDINR_Momentum": usdinr_momentum,
                "Currency_Weight": currency_weight,
                "Currency_Impact_Raw": currency_impact,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 11. GILI Score Calculation
# ============================================================

def calculate_gili_scores(
    gili_summary: pd.DataFrame,
    gili_settings: dict,
) -> pd.DataFrame:
    """
    Normalize raw components and calculate final GILI score.
    """
    scored = gili_summary.copy()

    effective_weights = get_effective_component_weights(gili_settings)

    scored["Relative_Strength_Score"] = normalize_to_0_100(
        scored["Relative_Strength_Raw"]
    )

    scored["Momentum_Score"] = normalize_to_0_100(
        scored["Momentum_Raw"]
    )

    scored["Currency_Score"] = normalize_to_0_100(
        scored["Currency_Impact_Raw"]
    )

    scored["Relative_Strength_Weight"] = effective_weights["relative_strength"]
    scored["Momentum_Weight"] = effective_weights["momentum"]
    scored["Currency_Weight_Effective"] = effective_weights["currency"]

    scored["GILI_Score"] = 0.0

    for component_name, component_weight in effective_weights.items():
        score_column = COMPONENT_COLUMN_MAP[component_name]
        scored["GILI_Score"] += component_weight * scored[score_column]

    scored = scored.sort_values(
        by="GILI_Score",
        ascending=False,
        na_position="last",
    )

    scored = scored.reset_index(drop=True)

    scored["Rank"] = scored.index + 1

    ordered_columns = [
        "Rank",
        "Sector",
        "GILI_Score",
        "Relative_Strength_Score",
        "Momentum_Score",
        "Currency_Score",
        "Relative_Strength_Weight",
        "Momentum_Weight",
        "Currency_Weight_Effective",
        "Relative_Strength_Raw",
        "Momentum_Raw",
        "Currency_Impact_Raw",
        "USDINR_Momentum",
        "Currency_Weight",
        "India_Symbol",
        "Global_Symbol",
        "India_Return_Symbol",
    ]

    return scored[ordered_columns]


# ============================================================
# 12. Main GILI Workflow
# ============================================================

def calculate_gili_summary(
    relative_strength_summary: pd.DataFrame,
    momentum_summary: pd.DataFrame,
    sector_config: dict,
    gili_settings: dict | None = None,
) -> pd.DataFrame:
    """
    Calculate final GILI ranking table.
    """
    print("Calculating GILI summary...")

    if gili_settings is None:
        gili_settings = load_gili_settings()

    validate_relative_strength_summary(relative_strength_summary)
    validate_momentum_summary(momentum_summary)
    validate_sector_config(sector_config)
    validate_gili_settings(gili_settings)

    effective_weights = get_effective_component_weights(gili_settings)

    print(
        "Using GILI component weights: "
        f"Relative Strength={effective_weights['relative_strength']:.2%}, "
        f"Momentum={effective_weights['momentum']:.2%}, "
        f"Currency={effective_weights['currency']:.2%}"
    )

    gili_base_rows = build_gili_base_rows(
        relative_strength_summary=relative_strength_summary,
        momentum_summary=momentum_summary,
        sector_config=sector_config,
    )

    gili_summary = calculate_gili_scores(
        gili_summary=gili_base_rows,
        gili_settings=gili_settings,
    )

    for _, row in gili_summary.iterrows():
        print(
            f"Rank {row['Rank']}: {row['Sector']} "
            f"GILI={row['GILI_Score']:.2f}"
        )

    return gili_summary


# ============================================================
# 13. CSV Saving
# ============================================================

def save_gili_summary(
    gili_summary: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Save GILI summary to a CSV file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    gili_summary.to_csv(output_path, index=False)

    print(f"Saved GILI summary to {output_path}")

    return output_path