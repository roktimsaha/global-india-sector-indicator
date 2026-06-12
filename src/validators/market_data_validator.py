"""
Market Data Validator

Purpose:
    Validates downloaded market data CSV files before the project uses them
    for return calculations, momentum calculations, relative strength, or GILI.

Current checks:
    1. File exists.
    2. File is not empty.
    3. File contains required columns.
    4. File has at least one data row.

Designed for:
    Phase 1 of the Global India Sector Leadership Indicator project.
"""


# ============================================================
# 1. Imports
# ============================================================

from pathlib import Path

import pandas as pd


# ============================================================
# 2. Validator Settings
# ============================================================

REQUIRED_COLUMNS = [
    "Date",
    "Close",
]


# ============================================================
# 3. Single File Validation
# ============================================================

def validate_market_data_file(file_path: Path) -> bool:
    """
    Validate one market data CSV file.

    Args:
        file_path (Path): Path to the CSV file.

    Returns:
        bool: True if the file passes validation.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the CSV file is empty or missing required columns.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Missing data file: {file_path}")

    data = pd.read_csv(file_path)

    if data.empty:
        raise ValueError(f"Data file is empty: {file_path}")

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Data file {file_path} is missing columns: {missing_columns}"
        )

    print(f"Validated {file_path.name}: {len(data)} rows.")

    return True


# ============================================================
# 4. Multiple File Validation
# ============================================================

def validate_market_data_files(file_paths: list[Path]) -> bool:
    """
    Validate multiple market data CSV files.

    Args:
        file_paths (list[Path]): List of CSV file paths.

    Returns:
        bool: True if all files pass validation.

    Raises:
        RuntimeError: If one or more files fail validation.
    """
    print("Validating downloaded market data files...")

    failures = {}

    for file_path in file_paths:
        try:
            validate_market_data_file(file_path)
        except Exception as error:
            failures[file_path.name] = str(error)

    if failures:
        failure_messages = [
            f"{file_name}: {message}"
            for file_name, message in failures.items()
        ]

        raise RuntimeError(
            "Some data files failed validation:\n"
            + "\n".join(failure_messages)
        )

    print("All market data files passed validation.")

    return True