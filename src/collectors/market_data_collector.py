"""
Market Data Collector

Purpose:
    Downloads Indian sector index data, global sector ETF data, and USD/INR
    currency data from Yahoo Finance using yfinance.

Input:
    config/sectors.json

Output:
    CSV files inside the data/ folder.

Example output files:
    data/INDIA_Technology.csv
    data/GLOBAL_Technology.csv
    data/INDIA_Banking.csv
    data/GLOBAL_Banking.csv
    data/INDIA_Pharma.csv
    data/GLOBAL_Pharma.csv
    data/USDINR.csv

Designed for:
    Phase 1 and Phase 2 of the Global India Sector Leadership Indicator project.
"""


# ============================================================
# 1. Imports
# ============================================================

from pathlib import Path
import json

import pandas as pd
import yfinance as yf


# ============================================================
# 2. Project Paths
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[2]

CONFIG_PATH = ROOT_DIR / "config" / "sectors.json"

DATA_DIR = ROOT_DIR / "data"


# ============================================================
# 3. Collector Settings
# ============================================================

DEFAULT_PERIOD = "2y"
DEFAULT_INTERVAL = "1d"

CURRENCY_SYMBOL = "INR=X"
CURRENCY_OUTPUT_NAME = "USDINR"


# ============================================================
# 4. Config Loading
# ============================================================

def load_sector_config(config_path: Path = CONFIG_PATH) -> dict:
    """
    Load sector configuration from config/sectors.json.

    Expected structure:
        {
            "Technology": {
                "india_symbol": "^CNXIT",
                "global_symbol": "XLK",
                "currency_weight": 0.40
            }
        }

    Args:
        config_path (Path): Path to sectors.json.

    Returns:
        dict: Loaded sector configuration.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# 5. Output Name Helpers
# ============================================================

def clean_name_for_file(value: str) -> str:
    """
    Convert text into a simple filename-safe value.

    Example:
        "Financial Services" becomes "Financial_Services"
    """
    return (
        value.strip()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("&", "and")
    )


def build_sector_output_name(region: str, sector_name: str) -> str:
    """
    Build a consistent CSV output name for sector data.

    Args:
        region (str): Either INDIA or GLOBAL.
        sector_name (str): Sector name from config.

    Returns:
        str: Filename without .csv.
    """
    clean_sector_name = clean_name_for_file(sector_name)

    return f"{region}_{clean_sector_name}"


# ============================================================
# 6. Symbol Preparation
# ============================================================

def build_symbol_download_map(sector_config: dict) -> dict[str, str]:
    """
    Build a mapping of Yahoo Finance symbols to local CSV output names.

    Example:
        {
            "^CNXIT": "INDIA_Technology",
            "XLK": "GLOBAL_Technology",
            "INR=X": "USDINR"
        }

    The key is the Yahoo Finance download symbol.
    The value is the local CSV filename without .csv.
    """
    symbols_to_download = {}

    for sector_name, sector_details in sector_config.items():
        india_symbol = sector_details.get("india_symbol")
        global_symbol = sector_details.get("global_symbol")

        if india_symbol:
            india_output_name = build_sector_output_name(
                region="INDIA",
                sector_name=sector_name,
            )

            symbols_to_download[india_symbol] = india_output_name

        if global_symbol:
            global_output_name = build_sector_output_name(
                region="GLOBAL",
                sector_name=sector_name,
            )

            symbols_to_download[global_symbol] = global_output_name

    symbols_to_download[CURRENCY_SYMBOL] = CURRENCY_OUTPUT_NAME

    return symbols_to_download


# ============================================================
# 7. Download Logic
# ============================================================

def download_from_yfinance(
    symbol: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> pd.DataFrame:
    """
    Download historical market data from Yahoo Finance.

    Args:
        symbol (str): Yahoo Finance symbol, for example ^CNXIT, XLK, or INR=X.
        period (str): Time period to download, for example "2y".
        interval (str): Data interval, for example "1d".

    Returns:
        pd.DataFrame: Raw downloaded data.
    """
    print(f"Downloading {symbol}...")

    data = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    if data.empty:
        raise ValueError(f"No data downloaded for symbol: {symbol}")

    return data


# ============================================================
# 8. Data Cleaning
# ============================================================

def flatten_columns_if_needed(data: pd.DataFrame) -> pd.DataFrame:
    """
    Flatten yfinance MultiIndex columns if they appear.

    Sometimes yfinance returns columns like:
        ("Close", "XLK")

    This function converts them into simple columns like:
        "Close"
    """
    cleaned = data.copy()

    if isinstance(cleaned.columns, pd.MultiIndex):
        cleaned.columns = [
            column[0] if column[0] else column[1]
            for column in cleaned.columns.to_flat_index()
        ]

    return cleaned


def standardize_column_names(data: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize column names so they are easier to work with later.

    Example:
        "Adj Close" becomes "Adj_Close"
    """
    cleaned = data.copy()

    cleaned.columns = [
        str(column).strip().replace(" ", "_")
        for column in cleaned.columns
    ]

    return cleaned


def keep_required_columns(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    Keep only the columns needed for this project.

    Expected columns:
        Date, Open, High, Low, Close, Adj_Close, Volume

    Some instruments may not always have every column,
    so this function keeps whichever expected columns are available.
    """
    preferred_columns = [
        "Date",
        "Open",
        "High",
        "Low",
        "Close",
        "Adj_Close",
        "Volume",
    ]

    available_columns = [
        column for column in preferred_columns
        if column in data.columns
    ]

    if "Date" not in available_columns:
        raise ValueError(f"Downloaded data for {symbol} does not contain a Date column.")

    return data[available_columns]


def clean_downloaded_data(data: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    Clean yfinance data before saving it as a CSV file.

    Cleaning steps:
        1. Flatten MultiIndex columns if needed.
        2. Move Date from index to normal column.
        3. Standardize column names.
        4. Keep only required columns.
        5. Convert Date values into clean date format.

    Args:
        data (pd.DataFrame): Raw yfinance data.
        symbol (str): Yahoo Finance symbol.

    Returns:
        pd.DataFrame: Cleaned data ready for CSV export.
    """
    cleaned = flatten_columns_if_needed(data)

    cleaned = cleaned.reset_index()

    cleaned = standardize_column_names(cleaned)

    cleaned = keep_required_columns(cleaned, symbol)

    cleaned["Date"] = pd.to_datetime(cleaned["Date"]).dt.date

    return cleaned


# ============================================================
# 9. CSV Saving
# ============================================================

def save_data_to_csv(
    data: pd.DataFrame,
    output_name: str,
    data_dir: Path = DATA_DIR,
) -> Path:
    """
    Save cleaned market data to a CSV file.

    Args:
        data (pd.DataFrame): Cleaned market data.
        output_name (str): Filename without .csv.
        data_dir (Path): Output folder.

    Returns:
        Path: Full path to the saved CSV file.
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    output_path = data_dir / f"{output_name}.csv"

    data.to_csv(output_path, index=False)

    return output_path


# ============================================================
# 10. Single Symbol Workflow
# ============================================================

def collect_single_symbol(
    symbol: str,
    output_name: str,
    period: str = DEFAULT_PERIOD,
    interval: str = DEFAULT_INTERVAL,
) -> Path:
    """
    Download, clean, and save one market symbol.

    Args:
        symbol (str): Yahoo Finance symbol.
        output_name (str): CSV filename without .csv.
        period (str): Download period.
        interval (str): Download interval.

    Returns:
        Path: Path to saved CSV file.
    """
    raw_data = download_from_yfinance(
        symbol=symbol,
        period=period,
        interval=interval,
    )

    cleaned_data = clean_downloaded_data(
        data=raw_data,
        symbol=symbol,
    )

    output_path = save_data_to_csv(
        data=cleaned_data,
        output_name=output_name,
    )

    relative_path = output_path.relative_to(ROOT_DIR)

    print(f"Saved {relative_path} with {len(cleaned_data)} rows.")

    return output_path


# ============================================================
# 11. Main Collector Workflow
# ============================================================

def collect_market_data() -> list[Path]:
    """
    Main workflow for Indian sector, global sector, and currency collection.

    Steps:
        1. Load sector configuration.
        2. Build Yahoo Finance symbol map.
        3. Download each symbol.
        4. Save each dataset as CSV.
        5. Report any failures.

    Returns:
        list[Path]: List of saved CSV file paths.
    """
    sector_config = load_sector_config()

    symbols_to_download = build_symbol_download_map(sector_config)

    saved_files = []
    failures = {}

    for symbol, output_name in symbols_to_download.items():
        try:
            saved_file = collect_single_symbol(
                symbol=symbol,
                output_name=output_name,
            )

            saved_files.append(saved_file)

        except Exception as error:
            failures[symbol] = str(error)

    if failures:
        failure_messages = [
            f"{symbol}: {message}"
            for symbol, message in failures.items()
        ]

        raise RuntimeError(
            "Some downloads failed:\n" + "\n".join(failure_messages)
        )

    return saved_files


# ============================================================
# 12. Script Entry Point
# ============================================================

if __name__ == "__main__":
    collect_market_data()