"""
Main Application Entry Point

Purpose:
    Runs the Global India Sector Indicator application.

Current Phase:
    Phase 1 - Collect and validate global ETF and USD/INR currency data.
"""


# ============================================================
# 1. Imports
# ============================================================

from collectors.global_etf_collector import collect_global_market_data
from validators.market_data_validator import validate_market_data_files


# ============================================================
# 2. Main Application Workflow
# ============================================================

def main() -> None:
    """
    Run the main application workflow.
    """
    print("Global India Sector Indicator")
    print("Starting global ETF and currency data collection...")
    print()

    saved_files = collect_global_market_data()

    print()
    validate_market_data_files(saved_files)

    print()
    print("Data collection and validation completed successfully.")
    print("Saved files:")

    for file_path in saved_files:
        print(f"- {file_path}")


# ============================================================
# 3. Script Entry Point
# ============================================================

if __name__ == "__main__":
    main()