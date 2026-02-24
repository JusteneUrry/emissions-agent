"""
File I/O module for the Emissions Dashboard.

This module handles file upload, parsing, and column recognition for consumption data.
Supports CSV and Excel file formats with flexible column naming patterns.
"""

import re
from typing import Optional
import pandas as pd
from streamlit.runtime.uploaded_file_manager import UploadedFile


class UnsupportedFileFormatError(ValueError):
    """Raised when uploaded file format is not CSV or Excel."""
    pass


class ColumnNotFoundError(ValueError):
    """Raised when required column cannot be identified."""
    pass


def load_consumption_file(uploaded_file: UploadedFile) -> pd.DataFrame:
    """
    Load consumption data from CSV or Excel file.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        DataFrame with raw consumption data
        
    Raises:
        UnsupportedFileFormatError: If file format is unsupported
    """
    file_name = uploaded_file.name.lower()
    
    if file_name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    elif file_name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file, engine='openpyxl')
    else:
        raise UnsupportedFileFormatError(
            f"Unsupported file format. Please upload a CSV (.csv) or Excel (.xlsx) file."
        )
    
    return df


def identify_consumption_column(df: pd.DataFrame) -> str:
    """
    Identify consumption column using pattern matching.
    
    Searches for columns matching: consumption, kwh, usage, energy (case-insensitive)
    
    Args:
        df: DataFrame with consumption data
        
    Returns:
        Name of identified consumption column
        
    Raises:
        ColumnNotFoundError: If no consumption column found
    """
    pattern = re.compile(r'(consumption|kwh|usage|energy)', re.IGNORECASE)
    
    for col in df.columns:
        if pattern.search(str(col)):
            return col
    
    raise ColumnNotFoundError(
        "No consumption column found. Expected column names containing: "
        "'consumption', 'kwh', 'usage', or 'energy' (case-insensitive)."
    )


def identify_time_columns(df: pd.DataFrame) -> dict[str, Optional[str]]:
    """
    Identify timestamp and time period columns.
    
    Returns:
        Dictionary with keys: 'timestamp', 'time_period', 'date'
        Values are column names or None if not found
    """
    result = {
        'timestamp': None,
        'time_period': None,
        'date': None
    }
    
    # Pattern for time period columns (period, time_period, interval, tp)
    # Check this FIRST to avoid matching "time_period" as "timestamp"
    period_pattern = re.compile(r'(period|time_period|interval|tp)', re.IGNORECASE)
    
    # Pattern for timestamp columns (timestamp, datetime, date_time, time)
    timestamp_pattern = re.compile(r'(timestamp|datetime|date_time|time)', re.IGNORECASE)
    
    # Pattern for date columns (date, day) - excluding datetime
    date_pattern = re.compile(r'^(date|day)$', re.IGNORECASE)
    
    for col in df.columns:
        col_str = str(col)
        
        # Check for time period column FIRST (to avoid "time_period" matching "time")
        if result['time_period'] is None and period_pattern.search(col_str):
            result['time_period'] = col
            continue  # Skip to next column
        
        # Check for date column
        if result['date'] is None and date_pattern.match(col_str):
            result['date'] = col
            continue  # Skip to next column
        
        # Check for timestamp column (but not if it's already identified as date or period)
        if result['timestamp'] is None and timestamp_pattern.search(col_str):
            result['timestamp'] = col
    
    return result


def parse_emissions_period_code(code: str) -> tuple[str, int]:
    """
    Parse combined YYYYMMDDTTT code into date and period.
    
    Args:
        code: String in format YYYYMMDDTTT (e.g., "20230101001")
        
    Returns:
        Tuple of (date_string YYYYMMDD, period_int TTT)
        
    Raises:
        ValueError: If code format is invalid
    """
    code_str = str(code).strip()
    
    # Expected format: YYYYMMDDTTT (11 characters)
    if len(code_str) != 11:
        raise ValueError(
            f"Invalid emissions period code format: '{code_str}'. "
            f"Expected format: YYYYMMDDTTT (11 characters)"
        )
    
    # Extract date (first 8 characters) and period (last 3 characters)
    date_str = code_str[:8]
    period_str = code_str[8:]
    
    # Validate date portion is numeric
    if not date_str.isdigit():
        raise ValueError(
            f"Invalid date portion in code: '{date_str}'. Must be numeric YYYYMMDD."
        )
    
    # Validate period portion is numeric
    if not period_str.isdigit():
        raise ValueError(
            f"Invalid period portion in code: '{period_str}'. Must be numeric TTT."
        )
    
    # Convert period to integer (preserves leading zeros in original string)
    period_int = int(period_str)
    
    return date_str, period_int
