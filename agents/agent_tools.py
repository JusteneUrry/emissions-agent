"""
Agent tool wrappers for AWS Bedrock integration.

This module exposes existing emissions modules (io.py, interval.py, factors.py, calc.py, viz.py)
as Bedrock agent tools with proper error handling and JSON serialization.
"""

from typing import Any, Dict, Optional
import pandas as pd
from streamlit.runtime.uploaded_file_manager import UploadedFile

from emissions.io import (
    load_consumption_file,
    identify_consumption_column,
    identify_time_columns,
    parse_emissions_period_code,
    UnsupportedFileFormatError,
    ColumnNotFoundError
)
from emissions.serialization import serialize_tool_result, dataframe_to_json


# ============================================================================
# File I/O Tool Wrappers
# ============================================================================

def tool_load_consumption_file(uploaded_file: UploadedFile) -> Dict[str, Any]:
    """
    Agent tool wrapper for load_consumption_file.
    
    Loads electricity consumption data from a CSV or Excel file and returns
    a JSON-serializable result suitable for AWS Bedrock agent tools.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Dictionary with keys:
        - 'success': Boolean indicating if operation succeeded
        - 'result': Serialized DataFrame (if success=True)
        - 'error': Error message (if success=False)
        - 'error_type': Type of error (if success=False)
        
    Example:
        >>> result = tool_load_consumption_file(uploaded_file)
        >>> if result['success']:
        ...     df_data = result['result']['value']
        ...     print(f"Loaded {df_data['metadata']['row_count']} rows")
    """
    try:
        df = load_consumption_file(uploaded_file)
        return {
            'success': True,
            'result': serialize_tool_result(df),
            'message': f"Successfully loaded {len(df)} rows from {uploaded_file.name}"
        }
    except UnsupportedFileFormatError as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': 'UnsupportedFileFormatError',
            'message': 'File format not supported. Please upload CSV or Excel file.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': f'Failed to load file: {str(e)}'
        }


def tool_identify_consumption_column(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Agent tool wrapper for identify_consumption_column.
    
    Identifies the consumption column in a DataFrame using pattern matching.
    
    Args:
        df: DataFrame with consumption data
        
    Returns:
        Dictionary with keys:
        - 'success': Boolean indicating if operation succeeded
        - 'result': Column name (if success=True)
        - 'error': Error message (if success=False)
        - 'error_type': Type of error (if success=False)
        
    Example:
        >>> result = tool_identify_consumption_column(df)
        >>> if result['success']:
        ...     col_name = result['result']
        ...     print(f"Consumption column: {col_name}")
    """
    try:
        column_name = identify_consumption_column(df)
        return {
            'success': True,
            'result': column_name,
            'message': f"Identified consumption column: '{column_name}'"
        }
    except ColumnNotFoundError as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': 'ColumnNotFoundError',
            'message': 'No consumption column found. Expected column names containing: consumption, kwh, usage, or energy.'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': f'Failed to identify consumption column: {str(e)}'
        }


def tool_identify_time_columns(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Agent tool wrapper for identify_time_columns.
    
    Identifies timestamp, time period, and date columns in a DataFrame.
    
    Args:
        df: DataFrame with consumption data
        
    Returns:
        Dictionary with keys:
        - 'success': Boolean indicating if operation succeeded
        - 'result': Dict with keys 'timestamp', 'time_period', 'date' (if success=True)
        - 'error': Error message (if success=False)
        - 'error_type': Type of error (if success=False)
        
    Example:
        >>> result = tool_identify_time_columns(df)
        >>> if result['success']:
        ...     time_cols = result['result']
        ...     print(f"Timestamp column: {time_cols['timestamp']}")
        ...     print(f"Time period column: {time_cols['time_period']}")
    """
    try:
        time_columns = identify_time_columns(df)
        
        # Create a summary message
        found_cols = [k for k, v in time_columns.items() if v is not None]
        if found_cols:
            message = f"Identified time columns: {', '.join(f'{k}={v}' for k, v in time_columns.items() if v is not None)}"
        else:
            message = "No time columns found"
        
        return {
            'success': True,
            'result': time_columns,
            'message': message
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': f'Failed to identify time columns: {str(e)}'
        }


def tool_parse_emissions_period_code(code: str) -> Dict[str, Any]:
    """
    Agent tool wrapper for parse_emissions_period_code.
    
    Parses a combined YYYYMMDDTTT emissions period code into date and period components.
    
    Args:
        code: String in format YYYYMMDDTTT (e.g., "20230101001")
        
    Returns:
        Dictionary with keys:
        - 'success': Boolean indicating if operation succeeded
        - 'result': Dict with keys 'date' and 'period' (if success=True)
        - 'error': Error message (if success=False)
        - 'error_type': Type of error (if success=False)
        
    Example:
        >>> result = tool_parse_emissions_period_code("20230101001")
        >>> if result['success']:
        ...     parsed = result['result']
        ...     print(f"Date: {parsed['date']}, Period: {parsed['period']}")
    """
    try:
        date_str, period_int = parse_emissions_period_code(code)
        return {
            'success': True,
            'result': {
                'date': date_str,
                'period': period_int
            },
            'message': f"Parsed code '{code}' into date={date_str}, period={period_int}"
        }
    except ValueError as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': 'ValueError',
            'message': f'Invalid emissions period code format: {str(e)}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': f'Failed to parse emissions period code: {str(e)}'
        }


# ============================================================================
# Tool Result Formatting Functions
# ============================================================================

def format_dataframe_result(
    df: pd.DataFrame,
    include_preview: bool = True,
    preview_rows: int = 5
) -> Dict[str, Any]:
    """
    Format a DataFrame result with comprehensive metadata for Bedrock consumption.
    
    This function provides rich metadata about the DataFrame structure, including
    row counts, column names, data types, and an optional data preview. This helps
    the Bedrock agent understand the data structure without processing the entire dataset.
    
    Args:
        df: pandas DataFrame to format
        include_preview: Whether to include a preview of the first few rows
        preview_rows: Number of rows to include in preview (default: 5)
        
    Returns:
        Dictionary with keys:
        - 'type': 'dataframe'
        - 'metadata': Dict with structure information
        - 'preview': Optional list of first N rows
        - 'full_data': Complete serialized DataFrame
        
    Example:
        >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4.0, 5.0, 6.0]})
        >>> result = format_dataframe_result(df, include_preview=True, preview_rows=2)
        >>> result['metadata']['row_count']
        3
        >>> len(result['preview'])
        2
    """
    serialized = dataframe_to_json(df)
    
    result = {
        'type': 'dataframe',
        'metadata': {
            'row_count': len(df),
            'column_count': len(df.columns),
            'columns': list(df.columns),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'index_name': df.index.name if df.index.name else None,
            'memory_usage_bytes': int(df.memory_usage(deep=True).sum()),
            'shape': df.shape
        },
        'full_data': serialized
    }
    
    # Add preview if requested
    if include_preview and len(df) > 0:
        preview_df = df.head(preview_rows)
        result['preview'] = preview_df.to_dict(orient='records')
        result['preview_row_count'] = len(preview_df)
    
    return result


def format_success_result(
    result: Any,
    message: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a successful tool execution result for Bedrock consumption.
    
    This function creates a standardized success response that includes the result,
    a human-readable message, and optional metadata. The result is automatically
    serialized based on its type (DataFrame, dict, list, primitive).
    
    Args:
        result: The tool execution result (any type)
        message: Human-readable success message
        metadata: Optional additional metadata about the operation
        
    Returns:
        Dictionary with keys:
        - 'success': True
        - 'result': Serialized result with type information
        - 'message': Human-readable message
        - 'metadata': Optional metadata dict
        
    Example:
        >>> result = format_success_result(
        ...     result={'column': 'consumption_kwh'},
        ...     message="Successfully identified consumption column",
        ...     metadata={'pattern_matched': 'kwh'}
        ... )
        >>> result['success']
        True
    """
    formatted = {
        'success': True,
        'message': message
    }
    
    # Handle DataFrame with rich formatting
    if isinstance(result, pd.DataFrame):
        formatted['result'] = format_dataframe_result(result)
    else:
        # Use generic serialization for other types
        formatted['result'] = serialize_tool_result(result)
    
    # Add metadata if provided
    if metadata:
        formatted['metadata'] = metadata
    
    return formatted


def format_error_result(
    error: Exception,
    context: str,
    user_message: Optional[str] = None,
    recovery_suggestions: Optional[list[str]] = None
) -> Dict[str, Any]:
    """
    Format an error result with structured information for Bedrock consumption.
    
    This function creates a standardized error response that includes the error type,
    message, context, and optional recovery suggestions. This helps the Bedrock agent
    understand what went wrong and potentially recover or provide helpful guidance to the user.
    
    Args:
        error: The exception that occurred
        context: Description of what operation was being performed
        user_message: Optional user-friendly error message (if None, uses str(error))
        recovery_suggestions: Optional list of suggestions for recovering from the error
        
    Returns:
        Dictionary with keys:
        - 'success': False
        - 'error': Error message string
        - 'error_type': Exception class name
        - 'context': Description of the operation
        - 'message': User-friendly message
        - 'recovery_suggestions': Optional list of recovery steps
        - 'technical_details': Full exception details
        
    Example:
        >>> try:
        ...     raise ValueError("Column 'consumption' not found")
        ... except ValueError as e:
        ...     result = format_error_result(
        ...         error=e,
        ...         context="Identifying consumption column",
        ...         user_message="Could not find consumption column in the data",
        ...         recovery_suggestions=[
        ...             "Check that your file contains a column with consumption data",
        ...             "Column names should include: consumption, kwh, usage, or energy"
        ...         ]
        ...     )
        >>> result['success']
        False
        >>> result['error_type']
        'ValueError'
    """
    error_type = type(error).__name__
    error_message = str(error)
    
    formatted = {
        'success': False,
        'error': error_message,
        'error_type': error_type,
        'context': context,
        'message': user_message if user_message else error_message,
        'technical_details': {
            'exception_class': error_type,
            'exception_message': error_message,
            'operation': context
        }
    }
    
    # Add recovery suggestions if provided
    if recovery_suggestions:
        formatted['recovery_suggestions'] = recovery_suggestions
    
    return formatted


def format_validation_result(
    is_valid: bool,
    warnings: list[str],
    errors: list[str],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a data validation result for Bedrock consumption.
    
    This function creates a structured validation response that distinguishes between
    warnings (issues that don't prevent processing) and errors (issues that block processing).
    This helps the Bedrock agent decide whether to proceed with the workflow or request
    user intervention.
    
    Args:
        is_valid: Whether the data passed validation (no blocking errors)
        warnings: List of warning messages (non-blocking issues)
        errors: List of error messages (blocking issues)
        metadata: Optional metadata about the validation (e.g., counts, statistics)
        
    Returns:
        Dictionary with keys:
        - 'success': True (validation completed, even if data invalid)
        - 'is_valid': Boolean indicating if data is valid
        - 'warnings': List of warning messages
        - 'errors': List of error messages
        - 'warning_count': Number of warnings
        - 'error_count': Number of errors
        - 'metadata': Optional validation metadata
        - 'message': Summary message
        
    Example:
        >>> result = format_validation_result(
        ...     is_valid=True,
        ...     warnings=["Found 3 missing periods", "Found 2 negative values"],
        ...     errors=[],
        ...     metadata={'missing_count': 3, 'negative_count': 2}
        ... )
        >>> result['is_valid']
        True
        >>> result['warning_count']
        2
    """
    warning_count = len(warnings)
    error_count = len(errors)
    
    # Create summary message
    if is_valid and warning_count == 0:
        message = "Validation passed with no issues"
    elif is_valid and warning_count > 0:
        message = f"Validation passed with {warning_count} warning(s)"
    else:
        message = f"Validation failed with {error_count} error(s)"
        if warning_count > 0:
            message += f" and {warning_count} warning(s)"
    
    formatted = {
        'success': True,  # Validation completed successfully
        'is_valid': is_valid,
        'warnings': warnings,
        'errors': errors,
        'warning_count': warning_count,
        'error_count': error_count,
        'message': message
    }
    
    # Add metadata if provided
    if metadata:
        formatted['metadata'] = metadata
    
    return formatted


def format_calculation_result(
    result_value: float,
    unit: str,
    calculation_details: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a numerical calculation result for Bedrock consumption.
    
    This function creates a structured response for numerical calculations (e.g., emissions totals)
    that includes the value, unit, calculation details, and optional metadata. This helps the
    Bedrock agent understand and explain the calculation to users.
    
    Args:
        result_value: The calculated numerical result
        unit: Unit of measurement (e.g., "tonnes CO2-e", "kWh")
        calculation_details: Dict with calculation methodology and inputs
        metadata: Optional additional metadata
        
    Returns:
        Dictionary with keys:
        - 'success': True
        - 'result': The numerical value
        - 'unit': Unit of measurement
        - 'formatted_value': Human-readable formatted string
        - 'calculation_details': Dict with methodology info
        - 'metadata': Optional metadata
        
    Example:
        >>> result = format_calculation_result(
        ...     result_value=123.456,
        ...     unit="tonnes CO2-e",
        ...     calculation_details={
        ...         'method': 'interval-based',
        ...         'total_consumption_kwh': 50000,
        ...         'average_factor_g_per_kwh': 750.5
        ...     },
        ...     metadata={'matched_records': 288, 'unmatched_records': 0}
        ... )
        >>> result['formatted_value']
        '123.46 tonnes CO2-e'
    """
    # Format the value for display (2 decimal places)
    formatted_value = f"{result_value:.2f} {unit}"
    
    formatted = {
        'success': True,
        'result': result_value,
        'unit': unit,
        'formatted_value': formatted_value,
        'calculation_details': calculation_details,
        'message': f"Calculation completed: {formatted_value}"
    }
    
    # Add metadata if provided
    if metadata:
        formatted['metadata'] = metadata
    
    return formatted


# ============================================================================
# Tool Schema Definitions for AWS Bedrock
# ============================================================================

TOOL_SCHEMAS = {
    'load_consumption_file': {
        'name': 'load_consumption_file',
        'description': (
            'Load electricity consumption data from a CSV or Excel file. '
            'Use this as the first step when a user uploads a file. '
            'Returns a DataFrame with the raw consumption data.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'file_path': {
                    'type': 'string',
                    'description': 'Path to the uploaded CSV or Excel file'
                }
            },
            'required': ['file_path']
        }
    },
    
    'identify_consumption_column': {
        'name': 'identify_consumption_column',
        'description': (
            'Identify the consumption column in a DataFrame using pattern matching. '
            'Searches for columns matching: consumption, kwh, usage, energy (case-insensitive). '
            'Use this after loading a file to determine which column contains consumption data.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'dataframe': {
                    'type': 'object',
                    'description': 'DataFrame with consumption data (serialized)'
                }
            },
            'required': ['dataframe']
        }
    },
    
    'identify_time_columns': {
        'name': 'identify_time_columns',
        'description': (
            'Identify timestamp, time period, and date columns in a DataFrame. '
            'Returns a dictionary with keys: timestamp, time_period, date. '
            'Values are column names or None if not found. '
            'Use this after loading a file to understand the time structure of the data.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'dataframe': {
                    'type': 'object',
                    'description': 'DataFrame with consumption data (serialized)'
                }
            },
            'required': ['dataframe']
        }
    },
    
    'parse_emissions_period_code': {
        'name': 'parse_emissions_period_code',
        'description': (
            'Parse a combined YYYYMMDDTTT emissions period code into date and period components. '
            'The code format is: YYYYMMDD (date) + TTT (time period with leading zeros). '
            'Example: "20230101001" -> date="20230101", period=1. '
            'Use this when consumption data contains combined period codes.'
        ),
        'inputSchema': {
            'type': 'object',
            'properties': {
                'code': {
                    'type': 'string',
                    'description': 'Emissions period code in format YYYYMMDDTTT (11 characters)'
                }
            },
            'required': ['code']
        }
    }
}


def get_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """
    Get the Bedrock tool schema for a specific tool.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Tool schema dictionary or None if tool not found
    """
    return TOOL_SCHEMAS.get(tool_name)


def get_all_tool_schemas() -> Dict[str, Dict[str, Any]]:
    """
    Get all Bedrock tool schemas.
    
    Returns:
        Dictionary mapping tool names to their schemas
    """
    return TOOL_SCHEMAS.copy()
