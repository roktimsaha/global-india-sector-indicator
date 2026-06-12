"""
Main Application Entry Point

Purpose:
    Runs the Global India Sector Indicator application.

Current Phase:
    Phase 1 - Collect global ETF and USD/INR currency data.
"""


# ============================================================
# 1. Imports
# ============================================================

from collectors.global_etf_collector import collect_global_market_data


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
    print("Data collection completed successfully.")
    print("Saved files:")

    for file_path in saved_files:
        print(f"- {file_path}")


# ============================================================
# 3. Script Entry Point
# ============================================================

if __name__ == "__main__":
    main()