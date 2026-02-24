"""
Tests for agent tool wrappers.

This module tests the agent tool wrappers in agents/agent_tools.py to ensure
they properly wrap the emissions I/O functions with error handling and JSON serialization.
"""

import pytest
import pandas as pd
from io import BytesIO
from streamlit.runtime.uploaded_file_manager import UploadedFile

from agents.agent_tools import (
    tool_load_consumption_file,
    tool_identify_consumption_column,
    tool_identify_time_columns,
    tool_parse_emissions_period_code,
    get_tool_schema,
    get_all_tool_schemas
)


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_uploaded_file(content: bytes, filename: str):
    """Create a mock UploadedFile object for testing."""
    file_obj = BytesIO(content)
    
    # Create a minimal mock that has the required attributes
    class MockUploadedFile:
        def __init__(self, file_obj, name):
            self.name = name
            self._file_obj = file_obj
        
        def read(self, size=-1):
            return self._file_obj.read(size)
        
        def seek(self, offset, whence=0):
            return self._file_obj.seek(offset, whence)
        
        def tell(self):
            return self._file_obj.tell()
        
        def readable(self):
            return self._file_obj.readable()
        
        def writable(self):
            return self._file_obj.writable()
    
    return MockUploadedFile(file_obj, filename)


# ============================================================================
# Test tool_load_consumption_file
# ============================================================================

def test_tool_load_consumption_file_csv_success():
    """Test successful CSV file loading."""
    csv_content = b"timestamp,consumption_kwh\n2023-01-01 00:00:00,10.5\n2023-01-01 00:05:00,12.3"
    uploaded_file = create_mock_uploaded_file(csv_content, "test.csv")
    
    result = tool_load_consumption_file(uploaded_file)
    
    assert result['success'] is True
    assert 'result' in result
    assert result['result']['type'] == 'dataframe'
    assert result['result']['value']['metadata']['row_count'] == 2
    assert 'Successfully loaded' in result['message']


def test_tool_load_consumption_file_unsupported_format():
    """Test error handling for unsupported file format."""
    txt_content = b"some text content"
    uploaded_file = create_mock_uploaded_file(txt_content, "test.txt")
    
    result = tool_load_consumption_file(uploaded_file)
    
    assert result['success'] is False
    assert result['error_type'] == 'UnsupportedFileFormatError'
    assert 'error' in result
    assert 'File format not supported' in result['message']


# ============================================================================
# Test tool_identify_consumption_column
# ============================================================================

def test_tool_identify_consumption_column_success():
    """Test successful consumption column identification."""
    df = pd.DataFrame({
        'timestamp': ['2023-01-01 00:00:00'],
        'consumption_kwh': [10.5]
    })
    
    result = tool_identify_consumption_column(df)
    
    assert result['success'] is True
    assert result['result'] == 'consumption_kwh'
    assert 'consumption_kwh' in result['message']


def test_tool_identify_consumption_column_case_insensitive():
    """Test consumption column identification with different case."""
    df = pd.DataFrame({
        'Timestamp': ['2023-01-01 00:00:00'],
        'KWH': [10.5]
    })
    
    result = tool_identify_consumption_column(df)
    
    assert result['success'] is True
    assert result['result'] == 'KWH'


def test_tool_identify_consumption_column_not_found():
    """Test error handling when consumption column not found."""
    df = pd.DataFrame({
        'timestamp': ['2023-01-01 00:00:00'],
        'value': [10.5]
    })
    
    result = tool_identify_consumption_column(df)
    
    assert result['success'] is False
    assert result['error_type'] == 'ColumnNotFoundError'
    assert 'No consumption column found' in result['message']


# ============================================================================
# Test tool_identify_time_columns
# ============================================================================

def test_tool_identify_time_columns_timestamp():
    """Test identification of timestamp column."""
    df = pd.DataFrame({
        'datetime': ['2023-01-01 00:00:00'],
        'consumption_kwh': [10.5]
    })
    
    result = tool_identify_time_columns(df)
    
    assert result['success'] is True
    assert result['result']['timestamp'] == 'datetime'
    assert result['result']['time_period'] is None
    assert result['result']['date'] is None


def test_tool_identify_time_columns_period():
    """Test identification of time period column."""
    df = pd.DataFrame({
        'date': ['2023-01-01'],
        'time_period': [1],
        'consumption_kwh': [10.5]
    })
    
    result = tool_identify_time_columns(df)
    
    assert result['success'] is True
    assert result['result']['date'] == 'date'
    assert result['result']['time_period'] == 'time_period'
    assert result['result']['timestamp'] is None


def test_tool_identify_time_columns_none_found():
    """Test when no time columns are found."""
    df = pd.DataFrame({
        'consumption_kwh': [10.5],
        'value': [20.0]
    })
    
    result = tool_identify_time_columns(df)
    
    assert result['success'] is True
    assert result['result']['timestamp'] is None
    assert result['result']['time_period'] is None
    assert result['result']['date'] is None
    assert 'No time columns found' in result['message']


# ============================================================================
# Test tool_parse_emissions_period_code
# ============================================================================

def test_tool_parse_emissions_period_code_success():
    """Test successful parsing of emissions period code."""
    result = tool_parse_emissions_period_code("20230101001")
    
    assert result['success'] is True
    assert result['result']['date'] == '20230101'
    assert result['result']['period'] == 1


def test_tool_parse_emissions_period_code_leading_zeros():
    """Test parsing preserves leading zeros in period."""
    result = tool_parse_emissions_period_code("20230115042")
    
    assert result['success'] is True
    assert result['result']['date'] == '20230115'
    assert result['result']['period'] == 42


def test_tool_parse_emissions_period_code_invalid_length():
    """Test error handling for invalid code length."""
    result = tool_parse_emissions_period_code("2023010100")  # Only 10 characters
    
    assert result['success'] is False
    assert result['error_type'] == 'ValueError'
    assert 'Invalid emissions period code format' in result['message']


def test_tool_parse_emissions_period_code_invalid_format():
    """Test error handling for non-numeric code."""
    result = tool_parse_emissions_period_code("2023-01-0001")
    
    assert result['success'] is False
    assert result['error_type'] == 'ValueError'


# ============================================================================
# Test Tool Schema Functions
# ============================================================================

def test_get_tool_schema_valid():
    """Test retrieving a valid tool schema."""
    schema = get_tool_schema('load_consumption_file')
    
    assert schema is not None
    assert schema['name'] == 'load_consumption_file'
    assert 'description' in schema
    assert 'inputSchema' in schema


def test_get_tool_schema_invalid():
    """Test retrieving an invalid tool schema."""
    schema = get_tool_schema('nonexistent_tool')
    
    assert schema is None


def test_get_all_tool_schemas():
    """Test retrieving all tool schemas."""
    schemas = get_all_tool_schemas()
    
    assert isinstance(schemas, dict)
    assert len(schemas) == 4  # We have 4 I/O tools
    assert 'load_consumption_file' in schemas
    assert 'identify_consumption_column' in schemas
    assert 'identify_time_columns' in schemas
    assert 'parse_emissions_period_code' in schemas


# ============================================================================
# Test Tool Schema Structure
# ============================================================================

def test_tool_schemas_have_required_fields():
    """Test that all tool schemas have required fields."""
    schemas = get_all_tool_schemas()
    
    for tool_name, schema in schemas.items():
        assert 'name' in schema, f"Tool {tool_name} missing 'name' field"
        assert 'description' in schema, f"Tool {tool_name} missing 'description' field"
        assert 'inputSchema' in schema, f"Tool {tool_name} missing 'inputSchema' field"
        
        # Check inputSchema structure
        input_schema = schema['inputSchema']
        assert input_schema['type'] == 'object'
        assert 'properties' in input_schema
        assert 'required' in input_schema


def test_tool_schemas_descriptions_are_informative():
    """Test that tool descriptions are informative."""
    schemas = get_all_tool_schemas()
    
    for tool_name, schema in schemas.items():
        description = schema['description']
        assert len(description) > 20, f"Tool {tool_name} has too short description"
        assert '.' in description, f"Tool {tool_name} description should have sentences"


# ============================================================================
# Integration Test
# ============================================================================

def test_tool_workflow_integration():
    """Test a complete workflow using multiple tools."""
    # Step 1: Load file
    csv_content = b"DateTime,Consumption_kWh\n2023-01-01 00:00:00,10.5\n2023-01-01 00:05:00,12.3"
    uploaded_file = create_mock_uploaded_file(csv_content, "test.csv")
    
    load_result = tool_load_consumption_file(uploaded_file)
    assert load_result['success'] is True
    
    # Extract DataFrame from serialized result
    df_data = load_result['result']['value']
    records = df_data['data']
    df = pd.DataFrame(records)
    
    # Step 2: Identify consumption column
    consumption_result = tool_identify_consumption_column(df)
    assert consumption_result['success'] is True
    assert 'Consumption_kWh' in consumption_result['result']
    
    # Step 3: Identify time columns
    time_result = tool_identify_time_columns(df)
    assert time_result['success'] is True
    assert time_result['result']['timestamp'] == 'DateTime'
