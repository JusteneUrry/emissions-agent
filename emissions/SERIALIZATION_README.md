# DataFrame JSON Serialization Module

## Overview

The `serialization.py` module provides utilities for converting pandas DataFrames and other Python types to JSON-serializable formats for AWS Bedrock agent tool integration. This enables the emissions calculation modules to be exposed as agent-callable tools.

## Key Features

- **DataFrame Serialization**: Convert pandas DataFrames to JSON-serializable dictionaries with metadata
- **Round-Trip Conversion**: Reconstruct DataFrames from serialized JSON with preserved data types
- **Special Type Handling**: Automatic conversion of datetime, NaN, numpy types, and infinity values
- **Metadata Preservation**: Includes row counts, column names, and data types for reconstruction
- **Generic Tool Serializer**: Handles DataFrames, dicts, lists, and primitives in tool outputs

## Core Functions

### `dataframe_to_json(df: pd.DataFrame) -> dict`

Converts a pandas DataFrame to a JSON-serializable dictionary.

**Returns:**
```python
{
    'data': [
        {'col1': value1, 'col2': value2},  # Row 1
        {'col1': value3, 'col2': value4}   # Row 2
    ],
    'metadata': {
        'row_count': 2,
        'column_count': 2,
        'columns': ['col1', 'col2'],
        'dtypes': {'col1': 'int64', 'col2': 'float64'},
        'index_name': None
    }
}
```

**Type Conversions:**
- `datetime` → ISO format string (`"2023-01-01T00:00:00"`)
- `NaN` → `None` (JSON null)
- `np.inf` → `"inf"` string
- Numpy types → Python native types

### `json_to_dataframe(data: dict) -> pd.DataFrame`

Reconstructs a pandas DataFrame from serialized JSON.

**Input:** Dictionary with `'data'` and `'metadata'` keys (from `dataframe_to_json`)

**Features:**
- Restores original column order
- Attempts to restore original dtypes based on metadata
- Handles datetime reconstruction from ISO strings
- Preserves None values as NaN in numeric columns

### `serialize_tool_result(result: Any) -> dict`

Generic serializer for agent tool outputs.

**Returns:**
```python
{
    'type': 'dataframe' | 'dict' | 'list' | 'str' | 'int' | 'float' | ...,
    'value': <serialized_value>
}
```

**Supported Types:**
- `pd.DataFrame` → Uses `dataframe_to_json()`
- `dict` → Recursively serializes values
- `list` → Serializes each element
- `datetime`/`date` → ISO format strings
- Numpy types → Python native types
- Primitives → Passed through

## Usage Examples

### Basic DataFrame Serialization

```python
from emissions.serialization import dataframe_to_json, json_to_dataframe

# Create DataFrame
df = pd.DataFrame({
    'state': ['NSW', 'VIC'],
    'factor': [720.0, 890.0]
})

# Serialize
serialized = dataframe_to_json(df)
print(serialized['metadata']['row_count'])  # 2

# Reconstruct
reconstructed = json_to_dataframe(serialized)
```

### DateTime Handling

```python
df = pd.DataFrame({
    'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02']),
    'value': [10, 20]
})

serialized = dataframe_to_json(df)
# serialized['data'][0]['timestamp'] == '2023-01-01T00:00:00'

reconstructed = json_to_dataframe(serialized)
# reconstructed['timestamp'] is datetime64[ns] dtype
```

### Agent Tool Wrapper Pattern

```python
from emissions.serialization import dataframe_to_json

def agent_tool_load_factors(state: str, interval: int) -> dict:
    """Agent tool wrapper for load_interval_factors."""
    try:
        # Call original emissions function
        result_df = load_interval_factors(state, interval)
        
        # Serialize for Bedrock
        serialized = dataframe_to_json(result_df)
        
        return {
            'success': True,
            'data': serialized,
            'message': f'Loaded {len(result_df)} factors'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

### Mixed Type Tool Results

```python
from emissions.serialization import serialize_tool_result

# Tool returns DataFrame + metadata
tool_result = {
    'factors': df,  # DataFrame
    'count': 10,
    'timestamp': datetime.now()
}

serialized = serialize_tool_result(tool_result)
# Handles DataFrame, primitives, and datetime automatically
```

## Edge Cases Handled

1. **Empty DataFrames**: Preserves column structure with zero rows
2. **NaN Values**: Converted to None (JSON null) and back to NaN
3. **Infinity**: Converted to string representation (`"inf"`, `"-inf"`)
4. **Large DataFrames**: Efficiently handles 1000+ rows
5. **Special Column Names**: Supports spaces, dashes, underscores
6. **Single Row/Column**: Works correctly with minimal DataFrames
7. **Nested DataFrames**: Recursively serializes DataFrames in dicts

## Testing

The module includes comprehensive test coverage:

- **28 unit tests** in `test_serialization.py`
  - DataFrame serialization and deserialization
  - Round-trip conversion
  - Edge cases and special types
  
- **13 integration tests** in `test_serialization_integration.py`
  - Emissions-specific DataFrame structures
  - Tool result formats
  - Real-world usage patterns

Run tests:
```bash
pytest test_serialization.py test_serialization_integration.py -v
```

## Examples

See `serialization_example.py` for detailed usage examples:
```bash
python -m emissions.serialization_example
```

## Requirements Validation

This module satisfies the following requirements from the emissions-dashboard spec:

- **Requirement 0.1.3**: Tool invocation wrappers handle DataFrame serialization
- **Requirement 0.1.4**: Tool results returned in JSON-serializable format
- **Requirement 0.1.5**: Structured error handling returns error messages to agent

## Design Alignment

Aligns with the Agent Tools Layer design (design.md):
- Exposes existing modules as agent-callable tools
- Handles DataFrame to JSON serialization for Bedrock
- Includes metadata (row counts, column names, data types)
- Supports error result formatting

## Future Enhancements

Potential improvements for future iterations:
- Compression for large DataFrames
- Schema validation for deserialization
- Custom serializers for domain-specific types
- Streaming serialization for very large datasets
