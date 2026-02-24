"""Interval detection and data validation module."""

import pandas as pd


def detect_interval_from_periods(periods: pd.Series) -> int:
    """
    Detect interval from time period codes.
    
    Logic:
    - If max period <= 48: 30-minute interval
    - If max period <= 288: 5-minute interval
    
    Args:
        periods: Series of integer time period codes
        
    Returns:
        Interval in minutes (5 or 30)
        
    Raises:
        ValueError: If period range doesn't match known intervals
    """
    max_period = periods.max()
    
    if max_period <= 48:
        return 30
    elif max_period <= 288:
        return 5
    else:
        raise ValueError(
            f"Period range doesn't match known intervals. "
            f"Max period: {max_period}. Expected <= 48 (30-min) or <= 288 (5-min)."
        )


def detect_interval_from_timestamps(timestamps: pd.Series) -> int:
    """
    Detect interval from timestamp deltas.
    
    Calculates mode of time differences between consecutive timestamps.
    
    Args:
        timestamps: Series of datetime values
        
    Returns:
        Interval in minutes (5 or 30)
    """
    # Calculate time differences between consecutive timestamps
    time_deltas = timestamps.diff()
    
    # Convert timedeltas to minutes
    delta_minutes = time_deltas.dt.total_seconds() / 60
    
    # Remove NaN values (first row will be NaN from diff())
    delta_minutes = delta_minutes.dropna()
    
    # Find the mode (most common value)
    mode_value = delta_minutes.mode()
    
    # If mode returns multiple values, take the first one
    if len(mode_value) > 0:
        interval = int(mode_value.iloc[0])
    else:
        raise ValueError("Unable to determine interval from timestamps")
    
    return interval


def validate_interval_consistency(
    timestamp_interval: int,
    period_interval: int
) -> bool:
    """
    Check if timestamp-derived and period-derived intervals match.
    
    Args:
        timestamp_interval: Interval detected from timestamps (in minutes)
        period_interval: Interval detected from time periods (in minutes)
    
    Returns:
        True if consistent, False if conflict detected
    """
    return timestamp_interval == period_interval


def check_missing_periods(
    df: pd.DataFrame,
    datetime_col: str,
    interval_minutes: int
) -> list[str]:
    """
    Identify missing time periods in sequence.
    
    Args:
        df: DataFrame sorted by datetime
        datetime_col: Name of datetime column
        interval_minutes: Expected interval (5 or 30)
        
    Returns:
        List of missing datetime strings
    """
    if len(df) == 0:
        return []
    
    # Ensure the dataframe is sorted by datetime
    df_sorted = df.sort_values(by=datetime_col).reset_index(drop=True)
    
    # Get the datetime series
    datetimes = df_sorted[datetime_col]
    
    # Create expected full range
    start_time = datetimes.iloc[0]
    end_time = datetimes.iloc[-1]
    
    # Generate expected datetime range
    expected_range = pd.date_range(
        start=start_time,
        end=end_time,
        freq=f'{interval_minutes}min'
    )
    
    # Find missing periods
    actual_set = set(datetimes)
    expected_set = set(expected_range)
    missing_periods = expected_set - actual_set
    
    # Convert to sorted list of strings
    missing_list = sorted([dt.strftime('%Y-%m-%d %H:%M:%S') for dt in missing_periods])
    
    return missing_list


def check_duplicate_periods(df: pd.DataFrame, datetime_col: str) -> int:
    """
    Count duplicate time periods (potential DST transitions).
    
    Args:
        df: DataFrame with datetime column
        datetime_col: Name of datetime column
    
    Returns:
        Number of duplicate periods found
    """
    # Count duplicates by checking if any datetime appears more than once
    duplicate_count = df[datetime_col].duplicated().sum()
    
    return int(duplicate_count)


def check_negative_consumption(df: pd.DataFrame, consumption_col: str) -> int:
    """
    Count negative consumption values.
    
    Args:
        df: DataFrame with consumption column
        consumption_col: Name of consumption column
    
    Returns:
        Number of negative values found
    """
    # Count values less than 0
    negative_count = (df[consumption_col] < 0).sum()
    
    return int(negative_count)
