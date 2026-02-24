"""
Tests for agent tool formatting functions.

This module tests the formatting functions in agents/agent_tools.py that standardize
tool results for AWS Bedrock agent consumption. These functions ensure consistent
structure for DataFrames, success results, error results, validation results, and
calculation results.
"""

import pytest
import pandas as pd
from agents.agent_tools import (
    format_dataframe_result,
    format_success_result,
    format_error_result,
    format_validation_result,
    format_calculation_result
)


# ============================================================================
# Test format_dataframe_result
# ============================================================================

def test_format_dataframe_result_basic():
    """Test basic DataFrame formatting with default parameters."""
    df = pd.DataFrame({
        'a': [1, 2, 3],
        'b': [4.0, 5.0, 6.0],
        'c': ['x', 'y', 'z']
    })
    
    result = format_dataframe_result(df)
    
    assert result['type'] == 'dataframe'
    assert 'metadata' in result
    assert 'full_data' in result
    assert 'preview' in result
    
    # Check metadata
    metadata = result['metadata']
    assert metadata['row_count'] == 3
    assert metadata['column_count'] == 3
    assert metadata['columns'] == ['a', 'b', 'c']
    assert metadata['shape'] == (3, 3)
    assert 'dtypes' in metadata
    assert 'memory_usage_bytes' in metadata


def test_format_dataframe_result_with_preview():
    """Test DataFrame formatting with preview enabled."""
    df = pd.DataFrame({
        'x': range(10),
        'y': range(10, 20)
    })
    
    result = format_dataframe_result(df, include_preview=True, preview_rows=3)
    
    assert 'preview' in result
    assert result['preview_row_count'] == 3
    assert len(result['preview']) == 3
    assert result['preview'][0] == {'x': 0, 'y': 10}
    assert result['preview'][2] == {'x': 2, 'y': 12}


def test_format_dataframe_result_without_preview():
    """Test DataFrame formatting with preview disabled."""
    df = pd.DataFrame({'a': [1, 2, 3]})
    
    result = format_dataframe_result(df, include_preview=False)
    
    assert 'preview' not in result
    assert 'preview_row_count' not in result
    assert 'full_data' in result


def test_format_dataframe_result_empty_dataframe():
    """Test formatting an empty DataFrame."""
    df = pd.DataFrame()
    
    result = format_dataframe_result(df)
    
    assert result['metadata']['row_count'] == 0
    assert result['metadata']['column_count'] == 0
    assert result['metadata']['columns'] == []
    assert 'preview' not in result  # No preview for empty DataFrame


def test_format_dataframe_result_with_index_name():
    """Test DataFrame formatting with named index."""
    df = pd.DataFrame({'a': [1, 2, 3]})
    df.index.name = 'my_index'
    
    result = format_dataframe_result(df)
    
    assert result['metadata']['index_name'] == 'my_index'


def test_format_dataframe_result_without_index_name():
    """Test DataFrame formatting without named index."""
    df = pd.DataFrame({'a': [1, 2, 3]})
    
    result = format_dataframe_result(df)
    
    assert result['metadata']['index_name'] is None


def test_format_dataframe_result_dtypes():
    """Test that dtypes are correctly captured."""
    df = pd.DataFrame({
        'int_col': [1, 2, 3],
        'float_col': [1.0, 2.0, 3.0],
        'str_col': ['a', 'b', 'c'],
        'bool_col': [True, False, True]
    })
    
    result = format_dataframe_result(df)
    
    dtypes = result['metadata']['dtypes']
    assert 'int_col' in dtypes
    assert 'float_col' in dtypes
    assert 'str_col' in dtypes
    assert 'bool_col' in dtypes
    assert 'int' in dtypes['int_col']
    assert 'float' in dtypes['float_col']


def test_format_dataframe_result_large_preview():
    """Test that preview is limited to available rows."""
    df = pd.DataFrame({'a': [1, 2]})
    
    result = format_dataframe_result(df, include_preview=True, preview_rows=10)
    
    assert result['preview_row_count'] == 2  # Only 2 rows available
    assert len(result['preview']) == 2


# ============================================================================
# Test format_success_result
# ============================================================================

def test_format_success_result_with_string():
    """Test success result formatting with string result."""
    result = format_success_result(
        result="consumption_kwh",
        message="Successfully identified consumption column"
    )
    
    assert result['success'] is True
    assert result['message'] == "Successfully identified consumption column"
    assert 'result' in result
    assert result['result']['type'] == 'str'
    assert result['result']['value'] == "consumption_kwh"


def test_format_success_result_with_dict():
    """Test success result formatting with dictionary result."""
    result = format_success_result(
        result={'timestamp': 'datetime', 'period': None},
        message="Identified time columns"
    )
    
    assert result['success'] is True
    assert result['result']['type'] == 'dict'
    assert result['result']['value'] == {'timestamp': 'datetime', 'period': None}


def test_format_success_result_with_list():
    """Test success result formatting with list result."""
    result = format_success_result(
        result=['col1', 'col2', 'col3'],
        message="Found columns"
    )
    
    assert result['success'] is True
    assert result['result']['type'] == 'list'
    assert result['result']['value'] == ['col1', 'col2', 'col3']


def test_format_success_result_with_number():
    """Test success result formatting with numeric result."""
    result = format_success_result(
        result=42,
        message="Calculation complete"
    )
    
    assert result['success'] is True
    assert result['result']['type'] == 'int'
    assert result['result']['value'] == 42


def test_format_success_result_with_dataframe():
    """Test success result formatting with DataFrame result."""
    df = pd.DataFrame({'a': [1, 2, 3]})
    
    result = format_success_result(
        result=df,
        message="Data loaded successfully"
    )
    
    assert result['success'] is True
    assert result['result']['type'] == 'dataframe'
    assert 'metadata' in result['result']
    assert result['result']['metadata']['row_count'] == 3


def test_format_success_result_with_metadata():
    """Test success result formatting with additional metadata."""
    result = format_success_result(
        result="consumption_kwh",
        message="Column identified",
        metadata={'pattern_matched': 'kwh', 'confidence': 0.95}
    )
    
    assert result['success'] is True
    assert 'metadata' in result
    assert result['metadata']['pattern_matched'] == 'kwh'
    assert result['metadata']['confidence'] == 0.95


def test_format_success_result_without_metadata():
    """Test success result formatting without metadata."""
    result = format_success_result(
        result="test",
        message="Success"
    )
    
    assert result['success'] is True
    assert 'metadata' not in result


def test_format_success_result_with_none():
    """Test success result formatting with None result."""
    result = format_success_result(
        result=None,
        message="Operation completed"
    )
    
    assert result['success'] is True
    assert result['result']['type'] == 'NoneType'
    assert result['result']['value'] is None


def test_format_success_result_with_boolean():
    """Test success result formatting with boolean result."""
    result = format_success_result(
        result=True,
        message="Validation passed"
    )
    
    assert result['success'] is True
    assert result['result']['type'] == 'bool'
    assert result['result']['value'] is True


# ============================================================================
# Test format_error_result
# ============================================================================

def test_format_error_result_basic():
    """Test basic error result formatting."""
    error = ValueError("Column not found")
    
    result = format_error_result(
        error=error,
        context="Identifying consumption column"
    )
    
    assert result['success'] is False
    assert result['error'] == "Column not found"
    assert result['error_type'] == 'ValueError'
    assert result['context'] == "Identifying consumption column"
    assert result['message'] == "Column not found"
    assert 'technical_details' in result


def test_format_error_result_with_user_message():
    """Test error result formatting with custom user message."""
    error = ValueError("Column 'consumption' not found")
    
    result = format_error_result(
        error=error,
        context="Identifying consumption column",
        user_message="Could not find consumption column in the data"
    )
    
    assert result['success'] is False
    assert result['message'] == "Could not find consumption column in the data"
    assert result['error'] == "Column 'consumption' not found"


def test_format_error_result_with_recovery_suggestions():
    """Test error result formatting with recovery suggestions."""
    error = ValueError("Column not found")
    
    result = format_error_result(
        error=error,
        context="Identifying consumption column",
        recovery_suggestions=[
            "Check that your file contains a column with consumption data",
            "Column names should include: consumption, kwh, usage, or energy"
        ]
    )
    
    assert result['success'] is False
    assert 'recovery_suggestions' in result
    assert len(result['recovery_suggestions']) == 2
    assert "consumption data" in result['recovery_suggestions'][0]


def test_format_error_result_without_recovery_suggestions():
    """Test error result formatting without recovery suggestions."""
    error = ValueError("Error occurred")
    
    result = format_error_result(
        error=error,
        context="Processing data"
    )
    
    assert result['success'] is False
    assert 'recovery_suggestions' not in result


def test_format_error_result_technical_details():
    """Test that technical details are properly captured."""
    error = FileNotFoundError("File not found: data.csv")
    
    result = format_error_result(
        error=error,
        context="Loading file"
    )
    
    technical = result['technical_details']
    assert technical['exception_class'] == 'FileNotFoundError'
    assert technical['exception_message'] == "File not found: data.csv"
    assert technical['operation'] == "Loading file"


def test_format_error_result_different_exception_types():
    """Test error formatting with different exception types."""
    exceptions = [
        (ValueError("value error"), 'ValueError'),
        (TypeError("type error"), 'TypeError'),
        (KeyError("key error"), 'KeyError'),
        (RuntimeError("runtime error"), 'RuntimeError')
    ]
    
    for error, expected_type in exceptions:
        result = format_error_result(error=error, context="Test")
        assert result['error_type'] == expected_type


# ============================================================================
# Test format_validation_result
# ============================================================================

def test_format_validation_result_valid_no_issues():
    """Test validation result with no warnings or errors."""
    result = format_validation_result(
        is_valid=True,
        warnings=[],
        errors=[]
    )
    
    assert result['success'] is True
    assert result['is_valid'] is True
    assert result['warnings'] == []
    assert result['errors'] == []
    assert result['warning_count'] == 0
    assert result['error_count'] == 0
    assert result['message'] == "Validation passed with no issues"


def test_format_validation_result_valid_with_warnings():
    """Test validation result that is valid but has warnings."""
    result = format_validation_result(
        is_valid=True,
        warnings=["Found 3 missing periods", "Found 2 negative values"],
        errors=[]
    )
    
    assert result['success'] is True
    assert result['is_valid'] is True
    assert result['warning_count'] == 2
    assert result['error_count'] == 0
    assert "2 warning(s)" in result['message']
    assert len(result['warnings']) == 2


def test_format_validation_result_invalid_with_errors():
    """Test validation result that is invalid with errors."""
    result = format_validation_result(
        is_valid=False,
        warnings=[],
        errors=["Missing required column: timestamp", "Invalid date format"]
    )
    
    assert result['success'] is True  # Validation completed successfully
    assert result['is_valid'] is False
    assert result['warning_count'] == 0
    assert result['error_count'] == 2
    assert "2 error(s)" in result['message']
    assert len(result['errors']) == 2


def test_format_validation_result_invalid_with_warnings_and_errors():
    """Test validation result with both warnings and errors."""
    result = format_validation_result(
        is_valid=False,
        warnings=["Data quality issue"],
        errors=["Critical error 1", "Critical error 2"]
    )
    
    assert result['success'] is True
    assert result['is_valid'] is False
    assert result['warning_count'] == 1
    assert result['error_count'] == 2
    assert "2 error(s)" in result['message']
    assert "1 warning(s)" in result['message']


def test_format_validation_result_with_metadata():
    """Test validation result with additional metadata."""
    result = format_validation_result(
        is_valid=True,
        warnings=["Found 3 missing periods"],
        errors=[],
        metadata={'missing_count': 3, 'total_records': 288}
    )
    
    assert result['success'] is True
    assert 'metadata' in result
    assert result['metadata']['missing_count'] == 3
    assert result['metadata']['total_records'] == 288


def test_format_validation_result_without_metadata():
    """Test validation result without metadata."""
    result = format_validation_result(
        is_valid=True,
        warnings=[],
        errors=[]
    )
    
    assert result['success'] is True
    assert 'metadata' not in result


def test_format_validation_result_message_variations():
    """Test that validation messages are appropriate for different scenarios."""
    # No issues
    result1 = format_validation_result(True, [], [])
    assert "no issues" in result1['message']
    
    # Warnings only
    result2 = format_validation_result(True, ["warning"], [])
    assert "1 warning(s)" in result2['message']
    
    # Errors only
    result3 = format_validation_result(False, [], ["error"])
    assert "1 error(s)" in result3['message']
    assert "warning" not in result3['message']
    
    # Both warnings and errors
    result4 = format_validation_result(False, ["w1", "w2"], ["e1"])
    assert "1 error(s)" in result4['message']
    assert "2 warning(s)" in result4['message']


# ============================================================================
# Test format_calculation_result
# ============================================================================

def test_format_calculation_result_basic():
    """Test basic calculation result formatting."""
    result = format_calculation_result(
        result_value=123.456,
        unit="tonnes CO2-e",
        calculation_details={
            'method': 'interval-based',
            'total_consumption_kwh': 50000
        }
    )
    
    assert result['success'] is True
    assert result['result'] == 123.456
    assert result['unit'] == "tonnes CO2-e"
    assert result['formatted_value'] == "123.46 tonnes CO2-e"
    assert 'calculation_details' in result
    assert result['calculation_details']['method'] == 'interval-based'


def test_format_calculation_result_with_metadata():
    """Test calculation result with additional metadata."""
    result = format_calculation_result(
        result_value=100.0,
        unit="kWh",
        calculation_details={'method': 'sum'},
        metadata={'matched_records': 288, 'unmatched_records': 0}
    )
    
    assert result['success'] is True
    assert 'metadata' in result
    assert result['metadata']['matched_records'] == 288
    assert result['metadata']['unmatched_records'] == 0


def test_format_calculation_result_without_metadata():
    """Test calculation result without metadata."""
    result = format_calculation_result(
        result_value=50.0,
        unit="kg",
        calculation_details={'method': 'average'}
    )
    
    assert result['success'] is True
    assert 'metadata' not in result


def test_format_calculation_result_formatting():
    """Test that numerical values are formatted correctly."""
    test_cases = [
        (123.456, "123.46"),
        (0.001, "0.00"),
        (1000.999, "1001.00"),
        (42, "42.00"),
        (0, "0.00")
    ]
    
    for value, expected_formatted in test_cases:
        result = format_calculation_result(
            result_value=value,
            unit="units",
            calculation_details={}
        )
        assert result['formatted_value'] == f"{expected_formatted} units"


def test_format_calculation_result_message():
    """Test that calculation result includes appropriate message."""
    result = format_calculation_result(
        result_value=75.5,
        unit="tonnes CO2-e",
        calculation_details={'method': 'test'}
    )
    
    assert 'message' in result
    assert "75.50 tonnes CO2-e" in result['message']
    assert "Calculation completed" in result['message']


def test_format_calculation_result_detailed_calculation_info():
    """Test calculation result with comprehensive calculation details."""
    result = format_calculation_result(
        result_value=250.75,
        unit="tonnes CO2-e",
        calculation_details={
            'method': 'interval-based',
            'total_consumption_kwh': 100000,
            'average_factor_g_per_kwh': 750.5,
            'matched_intervals': 288,
            'date_range': '2023-01-01 to 2023-01-31'
        }
    )
    
    assert result['success'] is True
    details = result['calculation_details']
    assert details['method'] == 'interval-based'
    assert details['total_consumption_kwh'] == 100000
    assert details['average_factor_g_per_kwh'] == 750.5
    assert details['matched_intervals'] == 288
    assert details['date_range'] == '2023-01-01 to 2023-01-31'


def test_format_calculation_result_zero_value():
    """Test calculation result with zero value."""
    result = format_calculation_result(
        result_value=0.0,
        unit="tonnes CO2-e",
        calculation_details={'method': 'test'}
    )
    
    assert result['success'] is True
    assert result['result'] == 0.0
    assert result['formatted_value'] == "0.00 tonnes CO2-e"


def test_format_calculation_result_large_value():
    """Test calculation result with large value."""
    result = format_calculation_result(
        result_value=1234567.89,
        unit="kWh",
        calculation_details={'method': 'sum'}
    )
    
    assert result['success'] is True
    assert result['result'] == 1234567.89
    assert result['formatted_value'] == "1234567.89 kWh"


def test_format_calculation_result_negative_value():
    """Test calculation result with negative value."""
    result = format_calculation_result(
        result_value=-50.25,
        unit="units",
        calculation_details={'method': 'difference'}
    )
    
    assert result['success'] is True
    assert result['result'] == -50.25
    assert result['formatted_value'] == "-50.25 units"


# ============================================================================
# Integration Tests
# ============================================================================

def test_formatting_functions_consistency():
    """Test that all formatting functions follow consistent structure."""
    # All success-type results should have 'success' key
    df_result = format_dataframe_result(pd.DataFrame({'a': [1]}))
    success_result = format_success_result("test", "message")
    validation_result = format_validation_result(True, [], [])
    calc_result = format_calculation_result(10.0, "units", {})
    
    # DataFrame result doesn't have 'success' key (it's a component)
    assert 'type' in df_result
    
    # These should have 'success' key
    assert success_result['success'] is True
    assert validation_result['success'] is True
    assert calc_result['success'] is True


def test_error_result_structure():
    """Test that error results have consistent structure."""
    error = ValueError("test error")
    result = format_error_result(error, "test context")
    
    # Required fields
    assert 'success' in result
    assert 'error' in result
    assert 'error_type' in result
    assert 'context' in result
    assert 'message' in result
    assert 'technical_details' in result
    
    # Success should be False
    assert result['success'] is False


def test_dataframe_result_in_success_result():
    """Test that DataFrame results are properly nested in success results."""
    df = pd.DataFrame({'a': [1, 2, 3]})
    
    result = format_success_result(df, "Data loaded")
    
    assert result['success'] is True
    assert result['result']['type'] == 'dataframe'
    assert 'metadata' in result['result']
    assert result['result']['metadata']['row_count'] == 3
