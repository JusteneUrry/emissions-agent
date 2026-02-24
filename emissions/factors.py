"""
Emissions factors module for loading and managing emissions factor data.

This module provides functions to load interval-specific and annual emissions
factors from CSV files, and extract metadata from documentation.
"""

import os
from pathlib import Path
from typing import Optional

import pandas as pd


def load_interval_factors(
    state: str,
    interval_minutes: int,
    factors_dir: str = "data/emissions_factors"
) -> pd.DataFrame:
    """
    Load interval-specific emissions factors.
    
    Loads emissions factors from CSV file and filters by the specified
    NEM state and interval duration.
    
    Args:
        state: NEM state code (NSW, VIC, QLD, SA, TAS)
        interval_minutes: Data interval in minutes (5 or 30)
        factors_dir: Directory containing factor files
        
    Returns:
        DataFrame with columns:
        - state: NEM state code
        - interval_minutes: Interval duration in minutes
        - emissions_period_code: Combined date and period code (YYYYMMDDTTT)
        - factor_g_per_kwh: Emissions factor in grams CO2-e per kWh
        - source: Data source identifier
        - dataset_version: Version of the dataset
        
    Raises:
        FileNotFoundError: If the emissions factor file is missing
    """
    # Construct file path
    file_path = Path(factors_dir) / "interval_factors.csv"
    
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(
            f"Interval emissions factor file not found: {file_path}"
        )
    
    # Load CSV file
    df = pd.read_csv(file_path)
    
    # Filter by state and interval
    filtered_df = df[
        (df['state'] == state) & 
        (df['interval_minutes'] == interval_minutes)
    ]
    
    return filtered_df


def load_annual_factors(
    state: str,
    factors_dir: str = "data/emissions_factors"
) -> pd.DataFrame:
    """
    Load annual average emissions factors.
    
    Loads annual emissions factors from CSV file and filters by the
    specified NEM state.
    
    Args:
        state: NEM state code (NSW, VIC, QLD, SA, TAS)
        factors_dir: Directory containing factor files
        
    Returns:
        DataFrame with columns:
        - state: NEM state code
        - year: Calendar year
        - annual_factor_g_per_kwh: Annual average emissions factor in grams CO2-e per kWh
        - source: Data source identifier
        - dataset_version: Version of the dataset
        
    Raises:
        FileNotFoundError: If the emissions factor file is missing
    """
    # Construct file path
    file_path = Path(factors_dir) / "annual_factors.csv"
    
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(
            f"Annual emissions factor file not found: {file_path}"
        )
    
    # Load CSV file
    df = pd.read_csv(file_path)
    
    # Filter by state
    filtered_df = df[df['state'] == state]
    
    return filtered_df


def get_factor_metadata(
    factors_dir: str = "data/emissions_factors"
) -> dict:
    """
    Extract metadata from emissions factor README.
    
    Reads the README.md file in the emissions factors directory and
    extracts information about data sources, versions, and methodology.
    
    Args:
        factors_dir: Directory containing factor files and README
        
    Returns:
        Dictionary with metadata information:
        - source: Data source description
        - version: Dataset version information
        - methodology: Calculation methodology description
        - raw_content: Full README content
        
    Raises:
        FileNotFoundError: If the README.md file is missing
    """
    # Construct file path
    readme_path = Path(factors_dir) / "README.md"
    
    # Check if file exists
    if not readme_path.exists():
        raise FileNotFoundError(
            f"Emissions factor README not found: {readme_path}"
        )
    
    # Read README content
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Initialize metadata dictionary
    metadata = {
        'source': None,
        'version': None,
        'methodology': None,
        'raw_content': content
    }
    
    # Parse content for key information
    # Look for common section headers and extract information
    lines = content.split('\n')
    current_section = None
    
    for line in lines:
        line_lower = line.lower()
        
        # Detect section headers
        if 'source' in line_lower and line.startswith('#'):
            current_section = 'source'
        elif 'version' in line_lower and line.startswith('#'):
            current_section = 'version'
        elif 'methodology' in line_lower and line.startswith('#'):
            current_section = 'methodology'
        elif line.startswith('#'):
            current_section = None
        
        # Extract content from sections
        elif current_section and line.strip() and not line.startswith('#'):
            if metadata[current_section] is None:
                metadata[current_section] = line.strip()
            else:
                metadata[current_section] += ' ' + line.strip()
    
    return metadata
