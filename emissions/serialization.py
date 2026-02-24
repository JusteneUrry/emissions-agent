"""
JSON serialization utilities for DataFrame outputs.

This module provides functions to convert pandas DataFrames to JSON-serializable
dictionaries and back, enabling AWS Bedrock agent tool integration.
"""

import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date


def dataframe_to_json(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Convert a pandas DataFrame to a JSON-serializable dictionary with metadata.
    
    This function handles pandas-specific types (datetime, NaN, etc.) and includes
    metadata about the DataFrame structure for reconstruction.
    
    Args:
        df: pandas DataFrame to serialize
        
    Returns:
        Dictionary with keys:
        - 'data': List of records (each row as a dict)
        - 'metadata': Dict containing:
            - 'row_count': Number of rows
            - 'column_count': Number of columns
            - 'columns': List of column names
            - 'dtypes': Dict mapping column names to string dtype representations
            - 'index_name': Name of the index (if any)
            
    Example:
        >>> df = pd.DataFrame({'a': [1, 2], 'b': [3.0, 4.0]})
        >>> result = dataframe_to_json(df)
        >>> result['metadata']['row_count']
        2
        >>> result['data'][0]
        {'a': 1, 'b': 3.0}
    """
    # Convert DataFrame to records orientation
    # This creates a list of dicts, one per row
    records = df.to_dict(orient='records')
    
    # Process each record to handle special types
    processed_records = []
    for record in records:
        processed_record = {}
        for key, value in record.items():
            processed_record[key] = _serialize_value(value)
        processed_records.append(processed_record)
    
    # Extract metadata
    metadata = {
        'row_count': len(df),
        'column_count': len(df.columns),
        'columns': list(df.columns),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'index_name': df.index.name if df.index.name else None
    }
    
    return {
        'data': processed_records,
        'metadata': metadata
    }


def json_to_dataframe(data: Dict[str, Any]) -> pd.DataFrame:
    """
    Reconstruct a pandas DataFrame from a serialized JSON dictionary.
    
    This function reverses the serialization performed by dataframe_to_json(),
    restoring the DataFrame structure and attempting to restore original dtypes.
    
    Args:
        data: Dictionary with 'data' and 'metadata' keys (from dataframe_to_json)
        
    Returns:
        Reconstructed pandas DataFrame
        
    Raises:
        ValueError: If data format is invalid
        
    Example:
        >>> serialized = {'data': [{'a': 1, 'b': 3.0}], 'metadata': {...}}
        >>> df = json_to_dataframe(serialized)
        >>> df.shape
        (1, 2)
    """
    if 'data' not in data or 'metadata' not in data:
        raise ValueError("Invalid serialized data: missing 'data' or 'metadata' keys")
    
    records = data['data']
    metadata = data['metadata']
    
    # Handle empty DataFrame
    if not records:
        return pd.DataFrame(columns=metadata.get('columns', []))
    
    # Deserialize values in each record
    deserialized_records = []
    for record in records:
        deserialized_record = {}
        for key, value in record.items():
            deserialized_record[key] = _deserialize_value(value)
        deserialized_records.append(deserialized_record)
    
    # Create DataFrame from records
    df = pd.DataFrame(deserialized_records)
    
    # Attempt to restore dtypes based on metadata
    if 'dtypes' in metadata:
        for col, dtype_str in metadata['dtypes'].items():
            if col in df.columns:
                try:
                    # Handle datetime types
                    if 'datetime' in dtype_str:
                        df[col] = pd.to_datetime(df[col])
                    # Handle numeric types
                    elif dtype_str.startswith('int'):
                        df[col] = df[col].astype('Int64')  # Nullable integer
                    elif dtype_str.startswith('float'):
                        df[col] = df[col].astype('float64')
                    # Handle boolean
                    elif dtype_str == 'bool':
                        df[col] = df[col].astype('bool')
                except (ValueError, TypeError):
                    # If conversion fails, keep the inferred type
                    pass
    
    # Restore index name if present
    if metadata.get('index_name'):
        df.index.name = metadata['index_name']
    
    return df


def serialize_tool_result(result: Any) -> Dict[str, Any]:
    """
    Generic serializer for agent tool outputs.
    
    This function handles various Python types and converts them to JSON-serializable
    formats suitable for AWS Bedrock agent tools.
    
    Supported types:
    - pandas DataFrame: Converted using dataframe_to_json()
    - dict: Recursively serialized
    - list: Recursively serialized
    - Primitives (str, int, float, bool, None): Passed through
    - datetime/date: Converted to ISO format strings
    - numpy types: Converted to Python native types
    
    Args:
        result: The tool output to serialize
        
    Returns:
        JSON-serializable dictionary with keys:
        - 'type': String indicating the result type
        - 'value': The serialized value
        
    Example:
        >>> df = pd.DataFrame({'a': [1, 2]})
        >>> result = serialize_tool_result(df)
        >>> result['type']
        'dataframe'
        >>> 'data' in result['value']
        True
    """
    # Handle DataFrame
    if isinstance(result, pd.DataFrame):
        return {
            'type': 'dataframe',
            'value': dataframe_to_json(result)
        }
    
    # Handle dict
    if isinstance(result, dict):
        serialized_dict = {}
        for key, value in result.items():
            # Recursively serialize dict values
            if isinstance(value, (pd.DataFrame, datetime, date, np.ndarray)):
                serialized_dict[key] = _serialize_value(value)
            else:
                serialized_dict[key] = value
        return {
            'type': 'dict',
            'value': serialized_dict
        }
    
    # Handle list
    if isinstance(result, list):
        serialized_list = [_serialize_value(item) for item in result]
        return {
            'type': 'list',
            'value': serialized_list
        }
    
    # Handle primitives and other types
    return {
        'type': type(result).__name__,
        'value': _serialize_value(result)
    }


def _serialize_value(value: Any) -> Any:
    """
    Serialize a single value to a JSON-compatible type.
    
    Args:
        value: Value to serialize
        
    Returns:
        JSON-serializable representation of the value
    """
    # Handle None
    if value is None:
        return None
    
    # Handle NaN and infinity
    if isinstance(value, float):
        if np.isnan(value):
            return None  # Convert NaN to None for JSON
        if np.isinf(value):
            return str(value)  # Convert inf to string
        return value
    
    # Handle numpy types
    if isinstance(value, (np.integer, np.floating)):
        return value.item()  # Convert to Python native type
    
    if isinstance(value, np.bool_):
        return bool(value)
    
    if isinstance(value, np.ndarray):
        return value.tolist()
    
    # Handle DataFrame (nested) - check before pd.isna()
    if isinstance(value, pd.DataFrame):
        return dataframe_to_json(value)
    
    # Handle datetime types
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    
    # Handle pandas NA/NaT (check after DataFrame to avoid ambiguity)
    try:
        if pd.isna(value):
            return None
    except (ValueError, TypeError):
        # pd.isna() can raise ValueError for some types
        pass
    
    # Return as-is for primitives (str, int, float, bool)
    return value


def _deserialize_value(value: Any) -> Any:
    """
    Deserialize a value from JSON representation.
    
    Args:
        value: JSON value to deserialize
        
    Returns:
        Deserialized Python value
    """
    # Handle None (could be original None or NaN)
    if value is None:
        return None
    
    # Handle ISO datetime strings
    if isinstance(value, str):
        # Try to parse as datetime
        if 'T' in value or '-' in value:
            try:
                return pd.to_datetime(value)
            except (ValueError, TypeError):
                pass
        
        # Handle infinity strings
        if value in ('inf', '-inf', 'nan'):
            return float(value)
    
    # Handle nested DataFrame
    if isinstance(value, dict) and 'data' in value and 'metadata' in value:
        return json_to_dataframe(value)
    
    # Return as-is for other types
    return value
