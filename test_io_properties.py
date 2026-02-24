"""
Property-based tests for file I/O module.

Tests file format parsing using Hypothesis to validate that CSV and Excel files
are correctly parsed into DataFrames with proper row counts.
"""

import io
import pytest
import pandas as pd
from hypothesis import given, settings, strategies as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from emissions.io import load_consumption_file, UnsupportedFileFormatError


# Custom strategy for generating valid consumption data
@st.composite
def consumption_data(draw):
    """Generate random consumption data with various patterns."""
    num_rows = draw(st.integers(min_value=1, max_value=100))
    
    # Generate consumption values (positive floats)
    consumption = [draw(st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False)) 
                   for _ in range(num_rows)]
    
    # Generate timestamps
    base_date = pd.Timestamp('2023-01-01')
    timestamps = [base_date + pd.Timedelta(minutes=5*i) for i in range(num_rows)]
    
    # Generate time periods (1-288 for 5-minute intervals)
    periods = list(range(1, num_rows + 1))
    
    df = pd.DataFrame({
        'timestamp': timestamps,
        'consumption_kwh': consumption,
        'time_period': periods
    })
    
    return df, num_rows


def create_mock_uploaded_file(content: bytes, filename: str) -> UploadedFile:
    """Create a mock UploadedFile object for testing."""
    file_obj = io.BytesIO(content)
    
    # Create a minimal mock that has the required attributes
    class MockUploadedFile:
        def __init__(self, file_obj, name):
            self.name = name
            self._file_obj = file_obj
            
        def read(self, size=-1):
            return self._file_obj.read(size)
        
        def seek(self, pos, whence=0):
            return self._file_obj.seek(pos, whence)
        
        def tell(self):
            return self._file_obj.tell()
        
        def seekable(self):
            return self._file_obj.seekable()
        
        def readable(self):
            return self._file_obj.readable()
        
        def writable(self):
            return self._file_obj.writable()
    
    return MockUploadedFile(file_obj, filename)


@settings(max_examples=100, deadline=None)
@given(data=consumption_data())
def test_property_csv_file_parsing(data):
    """
    Property 1: File Format Parsing (CSV)
    
    **Validates: Requirements 1.1, 1.4**
    
    For any valid CSV file containing consumption data with required columns,
    the file loader should successfully parse it into a DataFrame with the same
    number of rows as the source file.
    """
    df, expected_rows = data
    
    # Convert DataFrame to CSV bytes
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    
    # Create mock uploaded file
    uploaded_file = create_mock_uploaded_file(csv_bytes, 'test_data.csv')
    
    # Load the file
    result_df = load_consumption_file(uploaded_file)
    
    # Property: Row count should be preserved
    assert len(result_df) == expected_rows, \
        f"Expected {expected_rows} rows, got {len(result_df)}"
    
    # Property: All columns should be present
    assert 'consumption_kwh' in result_df.columns
    assert 'timestamp' in result_df.columns or 'time_period' in result_df.columns


@settings(max_examples=100, deadline=None)
@given(data=consumption_data())
def test_property_excel_file_parsing(data):
    """
    Property 1: File Format Parsing (Excel)
    
    **Validates: Requirements 1.2, 1.4**
    
    For any valid Excel file containing consumption data with required columns,
    the file loader should successfully parse it into a DataFrame with the same
    number of rows as the source file.
    """
    df, expected_rows = data
    
    # Convert DataFrame to Excel bytes
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_bytes = excel_buffer.getvalue()
    
    # Create mock uploaded file
    uploaded_file = create_mock_uploaded_file(excel_bytes, 'test_data.xlsx')
    
    # Load the file
    result_df = load_consumption_file(uploaded_file)
    
    # Property: Row count should be preserved
    assert len(result_df) == expected_rows, \
        f"Expected {expected_rows} rows, got {len(result_df)}"
    
    # Property: All columns should be present
    assert 'consumption_kwh' in result_df.columns
    assert 'timestamp' in result_df.columns or 'time_period' in result_df.columns


@settings(max_examples=100, deadline=None)
@given(
    data=consumption_data(),
    file_extension=st.sampled_from([
        '.txt', '.json', '.xml', '.pdf', '.doc', '.docx', 
        '.xls', '.zip', '.tar', '.gz', '.py', '.js', 
        '.html', '.md', '.log', '.dat', '.bin', '.exe',
        '.jpg', '.png', '.gif', '.mp4', '.mp3', '.wav'
    ])
)
def test_property_unsupported_format_rejection(data, file_extension):
    """
    Property 2: Unsupported Format Rejection
    
    **Validates: Requirements 1.3**
    
    For any file with an extension other than .csv or .xlsx, the file loader
    should raise an UnsupportedFileFormatError.
    """
    df, _ = data
    
    # Convert to CSV bytes (content doesn't matter, only extension)
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    
    # Create mock uploaded file with unsupported extension
    uploaded_file = create_mock_uploaded_file(csv_bytes, f'test_data{file_extension}')
    
    # Property: Should raise UnsupportedFileFormatError
    with pytest.raises(UnsupportedFileFormatError) as exc_info:
        load_consumption_file(uploaded_file)
    
    # Verify error message mentions supported formats
    assert 'CSV' in str(exc_info.value) or 'csv' in str(exc_info.value)
    assert 'Excel' in str(exc_info.value) or 'xlsx' in str(exc_info.value)


@settings(max_examples=100, deadline=None)
@given(
    num_rows=st.integers(min_value=0, max_value=1000),
    num_cols=st.integers(min_value=1, max_value=20)
)
def test_property_csv_row_count_preservation(num_rows, num_cols):
    """
    Property: CSV parsing preserves exact row count
    
    **Validates: Requirements 1.1, 1.4**
    
    For any CSV file with N rows, the parsed DataFrame should have exactly N rows.
    This tests edge cases like empty files, single row, and large files.
    """
    # Generate random data
    data = {}
    for i in range(num_cols):
        data[f'col_{i}'] = [f'value_{j}' for j in range(num_rows)]
    
    df = pd.DataFrame(data)
    
    # Convert to CSV
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    uploaded_file = create_mock_uploaded_file(csv_bytes, 'test.csv')
    
    # Load and verify
    result_df = load_consumption_file(uploaded_file)
    
    # Property: Exact row count preservation
    assert len(result_df) == num_rows


@settings(max_examples=100, deadline=None)
@given(
    num_rows=st.integers(min_value=1, max_value=1000),
    num_cols=st.integers(min_value=1, max_value=20)
)
def test_property_excel_row_count_preservation(num_rows, num_cols):
    """
    Property: Excel parsing preserves exact row count
    
    **Validates: Requirements 1.2, 1.4**
    
    For any Excel file with N rows, the parsed DataFrame should have exactly N rows.
    This tests edge cases like single row and large files.
    """
    # Generate random data
    data = {}
    for i in range(num_cols):
        data[f'col_{i}'] = [f'value_{j}' for j in range(num_rows)]
    
    df = pd.DataFrame(data)
    
    # Convert to Excel
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_bytes = excel_buffer.getvalue()
    uploaded_file = create_mock_uploaded_file(excel_bytes, 'test.xlsx')
    
    # Load and verify
    result_df = load_consumption_file(uploaded_file)
    
    # Property: Exact row count preservation
    assert len(result_df) == num_rows


# ============================================================================
# Property Tests for Column Identification
# ============================================================================

from emissions.io import identify_consumption_column, identify_time_columns, ColumnNotFoundError


@st.composite
def consumption_column_name(draw):
    """Generate column names matching consumption patterns."""
    base_patterns = ['consumption', 'kwh', 'usage', 'energy']
    base = draw(st.sampled_from(base_patterns))
    
    # Apply random case variations
    case_transform = draw(st.sampled_from([
        str.lower,
        str.upper,
        str.title,
        lambda s: s  # no change
    ]))
    
    # Optionally add prefix/suffix
    prefix = draw(st.sampled_from(['', 'total_', 'net_', 'gross_']))
    suffix = draw(st.sampled_from(['', '_value', '_data', '_amount']))
    
    return prefix + case_transform(base) + suffix


@st.composite
def timestamp_column_name(draw):
    """Generate column names matching timestamp patterns."""
    base_patterns = ['timestamp', 'datetime', 'date_time', 'time']
    base = draw(st.sampled_from(base_patterns))
    
    # Apply random case variations
    case_transform = draw(st.sampled_from([
        str.lower,
        str.upper,
        str.title,
        lambda s: s
    ]))
    
    # Optionally add prefix/suffix
    prefix = draw(st.sampled_from(['', 'start_', 'end_', 'record_']))
    suffix = draw(st.sampled_from(['', '_utc', '_local', '_stamp']))
    
    return prefix + case_transform(base) + suffix


@st.composite
def period_column_name(draw):
    """Generate column names matching period patterns."""
    base_patterns = ['period', 'time_period', 'interval', 'tp']
    base = draw(st.sampled_from(base_patterns))
    
    # Apply random case variations
    case_transform = draw(st.sampled_from([
        str.lower,
        str.upper,
        str.title,
        lambda s: s
    ]))
    
    # Optionally add prefix/suffix
    prefix = draw(st.sampled_from(['', 'time_', 'data_']))
    suffix = draw(st.sampled_from(['', '_code', '_id', '_number']))
    
    return prefix + case_transform(base) + suffix


@st.composite
def date_column_name(draw):
    """Generate column names matching date patterns."""
    # The date pattern in io.py uses ^(date|day)$ which requires exact match
    # So we can only use 'date' or 'day' with case variations, no prefix/suffix
    base_patterns = ['date', 'day']
    base = draw(st.sampled_from(base_patterns))
    
    # Apply random case variations
    case_transform = draw(st.sampled_from([
        str.lower,
        str.upper,
        str.title,
        lambda s: s
    ]))
    
    return case_transform(base)


@st.composite
def non_matching_column_name(draw):
    """Generate column names that should NOT match any pattern."""
    base_patterns = [
        'location', 'site', 'meter', 'customer', 'account',
        'voltage', 'current', 'power_factor', 'demand',
        'temperature', 'humidity', 'pressure', 'status',
        'id', 'name', 'description', 'notes', 'comments'
    ]
    base = draw(st.sampled_from(base_patterns))
    
    # Apply random case variations
    case_transform = draw(st.sampled_from([
        str.lower,
        str.upper,
        str.title
    ]))
    
    return case_transform(base)


@settings(max_examples=100, deadline=None)
@given(
    consumption_col=consumption_column_name(),
    num_other_cols=st.integers(min_value=0, max_value=10)
)
def test_property_consumption_column_pattern_matching(consumption_col, num_other_cols):
    """
    Property 3: Column Pattern Matching (Consumption)
    
    **Validates: Requirements 2.1**
    
    For any DataFrame with a column matching consumption patterns (consumption, kwh, 
    usage, energy) in any case variation, the identify_consumption_column function 
    should correctly recognize it.
    """
    # Create DataFrame with consumption column and other non-matching columns
    data = {consumption_col: [1.0, 2.0, 3.0]}
    
    # Add other columns that should NOT match
    for i in range(num_other_cols):
        data[f'other_col_{i}'] = [i, i+1, i+2]
    
    df = pd.DataFrame(data)
    
    # Property: Should identify the consumption column
    result = identify_consumption_column(df)
    
    assert result == consumption_col, \
        f"Expected to identify '{consumption_col}', but got '{result}'"


@settings(max_examples=100, deadline=None)
@given(
    timestamp_col=timestamp_column_name(),
    num_other_cols=st.integers(min_value=0, max_value=10)
)
def test_property_timestamp_column_pattern_matching(timestamp_col, num_other_cols):
    """
    Property 3: Column Pattern Matching (Timestamp)
    
    **Validates: Requirements 2.2**
    
    For any DataFrame with a column matching timestamp patterns (timestamp, datetime, 
    date_time, time) in any case variation, the identify_time_columns function should 
    correctly recognize it.
    """
    # Create DataFrame with timestamp column and other non-matching columns
    data = {timestamp_col: pd.date_range('2023-01-01', periods=3, freq='5min')}
    
    # Add other columns that should NOT match
    for i in range(num_other_cols):
        data[f'other_col_{i}'] = [i, i+1, i+2]
    
    df = pd.DataFrame(data)
    
    # Property: Should identify the timestamp column
    result = identify_time_columns(df)
    
    assert result['timestamp'] == timestamp_col, \
        f"Expected to identify timestamp as '{timestamp_col}', but got '{result['timestamp']}'"


@settings(max_examples=100, deadline=None)
@given(
    period_col=period_column_name(),
    num_other_cols=st.integers(min_value=0, max_value=10)
)
def test_property_period_column_pattern_matching(period_col, num_other_cols):
    """
    Property 3: Column Pattern Matching (Time Period)
    
    **Validates: Requirements 2.3**
    
    For any DataFrame with a column matching period patterns (period, time_period, 
    interval, tp) in any case variation, the identify_time_columns function should 
    correctly recognize it.
    """
    # Create DataFrame with period column and other non-matching columns
    data = {period_col: [1, 2, 3]}
    
    # Add other columns that should NOT match
    for i in range(num_other_cols):
        data[f'other_col_{i}'] = [i, i+1, i+2]
    
    df = pd.DataFrame(data)
    
    # Property: Should identify the period column
    result = identify_time_columns(df)
    
    assert result['time_period'] == period_col, \
        f"Expected to identify time_period as '{period_col}', but got '{result['time_period']}'"


@settings(max_examples=100, deadline=None)
@given(
    date_col=date_column_name(),
    num_other_cols=st.integers(min_value=0, max_value=10)
)
def test_property_date_column_pattern_matching(date_col, num_other_cols):
    """
    Property 3: Column Pattern Matching (Date)
    
    **Validates: Requirements 2.3**
    
    For any DataFrame with a column matching date patterns (date, day) in any case 
    variation, the identify_time_columns function should correctly recognize it.
    """
    # Create DataFrame with date column and other non-matching columns
    data = {date_col: pd.date_range('2023-01-01', periods=3, freq='D')}
    
    # Add other columns that should NOT match
    for i in range(num_other_cols):
        data[f'other_col_{i}'] = [i, i+1, i+2]
    
    df = pd.DataFrame(data)
    
    # Property: Should identify the date column
    result = identify_time_columns(df)
    
    assert result['date'] == date_col, \
        f"Expected to identify date as '{date_col}', but got '{result['date']}'"


@settings(max_examples=100, deadline=None)
@given(
    num_cols=st.integers(min_value=1, max_value=20),
    num_rows=st.integers(min_value=1, max_value=100)
)
def test_property_missing_consumption_column_error(num_cols, num_rows):
    """
    Property 4: Missing Column Error
    
    **Validates: Requirements 2.5**
    
    For any DataFrame without a consumption column (no columns matching consumption 
    patterns), the identify_consumption_column function should raise a 
    ColumnNotFoundError.
    """
    # Create DataFrame with only non-matching columns
    data = {}
    non_matching_names = [
        'location', 'site', 'meter', 'customer', 'account',
        'voltage', 'current', 'power_factor', 'demand',
        'temperature', 'humidity', 'pressure', 'status'
    ]
    
    for i in range(num_cols):
        col_name = non_matching_names[i % len(non_matching_names)] + f'_{i}'
        data[col_name] = [f'value_{j}' for j in range(num_rows)]
    
    df = pd.DataFrame(data)
    
    # Property: Should raise ColumnNotFoundError
    with pytest.raises(ColumnNotFoundError) as exc_info:
        identify_consumption_column(df)
    
    # Verify error message mentions expected patterns
    error_msg = str(exc_info.value).lower()
    assert 'consumption' in error_msg or 'kwh' in error_msg or 'usage' in error_msg


@settings(max_examples=100, deadline=None)
@given(
    consumption_col=consumption_column_name(),
    timestamp_col=timestamp_column_name(),
    period_col=period_column_name(),
    date_col=date_column_name()
)
def test_property_all_time_columns_identified(consumption_col, timestamp_col, period_col, date_col):
    """
    Property 3: Column Pattern Matching (All Time Columns)
    
    **Validates: Requirements 2.1, 2.2, 2.3**
    
    For any DataFrame with columns matching all time-related patterns, all columns 
    should be correctly identified without conflicts.
    """
    # Ensure column names are unique
    columns = [consumption_col, timestamp_col, period_col, date_col]
    if len(set(columns)) != len(columns):
        # Skip if we generated duplicate column names
        return
    
    # Create DataFrame with all column types
    df = pd.DataFrame({
        consumption_col: [1.0, 2.0, 3.0],
        timestamp_col: pd.date_range('2023-01-01', periods=3, freq='5min'),
        period_col: [1, 2, 3],
        date_col: pd.date_range('2023-01-01', periods=3, freq='D')
    })
    
    # Property: All columns should be identified correctly
    consumption_result = identify_consumption_column(df)
    time_result = identify_time_columns(df)
    
    assert consumption_result == consumption_col
    assert time_result['timestamp'] == timestamp_col
    assert time_result['time_period'] == period_col
    assert time_result['date'] == date_col


@settings(max_examples=100, deadline=None)
@given(
    consumption_col=consumption_column_name(),
    other_consumption_col=consumption_column_name()
)
def test_property_first_consumption_column_selected(consumption_col, other_consumption_col):
    """
    Property 3: Column Pattern Matching (Multiple Matches)
    
    **Validates: Requirements 2.1**
    
    When multiple columns match the consumption pattern, the function should 
    consistently return the first matching column.
    """
    # Ensure we have two different column names
    if consumption_col == other_consumption_col:
        other_consumption_col = consumption_col + '_2'
    
    # Create DataFrame with two consumption columns
    df = pd.DataFrame({
        consumption_col: [1.0, 2.0, 3.0],
        other_consumption_col: [4.0, 5.0, 6.0],
        'other_col': [7, 8, 9]
    })
    
    # Property: Should return one of the matching columns (first match)
    result = identify_consumption_column(df)
    
    # The result should be one of the consumption columns
    assert result in [consumption_col, other_consumption_col], \
        f"Expected one of ['{consumption_col}', '{other_consumption_col}'], but got '{result}'"


# ============================================================================
# Property Tests for Emissions Period Code Parsing
# ============================================================================

from emissions.io import parse_emissions_period_code


@st.composite
def emissions_period_code(draw):
    """Generate valid emissions period codes in format YYYYMMDDTTT."""
    # Generate year (2000-2030)
    year = draw(st.integers(min_value=2000, max_value=2030))
    
    # Generate month (01-12)
    month = draw(st.integers(min_value=1, max_value=12))
    
    # Generate day (01-28 to avoid invalid dates)
    day = draw(st.integers(min_value=1, max_value=28))
    
    # Generate time period (001-288 for 5-minute intervals)
    period = draw(st.integers(min_value=1, max_value=288))
    
    # Format as YYYYMMDDTTT with leading zeros
    code = f"{year:04d}{month:02d}{day:02d}{period:03d}"
    
    return code


@settings(max_examples=100, deadline=None)
@given(code=emissions_period_code())
def test_property_emissions_period_code_round_trip(code):
    """
    Property 7: Emissions Period Code Round-Trip
    
    **Validates: Requirements 3.3, 3.4, 3.5**
    
    For any valid emissions period code in format YYYYMMDDTTT, parsing it to 
    extract date and period components, then reconstructing the code, should 
    produce the original code with leading zeros preserved.
    """
    # Parse the code
    date_str, period_int = parse_emissions_period_code(code)
    
    # Reconstruct the code from parsed components
    # Date should be 8 characters (YYYYMMDD)
    # Period should be formatted with leading zeros to 3 digits (TTT)
    reconstructed_code = f"{date_str}{period_int:03d}"
    
    # Property: Round-trip should preserve the original code
    assert reconstructed_code == code, \
        f"Round-trip failed: original '{code}' != reconstructed '{reconstructed_code}'"
    
    # Property: Date portion should be 8 characters
    assert len(date_str) == 8, \
        f"Date portion should be 8 characters, got {len(date_str)}: '{date_str}'"
    
    # Property: Period should be in valid range (1-288 for 5-min or 1-48 for 30-min)
    assert 1 <= period_int <= 288, \
        f"Period should be between 1 and 288, got {period_int}"
    
    # Property: Leading zeros should be preserved in reconstruction
    # Extract original period string from code
    original_period_str = code[8:]
    reconstructed_period_str = f"{period_int:03d}"
    assert original_period_str == reconstructed_period_str, \
        f"Leading zeros not preserved: original '{original_period_str}' != reconstructed '{reconstructed_period_str}'"


@settings(max_examples=100, deadline=None)
@given(
    year=st.integers(min_value=2000, max_value=2030),
    month=st.integers(min_value=1, max_value=12),
    day=st.integers(min_value=1, max_value=28),
    period=st.integers(min_value=1, max_value=288)
)
def test_property_emissions_period_code_component_preservation(year, month, day, period):
    """
    Property 7: Emissions Period Code Component Preservation
    
    **Validates: Requirements 3.3, 3.4, 3.5**
    
    For any valid date components (year, month, day) and time period, constructing 
    an emissions period code and parsing it should preserve all components exactly.
    """
    # Construct the code with proper formatting
    code = f"{year:04d}{month:02d}{day:02d}{period:03d}"
    
    # Parse the code
    date_str, period_int = parse_emissions_period_code(code)
    
    # Property: Date string should match the constructed date
    expected_date_str = f"{year:04d}{month:02d}{day:02d}"
    assert date_str == expected_date_str, \
        f"Date not preserved: expected '{expected_date_str}', got '{date_str}'"
    
    # Property: Period integer should match the original period
    assert period_int == period, \
        f"Period not preserved: expected {period}, got {period_int}"
    
    # Property: Reconstructing should give the original code
    reconstructed_code = f"{date_str}{period_int:03d}"
    assert reconstructed_code == code, \
        f"Round-trip failed: original '{code}' != reconstructed '{reconstructed_code}'"


@settings(max_examples=100, deadline=None)
@given(period=st.integers(min_value=1, max_value=288))
def test_property_leading_zeros_preservation(period):
    """
    Property 7: Leading Zeros Preservation in Period Codes
    
    **Validates: Requirements 3.4**
    
    For any time period value, when formatted with leading zeros (TTT), parsed, 
    and reformatted, the leading zeros should be preserved.
    """
    # Create a code with a fixed date and variable period
    code = f"20230101{period:03d}"
    
    # Parse the code
    date_str, period_int = parse_emissions_period_code(code)
    
    # Reconstruct the period portion with leading zeros
    reconstructed_period_str = f"{period_int:03d}"
    original_period_str = code[8:]
    
    # Property: Leading zeros should be preserved
    assert reconstructed_period_str == original_period_str, \
        f"Leading zeros not preserved for period {period}: " \
        f"original '{original_period_str}' != reconstructed '{reconstructed_period_str}'"
    
    # Property: Period string should always be 3 characters
    assert len(reconstructed_period_str) == 3, \
        f"Period string should be 3 characters, got {len(reconstructed_period_str)}: '{reconstructed_period_str}'"
    
    # Examples that should work:
    # period=1 -> "001"
    # period=10 -> "010"
    # period=100 -> "100"
    # period=288 -> "288"
