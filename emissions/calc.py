"""
Emissions calculation module for the Emissions Dashboard.

This module performs emissions calculations using interval-specific and annual
emissions factors. It provides functions for calculating emissions, aggregating
results, and comparing different calculation methodologies.
"""

import logging
from typing import Tuple

import pandas as pd


# Set up logger for this module
logger = logging.getLogger('emissions.calc')


def calculate_interval_emissions(
    consumption_df: pd.DataFrame,
    interval_factors_df: pd.DataFrame,
    consumption_col: str,
    period_code_col: str
) -> Tuple[pd.DataFrame, float]:
    """
    Calculate emissions using interval-specific factors.
    
    This function joins consumption data with interval-specific emissions factors
    and calculates emissions for each time period. It handles unmatched records
    by logging warnings and excluding them from the total.
    
    Process:
    1. Join consumption with factors on emissions_period_code
    2. Calculate emissions_g = consumption_kwh × factor_g_per_kwh
    3. Calculate emissions_tonnes = emissions_g ÷ 1,000,000
    4. Sum total emissions
    5. Log warnings for unmatched records
    
    Args:
        consumption_df: Consumption data with emissions_period_code column
        interval_factors_df: Interval emissions factors with columns:
            - emissions_period_code: Period identifier (YYYYMMDDTTT)
            - factor_g_per_kwh: Emissions factor in grams per kWh
        consumption_col: Name of consumption column in consumption_df
        period_code_col: Name of emissions_period_code column in consumption_df
        
    Returns:
        Tuple of (detailed_results_df, total_emissions_tonnes)
        
        detailed_results_df includes:
        - All original columns from consumption_df
        - factor_g_per_kwh: Emissions factor used
        - emissions_g: Emissions in grams
        - emissions_tonnes: Emissions in tonnes
        
    Raises:
        ValueError: If required columns are missing from input DataFrames
    """
    logger.info("Starting interval-based emissions calculation")
    
    # Validate input DataFrames
    if consumption_df.empty:
        logger.warning("Empty consumption DataFrame provided")
        return pd.DataFrame(), 0.0
    
    if interval_factors_df.empty:
        logger.warning("Empty interval factors DataFrame provided")
        return pd.DataFrame(), 0.0
    
    # Validate required columns
    if consumption_col not in consumption_df.columns:
        raise ValueError(f"Consumption column '{consumption_col}' not found in consumption DataFrame")
    
    if period_code_col not in consumption_df.columns:
        raise ValueError(f"Period code column '{period_code_col}' not found in consumption DataFrame")
    
    if 'emissions_period_code' not in interval_factors_df.columns:
        raise ValueError("'emissions_period_code' column not found in interval factors DataFrame")
    
    if 'factor_g_per_kwh' not in interval_factors_df.columns:
        raise ValueError("'factor_g_per_kwh' column not found in interval factors DataFrame")
    
    # Log initial record counts
    total_records = len(consumption_df)
    logger.info(f"Processing {total_records} consumption records")
    logger.info(f"Available emissions factors: {len(interval_factors_df)} records")
    
    # Perform left join to match consumption with factors
    # Using left join to keep all consumption records and identify unmatched ones
    results_df = consumption_df.merge(
        interval_factors_df[['emissions_period_code', 'factor_g_per_kwh']],
        left_on=period_code_col,
        right_on='emissions_period_code',
        how='left'
    )
    
    # Identify matched and unmatched records
    matched_mask = results_df['factor_g_per_kwh'].notna()
    matched_count = matched_mask.sum()
    unmatched_count = (~matched_mask).sum()
    
    logger.info(f"Matched records: {matched_count} ({matched_count/total_records*100:.1f}%)")
    
    if unmatched_count > 0:
        logger.warning(
            f"Unmatched records: {unmatched_count} ({unmatched_count/total_records*100:.1f}%). "
            f"These records will be excluded from total emissions calculation."
        )
        
        # Log sample of unmatched period codes for debugging
        unmatched_codes = results_df.loc[~matched_mask, period_code_col].unique()
        sample_size = min(5, len(unmatched_codes))
        logger.warning(f"Sample unmatched period codes: {unmatched_codes[:sample_size].tolist()}")
    
    # Calculate emissions for matched records
    # emissions_g = consumption_kwh × factor_g_per_kwh
    results_df['emissions_g'] = results_df[consumption_col] * results_df['factor_g_per_kwh']
    
    # Calculate emissions in tonnes
    # emissions_tonnes = emissions_g ÷ 1,000,000
    results_df['emissions_tonnes'] = results_df['emissions_g'] / 1_000_000
    
    # Calculate total emissions (only for matched records)
    total_emissions_tonnes = results_df.loc[matched_mask, 'emissions_tonnes'].sum()
    
    logger.info(f"Total emissions calculated: {total_emissions_tonnes:.6f} tonnes CO2-e")
    logger.info(f"Total consumption: {consumption_df[consumption_col].sum():.2f} kWh")
    
    return results_df, total_emissions_tonnes



def calculate_annual_emissions(
    consumption_df: pd.DataFrame,
    annual_factors_df: pd.DataFrame,
    consumption_col: str,
    datetime_col: str
) -> Tuple[pd.DataFrame, float]:
    """
    Calculate emissions using annual average factors.
    
    This function extracts the financial year from each consumption record and applies
    year-specific annual emissions factors. It handles multi-year data by
    matching each record to its corresponding financial year's factor.
    
    Process:
    1. Extract financial year from datetime column
    2. Join consumption with annual factors on financial year
    3. Calculate annual_emissions_g = consumption_kwh × annual_factor_g_per_kwh
    4. Calculate annual_emissions_tonnes = annual_emissions_g ÷ 1,000,000
    5. Sum total emissions
    6. Log warnings for unmatched records
    
    Args:
        consumption_df: Consumption data with datetime column
        annual_factors_df: Annual emissions factors with columns:
            - year: Financial year (starting year of FY period)
            - annual_factor_g_per_kwh: Annual average emissions factor in grams per kWh
        consumption_col: Name of consumption column in consumption_df
        datetime_col: Name of datetime column in consumption_df
        
    Returns:
        Tuple of (detailed_results_df, total_annual_emissions_tonnes)
        
        detailed_results_df includes:
        - All original columns from consumption_df
        - financial_year: Extracted financial year
        - annual_factor_g_per_kwh: Annual emissions factor used
        - annual_emissions_g: Emissions in grams
        - annual_emissions_tonnes: Emissions in tonnes
        
    Raises:
        ValueError: If required columns are missing from input DataFrames
    """
    logger.info("Starting annual comparison emissions calculation")
    
    # Validate input DataFrames
    if consumption_df.empty:
        logger.warning("Empty consumption DataFrame provided")
        return pd.DataFrame(), 0.0
    
    if annual_factors_df.empty:
        logger.warning("Empty annual factors DataFrame provided")
        return pd.DataFrame(), 0.0
    
    # Validate required columns
    if consumption_col not in consumption_df.columns:
        raise ValueError(f"Consumption column '{consumption_col}' not found in consumption DataFrame")
    
    if datetime_col not in consumption_df.columns:
        raise ValueError(f"Datetime column '{datetime_col}' not found in consumption DataFrame")
    
    if 'year' not in annual_factors_df.columns:
        raise ValueError("'year' column not found in annual factors DataFrame")
    
    if 'annual_factor_g_per_kwh' not in annual_factors_df.columns:
        raise ValueError("'annual_factor_g_per_kwh' column not found in annual factors DataFrame")
    
    # Log initial record counts
    total_records = len(consumption_df)
    logger.info(f"Processing {total_records} consumption records")
    logger.info(f"Available annual factors: {len(annual_factors_df)} years")
    
    # Create a copy of consumption DataFrame to avoid modifying original
    results_df = consumption_df.copy()
    
    # Extract financial year from datetime column
    # Australian financial year runs July 1 - June 30
    # The year label corresponds to the starting year of the FY
    # E.g., FY2022-23 (July 2022 - June 2023) is labeled as 2022
    # E.g., FY2023-24 (July 2023 - June 2024) is labeled as 2023
    if pd.api.types.is_datetime64_any_dtype(results_df[datetime_col]):
        dt_series = results_df[datetime_col]
    else:
        # Convert to datetime first if it's not already
        dt_series = pd.to_datetime(results_df[datetime_col])
    
    # Map to financial year: if month >= 7 (July onwards), use current year
    # if month < 7 (Jan-June), use previous year
    results_df['financial_year'] = dt_series.apply(
        lambda dt: dt.year if dt.month >= 7 else dt.year - 1
    )
    
    # Log financial year range in consumption data
    year_min = results_df['financial_year'].min()
    year_max = results_df['financial_year'].max()
    logger.info(f"Consumption data spans financial years: {year_min} to {year_max}")
    
    # Perform left join to match consumption with annual factors on financial year
    # Using left join to keep all consumption records and identify unmatched ones
    results_df = results_df.merge(
        annual_factors_df[['year', 'annual_factor_g_per_kwh']],
        left_on='financial_year',
        right_on='year',
        how='left'
    )
    
    # Identify matched and unmatched records
    matched_mask = results_df['annual_factor_g_per_kwh'].notna()
    matched_count = matched_mask.sum()
    unmatched_count = (~matched_mask).sum()
    
    logger.info(f"Matched records: {matched_count} ({matched_count/total_records*100:.1f}%)")
    
    if unmatched_count > 0:
        logger.warning(
            f"Unmatched records: {unmatched_count} ({unmatched_count/total_records*100:.1f}%). "
            f"These records will be excluded from total emissions calculation."
        )
        
        # Log sample of unmatched financial years for debugging
        unmatched_years = results_df.loc[~matched_mask, 'financial_year'].unique()
        logger.warning(f"Unmatched financial years: {sorted(unmatched_years.tolist())}")
    
    # Calculate emissions for matched records
    # annual_emissions_g = consumption_kwh × annual_factor_g_per_kwh
    results_df['annual_emissions_g'] = results_df[consumption_col] * results_df['annual_factor_g_per_kwh']
    
    # Calculate emissions in tonnes
    # annual_emissions_tonnes = annual_emissions_g ÷ 1,000,000
    results_df['annual_emissions_tonnes'] = results_df['annual_emissions_g'] / 1_000_000
    
    # Calculate total emissions (only for matched records)
    total_annual_emissions_tonnes = results_df.loc[matched_mask, 'annual_emissions_tonnes'].sum()
    
    logger.info(f"Total annual emissions calculated: {total_annual_emissions_tonnes:.6f} tonnes CO2-e")
    logger.info(f"Total consumption: {consumption_df[consumption_col].sum():.2f} kWh")
    
    return results_df, total_annual_emissions_tonnes


def calculate_percentage_difference(interval_total: float, annual_total: float) -> float:
    """
    Calculate the percentage difference between interval and annual emissions totals.
    
    This function computes the percentage difference using the formula:
    ((interval_total - annual_total) / annual_total) × 100
    
    A positive value indicates that interval-based emissions are higher than annual
    average emissions, while a negative value indicates they are lower.
    
    Args:
        interval_total: Total emissions calculated using interval-specific factors (tonnes)
        annual_total: Total emissions calculated using annual average factors (tonnes)
        
    Returns:
        Percentage difference as a float. Positive values mean interval > annual,
        negative values mean interval < annual.
        
    Raises:
        ValueError: If annual_total is zero (division by zero)
        
    Examples:
        >>> calculate_percentage_difference(105.0, 100.0)
        5.0
        >>> calculate_percentage_difference(95.0, 100.0)
        -5.0
    """
    if annual_total == 0:
        raise ValueError("Annual total cannot be zero for percentage difference calculation")
    
    percentage_diff = ((interval_total - annual_total) / annual_total) * 100
    
    logger.info(
        f"Percentage difference calculated: {percentage_diff:.2f}% "
        f"(interval: {interval_total:.6f} tonnes, annual: {annual_total:.6f} tonnes)"
    )
    
    return percentage_diff


def aggregate_daily_emissions(
    interval_results_df: pd.DataFrame,
    datetime_col: str
) -> pd.DataFrame:
    """
    Aggregate interval emissions by day.
    
    This function takes interval-level emissions results and aggregates them
    to daily totals. It groups by date and sums both consumption and emissions
    values to provide a daily summary suitable for visualization and reporting.
    
    Process:
    1. Extract date from datetime column
    2. Group by date
    3. Sum consumption_kwh to get total_consumption_kwh
    4. Sum emissions_tonnes to get total_emissions_tonnes
    5. Return DataFrame with date, total_consumption_kwh, total_emissions_tonnes
    
    Args:
        interval_results_df: DataFrame from calculate_interval_emissions() containing:
            - datetime column (name specified by datetime_col parameter)
            - consumption_kwh: Consumption values in kWh
            - emissions_tonnes: Emissions values in tonnes
        datetime_col: Name of the datetime column in interval_results_df
        
    Returns:
        DataFrame with columns:
        - date: Date values (datetime.date objects)
        - total_consumption_kwh: Sum of consumption for each day
        - total_emissions_tonnes: Sum of emissions for each day
        
    Raises:
        ValueError: If required columns are missing from input DataFrame
        
    Examples:
        >>> interval_results = pd.DataFrame({
        ...     'timestamp': pd.to_datetime(['2023-01-01 00:00', '2023-01-01 00:05', '2023-01-02 00:00']),
        ...     'consumption_kwh': [10.0, 15.0, 20.0],
        ...     'emissions_tonnes': [0.0075, 0.0112, 0.0150]
        ... })
        >>> daily = aggregate_daily_emissions(interval_results, 'timestamp')
        >>> daily.shape[0]
        2
        >>> daily.columns.tolist()
        ['date', 'total_consumption_kwh', 'total_emissions_tonnes']
    """
    logger.info("Starting daily emissions aggregation")
    
    # Validate input DataFrame
    if interval_results_df.empty:
        logger.warning("Empty interval results DataFrame provided")
        return pd.DataFrame(columns=['date', 'total_consumption_kwh', 'total_emissions_tonnes'])
    
    # Validate required columns
    if datetime_col not in interval_results_df.columns:
        raise ValueError(f"Datetime column '{datetime_col}' not found in interval results DataFrame")
    
    if 'consumption_kwh' not in interval_results_df.columns:
        raise ValueError("'consumption_kwh' column not found in interval results DataFrame")
    
    if 'emissions_tonnes' not in interval_results_df.columns:
        raise ValueError("'emissions_tonnes' column not found in interval results DataFrame")
    
    # Log initial record count
    total_records = len(interval_results_df)
    logger.info(f"Aggregating {total_records} interval records to daily totals")
    
    # Create a copy to avoid modifying original DataFrame
    df = interval_results_df.copy()
    
    # Extract date from datetime column
    # Handle both datetime objects and string representations
    if pd.api.types.is_datetime64_any_dtype(df[datetime_col]):
        df['date'] = df[datetime_col].dt.date
    else:
        # Convert to datetime first if it's not already
        dt_series = pd.to_datetime(df[datetime_col])
        df['date'] = dt_series.dt.date
    
    # Group by date and aggregate
    daily_df = df.groupby('date', as_index=False).agg({
        'consumption_kwh': 'sum',
        'emissions_tonnes': 'sum'
    })
    
    # Rename columns to match output specification
    daily_df = daily_df.rename(columns={
        'consumption_kwh': 'total_consumption_kwh',
        'emissions_tonnes': 'total_emissions_tonnes'
    })
    
    # Log aggregation results
    num_days = len(daily_df)
    total_consumption = daily_df['total_consumption_kwh'].sum()
    total_emissions = daily_df['total_emissions_tonnes'].sum()
    
    logger.info(f"Aggregated to {num_days} days")
    logger.info(f"Total daily consumption: {total_consumption:.2f} kWh")
    logger.info(f"Total daily emissions: {total_emissions:.6f} tonnes CO2-e")
    
    # Log date range
    if num_days > 0:
        date_min = daily_df['date'].min()
        date_max = daily_df['date'].max()
        logger.info(f"Date range: {date_min} to {date_max}")
    
    return daily_df
