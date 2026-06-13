"""
GILI Calculator

Purpose:
    Calculates the Global India Sector Leadership Indicator score.

GILI v2 formula:
    GILI =
        Effective Relative Strength Weight * Relative Strength Score
        + Effective Momentum Weight * Momentum Score
        + Effective Currency Weight * Currency Score

Currency formula:
    Currency_Impact_Raw =
        USDINR_Momentum * currency_weight * currency_direction

Normalization:
    Supports config-driven normalization.

    Preferred GILI v2 method:
        winsorized_minmax

    This method:
        1. Converts raw component values to numeric.
        2. Calculates lower and upper percentile thresholds.
        3. Clips values to those thresholds.
        4. Applies min-max normalization to 0-100.
        5. Assigns a neutral score when all valid values are equal.
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
# 3. Settings
# ============================================================

DEFAULT_GILI_SETTINGS = {
    "formula_version": "GILI_V2_EXCESS_RETURN",
    "components": {
        "relative_strength": {
            "enabled": True,
            "weight": 0.55,
        },
        "momentum": {
            "enabled": True,
            "weight": 0.30,
        },
        "currency": {
            "enabled": True,
            "weight": 0.15,
        },
    },
    "normalization": {
        "method": "winsorized_minmax",
        "lower_percentile": 5,
        "upper_percentile": 95,
        "equal_value_score": 50,
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
# 5. Settings Loading
# ============================================================

def load_gili_settings(settings_path: Path = GILI_SETTINGS_PATH) -> dict:
    """
    Load GILI settings from config/gili_settings.json.

    If the settings file does not exist, default settings are used.
    """
    if not settings_path.exists():
        return DEFAULT_GILI_SETTINGS

    with settings_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_normalization_settings(gili_settings: dict) -> dict:
    """
    Return normalization settings with safe defaults.

    This makes the feature config-driven while still allowing the program
    to run if the normalization block has not yet been added to config.
    """
    default_normalization = DEFAULT_GILI_SETTINGS["normalization"].copy()

    user_normalization = gili_settings.get("normalization", {})

    if user_normalization is None:
        user_normalization = {}

    normalization_settings = {
        **default_normalization,
        **user_normalization,
    }

    return normalization_settings


def validate_normalization_settings(gili_settings: dict) -> None:
    """
    Validate normalization settings.
    """
    normalization_settings = get_normalization_settings(gili_settings)

    method = normalization_settings.get("method")
    lower_percentile = normalization_settings.get("lower_percentile")
    upper_percentile = normalization_settings.get("upper_percentile")
    equal_value_score = normalization_settings.get("equal_value_score")

    supported_methods = [
        "minmax",
        "simple_minmax",
        "winsorized_minmax",
    ]

    if method not in supported_methods:
        raise ValueError(
            "Unsupported normalization method. "
            f"Got '{method}'. Supported methods: {supported_methods}"
        )

    if not isinstance(equal_value_score, (int, float)) or isinstance(equal_value_score, bool):
        raise ValueError("normalization.equal_value_score must be numeric.")

    if equal_value_score < 0 or equal_value_score > 100:
        raise ValueError(
            "normalization.equal_value_score must be between 0 and 100."
        )

    if method == "winsorized_minmax":
        if not isinstance(lower_percentile, (int, float)) or isinstance(lower_percentile, bool):
            raise ValueError(
                "normalization.lower_percentile must be numeric."
            )

        if not isinstance(upper_percentile, (int, float)) or isinstance(upper_percentile, bool):
            raise ValueError(
                "normalization.upper_percentile must be numeric."
            )

        if lower_percentile < 0 or lower_percentile > 100:
            raise ValueError(
                "normalization.lower_percentile must be between 0 and 100."
            )

        if upper_percentile < 0 or upper_percentile > 100:
            raise ValueError(
                "normalization.upper_percentile must be between 0 and 100."
            )

        if lower_percentile >= upper_percentile:
            raise ValueError(
                "normalization.lower_percentile must be less than "
                "normalization.upper_percentile."
            )


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

        enabled = component_settings["enabled"]
        weight = component_settings["weight"]

        if not isinstance(enabled, bool):
            raise ValueError(
                f"GILI component '{component_name}' enabled must be true or false."
            )

        if not isinstance(weight, (int, float)) or isinstance(weight, bool):
            raise ValueError(
                f"GILI component '{component_name}' weight must be numeric."
            )

        if enabled:
            enabled_count += 1

        if weight < 0:
            raise ValueError(
                f"GILI component '{component_name}' weight cannot be negative."
            )

    if enabled_count == 0:
        raise ValueError("At least one GILI component must be enabled.")

    validate_normalization_settings(gili_settings)


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

    if not isinstance(normalize_enabled_weights, bool):
        raise ValueError("normalize_enabled_weights must be true or false.")

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

    GILI v2 prefers Relative_Strength_Raw.
    Relative_Strength_Composite is supported temporarily for compatibility.
    """
    if "Sector" not in relative_strength_summary.columns:
        raise ValueError("Relative strength summary is missing column: Sector")

    has_v2_column = "Relative_Strength_Raw" in relative_strength_summary.columns
    has_legacy_column = (
        "Relative_Strength_Composite" in relative_strength_summary.columns
    )

    if not has_v2_column and not has_legacy_column:
        raise ValueError(
            "Relative strength summary must contain either "
            "Relative_Strength_Raw or Relative_Strength_Composite."
        )


def validate_momentum_summary(momentum_summary: pd.DataFrame) -> None:
    """
    Validate required momentum columns.

    GILI v2 prefers Momentum_Raw.
    Momentum is supported temporarily for compatibility.
    """
    if "Symbol" not in momentum_summary.columns:
        raise ValueError("Momentum summary is missing column: Symbol")

    has_v2_column = "Momentum_Raw" in momentum_summary.columns
    has_legacy_column = "Momentum" in momentum_summary.columns

    if not has_v2_column and not has_legacy_column:
        raise ValueError(
            "Momentum summary must contain either Momentum_Raw or Momentum."
        )


def is_sector_enabled(sector_details: dict) -> bool:
    """
    Check whether a sector is enabled.

    Backward-compatible behavior:
        If 'enabled' is missing, treat sector as enabled.
    """
    return sector_details.get("enabled", True)


def validate_sector_config(sector_config: dict) -> None:
    """
    Validate that each enabled sector has the fields needed for GILI.
    """
    failures = {}

    for sector_name, sector_details in sector_config.items():
        if not is_sector_enabled(sector_details):
            continue

        missing_fields = []

        required_fields = [
            "india_symbol",
            "global_symbol",
            "currency_weight",
            "currency_direction",
        ]

        for field in required_fields:
            if field not in sector_details:
                missing_fields.append(field)

        if missing_fields:
            failures[sector_name] = missing_fields
            continue

        currency_weight = sector_details["currency_weight"]
        currency_direction = sector_details["currency_direction"]

        if not isinstance(currency_weight, (int, float)) or isinstance(currency_weight, bool):
            raise ValueError(
                f"Sector '{sector_name}' currency_weight must be numeric."
            )

        if currency_weight < 0 or currency_weight > 1:
            raise ValueError(
                f"Sector '{sector_name}' currency_weight must be between 0 and 1."
            )

        if currency_direction not in [-1, 0, 1]:
            raise ValueError(
                f"Sector '{sector_name}' currency_direction must be -1, 0, or 1."
            )

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

    row = matching_rows.iloc[0]

    if "Momentum_Raw" in row.index:
        return row["Momentum_Raw"]

    return row["Momentum"]


def get_relative_strength_for_sector(
    relative_strength_summary: pd.DataFrame,
    sector_name: str,
) -> float:
    """
    Get relative strength raw value for one sector.
    """
    matching_rows = relative_strength_summary[
        relative_strength_summary["Sector"] == sector_name
    ]

    if matching_rows.empty:
        raise ValueError(
            f"Missing relative strength row for sector: {sector_name}"
        )

    row = matching_rows.iloc[0]

    if "Relative_Strength_Raw" in row.index:
        return row["Relative_Strength_Raw"]

    return row["Relative_Strength_Composite"]


# ============================================================
# 8. Normalization
# ============================================================

def normalize_minmax(
    values: pd.Series,
    equal_value_score: float = 50,
) -> pd.Series:
    """
    Normalize a numeric series to a 0-100 scale using simple min-max.

    Formula:
        normalized = ((value - min_value) / (max_value - min_value)) * 100

    If all valid values are equal, every valid value receives equal_value_score.
    """
    numeric_values = pd.to_numeric(values, errors="coerce")

    min_value = numeric_values.min()
    max_value = numeric_values.max()

    if pd.isna(min_value) or pd.isna(max_value):
        return numeric_values

    if max_value == min_value:
        return numeric_values.apply(
            lambda value: equal_value_score if not pd.isna(value) else None
        )

    return ((numeric_values - min_value) / (max_value - min_value)) * 100


def normalize_winsorized_minmax(
    values: pd.Series,
    lower_percentile: float = 5,
    upper_percentile: float = 95,
    equal_value_score: float = 50,
) -> pd.Series:
    """
    Normalize a numeric series to a 0-100 scale using winsorized min-max.

    Steps:
        1. Convert values to numeric.
        2. Calculate lower and upper percentile thresholds.
        3. Clip values to those thresholds.
        4. Apply min-max normalization to clipped values.
        5. If all valid clipped values are equal, assign equal_value_score.
    """
    numeric_values = pd.to_numeric(values, errors="coerce")

    valid_values = numeric_values.dropna()

    if valid_values.empty:
        return numeric_values

    lower_threshold = valid_values.quantile(lower_percentile / 100)
    upper_threshold = valid_values.quantile(upper_percentile / 100)

    clipped_values = numeric_values.clip(
        lower=lower_threshold,
        upper=upper_threshold,
    )

    min_value = clipped_values.min()
    max_value = clipped_values.max()

    if pd.isna(min_value) or pd.isna(max_value):
        return clipped_values

    if max_value == min_value:
        return clipped_values.apply(
            lambda value: equal_value_score if not pd.isna(value) else None
        )

    return ((clipped_values - min_value) / (max_value - min_value)) * 100


def normalize_to_0_100(
    values: pd.Series,
    gili_settings: dict,
) -> pd.Series:
    """
    Normalize a numeric series to a 0-100 score using config settings.

    Supported methods:
        - minmax
        - simple_minmax
        - winsorized_minmax
    """
    normalization_settings = get_normalization_settings(gili_settings)

    method = normalization_settings["method"]
    lower_percentile = normalization_settings["lower_percentile"]
    upper_percentile = normalization_settings["upper_percentile"]
    equal_value_score = normalization_settings["equal_value_score"]

    if method in ["minmax", "simple_minmax"]:
        return normalize_minmax(
            values=values,
            equal_value_score=equal_value_score,
        )

    if method == "winsorized_minmax":
        return normalize_winsorized_minmax(
            values=values,
            lower_percentile=lower_percentile,
            upper_percentile=upper_percentile,
            equal_value_score=equal_value_score,
        )

    raise ValueError(f"Unsupported normalization method: {method}")


# ============================================================
# 9. Currency Impact Calculation
# ============================================================

def calculate_currency_impact(
    usdinr_momentum: float,
    currency_weight: float,
    currency_direction: int,
) -> float | None:
    """
    Calculate raw currency impact for one sector.

    GILI v2 formula:
        Currency_Impact_Raw =
            USDINR_Momentum * currency_weight * currency_direction

    Meaning:
        currency_direction =  1 means INR weakness helps the sector
        currency_direction = -1 means INR weakness hurts the sector
        currency_direction =  0 means mostly neutral
    """
    if pd.isna(usdinr_momentum) or pd.isna(currency_weight):
        return None

    if currency_direction not in [-1, 0, 1]:
        raise ValueError("currency_direction must be -1, 0, or 1.")

    return usdinr_momentum * currency_weight * currency_direction


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

    Each row represents one enabled sector.
    """
    usdinr_momentum = get_momentum_for_symbol(
        momentum_summary=momentum_summary,
        symbol_name=USDINR_SYMBOL_NAME,
    )

    rows = []

    for sector_name, sector_details in sector_config.items():
        if not is_sector_enabled(sector_details):
            print(f"Skipping disabled sector in GILI: {sector_name}")
            continue

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
        currency_direction = sector_details["currency_direction"]

        currency_impact = calculate_currency_impact(
            usdinr_momentum=usdinr_momentum,
            currency_weight=currency_weight,
            currency_direction=currency_direction,
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
                "Currency_Direction": currency_direction,
                "Currency_Impact_Raw": currency_impact,
            }
        )

    if not rows:
        raise ValueError("No enabled sectors available for GILI calculation.")

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
    normalization_settings = get_normalization_settings(gili_settings)

    scored["Relative_Strength_Score"] = normalize_to_0_100(
        values=scored["Relative_Strength_Raw"],
        gili_settings=gili_settings,
    )

    scored["Momentum_Score"] = normalize_to_0_100(
        values=scored["Momentum_Raw"],
        gili_settings=gili_settings,
    )

    scored["Currency_Score"] = normalize_to_0_100(
        values=scored["Currency_Impact_Raw"],
        gili_settings=gili_settings,
    )

    # New internal effective weight columns.
    scored["Effective_RS_Weight"] = effective_weights["relative_strength"]
    scored["Effective_Momentum_Weight"] = effective_weights["momentum"]
    scored["Effective_Currency_Weight"] = effective_weights["currency"]

    # Backward-compatible aliases required by the current report generator.
    scored["Relative_Strength_Weight"] = scored["Effective_RS_Weight"]
    scored["Momentum_Weight"] = scored["Effective_Momentum_Weight"]
    scored["Currency_Weight_Effective"] = scored["Effective_Currency_Weight"]

    scored["GILI"] = 0.0

    for component_name, component_weight in effective_weights.items():
        score_column = COMPONENT_COLUMN_MAP[component_name]
        scored["GILI"] += component_weight * scored[score_column]

    # Backward-compatible alias required by the current report generator.
    scored["GILI_Score"] = scored["GILI"]

    scored = scored.sort_values(
        by="GILI",
        ascending=False,
        na_position="last",
    )

    scored = scored.reset_index(drop=True)

    scored["Rank"] = scored.index + 1

    formula_version = gili_settings.get(
        "formula_version",
        "GILI_V2_EXCESS_RETURN",
    )

    scored["Formula_Version"] = formula_version
    scored["Normalization_Method"] = normalization_settings["method"]
    scored["Normalization_Lower_Percentile"] = normalization_settings["lower_percentile"]
    scored["Normalization_Upper_Percentile"] = normalization_settings["upper_percentile"]
    scored["Normalization_Equal_Value_Score"] = normalization_settings["equal_value_score"]

    ordered_columns = [
        "Rank",
        "Sector",
        "India_Symbol",
        "Global_Symbol",

        "Relative_Strength_Raw",
        "Relative_Strength_Score",
        "Momentum_Raw",
        "Momentum_Score",
        "Currency_Impact_Raw",
        "Currency_Score",

        "Currency_Weight",
        "Currency_Direction",
        "USDINR_Momentum",

        "Effective_RS_Weight",
        "Effective_Momentum_Weight",
        "Effective_Currency_Weight",

        # Backward-compatible report-generator columns.
        "Relative_Strength_Weight",
        "Momentum_Weight",
        "Currency_Weight_Effective",

        "GILI",
        "GILI_Score",
        "Formula_Version",

        "Normalization_Method",
        "Normalization_Lower_Percentile",
        "Normalization_Upper_Percentile",
        "Normalization_Equal_Value_Score",

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
    normalization_settings = get_normalization_settings(gili_settings)

    print(
        "Using GILI component weights: "
        f"Relative Strength={effective_weights['relative_strength']:.2%}, "
        f"Momentum={effective_weights['momentum']:.2%}, "
        f"Currency={effective_weights['currency']:.2%}"
    )

    print(
        "Using normalization method: "
        f"{normalization_settings['method']} "
        f"(lower={normalization_settings['lower_percentile']}, "
        f"upper={normalization_settings['upper_percentile']}, "
        f"equal_value_score={normalization_settings['equal_value_score']})"
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
            f"GILI={row['GILI']:.2f}"
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