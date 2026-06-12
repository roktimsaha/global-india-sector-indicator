"""
Return Calculator

Purpose:
    Calculates 1-month, 3-month, and 6-month returns from downloaded
    market data CSV files.

Current approach:
    1 month = 21 trading days
    3 month = 63 trading days
    6 month = 126 trading days

Output:
    data/returns_summary.csv

Designed for:
    Phase 2 of the Global India Sector Leadership Indicator project.
"""


# ============================================================
# 1. Imports
# ============================================================

from pathlib import Path

import pandas as pd


# ============================================================
# 2. Return Settings
# ============================================================

RETURN_PERIODS = {
    "Return_1M": 21,
    "Return_3M": 63,
    "Return_6M": 126,
}

PREFERRED_PRICE_COLUMNS = [
    "Adj_Close",
    "Close",
]


# ============================================================
# 3. CSV Loading
# ============================================================

def load_market_data(file_path: Path) -> pd.DataFrame:
    """
    Load one market data CSV file.

    Args:
        file_path (Path): Path to the CSV file.

    Returns:
        pd.DataFrame: Loaded market data.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Missing data file: {file_path}")

    data = pd.read_csv(file_path)

    if data.empty:
        raise ValueError(f"Data file is empty: {file_path}")

    return data


# ============================================================
# 4. Price Column Selection
# ============================================================

def select_price_column(data: pd.DataFrame) -> str:
    """
    Select the best available price column for return calculations.

    Preference:
        1. Adj_Close
        2. Close

    Returns:
        str: Selected price column name.
    """
    for column in PREFERRED_PRICE_COLUMNS:
        if column in data.columns:
            return column

    raise ValueError(
        f"No valid price column found. Expected one of: {PREFERRED_PRICE_COLUMNS}"
    )


# ============================================================
# 5. Data Preparation
# ============================================================

def prepare_market_data(data: pd.DataFrame, file_path: Path) -> pd.DataFrame:
    """
    Prepare market data for return calculations.

    Steps:
        1. Confirm Date column exists.
        2. Convert Date to datetime.
        3. Sort data from oldest to newest.
        4. Remove rows where Date or selected price is missing.

    Args:
        data (pd.DataFrame): Raw market data.
        file_path (Path): Source CSV file path, used for error messages.

    Returns:
        pd.DataFrame: Prepared market data.
    """
    if "Date" not in data.columns:
        raise ValueError(f"Missing Date column in file: {file_path}")

    price_column = select_price_column(data)

    prepared = data.copy()

    prepared["Date"] = pd.to_datetime(prepared["Date"])

    prepared = prepared.sort_values("Date")

    prepared = prepared.dropna(subset=["Date", price_column])

    if prepared.empty:
        raise ValueError(f"No usable rows after cleaning file: {file_path}")

    return prepared


# ============================================================
# 6. Return Calculation
# ============================================================

def calculate_period_return(
    data: pd.DataFrame,
    price_column: str,
    trading_days: int,
) -> float | None:
    """
    Calculate return over a specific number of trading days.

    Formula:
        return = latest_price / old_price - 1

    Args:
        data (pd.DataFrame): Prepared market data.
        price_column (str): Price column to use.
        trading_days (int): Number of trading days to look back.

    Returns:
        float | None: Return as a decimal, or None if not enough data.
    """
    if len(data) <= trading_days:
        return None

    latest_price = data[price_column].iloc[-1]
    old_price = data[price_column].iloc[-1 - trading_days]

    return (latest_price / old_price) - 1


def calculate_returns_for_file(file_path: Path) -> dict:
    """
    Calculate 1M, 3M, and 6M returns for one CSV file.

    Args:
        file_path (Path): Market data CSV file.

    Returns:
        dict: Return summary for one symbol.
    """
    raw_data = load_market_data(file_path)

    prepared_data = prepare_market_data(raw_data, file_path)

    price_column = select_price_column(prepared_data)

    latest_row = prepared_data.iloc[-1]

    result = {
        "Symbol": file_path.stem,
        "Latest_Date": latest_row["Date"].date(),
        "Price_Column": price_column,
        "Latest_Price": latest_row[price_column],
    }

    for return_name, trading_days in RETURN_PERIODS.items():
        result[return_name] = calculate_period_return(
            data=prepared_data,
            price_column=price_column,
            trading_days=trading_days,
        )

    return result


# ============================================================
# 7. Multiple File Workflow
# ============================================================

def calculate_return_summary(file_paths: list[Path]) -> pd.DataFrame:
    """
    Calculate return summary for multiple market data files.

    Args:
        file_paths (list[Path]): List of market data CSV files.

    Returns:
        pd.DataFrame: Return summary table.
    """
    print("Calculating return summary...")

    results = []

    for file_path in file_paths:
        result = calculate_returns_for_file(file_path)
        results.append(result)

        print(
            f"Calculated returns for {file_path.name}: "
            f"1M={format_return(result['Return_1M'])}, "
            f"3M={format_return(result['Return_3M'])}, "
            f"6M={format_return(result['Return_6M'])}"
        )

    return pd.DataFrame(results)


# ============================================================
# 8. Formatting Helpers
# ============================================================

def format_return(value: float | None) -> str:
    """
    Format a return value for terminal display.

    Args:
        value (float | None): Return as decimal.

    Returns:
        str: Human-readable percentage.
    """
    if value is None:
        return "N/A"

    return f"{value:.2%}"


# ============================================================
# 9. CSV Saving
# ============================================================

def save_return_summary(
    return_summary: pd.DataFrame,
    output_path: Path,
) -> Path:
    """
    Save return summary to a CSV file.

    Args:
        return_summary (pd.DataFrame): Return summary table.
        output_path (Path): Output CSV path.

    Returns:
        Path: Saved output path.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    return_summary.to_csv(output_path, index=False)

    print(f"Saved return summary to {output_path}")

    return output_path