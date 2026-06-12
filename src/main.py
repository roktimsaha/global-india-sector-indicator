"""
Main Application Entry Point

Purpose:
    Runs the Global India Sector Indicator application.

Current Phase:
    Phase 3 - Calculate the first GILI sector ranking and text report.
"""


# ============================================================
# 1. Imports
# ============================================================

from pathlib import Path

from collectors.market_data_collector import collect_market_data, load_sector_config
from validators.market_data_validator import validate_market_data_files
from calculations.return_calculator import (
    calculate_return_summary,
    save_return_summary,
)
from calculations.momentum_calculator import (
    calculate_momentum_summary,
    save_momentum_summary,
)
from calculations.relative_strength_calculator import (
    calculate_relative_strength_summary,
    save_relative_strength_summary,
)
from calculations.gili_calculator import (
    calculate_gili_summary,
    save_gili_summary,
)
from reports.gili_report_generator import save_gili_text_report


# ============================================================
# 2. Project Paths
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"

RETURNS_SUMMARY_PATH = DATA_DIR / "returns_summary.csv"
MOMENTUM_SUMMARY_PATH = DATA_DIR / "momentum_summary.csv"
RELATIVE_STRENGTH_SUMMARY_PATH = DATA_DIR / "relative_strength_summary.csv"
GILI_SUMMARY_PATH = DATA_DIR / "gili_summary.csv"
GILI_REPORT_PATH = DATA_DIR / "gili_report.txt"


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

    sector_config = load_sector_config()

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
    relative_strength_summary = calculate_relative_strength_summary(
        return_summary=return_summary,
        sector_config=sector_config,
    )

    print()
    save_relative_strength_summary(
        relative_strength_summary=relative_strength_summary,
        output_path=RELATIVE_STRENGTH_SUMMARY_PATH,
    )

    print()
    gili_summary = calculate_gili_summary(
        relative_strength_summary=relative_strength_summary,
        momentum_summary=momentum_summary,
        sector_config=sector_config,
    )

    print()
    save_gili_summary(
        gili_summary=gili_summary,
        output_path=GILI_SUMMARY_PATH,
    )

    print()
    save_gili_text_report(
        gili_summary=gili_summary,
        output_path=GILI_REPORT_PATH,
    )

    print()
    print(
        "Market data collection, validation, return calculation, "
        "momentum calculation, relative strength calculation, "
        "GILI ranking, and report generation completed successfully."
    )


# ============================================================
# 4. Script Entry Point
# ============================================================

if __name__ == "__main__":
    main()