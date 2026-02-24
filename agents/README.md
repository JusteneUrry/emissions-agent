# Agent Tool Wrappers

This directory contains the agent orchestration layer for the Emissions Intelligence Agent, including AWS Bedrock integration and tool wrappers.

## Overview

The agent tool wrappers expose existing emissions modules (io.py, interval.py, factors.py, calc.py, viz.py) as Bedrock agent tools with:

- **Structured error handling**: All errors are caught and returned in a consistent format
- **JSON serialization**: DataFrames and complex types are serialized for AWS Bedrock
- **Tool schemas**: Each tool has a Bedrock-compatible schema definition
- **Success/failure indicators**: All tools return a `success` boolean for easy error checking

## File I/O Tool Wrappers

### tool_load_consumption_file

Loads electricity consumption data from CSV or Excel files.

**Usage:**
```python
from agents.agent_tools import tool_load_consumption_file

result = tool_load_consumption_file(uploaded_file)

if result['success']:
    df_data = result['result']['value']
    print(f"Loaded {df_data['metadata']['row_count']} rows")
else:
    print(f"Error: {result['error']}")
```

**Returns:**
```python
{
    'success': True,
    'result': {
        'type': 'dataframe',
        'value': {
            'data': [...],  # List of records
            'metadata': {
                'row_count': 100,
                'column_count': 3,
                'columns': ['timestamp', 'consumption_kwh'],
                'dtypes': {...}
            }
        }
    },
    'message': 'Successfully loaded 100 rows from data.csv'
}
```

### tool_identify_consumption_column

Identifies the consumption column using pattern matching.

**Usage:**
```python
from agents.agent_tools import tool_identify_consumption_column

result = tool_identify_consumption_column(df)

if result['success']:
    col_name = result['result']
    print(f"Consumption column: {col_name}")
```

**Returns:**
```python
{
    'success': True,
    'result': 'consumption_kwh',
    'message': "Identified consumption column: 'consumption_kwh'"
}
```

### tool_identify_time_columns

Identifies timestamp, time period, and date columns.

**Usage:**
```python
from agents.agent_tools import tool_identify_time_columns

result = tool_identify_time_columns(df)

if result['success']:
    time_cols = result['result']
    print(f"Timestamp: {time_cols['timestamp']}")
    print(f"Time period: {time_cols['time_period']}")
    print(f"Date: {time_cols['date']}")
```

**Returns:**
```python
{
    'success': True,
    'result': {
        'timestamp': 'datetime',
        'time_period': None,
        'date': None
    },
    'message': 'Identified time columns: timestamp=datetime'
}
```

### tool_parse_emissions_period_code

Parses YYYYMMDDTTT emissions period codes.

**Usage:**
```python
from agents.agent_tools import tool_parse_emissions_period_code

result = tool_parse_emissions_period_code("20230101001")

if result['success']:
    parsed = result['result']
    print(f"Date: {parsed['date']}, Period: {parsed['period']}")
```

**Returns:**
```python
{
    'success': True,
    'result': {
        'date': '20230101',
        'period': 1
    },
    'message': "Parsed code '20230101001' into date=20230101, period=1"
}
```

## Tool Schemas

Each tool has a Bedrock-compatible schema that defines its name, description, and input parameters.

**Get a specific tool schema:**
```python
from agents.agent_tools import get_tool_schema

schema = get_tool_schema('load_consumption_file')
print(schema['description'])
print(schema['inputSchema'])
```

**Get all tool schemas:**
```python
from agents.agent_tools import get_all_tool_schemas

schemas = get_all_tool_schemas()
for tool_name, schema in schemas.items():
    print(f"{tool_name}: {schema['description']}")
```

## Error Handling

All tool wrappers follow a consistent error handling pattern:

**Success response:**
```python
{
    'success': True,
    'result': <tool output>,
    'message': <success message>
}
```

**Error response:**
```python
{
    'success': False,
    'error': <error message>,
    'error_type': <exception class name>,
    'message': <user-friendly message>
}
```

**Example error handling:**
```python
result = tool_load_consumption_file(uploaded_file)

if not result['success']:
    if result['error_type'] == 'UnsupportedFileFormatError':
        print("Please upload a CSV or Excel file")
    else:
        print(f"Unexpected error: {result['error']}")
```

## JSON Serialization

The tool wrappers use the `emissions.serialization` module to convert DataFrames and other complex types to JSON-serializable formats.

**DataFrame serialization:**
- Converts to records orientation (list of dicts)
- Handles pandas-specific types (datetime, NaN, etc.)
- Includes metadata (row count, column names, dtypes)

**See also:**
- `emissions/serialization.py` - Core serialization utilities
- `emissions/SERIALIZATION_README.md` - Detailed serialization documentation
- `emissions/serialization_example.py` - Usage examples

## Testing

Run the agent tool wrapper tests:

```bash
pytest test_agent_tools.py -v
```

The test suite covers:
- Successful tool invocations
- Error handling for various failure modes
- Tool schema validation
- Integration workflow testing

## Future Enhancements

Additional tool wrappers will be added for:
- Interval detection (interval.py)
- Emissions factor loading (factors.py)
- Emissions calculations (calc.py)
- Visualization generation (viz.py)

These will follow the same pattern as the file I/O tool wrappers.

## 📌 Hackathon Submission Links

- 📄 Use Case Documentation  
  docs/use-case.md

- 🏗 Architecture Diagram  
  docs/architecture.png

- 🎥 Demo Video  
  https://your-video-link
