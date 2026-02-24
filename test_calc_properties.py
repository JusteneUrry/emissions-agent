"""
Property-based tests for emissions calculation module.

Tests calculation logic using Hypothesis to validate mathematical properties
of percentage difference calculations.
"""

import pytest
import pandas as pd
from hypothesis import given, settings, strategies as st, assume, HealthCheck

from emissions.calc import calculate_percentage_difference


# ============================================================================
# Property Tests for Percentage Difference Calculation
# ============================================================================


@given(
    interval_total=st.floats(min_value=0.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    annual_total=st.floats(min_value=1e-10, max_value=1e6, allow_nan=False, allow_infinity=False)
)
@settings(max_examples=100)
def test_percentage_difference_formula(interval_total, annual_total):
    """
    **Validates: Requirements 10.7**
    
    Property 24: Percentage Difference Calculation
    
    Tests that calculate_percentage_difference correctly implements the formula:
    ((interval_total - annual_total) / annual_total) × 100
    
    This property verifies:
    - The mathematical formula is correctly implemented
    - The result matches manual calculation
    - The function handles various magnitudes of input values
    """
    # Calculate using the function
    result = calculate_percentage_difference(interval_total, annual_total)
    
    # Calculate expected value using the formula from requirement 10.7
    expected = ((interval_total - annual_total) / annual_total) * 100
    
    # Verify the result matches the expected formula
    assert abs(result - expected) < 1e-6, (
        f"Percentage difference calculation incorrect: "
        f"got {result}, expected {expected} "
        f"(interval={interval_total}, annual={annual_total})"
    )





# ============================================================================
# Property Tests for Daily Aggregation
# ============================================================================


@st.composite
def interval_emissions_dataframe(draw):
    """
    Generate interval-level emissions data spanning multiple days.

    Returns a DataFrame with columns:
    - datetime: Timestamps spanning multiple days
    - consumption_kwh: Random positive consumption values
    - emissions_tonnes: Random positive emissions values
    """
    # Generate number of days (at least 1, up to 10)
    num_days = draw(st.integers(min_value=1, max_value=10))

    # Choose interval: 5 or 30 minutes
    interval_minutes = draw(st.sampled_from([5, 30]))

    # Calculate number of intervals per day
    intervals_per_day = 1440 // interval_minutes  # 288 for 5-min, 48 for 30-min

    # Generate random start date
    start_year = draw(st.integers(min_value=2020, max_value=2024))
    start_month = draw(st.integers(min_value=1, max_value=12))
    start_day = draw(st.integers(min_value=1, max_value=28))  # Safe for all months

    start_datetime = pd.Timestamp(year=start_year, month=start_month, day=start_day, hour=0, minute=0)

    # Generate timestamps for all intervals across all days
    total_intervals = num_days * intervals_per_day
    timestamps = pd.date_range(
        start=start_datetime,
        periods=total_intervals,
        freq=f'{interval_minutes}min'
    )

    # Generate random consumption values (positive floats)
    consumption_values = draw(st.lists(
        st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=total_intervals,
        max_size=total_intervals
    ))

    # Generate random emissions values (positive floats)
    emissions_values = draw(st.lists(
        st.floats(min_value=0.0001, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=total_intervals,
        max_size=total_intervals
    ))

    # Create DataFrame
    df = pd.DataFrame({
        'datetime': timestamps,
        'consumption_kwh': consumption_values,
        'emissions_tonnes': emissions_values
    })

    return df


@given(interval_data=interval_emissions_dataframe())
@settings(max_examples=100)
def test_daily_aggregation_preserves_totals(interval_data):
    """
    **Validates: Requirements 11.1**

    Property 25: Daily Emissions Aggregation

    Tests that aggregate_daily_emissions correctly:
    1. Preserves total values (sum of daily totals equals sum of interval values)
    2. Groups data by date correctly
    3. Returns a DataFrame with expected columns

    This property verifies that aggregation doesn't lose or add data.
    """
    from emissions.calc import aggregate_daily_emissions

    # Calculate expected totals from interval data
    expected_total_consumption = interval_data['consumption_kwh'].sum()
    expected_total_emissions = interval_data['emissions_tonnes'].sum()

    # Perform daily aggregation
    daily_df = aggregate_daily_emissions(interval_data, 'datetime')

    # Property 1: Sum of daily totals should equal sum of interval values
    actual_total_consumption = daily_df['total_consumption_kwh'].sum()
    actual_total_emissions = daily_df['total_emissions_tonnes'].sum()

    assert abs(actual_total_consumption - expected_total_consumption) < 1e-6, (
        f"Total consumption not preserved: "
        f"expected {expected_total_consumption}, got {actual_total_consumption}"
    )

    assert abs(actual_total_emissions - expected_total_emissions) < 1e-6, (
        f"Total emissions not preserved: "
        f"expected {expected_total_emissions}, got {actual_total_emissions}"
    )

    # Property 2: DataFrame should have expected columns
    expected_columns = {'date', 'total_consumption_kwh', 'total_emissions_tonnes'}
    actual_columns = set(daily_df.columns)

    assert expected_columns == actual_columns, (
        f"Daily DataFrame has incorrect columns: "
        f"expected {expected_columns}, got {actual_columns}"
    )

    # Property 3: Number of unique days should match number of rows
    unique_dates = interval_data['datetime'].dt.date.nunique()
    assert len(daily_df) == unique_dates, (
        f"Number of daily records doesn't match unique dates: "
        f"expected {unique_dates} rows, got {len(daily_df)}"
    )

    # Property 4: Each daily total should equal sum of intervals for that date
    for _, daily_row in daily_df.iterrows():
        date = daily_row['date']

        # Filter interval data for this date
        interval_mask = interval_data['datetime'].dt.date == date
        interval_for_date = interval_data[interval_mask]

        # Calculate expected totals for this date
        expected_consumption = interval_for_date['consumption_kwh'].sum()
        expected_emissions = interval_for_date['emissions_tonnes'].sum()

        # Verify daily totals match
        assert abs(daily_row['total_consumption_kwh'] - expected_consumption) < 1e-6, (
            f"Daily consumption for {date} doesn't match interval sum: "
            f"expected {expected_consumption}, got {daily_row['total_consumption_kwh']}"
        )

        assert abs(daily_row['total_emissions_tonnes'] - expected_emissions) < 1e-6, (
            f"Daily emissions for {date} doesn't match interval sum: "
            f"expected {expected_emissions}, got {daily_row['total_emissions_tonnes']}"
        )


@given(
    num_days=st.integers(min_value=1, max_value=10),
    interval_minutes=st.sampled_from([5, 30])
)
@settings(max_examples=100)
def test_daily_aggregation_correct_day_count(num_days, interval_minutes):
    """
    **Validates: Requirements 11.1**

    Property 25: Daily Emissions Aggregation (Day Count)

    Tests that aggregate_daily_emissions returns the correct number of unique days.
    For any interval data spanning N days, the aggregated result should have N rows.
    """
    from emissions.calc import aggregate_daily_emissions

    # Calculate intervals per day
    intervals_per_day = 1440 // interval_minutes
    total_intervals = num_days * intervals_per_day

    # Generate complete interval data for N days
    start_datetime = pd.Timestamp('2023-01-01 00:00:00')
    timestamps = pd.date_range(
        start=start_datetime,
        periods=total_intervals,
        freq=f'{interval_minutes}min'
    )

    interval_data = pd.DataFrame({
        'datetime': timestamps,
        'consumption_kwh': [10.0] * total_intervals,
        'emissions_tonnes': [0.01] * total_intervals
    })

    # Perform daily aggregation
    daily_df = aggregate_daily_emissions(interval_data, 'datetime')

    # Property: Number of rows should equal number of days
    assert len(daily_df) == num_days, (
        f"Expected {num_days} daily records, but got {len(daily_df)}"
    )


@given(interval_data=interval_emissions_dataframe())
@settings(max_examples=100)
def test_daily_aggregation_non_negative_values(interval_data):
    """
    **Validates: Requirements 11.1**

    Property 25: Daily Emissions Aggregation (Non-Negative Values)

    Tests that aggregate_daily_emissions produces non-negative totals when
    given non-negative input values. This verifies that aggregation doesn't
    introduce negative values through calculation errors.
    """
    from emissions.calc import aggregate_daily_emissions

    # Ensure all input values are non-negative
    assume(all(interval_data['consumption_kwh'] >= 0))
    assume(all(interval_data['emissions_tonnes'] >= 0))

    # Perform daily aggregation
    daily_df = aggregate_daily_emissions(interval_data, 'datetime')

    # Property: All daily totals should be non-negative
    assert all(daily_df['total_consumption_kwh'] >= 0), (
        "Daily consumption totals contain negative values"
    )

    assert all(daily_df['total_emissions_tonnes'] >= 0), (
        "Daily emissions totals contain negative values"
    )


@given(
    consumption_value=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    emissions_value=st.floats(min_value=0.0001, max_value=1.0, allow_nan=False, allow_infinity=False),
    intervals_per_day=st.sampled_from([288, 48])  # 5-min or 30-min intervals
)
@settings(max_examples=100)
def test_daily_aggregation_single_day_sum(consumption_value, emissions_value, intervals_per_day):
    """
    **Validates: Requirements 11.1**

    Property 25: Daily Emissions Aggregation (Single Day)

    Tests that for a single day with constant values, the daily total equals
    the value multiplied by the number of intervals. This verifies the basic
    summation logic.
    """
    from emissions.calc import aggregate_daily_emissions

    # Create single day of data with constant values
    start_datetime = pd.Timestamp('2023-01-01 00:00:00')
    interval_minutes = 5 if intervals_per_day == 288 else 30

    timestamps = pd.date_range(
        start=start_datetime,
        periods=intervals_per_day,
        freq=f'{interval_minutes}min'
    )

    interval_data = pd.DataFrame({
        'datetime': timestamps,
        'consumption_kwh': [consumption_value] * intervals_per_day,
        'emissions_tonnes': [emissions_value] * intervals_per_day
    })

    # Perform daily aggregation
    daily_df = aggregate_daily_emissions(interval_data, 'datetime')

    # Property: Should have exactly 1 row for 1 day
    assert len(daily_df) == 1, f"Expected 1 daily record, got {len(daily_df)}"

    # Property: Daily total should equal value × number of intervals
    expected_consumption = consumption_value * intervals_per_day
    expected_emissions = emissions_value * intervals_per_day

    assert abs(daily_df['total_consumption_kwh'].iloc[0] - expected_consumption) < 1e-6, (
        f"Daily consumption doesn't match expected sum: "
        f"expected {expected_consumption}, got {daily_df['total_consumption_kwh'].iloc[0]}"
    )

    assert abs(daily_df['total_emissions_tonnes'].iloc[0] - expected_emissions) < 1e-6, (
        f"Daily emissions doesn't match expected sum: "
        f"expected {expected_emissions}, got {daily_df['total_emissions_tonnes'].iloc[0]}"
    )



if __name__ == '__main__':
    pytest.main([__file__, '-v'])


# ============================================================================
# Property Tests for Daily Aggregation
# ============================================================================


@st.composite
def interval_emissions_dataframe(draw):
    """
    Generate interval-level emissions data spanning multiple days.
    
    Returns a DataFrame with columns:
    - datetime: Timestamps spanning multiple days
    - consumption_kwh: Random positive consumption values
    - emissions_tonnes: Random positive emissions values
    """
    # Generate number of days (at least 1, up to 10)
    num_days = draw(st.integers(min_value=1, max_value=10))
    
    # Choose interval: 5 or 30 minutes
    interval_minutes = draw(st.sampled_from([5, 30]))
    
    # Calculate number of intervals per day
    intervals_per_day = 1440 // interval_minutes  # 288 for 5-min, 48 for 30-min
    
    # Generate random start date
    start_year = draw(st.integers(min_value=2020, max_value=2024))
    start_month = draw(st.integers(min_value=1, max_value=12))
    start_day = draw(st.integers(min_value=1, max_value=28))  # Safe for all months
    
    start_datetime = pd.Timestamp(year=start_year, month=start_month, day=start_day, hour=0, minute=0)
    
    # Generate timestamps for all intervals across all days
    total_intervals = num_days * intervals_per_day
    timestamps = pd.date_range(
        start=start_datetime,
        periods=total_intervals,
        freq=f'{interval_minutes}min'
    )
    
    # Generate random consumption values (positive floats)
    consumption_values = draw(st.lists(
        st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
        min_size=total_intervals,
        max_size=total_intervals
    ))
    
    # Generate random emissions values (positive floats)
    emissions_values = draw(st.lists(
        st.floats(min_value=0.0001, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=total_intervals,
        max_size=total_intervals
    ))
    
    # Create DataFrame
    df = pd.DataFrame({
        'datetime': timestamps,
        'consumption_kwh': consumption_values,
        'emissions_tonnes': emissions_values
    })
    
    return df


@given(interval_data=interval_emissions_dataframe())
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example])
def test_daily_aggregation_preserves_totals(interval_data):
    """
    **Validates: Requirements 11.1**
    
    Property 25: Daily Emissions Aggregation
    
    Tests that aggregate_daily_emissions correctly:
    1. Preserves total values (sum of daily totals equals sum of interval values)
    2. Groups data by date correctly
    3. Returns a DataFrame with expected columns
    
    This property verifies that aggregation doesn't lose or add data.
    """
    from emissions.calc import aggregate_daily_emissions
    
    # Calculate expected totals from interval data
    expected_total_consumption = interval_data['consumption_kwh'].sum()
    expected_total_emissions = interval_data['emissions_tonnes'].sum()
    
    # Perform daily aggregation
    daily_df = aggregate_daily_emissions(interval_data, 'datetime')
    
    # Property 1: Sum of daily totals should equal sum of interval values
    actual_total_consumption = daily_df['total_consumption_kwh'].sum()
    actual_total_emissions = daily_df['total_emissions_tonnes'].sum()
    
    assert abs(actual_total_consumption - expected_total_consumption) < 1e-6, (
        f"Total consumption not preserved: "
        f"expected {expected_total_consumption}, got {actual_total_consumption}"
    )
    
    assert abs(actual_total_emissions - expected_total_emissions) < 1e-6, (
        f"Total emissions not preserved: "
        f"expected {expected_total_emissions}, got {actual_total_emissions}"
    )
    
    # Property 2: DataFrame should have expected columns
    expected_columns = {'date', 'total_consumption_kwh', 'total_emissions_tonnes'}
    actual_columns = set(daily_df.columns)
    
    assert expected_columns == actual_columns, (
        f"Daily DataFrame has incorrect columns: "
        f"expected {expected_columns}, got {actual_columns}"
    )
    
    # Property 3: Number of unique days should match number of rows
    unique_dates = interval_data['datetime'].dt.date.nunique()
    assert len(daily_df) == unique_dates, (
        f"Number of daily records doesn't match unique dates: "
        f"expected {unique_dates} rows, got {len(daily_df)}"
    )
    
    # Property 4: Each daily total should equal sum of intervals for that date
    for _, daily_row in daily_df.iterrows():
        date = daily_row['date']
        
        # Filter interval data for this date
        interval_mask = interval_data['datetime'].dt.date == date
        interval_for_date = interval_data[interval_mask]
        
        # Calculate expected totals for this date
        expected_consumption = interval_for_date['consumption_kwh'].sum()
        expected_emissions = interval_for_date['emissions_tonnes'].sum()
        
        # Verify daily totals match
        assert abs(daily_row['total_consumption_kwh'] - expected_consumption) < 1e-6, (
            f"Daily consumption for {date} doesn't match interval sum: "
            f"expected {expected_consumption}, got {daily_row['total_consumption_kwh']}"
        )
        
        assert abs(daily_row['total_emissions_tonnes'] - expected_emissions) < 1e-6, (
            f"Daily emissions for {date} doesn't match interval sum: "
            f"expected {expected_emissions}, got {daily_row['total_emissions_tonnes']}"
        )


@given(
    num_days=st.integers(min_value=1, max_value=10),
    interval_minutes=st.sampled_from([5, 30])
)
@settings(max_examples=100)
def test_daily_aggregation_correct_day_count(num_days, interval_minutes):
    """
    **Validates: Requirements 11.1**
    
    Property 25: Daily Emissions Aggregation (Day Count)
    
    Tests that aggregate_daily_emissions returns the correct number of unique days.
    For any interval data spanning N days, the aggregated result should have N rows.
    """
    from emissions.calc import aggregate_daily_emissions
    
    # Calculate intervals per day
    intervals_per_day = 1440 // interval_minutes
    total_intervals = num_days * intervals_per_day
    
    # Generate complete interval data for N days
    start_datetime = pd.Timestamp('2023-01-01 00:00:00')
    timestamps = pd.date_range(
        start=start_datetime,
        periods=total_intervals,
        freq=f'{interval_minutes}min'
    )
    
    interval_data = pd.DataFrame({
        'datetime': timestamps,
        'consumption_kwh': [10.0] * total_intervals,
        'emissions_tonnes': [0.01] * total_intervals
    })
    
    # Perform daily aggregation
    daily_df = aggregate_daily_emissions(interval_data, 'datetime')
    
    # Property: Number of rows should equal number of days
    assert len(daily_df) == num_days, (
        f"Expected {num_days} daily records, but got {len(daily_df)}"
    )


@given(interval_data=interval_emissions_dataframe())
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example])
def test_daily_aggregation_non_negative_values(interval_data):
    """
    **Validates: Requirements 11.1**
    
    Property 25: Daily Emissions Aggregation (Non-Negative Values)
    
    Tests that aggregate_daily_emissions produces non-negative totals when
    given non-negative input values. This verifies that aggregation doesn't
    introduce negative values through calculation errors.
    """
    from emissions.calc import aggregate_daily_emissions
    
    # Ensure all input values are non-negative
    assume(all(interval_data['consumption_kwh'] >= 0))
    assume(all(interval_data['emissions_tonnes'] >= 0))
    
    # Perform daily aggregation
    daily_df = aggregate_daily_emissions(interval_data, 'datetime')
    
    # Property: All daily totals should be non-negative
    assert all(daily_df['total_consumption_kwh'] >= 0), (
        "Daily consumption totals contain negative values"
    )
    
    assert all(daily_df['total_emissions_tonnes'] >= 0), (
        "Daily emissions totals contain negative values"
    )


@given(
    consumption_value=st.floats(min_value=0.1, max_value=100.0, allow_nan=False, allow_infinity=False),
    emissions_value=st.floats(min_value=0.0001, max_value=1.0, allow_nan=False, allow_infinity=False),
    intervals_per_day=st.sampled_from([288, 48])  # 5-min or 30-min intervals
)
@settings(max_examples=100)
def test_daily_aggregation_single_day_sum(consumption_value, emissions_value, intervals_per_day):
    """
    **Validates: Requirements 11.1**
    
    Property 25: Daily Emissions Aggregation (Single Day)
    
    Tests that for a single day with constant values, the daily total equals
    the value multiplied by the number of intervals. This verifies the basic
    summation logic.
    """
    from emissions.calc import aggregate_daily_emissions
    
    # Create single day of data with constant values
    start_datetime = pd.Timestamp('2023-01-01 00:00:00')
    interval_minutes = 5 if intervals_per_day == 288 else 30
    
    timestamps = pd.date_range(
        start=start_datetime,
        periods=intervals_per_day,
        freq=f'{interval_minutes}min'
    )
    
    interval_data = pd.DataFrame({
        'datetime': timestamps,
        'consumption_kwh': [consumption_value] * intervals_per_day,
        'emissions_tonnes': [emissions_value] * intervals_per_day
    })
    
    # Perform daily aggregation
    daily_df = aggregate_daily_emissions(interval_data, 'datetime')
    
    # Property: Should have exactly 1 row for 1 day
    assert len(daily_df) == 1, f"Expected 1 daily record, got {len(daily_df)}"
    
    # Property: Daily total should equal value × number of intervals
    expected_consumption = consumption_value * intervals_per_day
    expected_emissions = emissions_value * intervals_per_day
    
    assert abs(daily_df['total_consumption_kwh'].iloc[0] - expected_consumption) < 1e-6, (
        f"Daily consumption doesn't match expected sum: "
        f"expected {expected_consumption}, got {daily_df['total_consumption_kwh'].iloc[0]}"
    )
    
    assert abs(daily_df['total_emissions_tonnes'].iloc[0] - expected_emissions) < 1e-6, (
        f"Daily emissions doesn't match expected sum: "
        f"expected {expected_emissions}, got {daily_df['total_emissions_tonnes'].iloc[0]}"
    )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
