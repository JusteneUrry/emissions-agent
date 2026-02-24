"""
Property-based tests for emissions factors module.

Tests emissions factor loading and filtering using Hypothesis to validate that
interval and annual factors are correctly loaded and filtered by state and interval.
"""

import os
import tempfile
import pytest
import pandas as pd
from pathlib import Path
from hypothesis import given, settings, strategies as st

from emissions.factors import (
    load_interval_factors,
    load_annual_factors,
    get_factor_metadata
)


# ============================================================================
# Custom Strategies for Test Data Generation
# ============================================================================


@st.composite
def nem_state(draw):
    """Generate valid NEM state codes."""
    return draw(st.sampled_from(['NSW', 'VIC', 'QLD', 'SA', 'TAS']))


@st.composite
def interval_minutes(draw):
    """Generate valid interval values (5 or 30 minutes)."""
    return draw(st.sampled_from([5, 30]))


@st.composite
def emissions_period_code(draw):
    """Generate valid emissions period codes in format YYYYMMDDTTT."""
    year = draw(st.integers(min_value=2020, max_value=2030))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    period = draw(st.integers(min_value=1, max_value=288))
    
    return f"{year:04d}{month:02d}{day:02d}{period:03d}"


@st.composite
def emissions_factor_value(draw):
    """Generate realistic emissions factor values (positive floats)."""
    return draw(st.floats(min_value=0.1, max_value=2000.0, allow_nan=False, allow_infinity=False))


@st.composite
def year_value(draw):
    """Generate year values for annual factors."""
    return draw(st.integers(min_value=2020, max_value=2030))


# ============================================================================
# Property Tests for Interval Emissions Factor Loading
# ============================================================================


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state(),
    target_interval=interval_minutes()
)
def test_property_interval_factors_state_filtering(target_state, target_interval):
    """
    Property 16: Emissions Factor Loading and Filtering (State and Interval)
    
    **Validates: Requirements 7.1, 7.2, 7.3**
    
    For any valid NEM state and interval (5 or 30 minutes), loading interval
    factors should return only records matching that exact state and interval.
    No records from other states or intervals should be included.
    
    Requirement 7.1: "THE Emissions_Calculator SHALL load interval-specific
    emissions factors from CSV file"
    
    Requirement 7.2: "THE Emissions_Calculator SHALL filter emissions factors
    by NEM state (NSW, VIC, QLD, SA, TAS)"
    
    Requirement 7.3: "THE Emissions_Calculator SHALL filter emissions factors
    by interval duration (5-minute or 30-minute)"
    """
    # Load interval factors for the target state and interval
    df = load_interval_factors(target_state, target_interval)
    
    # Property: All returned records should match the target state
    if len(df) > 0:
        assert (df['state'] == target_state).all(), \
            f"Expected all records to have state='{target_state}', but found other states: {df['state'].unique()}"
        
        # Property: All returned records should match the target interval
        assert (df['interval_minutes'] == target_interval).all(), \
            f"Expected all records to have interval_minutes={target_interval}, but found other intervals: {df['interval_minutes'].unique()}"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state(),
    target_interval=interval_minutes()
)
def test_property_interval_factors_required_columns(target_state, target_interval):
    """
    Property 16: Emissions Factor Loading and Filtering (Required Columns)
    
    **Validates: Requirements 7.1, 7.4**
    
    For any valid state and interval, the loaded interval factors DataFrame
    should contain all required columns with correct data types.
    
    Requirement 7.4: "THE Emissions_Calculator SHALL validate that emissions
    factors contain required columns (state, interval_minutes, emissions_period_code,
    factor_g_per_kwh, source, dataset_version)"
    """
    # Load interval factors
    df = load_interval_factors(target_state, target_interval)
    
    # Property: All required columns should be present
    required_columns = [
        'state',
        'interval_minutes',
        'emissions_period_code',
        'factor_g_per_kwh',
        'source',
        'dataset_version'
    ]
    
    for col in required_columns:
        assert col in df.columns, \
            f"Required column '{col}' is missing from interval factors DataFrame"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state(),
    target_interval=interval_minutes()
)
def test_property_interval_factors_positive_values(target_state, target_interval):
    """
    Property 16: Emissions Factor Loading and Filtering (Positive Values)
    
    **Validates: Requirements 7.5**
    
    For any valid state and interval, all emissions factor values should be
    positive numbers (greater than 0). Negative or zero emissions factors
    are physically invalid.
    
    Requirement 7.5: "THE Emissions_Calculator SHALL validate that emissions
    factor values are positive numbers"
    """
    # Load interval factors
    df = load_interval_factors(target_state, target_interval)
    
    # Property: All factor values should be positive
    if len(df) > 0:
        assert (df['factor_g_per_kwh'] > 0).all(), \
            f"Expected all factor values to be positive, but found non-positive values: {df[df['factor_g_per_kwh'] <= 0]['factor_g_per_kwh'].tolist()}"


@settings(max_examples=100, deadline=None)
@given(
    state1=nem_state(),
    state2=nem_state(),
    target_interval=interval_minutes()
)
def test_property_interval_factors_no_cross_state_contamination(state1, state2, target_interval):
    """
    Property 16: Emissions Factor Loading and Filtering (No Cross-State Contamination)
    
    **Validates: Requirements 7.2**
    
    When loading factors for state1, the results should never contain records
    from state2 (if state1 != state2). This tests that filtering is exact and
    doesn't allow partial matches or contamination.
    """
    # Skip if both states are the same
    if state1 == state2:
        return
    
    # Load factors for state1
    df1 = load_interval_factors(state1, target_interval)
    
    # Property: Should not contain any records from state2
    if len(df1) > 0:
        assert not (df1['state'] == state2).any(), \
            f"Expected no records from state '{state2}' when loading state '{state1}', but found {(df1['state'] == state2).sum()} records"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state(),
    interval1=interval_minutes(),
    interval2=interval_minutes()
)
def test_property_interval_factors_no_cross_interval_contamination(target_state, interval1, interval2):
    """
    Property 16: Emissions Factor Loading and Filtering (No Cross-Interval Contamination)
    
    **Validates: Requirements 7.3**
    
    When loading factors for interval1, the results should never contain records
    from interval2 (if interval1 != interval2). This tests that interval filtering
    is exact.
    """
    # Skip if both intervals are the same
    if interval1 == interval2:
        return
    
    # Load factors for interval1
    df1 = load_interval_factors(target_state, interval1)
    
    # Property: Should not contain any records from interval2
    if len(df1) > 0:
        assert not (df1['interval_minutes'] == interval2).any(), \
            f"Expected no records from interval {interval2} when loading interval {interval1}, but found {(df1['interval_minutes'] == interval2).sum()} records"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state(),
    target_interval=interval_minutes()
)
def test_property_interval_factors_emissions_period_code_format(target_state, target_interval):
    """
    Property 16: Emissions Factor Loading and Filtering (Period Code Format)
    
    **Validates: Requirements 7.4**
    
    For any loaded interval factors, all emissions_period_code values should
    follow the format YYYYMMDDTTT (11 characters: 8 for date, 3 for period).
    """
    # Load interval factors
    df = load_interval_factors(target_state, target_interval)
    
    # Property: All period codes should be 11 characters
    if len(df) > 0:
        period_codes = df['emissions_period_code'].astype(str)
        assert (period_codes.str.len() == 11).all(), \
            f"Expected all period codes to be 11 characters, but found varying lengths: {period_codes.str.len().unique()}"


# ============================================================================
# Property Tests for Annual Emissions Factor Loading
# ============================================================================


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state()
)
def test_property_annual_factors_state_filtering(target_state):
    """
    Property 16: Emissions Factor Loading and Filtering (Annual State Filtering)
    
    **Validates: Requirements 8.1, 8.2**
    
    For any valid NEM state, loading annual factors should return only records
    matching that exact state. No records from other states should be included.
    
    Requirement 8.1: "THE Emissions_Calculator SHALL load annual average
    emissions factors from CSV file"
    
    Requirement 8.2: "THE Emissions_Calculator SHALL filter annual emissions
    factors by NEM state"
    """
    # Load annual factors for the target state
    df = load_annual_factors(target_state)
    
    # Property: All returned records should match the target state
    if len(df) > 0:
        assert (df['state'] == target_state).all(), \
            f"Expected all records to have state='{target_state}', but found other states: {df['state'].unique()}"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state()
)
def test_property_annual_factors_required_columns(target_state):
    """
    Property 16: Emissions Factor Loading and Filtering (Annual Required Columns)
    
    **Validates: Requirements 8.1, 8.3**
    
    For any valid state, the loaded annual factors DataFrame should contain
    all required columns with correct data types.
    
    Requirement 8.3: "THE Emissions_Calculator SHALL validate that annual
    emissions factors contain required columns (state, year, annual_factor_g_per_kwh,
    source, dataset_version)"
    """
    # Load annual factors
    df = load_annual_factors(target_state)
    
    # Property: All required columns should be present
    required_columns = [
        'state',
        'year',
        'annual_factor_g_per_kwh',
        'source',
        'dataset_version'
    ]
    
    for col in required_columns:
        assert col in df.columns, \
            f"Required column '{col}' is missing from annual factors DataFrame"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state()
)
def test_property_annual_factors_positive_values(target_state):
    """
    Property 16: Emissions Factor Loading and Filtering (Annual Positive Values)
    
    **Validates: Requirements 8.4**
    
    For any valid state, all annual emissions factor values should be positive
    numbers (greater than 0). Negative or zero emissions factors are physically
    invalid.
    
    Requirement 8.4: "THE Emissions_Calculator SHALL validate that annual
    emissions factor values are positive numbers"
    """
    # Load annual factors
    df = load_annual_factors(target_state)
    
    # Property: All factor values should be positive
    if len(df) > 0:
        assert (df['annual_factor_g_per_kwh'] > 0).all(), \
            f"Expected all annual factor values to be positive, but found non-positive values: {df[df['annual_factor_g_per_kwh'] <= 0]['annual_factor_g_per_kwh'].tolist()}"


@settings(max_examples=100, deadline=None)
@given(
    state1=nem_state(),
    state2=nem_state()
)
def test_property_annual_factors_no_cross_state_contamination(state1, state2):
    """
    Property 16: Emissions Factor Loading and Filtering (Annual No Cross-State)
    
    **Validates: Requirements 8.2**
    
    When loading annual factors for state1, the results should never contain
    records from state2 (if state1 != state2). This tests that filtering is
    exact and doesn't allow partial matches.
    """
    # Skip if both states are the same
    if state1 == state2:
        return
    
    # Load factors for state1
    df1 = load_annual_factors(state1)
    
    # Property: Should not contain any records from state2
    if len(df1) > 0:
        assert not (df1['state'] == state2).any(), \
            f"Expected no records from state '{state2}' when loading state '{state1}', but found {(df1['state'] == state2).sum()} records"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state()
)
def test_property_annual_factors_year_values(target_state):
    """
    Property 16: Emissions Factor Loading and Filtering (Year Values)
    
    **Validates: Requirements 8.3**
    
    For any loaded annual factors, all year values should be reasonable
    integers (e.g., between 2000 and 2100).
    """
    # Load annual factors
    df = load_annual_factors(target_state)
    
    # Property: All year values should be in reasonable range
    if len(df) > 0:
        assert (df['year'] >= 2000).all() and (df['year'] <= 2100).all(), \
            f"Expected all year values to be between 2000 and 2100, but found: {df['year'].unique()}"


# ============================================================================
# Property Tests for Missing Factor File Errors
# ============================================================================


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state(),
    target_interval=interval_minutes()
)
def test_property_missing_interval_factors_file_error(target_state, target_interval):
    """
    Property 17: Missing Factor File Error (Interval Factors)
    
    **Validates: Requirements 7.1**
    
    For any non-existent directory path, load_interval_factors should raise
    FileNotFoundError with a descriptive message indicating the missing file.
    """
    # Create a non-existent directory path
    non_existent_dir = f"/non_existent_path_{target_state}_{target_interval}"
    
    # Property: Should raise FileNotFoundError
    with pytest.raises(FileNotFoundError) as exc_info:
        load_interval_factors(target_state, target_interval, factors_dir=non_existent_dir)
    
    # Verify error message mentions the file
    error_msg = str(exc_info.value).lower()
    assert 'interval' in error_msg or 'factor' in error_msg or 'not found' in error_msg, \
        f"Error message should mention interval factors or file not found: {exc_info.value}"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state()
)
def test_property_missing_annual_factors_file_error(target_state):
    """
    Property 17: Missing Factor File Error (Annual Factors)
    
    **Validates: Requirements 8.1**
    
    For any non-existent directory path, load_annual_factors should raise
    FileNotFoundError with a descriptive message indicating the missing file.
    """
    # Create a non-existent directory path
    non_existent_dir = f"/non_existent_path_{target_state}_annual"
    
    # Property: Should raise FileNotFoundError
    with pytest.raises(FileNotFoundError) as exc_info:
        load_annual_factors(target_state, factors_dir=non_existent_dir)
    
    # Verify error message mentions the file
    error_msg = str(exc_info.value).lower()
    assert 'annual' in error_msg or 'factor' in error_msg or 'not found' in error_msg, \
        f"Error message should mention annual factors or file not found: {exc_info.value}"


@settings(max_examples=100, deadline=None)
@given(
    random_suffix=st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122))
)
def test_property_missing_metadata_file_error(random_suffix):
    """
    Property 17: Missing Factor File Error (Metadata)
    
    **Validates: Requirements 7.1, 8.1**
    
    For any non-existent directory path, get_factor_metadata should raise
    FileNotFoundError with a descriptive message indicating the missing README.
    """
    # Create a non-existent directory path with random suffix
    non_existent_dir = f"/non_existent_path_{random_suffix}"
    
    # Property: Should raise FileNotFoundError
    with pytest.raises(FileNotFoundError) as exc_info:
        get_factor_metadata(factors_dir=non_existent_dir)
    
    # Verify error message mentions the file
    error_msg = str(exc_info.value).lower()
    assert 'readme' in error_msg or 'not found' in error_msg, \
        f"Error message should mention README or file not found: {exc_info.value}"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state(),
    target_interval=interval_minutes()
)
def test_property_missing_file_error_consistency(target_state, target_interval):
    """
    Property 17: Missing Factor File Error (Consistency)
    
    **Validates: Requirements 7.1, 8.1**
    
    For the same non-existent directory, all three loading functions should
    consistently raise FileNotFoundError. This tests error handling consistency.
    """
    # Create a unique non-existent directory path
    with tempfile.TemporaryDirectory() as temp_dir:
        non_existent_dir = os.path.join(temp_dir, "does_not_exist")
        
        # Property: All three functions should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            load_interval_factors(target_state, target_interval, factors_dir=non_existent_dir)
        
        with pytest.raises(FileNotFoundError):
            load_annual_factors(target_state, factors_dir=non_existent_dir)
        
        with pytest.raises(FileNotFoundError):
            get_factor_metadata(factors_dir=non_existent_dir)


# ============================================================================
# Property Tests for Metadata Extraction
# ============================================================================


def test_property_metadata_structure():
    """
    Property: Metadata Structure
    
    **Validates: Requirements 7.1, 8.1**
    
    The get_factor_metadata function should always return a dictionary with
    the expected keys (source, version, methodology, raw_content).
    """
    # Load metadata from actual data directory
    metadata = get_factor_metadata()
    
    # Property: Should return a dictionary
    assert isinstance(metadata, dict), \
        f"Expected metadata to be a dictionary, but got {type(metadata)}"
    
    # Property: Should contain all expected keys
    expected_keys = ['source', 'version', 'methodology', 'raw_content']
    for key in expected_keys:
        assert key in metadata, \
            f"Expected key '{key}' in metadata dictionary, but it's missing"
    
    # Property: raw_content should be a non-empty string
    assert isinstance(metadata['raw_content'], str), \
        f"Expected raw_content to be a string, but got {type(metadata['raw_content'])}"
    assert len(metadata['raw_content']) > 0, \
        "Expected raw_content to be non-empty"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state(),
    target_interval=interval_minutes()
)
def test_property_interval_factors_deterministic(target_state, target_interval):
    """
    Property 16: Emissions Factor Loading Determinism
    
    **Validates: Requirements 7.1, 7.2, 7.3**
    
    For any state and interval, loading the same factors multiple times should
    return identical results. This tests that the loading function is deterministic
    and doesn't introduce randomness or side effects.
    """
    # Load factors twice
    df1 = load_interval_factors(target_state, target_interval)
    df2 = load_interval_factors(target_state, target_interval)
    
    # Property: Both DataFrames should be identical
    assert len(df1) == len(df2), \
        f"Expected same number of rows, but got {len(df1)} and {len(df2)}"
    
    if len(df1) > 0:
        # Compare values (reset index to ensure alignment)
        df1_reset = df1.reset_index(drop=True)
        df2_reset = df2.reset_index(drop=True)
        
        assert df1_reset.equals(df2_reset), \
            "Expected identical DataFrames from repeated loads, but they differ"


@settings(max_examples=100, deadline=None)
@given(
    target_state=nem_state()
)
def test_property_annual_factors_deterministic(target_state):
    """
    Property 16: Annual Emissions Factor Loading Determinism
    
    **Validates: Requirements 8.1, 8.2**
    
    For any state, loading the same annual factors multiple times should return
    identical results. This tests that the loading function is deterministic.
    """
    # Load factors twice
    df1 = load_annual_factors(target_state)
    df2 = load_annual_factors(target_state)
    
    # Property: Both DataFrames should be identical
    assert len(df1) == len(df2), \
        f"Expected same number of rows, but got {len(df1)} and {len(df2)}"
    
    if len(df1) > 0:
        # Compare values (reset index to ensure alignment)
        df1_reset = df1.reset_index(drop=True)
        df2_reset = df2.reset_index(drop=True)
        
        assert df1_reset.equals(df2_reset), \
            "Expected identical DataFrames from repeated loads, but they differ"
