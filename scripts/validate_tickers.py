"""
Ticker Validation Script

Purpose:
    Validates enabled sector tickers in config/sectors.json before running
    the full GILI workflow.

Checks:
    1. Enabled Indian sector tickers
    2. Enabled global benchmark tickers
    3. USDINR ticker
    4. At least 6 months of daily data

Run:
    python scripts/validate_tickers.py
"""


# ============================================================
# 1. Imports
# ============================================================

from pathlib import Path
import json
import sys

import yfinance as yf


# ============================================================
# 2. Project Paths
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]
SECTORS_CONFIG_PATH = ROOT_DIR / "config" / "sectors.json"


# ============================================================
# 3. Validation Settings
# ============================================================

USDINR_SYMBOL = "INR=X"

VALIDATION_PERIOD = "8mo"
VALIDATION_INTERVAL = "1d"

MINIMUM_ROWS_REQUIRED = 126


# ============================================================
# 4. Config Loading
# ============================================================

def load_sector_config(config_path: Path = SECTORS_CONFIG_PATH) -> dict:
    """
    Load sector configuration from config/sectors.json.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# 5. Sector Helpers
# ============================================================

def is_sector_enabled(sector_details: dict) -> bool:
    """
    Check whether a sector is enabled.

    Backward-compatible behavior:
        If 'enabled' is missing, treat the sector as enabled.
    """
    return sector_details.get("enabled", True)


def build_ticker_validation_list(sector_config: dict) -> list[dict]:
    """
    Build a list of tickers to validate.
    """
    tickers = []

    for sector_name, sector_details in sector_config.items():
        if not is_sector_enabled(sector_details):
            continue

        india_symbol = sector_details.get("india_symbol")
        global_symbol = sector_details.get("global_symbol")

        tickers.append(
            {
                "sector": sector_name,
                "type": "INDIA",
                "symbol": india_symbol,
            }
        )

        tickers.append(
            {
                "sector": sector_name,
                "type": "GLOBAL",
                "symbol": global_symbol,
            }
        )

    tickers.append(
        {
            "sector": "Currency",
            "type": "CURRENCY",
            "symbol": USDINR_SYMBOL,
        }
    )

    return tickers


# ============================================================
# 6. Single Ticker Validation
# ============================================================

def validate_symbol(symbol: str) -> tuple[bool, str, int]:
    """
    Validate one Yahoo Finance symbol.

    Returns:
        tuple:
            is_valid, message, row_count
    """
    if not symbol:
        return False, "Missing symbol", 0

    if symbol == "VERIFY_WITH_YFINANCE":
        return False, "Symbol still marked VERIFY_WITH_YFINANCE", 0

    try:
        data = yf.download(
            symbol,
            period=VALIDATION_PERIOD,
            interval=VALIDATION_INTERVAL,
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        row_count = len(data)

        if data.empty:
            return False, "No data returned", row_count

        if row_count < MINIMUM_ROWS_REQUIRED:
            return (
                False,
                f"Only {row_count} rows returned; minimum is {MINIMUM_ROWS_REQUIRED}",
                row_count,
            )

        return True, "PASS", row_count

    except Exception as error:
        return False, str(error), 0


# ============================================================
# 7. Report Printing
# ============================================================

def print_validation_result(
    sector: str,
    ticker_type: str,
    symbol: str,
    is_valid: bool,
    message: str,
    row_count: int,
) -> None:
    """
    Print one validation result row.
    """
    status = "PASS" if is_valid else "FAIL"

    print(
        f"{sector:<22} "
        f"{ticker_type:<10} "
        f"{symbol:<18} "
        f"{status:<6} "
        f"Rows: {row_count:<5} "
        f"{message}"
    )


# ============================================================
# 8. Main Validation Workflow
# ============================================================

def main() -> None:
    """
    Run ticker validation.
    """
    print("GILI Ticker Validation")
    print("=" * 80)

    sector_config = load_sector_config()

    tickers = build_ticker_validation_list(sector_config)

    failures = []

    print(
        f"{'Sector':<22} "
        f"{'Type':<10} "
        f"{'Symbol':<18} "
        f"{'Status':<6} "
        f"Details"
    )
    print("-" * 80)

    for ticker in tickers:
        sector = ticker["sector"]
        ticker_type = ticker["type"]
        symbol = ticker["symbol"]

        is_valid, message, row_count = validate_symbol(symbol)

        print_validation_result(
            sector=sector,
            ticker_type=ticker_type,
            symbol=symbol,
            is_valid=is_valid,
            message=message,
            row_count=row_count,
        )

        if not is_valid:
            failures.append(ticker)

    print("-" * 80)

    if failures:
        print(f"Ticker validation failed for {len(failures)} ticker(s).")
        sys.exit(1)

    print("All enabled tickers passed validation.")
    sys.exit(0)


# ============================================================
# 9. Script Entry Point
# ============================================================

if __name__ == "__main__":
    main()