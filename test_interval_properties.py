"""
Property-based tests for interval detection module.

Tests interval detection logic using Hypothesis to validate that the system
correctly infers 5-minute and 30-minute intervals from time period codes.
"""

import pytest
import pandas as pd
from hypothesis import given, settings, strategies as st

from emissions.interval import (
    detect_interval_from_periods,
    detect_interval_from_timestamps,
    validate_interval_consistency,
    check_missing_periods,
    check_duplicate_periods,
    check_negative_consumption
)


# ============================================================================
# Property Tests for Period-Based Interval Detection
# ============================================================================


@st.composite
def five_minute_periods(draw):
    """
    Generate time period series for 5-minute intervals.
    
    5-minute intervals have periods ranging from 001 to 288 (288 * 5 = 1440 minutes = 24 hours).
    """
    # Generate the max period first (must be > 48 for 5-minute detection)
    max_period = draw(st.integers(min_value=49, max_value=288))
    
    # Generate a subset of periods from 1 to max_period
    num_periods = draw(st.integers(min_value=1, max_value=min(100, max_period)))
    
    # Generate random periods between 1 and max_period
    periods_list = draw(st.lists(
        st.integers(min_value=1, max_value=max_period),
        min_size=1,
        max_size=num_periods
    ))
    
    # Ensure the max_period is actually in the list
    if max_period not in periods_list:
        periods_list.append(max_period)
    
    return pd.Series(periods_list), max_period


@st.composite
def thirty_minute_periods(draw):
    """
    Generate time period series for 30-minute intervals.
    
    30-minute intervals have periods ranging from 001 to 048 (48 * 30 = 1440 minutes = 24 hours).
    """
    # Generate the max period first (must be <= 48 for 30-minute detection)
    max_period = draw(st.integers(min_value=1, max_value=48))
    
    # Generate a subset of periods from 1 to max_period
    num_periods = draw(st.integers(min_value=1, max_value=min(48, max_period)))
    
    # Generate random periods between 1 and max_period
    periods_list = draw(st.lists(
        st.integers(min_value=1, max_value=max_period),
        min_size=1,
        max_size=num_periods
    ))
    
    # Ensure the max_period is actually in the list
    if max_period not in periods_list:
        periods_list.append(max_period)
    
    return pd.Series(periods_list), max_period


@settings(max_examples=100, deadline=None)
@given(data=five_minute_periods())
def test_property_5min_interval_detection_from_periods(data):
    """
    Property 8: 5-Minute Interval Detection from Periods
    
    **Validates: Requirements 4.2**
    
    For any time period series where the maximum period value is greater than 48
    and less than or equal to 288, the detect_interval_from_periods function
    should infer a 5-minute interval.
    
    Requirement 4.2: "WHEN time_period values range from 001 to 288, 
    THE Interval_Detector SHALL infer a 5-minute interval"
    """
    periods, max_period = data
    
    # Verify our test data is in the correct range
    assert max_period > 48, f"Test data error: max_period {max_period} should be > 48 for 5-minute test"
    assert max_period <= 288, f"Test data error: max_period {max_period} should be <= 288"
    
    # Detect interval
    result = detect_interval_from_periods(periods)
    
    # Property: Should detect 5-minute interval
    assert result == 5, \
        f"Expected 5-minute interval for max_period={max_period}, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(data=thirty_minute_periods())
def test_property_30min_interval_detection_from_periods(data):
    """
    Property 9: 30-Minute Interval Detection from Periods
    
    **Validates: Requirements 4.3**
    
    For any time period series where the maximum period value is less than or
    equal to 48, the detect_interval_from_periods function should infer a
    30-minute interval.
    
    Requirement 4.3: "WHEN time_period values range from 001 to 048, 
    THE Interval_Detector SHALL infer a 30-minute interval"
    """
    periods, max_period = data
    
    # Verify our test data is in the correct range
    assert max_period <= 48, f"Test data error: max_period {max_period} should be <= 48 for 30-minute test"
    assert max_period >= 1, f"Test data error: max_period {max_period} should be >= 1"
    
    # Detect interval
    result = detect_interval_from_periods(periods)
    
    # Property: Should detect 30-minute interval
    assert result == 30, \
        f"Expected 30-minute interval for max_period={max_period}, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(
    max_period=st.integers(min_value=49, max_value=288)
)
def test_property_5min_boundary_detection(max_period):
    """
    Property 8: 5-Minute Interval Detection (Boundary Test)
    
    **Validates: Requirements 4.2**
    
    For any period series with max_period in range [49, 288], the function
    should consistently detect a 5-minute interval. This tests the boundary
    condition where max_period > 48.
    """
    # Create a simple series with just the max period
    periods = pd.Series([1, max_period])
    
    # Detect interval
    result = detect_interval_from_periods(periods)
    
    # Property: Should detect 5-minute interval
    assert result == 5, \
        f"Expected 5-minute interval for max_period={max_period}, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(
    max_period=st.integers(min_value=1, max_value=48)
)
def test_property_30min_boundary_detection(max_period):
    """
    Property 9: 30-Minute Interval Detection (Boundary Test)
    
    **Validates: Requirements 4.3**
    
    For any period series with max_period in range [1, 48], the function
    should consistently detect a 30-minute interval. This tests the boundary
    condition where max_period <= 48.
    """
    # Create a simple series with just the max period
    periods = pd.Series([1, max_period])
    
    # Detect interval
    result = detect_interval_from_periods(periods)
    
    # Property: Should detect 30-minute interval
    assert result == 30, \
        f"Expected 30-minute interval for max_period={max_period}, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(
    num_periods=st.integers(min_value=1, max_value=288),
    max_period=st.integers(min_value=49, max_value=288)
)
def test_property_5min_detection_with_varying_sizes(num_periods, max_period):
    """
    Property 8: 5-Minute Interval Detection (Varying Series Sizes)
    
    **Validates: Requirements 4.2**
    
    For any series size and any max_period > 48, the function should detect
    a 5-minute interval. This tests that detection works regardless of how
    many periods are in the series.
    """
    # Generate periods up to max_period
    periods = pd.Series(range(1, min(num_periods + 1, max_period + 1)))
    
    # Ensure max is in the 5-minute range
    if periods.max() < max_period:
        periods = pd.concat([periods, pd.Series([max_period])], ignore_index=True)
    
    # Detect interval
    result = detect_interval_from_periods(periods)
    
    # Property: Should detect 5-minute interval
    assert result == 5, \
        f"Expected 5-minute interval for series with {len(periods)} periods and max={periods.max()}, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(
    num_periods=st.integers(min_value=1, max_value=48),
    max_period=st.integers(min_value=1, max_value=48)
)
def test_property_30min_detection_with_varying_sizes(num_periods, max_period):
    """
    Property 9: 30-Minute Interval Detection (Varying Series Sizes)
    
    **Validates: Requirements 4.3**
    
    For any series size and any max_period <= 48, the function should detect
    a 30-minute interval. This tests that detection works regardless of how
    many periods are in the series.
    """
    # Generate periods up to max_period
    periods = pd.Series(range(1, min(num_periods + 1, max_period + 1)))
    
    # Ensure max is in the 30-minute range
    if periods.max() < max_period:
        periods = pd.concat([periods, pd.Series([max_period])], ignore_index=True)
    
    # Detect interval
    result = detect_interval_from_periods(periods)
    
    # Property: Should detect 30-minute interval
    assert result == 30, \
        f"Expected 30-minute interval for series with {len(periods)} periods and max={periods.max()}, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(
    periods_list=st.lists(
        st.integers(min_value=49, max_value=288),
        min_size=1,
        max_size=100
    )
)
def test_property_5min_detection_with_random_periods(periods_list):
    """
    Property 8: 5-Minute Interval Detection (Random Period Values)
    
    **Validates: Requirements 4.2**
    
    For any random collection of period values where all are in the range [49, 288],
    the function should detect a 5-minute interval. This tests that the function
    correctly handles non-sequential periods.
    """
    periods = pd.Series(periods_list)
    
    # Verify test data
    assert periods.max() > 48, "Test data should have max > 48"
    
    # Detect interval
    result = detect_interval_from_periods(periods)
    
    # Property: Should detect 5-minute interval
    assert result == 5, \
        f"Expected 5-minute interval for random periods with max={periods.max()}, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(
    periods_list=st.lists(
        st.integers(min_value=1, max_value=48),
        min_size=1,
        max_size=48
    )
)
def test_property_30min_detection_with_random_periods(periods_list):
    """
    Property 9: 30-Minute Interval Detection (Random Period Values)
    
    **Validates: Requirements 4.3**
    
    For any random collection of period values where all are in the range [1, 48],
    the function should detect a 30-minute interval. This tests that the function
    correctly handles non-sequential periods.
    """
    periods = pd.Series(periods_list)
    
    # Verify test data
    assert periods.max() <= 48, "Test data should have max <= 48"
    
    # Detect interval
    result = detect_interval_from_periods(periods)
    
    # Property: Should detect 30-minute interval
    assert result == 30, \
        f"Expected 30-minute interval for random periods with max={periods.max()}, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(
    invalid_max=st.integers(min_value=289, max_value=1000)
)
def test_property_invalid_period_range_error(invalid_max):
    """
    Property: Invalid Period Range Error
    
    **Validates: Requirements 4.2, 4.3**
    
    For any period series with max_period > 288, the function should raise
    a ValueError indicating the period range doesn't match known intervals.
    """
    periods = pd.Series([1, invalid_max])
    
    # Property: Should raise ValueError for invalid range
    with pytest.raises(ValueError) as exc_info:
        detect_interval_from_periods(periods)
    
    # Verify error message mentions the issue
    error_msg = str(exc_info.value).lower()
    assert 'period' in error_msg or 'interval' in error_msg, \
        f"Error message should mention period or interval: {exc_info.value}"


# ============================================================================
# Property Tests for Timestamp-Based Interval Detection
# ============================================================================


@st.composite
def timestamp_series_with_interval(draw):
    """
    Generate a series of evenly-spaced timestamps with a known interval.

    Returns tuple of (timestamps_series, expected_interval_minutes)
    """
    # Choose interval: 5 or 30 minutes
    interval_minutes = draw(st.sampled_from([5, 30]))

    # Generate number of timestamps (at least 2 for delta calculation)
    num_timestamps = draw(st.integers(min_value=2, max_value=100))

    # Generate a random start datetime
    start_year = draw(st.integers(min_value=2020, max_value=2024))
    start_month = draw(st.integers(min_value=1, max_value=12))
    start_day = draw(st.integers(min_value=1, max_value=28))  # Safe for all months
    start_hour = draw(st.integers(min_value=0, max_value=23))
    start_minute = draw(st.integers(min_value=0, max_value=59))

    start_datetime = pd.Timestamp(
        year=start_year,
        month=start_month,
        day=start_day,
        hour=start_hour,
        minute=start_minute
    )

    # Generate evenly-spaced timestamps
    timestamps = pd.date_range(
        start=start_datetime,
        periods=num_timestamps,
        freq=f'{interval_minutes}min'
    )

    return pd.Series(timestamps), interval_minutes


@settings(max_examples=100, deadline=None)
@given(data=timestamp_series_with_interval())
def test_property_interval_detection_from_timestamps(data):
    """
    Property 10: Interval Detection from Timestamps

    **Validates: Requirements 4.4**

    For any series of evenly-spaced datetime values, the interval detector
    should calculate the mode of time deltas and return the correct interval
    in minutes.

    Requirement 4.4: "WHEN timestamp data is provided without time periods,
    THE Interval_Detector SHALL calculate time deltas between consecutive
    timestamps to infer the interval"
    """
    timestamps, expected_interval = data

    # Verify test data has at least 2 timestamps
    assert len(timestamps) >= 2, "Test data should have at least 2 timestamps"

    # Detect interval from timestamps
    result = detect_interval_from_timestamps(timestamps)

    # Property: Should detect the correct interval
    assert result == expected_interval, \
        f"Expected {expected_interval}-minute interval, but got {result} minutes for {len(timestamps)} timestamps"


@settings(max_examples=100, deadline=None)
@given(
    interval_minutes=st.sampled_from([5, 30]),
    num_timestamps=st.integers(min_value=2, max_value=288)
)
def test_property_5min_and_30min_timestamp_detection(interval_minutes, num_timestamps):
    """
    Property 10: Interval Detection from Timestamps (Boundary Test)

    **Validates: Requirements 4.4**

    For any number of evenly-spaced timestamps with either 5-minute or
    30-minute intervals, the function should correctly detect the interval.
    This tests both common interval values across varying series sizes.
    """
    # Create evenly-spaced timestamps starting from a fixed date
    start_datetime = pd.Timestamp('2023-01-01 00:00:00')
    timestamps = pd.date_range(
        start=start_datetime,
        periods=num_timestamps,
        freq=f'{interval_minutes}min'
    )
    timestamps_series = pd.Series(timestamps)

    # Detect interval
    result = detect_interval_from_timestamps(timestamps_series)

    # Property: Should detect the correct interval
    assert result == interval_minutes, \
        f"Expected {interval_minutes}-minute interval for {num_timestamps} timestamps, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(
    start_year=st.integers(min_value=2020, max_value=2024),
    start_month=st.integers(min_value=1, max_value=12),
    interval_minutes=st.sampled_from([5, 30])
)
def test_property_timestamp_detection_across_dates(start_year, start_month, interval_minutes):
    """
    Property 10: Interval Detection from Timestamps (Date Variation)

    **Validates: Requirements 4.4**

    For any starting date and interval, the function should correctly detect
    the interval regardless of the calendar date. This tests that detection
    works across different months and years.
    """
    # Create timestamps starting from the generated date
    start_datetime = pd.Timestamp(year=start_year, month=start_month, day=1, hour=0, minute=0)

    # Generate a full day of data
    num_periods = 288 if interval_minutes == 5 else 48
    timestamps = pd.date_range(
        start=start_datetime,
        periods=num_periods,
        freq=f'{interval_minutes}min'
    )
    timestamps_series = pd.Series(timestamps)

    # Detect interval
    result = detect_interval_from_timestamps(timestamps_series)

    # Property: Should detect the correct interval
    assert result == interval_minutes, \
        f"Expected {interval_minutes}-minute interval for date {start_datetime.date()}, but got {result} minutes"



# ============================================================================
# Property Tests for Timestamp-Based Interval Detection
# ============================================================================


@st.composite
def timestamp_series_with_interval(draw):
    """
    Generate a series of evenly-spaced timestamps with a known interval.
    
    Returns tuple of (timestamps_series, expected_interval_minutes)
    """
    # Choose interval: 5 or 30 minutes
    interval_minutes = draw(st.sampled_from([5, 30]))
    
    # Generate number of timestamps (at least 2 for delta calculation)
    num_timestamps = draw(st.integers(min_value=2, max_value=100))
    
    # Generate a random start datetime
    start_year = draw(st.integers(min_value=2020, max_value=2024))
    start_month = draw(st.integers(min_value=1, max_value=12))
    start_day = draw(st.integers(min_value=1, max_value=28))  # Safe for all months
    start_hour = draw(st.integers(min_value=0, max_value=23))
    start_minute = draw(st.integers(min_value=0, max_value=59))
    
    start_datetime = pd.Timestamp(
        year=start_year,
        month=start_month,
        day=start_day,
        hour=start_hour,
        minute=start_minute
    )
    
    # Generate evenly-spaced timestamps
    timestamps = pd.date_range(
        start=start_datetime,
        periods=num_timestamps,
        freq=f'{interval_minutes}min'
    )
    
    return pd.Series(timestamps), interval_minutes


@settings(max_examples=100, deadline=None)
@given(data=timestamp_series_with_interval())
def test_property_interval_detection_from_timestamps(data):
    """
    Property 10: Interval Detection from Timestamps
    
    **Validates: Requirements 4.4**
    
    For any series of evenly-spaced datetime values, the interval detector
    should calculate the mode of time deltas and return the correct interval
    in minutes.
    
    Requirement 4.4: "WHEN timestamp data is provided without time periods,
    THE Interval_Detector SHALL calculate time deltas between consecutive
    timestamps to infer the interval"
    """
    timestamps, expected_interval = data
    
    # Verify test data has at least 2 timestamps
    assert len(timestamps) >= 2, "Test data should have at least 2 timestamps"
    
    # Detect interval from timestamps
    result = detect_interval_from_timestamps(timestamps)
    
    # Property: Should detect the correct interval
    assert result == expected_interval, \
        f"Expected {expected_interval}-minute interval, but got {result} minutes for {len(timestamps)} timestamps"


@settings(max_examples=100, deadline=None)
@given(
    interval_minutes=st.sampled_from([5, 30]),
    num_timestamps=st.integers(min_value=2, max_value=288)
)
def test_property_5min_and_30min_timestamp_detection(interval_minutes, num_timestamps):
    """
    Property 10: Interval Detection from Timestamps (Boundary Test)
    
    **Validates: Requirements 4.4**
    
    For any number of evenly-spaced timestamps with either 5-minute or
    30-minute intervals, the function should correctly detect the interval.
    This tests both common interval values across varying series sizes.
    """
    # Create evenly-spaced timestamps starting from a fixed date
    start_datetime = pd.Timestamp('2023-01-01 00:00:00')
    timestamps = pd.date_range(
        start=start_datetime,
        periods=num_timestamps,
        freq=f'{interval_minutes}min'
    )
    timestamps_series = pd.Series(timestamps)
    
    # Detect interval
    result = detect_interval_from_timestamps(timestamps_series)
    
    # Property: Should detect the correct interval
    assert result == interval_minutes, \
        f"Expected {interval_minutes}-minute interval for {num_timestamps} timestamps, but got {result} minutes"


@settings(max_examples=100, deadline=None)
@given(
    start_year=st.integers(min_value=2020, max_value=2024),
    start_month=st.integers(min_value=1, max_value=12),
    interval_minutes=st.sampled_from([5, 30])
)
def test_property_timestamp_detection_across_dates(start_year, start_month, interval_minutes):
    """
    Property 10: Interval Detection from Timestamps (Date Variation)
    
    **Validates: Requirements 4.4**
    
    For any starting date and interval, the function should correctly detect
    the interval regardless of the calendar date. This tests that detection
    works across different months and years.
    """
    # Create timestamps starting from the generated date
    start_datetime = pd.Timestamp(year=start_year, month=start_month, day=1, hour=0, minute=0)
    
    # Generate a full day of data
    num_periods = 288 if interval_minutes == 5 else 48
    timestamps = pd.date_range(
        start=start_datetime,
        periods=num_periods,
        freq=f'{interval_minutes}min'
    )
    timestamps_series = pd.Series(timestamps)
    
    # Detect interval
    result = detect_interval_from_timestamps(timestamps_series)
    
    # Property: Should detect the correct interval
    assert result == interval_minutes, \
        f"Expected {interval_minutes}-minute interval for date {start_datetime.date()}, but got {result} minutes"


# ============================================================================
# Property Tests for Interval Consistency Validation
# ============================================================================


@settings(max_examples=100, deadline=None)
@given(
    interval=st.sampled_from([5, 30])
)
def test_property_interval_consistency_when_matching(interval):
    """
    Property 11: Interval Consistency Validation (Matching Intervals)
    
    **Validates: Requirements 4.5, 4.6**
    
    When timestamp_interval equals period_interval, the function should
    return True indicating consistency.
    
    Requirement 4.5: "WHERE both timestamp and time_period data exist,
    THE Interval_Detector SHALL validate consistency between them"
    
    Requirement 4.6: "IF timestamp-derived interval conflicts with
    time_period-derived interval, THEN THE Interval_Detector SHALL
    display a warning message"
    """
    # Both intervals are the same
    result = validate_interval_consistency(interval, interval)
    
    # Property: Should return True when intervals match
    assert result is True, \
        f"Expected True when both intervals are {interval} minutes, but got {result}"


@settings(max_examples=100, deadline=None)
@given(
    timestamp_interval=st.sampled_from([5, 30]),
    period_interval=st.sampled_from([5, 30])
)
def test_property_interval_consistency_general(timestamp_interval, period_interval):
    """
    Property 11: Interval Consistency Validation (General Case)
    
    **Validates: Requirements 4.5, 4.6**
    
    For any combination of timestamp_interval and period_interval:
    - If they are equal, the function should return True
    - If they differ, the function should return False
    
    This property tests the core logic of consistency validation.
    """
    result = validate_interval_consistency(timestamp_interval, period_interval)
    
    # Property: Result should match whether intervals are equal
    expected = (timestamp_interval == period_interval)
    assert result == expected, \
        f"Expected {expected} for timestamp_interval={timestamp_interval} and period_interval={period_interval}, but got {result}"


@settings(max_examples=100, deadline=None)
@given(
    timestamp_interval=st.integers(min_value=1, max_value=60),
    period_interval=st.integers(min_value=1, max_value=60)
)
def test_property_interval_consistency_arbitrary_values(timestamp_interval, period_interval):
    """
    Property 11: Interval Consistency Validation (Arbitrary Intervals)
    
    **Validates: Requirements 4.5, 4.6**
    
    For any arbitrary interval values (not just 5 and 30), the function
    should correctly determine consistency. This tests that the function
    works with edge cases like unusual interval values.
    """
    result = validate_interval_consistency(timestamp_interval, period_interval)
    
    # Property: Result should be True if and only if intervals are equal
    if timestamp_interval == period_interval:
        assert result is True, \
            f"Expected True when both intervals are {timestamp_interval} minutes, but got {result}"
    else:
        assert result is False, \
            f"Expected False when timestamp_interval={timestamp_interval} and period_interval={period_interval}, but got {result}"


@settings(max_examples=100, deadline=None)
@given(
    interval=st.integers(min_value=1, max_value=1440)
)
def test_property_interval_consistency_reflexive(interval):
    """
    Property 11: Interval Consistency Validation (Reflexive Property)
    
    **Validates: Requirements 4.5**
    
    For any interval value, validating it against itself should always
    return True. This tests the reflexive property of consistency.
    """
    result = validate_interval_consistency(interval, interval)
    
    # Property: Any interval should be consistent with itself
    assert result is True, \
        f"Expected True when comparing interval {interval} with itself, but got {result}"


@settings(max_examples=100, deadline=None)
@given(
    interval1=st.integers(min_value=1, max_value=1440),
    interval2=st.integers(min_value=1, max_value=1440)
)
def test_property_interval_consistency_symmetric(interval1, interval2):
    """
    Property 11: Interval Consistency Validation (Symmetric Property)
    
    **Validates: Requirements 4.5**
    
    For any two intervals, validate_interval_consistency(a, b) should
    equal validate_interval_consistency(b, a). This tests the symmetric
    property of consistency.
    """
    result1 = validate_interval_consistency(interval1, interval2)
    result2 = validate_interval_consistency(interval2, interval1)
    
    # Property: Consistency check should be symmetric
    assert result1 == result2, \
        f"Expected symmetric results for intervals {interval1} and {interval2}, but got {result1} and {result2}"


def test_property_interval_consistency_conflict_detection():
    """
    Property 11: Interval Consistency Validation (Conflict Detection)
    
    **Validates: Requirements 4.6**
    
    When timestamp-derived interval (5 min) conflicts with period-derived
    interval (30 min), the function should return False to indicate a
    conflict that requires a warning message.
    """
    # Test the specific case mentioned in requirements: 5-minute vs 30-minute
    result_5_vs_30 = validate_interval_consistency(5, 30)
    result_30_vs_5 = validate_interval_consistency(30, 5)
    
    # Property: Should detect conflict between 5-minute and 30-minute intervals
    assert result_5_vs_30 is False, \
        "Expected False when comparing 5-minute and 30-minute intervals (conflict)"
    assert result_30_vs_5 is False, \
        "Expected False when comparing 30-minute and 5-minute intervals (conflict)"


# ============================================================================
# Property Tests for Data Validation
# ============================================================================


@st.composite
def unsorted_datetime_dataframe(draw):
    """
    Generate a DataFrame with datetime values in random order.
    
    Returns tuple of (unsorted_df, datetime_col_name)
    """
    # Generate number of rows
    num_rows = draw(st.integers(min_value=2, max_value=100))
    
    # Generate a random start datetime
    start_year = draw(st.integers(min_value=2020, max_value=2024))
    start_month = draw(st.integers(min_value=1, max_value=12))
    start_day = draw(st.integers(min_value=1, max_value=28))
    
    start_datetime = pd.Timestamp(year=start_year, month=start_month, day=start_day)
    
    # Generate sequential timestamps
    interval_minutes = draw(st.sampled_from([5, 30]))
    timestamps = pd.date_range(
        start=start_datetime,
        periods=num_rows,
        freq=f'{interval_minutes}min'
    )
    
    # Shuffle the timestamps to create random order
    shuffled_timestamps = timestamps.to_series().sample(frac=1).reset_index(drop=True)
    
    # Create DataFrame
    df = pd.DataFrame({
        'datetime': shuffled_timestamps,
        'consumption': draw(st.lists(
            st.floats(min_value=0.1, max_value=100.0),
            min_size=num_rows,
            max_size=num_rows
        ))
    })
    
    return df, 'datetime'


@settings(max_examples=100, deadline=None)
@given(data=unsorted_datetime_dataframe())
def test_property_data_sorting_by_datetime(data):
    """
    Property 12: Data Sorting by Datetime
    
    **Validates: Requirements 5.1**
    
    For any consumption DataFrame with datetime values in random order,
    after sorting by datetime, the data should be in ascending order.
    
    Requirement 5.1: "THE Data_Validator SHALL sort consumption data by
    datetime or derived datetime in ascending order"
    """
    df, datetime_col = data
    
    # Sort the DataFrame by datetime
    df_sorted = df.sort_values(by=datetime_col).reset_index(drop=True)
    
    # Property: After sorting, datetimes should be in ascending order
    datetimes = df_sorted[datetime_col]
    for i in range(len(datetimes) - 1):
        assert datetimes.iloc[i] <= datetimes.iloc[i + 1], \
            f"Datetimes not in ascending order at index {i}: {datetimes.iloc[i]} > {datetimes.iloc[i + 1]}"


@st.composite
def datetime_series_with_gaps(draw):
    """
    Generate a datetime series with deliberate gaps (missing periods).
    
    Returns tuple of (df, datetime_col, interval_minutes, expected_missing_count)
    """
    # Choose interval
    interval_minutes = draw(st.sampled_from([5, 30]))
    
    # Generate a base number of periods (ensure enough for gaps)
    num_periods = draw(st.integers(min_value=15, max_value=50))
    
    # Generate start datetime
    start_year = draw(st.integers(min_value=2020, max_value=2024))
    start_month = draw(st.integers(min_value=1, max_value=12))
    start_day = draw(st.integers(min_value=1, max_value=28))
    
    start_datetime = pd.Timestamp(year=start_year, month=start_month, day=start_day)
    
    # Generate complete datetime range
    complete_range = pd.date_range(
        start=start_datetime,
        periods=num_periods,
        freq=f'{interval_minutes}min'
    )
    
    # Create gaps by removing consecutive indices in the middle
    # This ensures we have actual gaps between first and last timestamp
    num_to_remove = draw(st.integers(min_value=1, max_value=min(5, num_periods - 10)))
    
    # Remove from middle section (not first or last few)
    gap_start_idx = draw(st.integers(min_value=3, max_value=num_periods - num_to_remove - 3))
    
    # Create indices to keep (all except the gap)
    indices_to_keep = list(range(gap_start_idx)) + list(range(gap_start_idx + num_to_remove, num_periods))
    
    # Create series with gaps
    timestamps_with_gaps = complete_range[indices_to_keep]
    
    # Create DataFrame
    df = pd.DataFrame({
        'datetime': timestamps_with_gaps,
        'consumption': [10.0] * len(timestamps_with_gaps)
    })
    
    # Calculate expected missing count
    expected_missing = num_to_remove
    
    return df, 'datetime', interval_minutes, expected_missing


@settings(max_examples=100, deadline=None)
@given(data=datetime_series_with_gaps())
def test_property_missing_period_detection(data):
    """
    Property 13: Missing Period Detection
    
    **Validates: Requirements 5.2, 13.3**
    
    For any time series with a known interval and deliberate gaps, the
    validator should detect and count the exact number of missing periods.
    
    Requirement 5.2: "WHEN missing time periods are detected in the sequence,
    THE Data_Validator SHALL display a warning message with the count of
    missing periods"
    
    Requirement 13.3: "WHEN duplicate time periods are detected during daylight
    saving transitions, THE Emissions_Dashboard SHALL display a warning message"
    """
    df, datetime_col, interval_minutes, expected_missing = data
    
    # Check for missing periods
    missing_periods = check_missing_periods(df, datetime_col, interval_minutes)
    
    # Property: The number of missing periods should match expected
    assert len(missing_periods) == expected_missing, \
        f"Expected {expected_missing} missing periods, but found {len(missing_periods)}"
    
    # Property: All missing periods should be valid datetime strings
    for missing_dt_str in missing_periods:
        # Should be parseable as datetime
        parsed = pd.to_datetime(missing_dt_str)
        assert isinstance(parsed, pd.Timestamp), \
            f"Missing period '{missing_dt_str}' is not a valid datetime string"


@st.composite
def datetime_series_with_duplicates(draw):
    """
    Generate a datetime series with duplicate values.
    
    Returns tuple of (df, datetime_col, expected_duplicate_count)
    """
    # Generate base number of unique timestamps
    num_unique = draw(st.integers(min_value=5, max_value=50))
    
    # Choose interval
    interval_minutes = draw(st.sampled_from([5, 30]))
    
    # Generate start datetime
    start_year = draw(st.integers(min_value=2020, max_value=2024))
    start_month = draw(st.integers(min_value=1, max_value=12))
    start_day = draw(st.integers(min_value=1, max_value=28))
    
    start_datetime = pd.Timestamp(year=start_year, month=start_month, day=start_day)
    
    # Generate unique timestamps
    unique_timestamps = pd.date_range(
        start=start_datetime,
        periods=num_unique,
        freq=f'{interval_minutes}min'
    )
    
    # Randomly duplicate some timestamps
    num_duplicates = draw(st.integers(min_value=1, max_value=min(5, num_unique)))
    
    # Select which timestamps to duplicate
    indices_to_duplicate = draw(st.lists(
        st.integers(min_value=0, max_value=num_unique - 1),
        min_size=num_duplicates,
        max_size=num_duplicates,
        unique=True
    ))
    
    # Create list with duplicates
    all_timestamps = list(unique_timestamps)
    for idx in indices_to_duplicate:
        all_timestamps.append(unique_timestamps[idx])
    
    # Create DataFrame
    df = pd.DataFrame({
        'datetime': all_timestamps,
        'consumption': [10.0] * len(all_timestamps)
    })
    
    return df, 'datetime', num_duplicates


@settings(max_examples=100, deadline=None)
@given(data=datetime_series_with_duplicates())
def test_property_duplicate_period_detection(data):
    """
    Property 14: Duplicate Period Detection
    
    **Validates: Requirements 5.3, 13.4**
    
    For any time series containing duplicate datetime values, the validator
    should detect and count all duplicates.
    
    Requirement 5.3: "WHEN duplicate time periods are detected, THE Data_Validator
    SHALL display a warning message indicating potential daylight saving time
    transitions"
    
    Requirement 13.4: "WHEN missing time periods are detected during daylight
    saving transitions, THE Emissions_Dashboard SHALL display a warning message"
    """
    df, datetime_col, expected_duplicates = data
    
    # Check for duplicate periods
    duplicate_count = check_duplicate_periods(df, datetime_col)
    
    # Property: The number of duplicates should match expected
    assert duplicate_count == expected_duplicates, \
        f"Expected {expected_duplicates} duplicate periods, but found {duplicate_count}"


@st.composite
def consumption_series_with_negatives(draw):
    """
    Generate a consumption series with negative values.
    
    Returns tuple of (df, consumption_col, expected_negative_count)
    """
    # Generate number of rows
    num_rows = draw(st.integers(min_value=5, max_value=50))
    
    # Generate number of negative values
    num_negatives = draw(st.integers(min_value=1, max_value=min(10, num_rows)))
    
    # Generate consumption values (mix of positive and negative)
    consumption_values = []
    
    # Add positive values
    for _ in range(num_rows - num_negatives):
        consumption_values.append(draw(st.floats(min_value=0.1, max_value=100.0)))
    
    # Add negative values
    for _ in range(num_negatives):
        consumption_values.append(draw(st.floats(min_value=-100.0, max_value=-0.1)))
    
    # Shuffle the values using Hypothesis's permutation
    consumption_values = draw(st.permutations(consumption_values))
    
    # Create DataFrame
    df = pd.DataFrame({
        'datetime': pd.date_range(start='2023-01-01', periods=num_rows, freq='5min'),
        'consumption': list(consumption_values)
    })
    
    return df, 'consumption', num_negatives


@settings(max_examples=100, deadline=None)
@given(data=consumption_series_with_negatives())
def test_property_negative_consumption_detection(data):
    """
    Property 15: Negative Consumption Detection
    
    **Validates: Requirements 5.4**
    
    For any consumption series containing negative values, the validator
    should detect and count the exact number of negative values.
    
    Requirement 5.4: "WHEN negative consumption values are detected,
    THE Data_Validator SHALL display a warning message with the count
    of negative values"
    """
    df, consumption_col, expected_negatives = data
    
    # Check for negative consumption
    negative_count = check_negative_consumption(df, consumption_col)
    
    # Property: The number of negative values should match expected
    assert negative_count == expected_negatives, \
        f"Expected {expected_negatives} negative consumption values, but found {negative_count}"


@settings(max_examples=100, deadline=None)
@given(
    num_rows=st.integers(min_value=1, max_value=100),
    all_positive=st.booleans()
)
def test_property_negative_consumption_boundary(num_rows, all_positive):
    """
    Property 15: Negative Consumption Detection (Boundary Test)
    
    **Validates: Requirements 5.4**
    
    For any consumption series with all positive values, the validator
    should detect zero negative values. For series with all negative
    values, it should detect all rows as negative.
    """
    if all_positive:
        # All positive values
        consumption_values = [10.0] * num_rows
        expected_negatives = 0
    else:
        # All negative values
        consumption_values = [-10.0] * num_rows
        expected_negatives = num_rows
    
    df = pd.DataFrame({
        'datetime': pd.date_range(start='2023-01-01', periods=num_rows, freq='5min'),
        'consumption': consumption_values
    })
    
    # Check for negative consumption
    negative_count = check_negative_consumption(df, 'consumption')
    
    # Property: Should match expected count
    assert negative_count == expected_negatives, \
        f"Expected {expected_negatives} negative values, but found {negative_count}"


@settings(max_examples=100, deadline=None)
@given(
    interval_minutes=st.sampled_from([5, 30]),
    num_periods=st.integers(min_value=2, max_value=100)
)
def test_property_no_missing_periods_in_complete_series(interval_minutes, num_periods):
    """
    Property 13: Missing Period Detection (Complete Series)
    
    **Validates: Requirements 5.2**
    
    For any complete time series with no gaps, the validator should
    detect zero missing periods.
    """
    # Generate complete datetime range with no gaps
    start_datetime = pd.Timestamp('2023-01-01 00:00:00')
    complete_range = pd.date_range(
        start=start_datetime,
        periods=num_periods,
        freq=f'{interval_minutes}min'
    )
    
    df = pd.DataFrame({
        'datetime': complete_range,
        'consumption': [10.0] * num_periods
    })
    
    # Check for missing periods
    missing_periods = check_missing_periods(df, 'datetime', interval_minutes)
    
    # Property: Should find no missing periods in complete series
    assert len(missing_periods) == 0, \
        f"Expected 0 missing periods in complete series, but found {len(missing_periods)}"


@settings(max_examples=100, deadline=None)
@given(
    num_rows=st.integers(min_value=1, max_value=100)
)
def test_property_no_duplicates_in_unique_series(num_rows):
    """
    Property 14: Duplicate Period Detection (Unique Series)
    
    **Validates: Requirements 5.3**
    
    For any time series with all unique datetime values, the validator
    should detect zero duplicates.
    """
    # Generate unique timestamps
    unique_timestamps = pd.date_range(
        start='2023-01-01',
        periods=num_rows,
        freq='5min'
    )
    
    df = pd.DataFrame({
        'datetime': unique_timestamps,
        'consumption': [10.0] * num_rows
    })
    
    # Check for duplicates
    duplicate_count = check_duplicate_periods(df, 'datetime')
    
    # Property: Should find no duplicates in unique series
    assert duplicate_count == 0, \
        f"Expected 0 duplicates in unique series, but found {duplicate_count}"
