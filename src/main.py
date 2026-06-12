"""
Main Application Entry Point

Purpose:
    Runs the Global India Sector Indicator application.

Current Phase:
    Phase 2 - Collect Indian sector data, global sector data, USD/INR data,
    validate CSV files, calculate returns, and calculate momentum.
"""


# ============================================================
# 1. Imports
# ============================================================

from pathlib import Path

from collectors.market_data_collector import collect_market_data
from validators.market_data_validator import validate_market_data_files
from calculations.return_calculator import (
    calculate_return_summary,
    save_return_summary,
)
from calculations.momentum_calculator import (
    calculate_momentum_summary,
    save_momentum_summary,
)


# ============================================================
# 2. Project Paths
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

RETURNS_SUMMARY_PATH = DATA_DIR / "returns_summary.csv"
MOMENTUM_SUMMARY_PATH = DATA_DIR / "momentum_summary.csv"


# ============================================================
# 3. Main Application Workflow
# ============================================================

def main() -> None:
    """
    Run the main application workflow.
    """
    print("Global India Sector Indicator")
    print("Starting market data collection...")
    print()

    saved_files = collect_market_data()

    print()
    validate_market_data_files(saved_files)

    print()
    return_summary = calculate_return_summary(saved_files)

    print()
    save_return_summary(
        return_summary=return_summary,
        output_path=RETURNS_SUMMARY_PATH,
    )

    print()
    momentum_summary = calculate_momentum_summary(return_summary)

    print()
    save_momentum_summary(
        momentum_summary=momentum_summary,
        output_path=MOMENTUM_SUMMARY_PATH,
    )

    print()
    print(
        "Market data collection, validation, return calculation, "
        "and momentum calculation completed successfully."
    )


# ============================================================
# 4. Script Entry Point
# ============================================================

if __name__ == "__main__":
    main()