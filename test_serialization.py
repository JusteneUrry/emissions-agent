"""
Tests for JSON serialization utilities.

This module tests the serialization and deserialization of pandas DataFrames
and other Python types for AWS Bedrock agent tool integration.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date
from emissions.serialization import (
    dataframe_to_json,
    json_to_dataframe,
    serialize_tool_result
)


class TestDataFrameToJson:
    """Tests for dataframe_to_json function."""
    
    def test_basic_dataframe(self):
        """Test serialization of a basic DataFrame with numeric data."""
        df = pd.DataFrame({
            'a': [1, 2, 3],
            'b': [4.0, 5.0, 6.0]
        })
        
        result = dataframe_to_json(df)
        
        # Check structure
        assert 'data' in result
        assert 'metadata' in result
        
        # Check data
        assert len(result['data']) == 3
        assert result['data'][0] == {'a': 1, 'b': 4.0}
        assert result['data'][1] == {'a': 2, 'b': 5.0}
        
        # Check metadata
        assert result['metadata']['row_count'] == 3
        assert result['metadata']['column_count'] == 2
        assert result['metadata']['columns'] == ['a', 'b']
        assert 'int' in result['metadata']['dtypes']['a']
        assert 'float' in result['metadata']['dtypes']['b']
    
    def test_empty_dataframe(self):
        """Test serialization of an empty DataFrame."""
        df = pd.DataFrame(columns=['x', 'y'])
        
        result = dataframe_to_json(df)
        
        assert result['data'] == []
        assert result['metadata']['row_count'] == 0
        assert result['metadata']['column_count'] == 2
        assert result['metadata']['columns'] == ['x', 'y']
    
    def test_datetime_column(self):
        """Test serialization of DataFrame with datetime column."""
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02']),
            'value': [10, 20]
        })
        
        result = dataframe_to_json(df)
        
        # Datetime should be converted to ISO format string
        assert isinstance(result['data'][0]['timestamp'], str)
        assert '2023-01-01' in result['data'][0]['timestamp']
        assert result['data'][0]['value'] == 10
        
        # Metadata should indicate datetime type
        assert 'datetime' in result['metadata']['dtypes']['timestamp']
    
    def test_nan_values(self):
        """Test serialization of DataFrame with NaN values."""
        df = pd.DataFrame({
            'a': [1.0, np.nan, 3.0],
            'b': [np.nan, 5.0, 6.0]
        })
        
        result = dataframe_to_json(df)
        
        # NaN should be converted to None
        assert result['data'][0]['a'] == 1.0
        assert result['data'][0]['b'] is None
        assert result['data'][1]['a'] is None
        assert result['data'][1]['b'] == 5.0
    
    def test_mixed_types(self):
        """Test serialization of DataFrame with mixed column types."""
        df = pd.DataFrame({
            'int_col': [1, 2],
            'float_col': [1.5, 2.5],
            'str_col': ['a', 'b'],
            'bool_col': [True, False],
            'date_col': pd.to_datetime(['2023-01-01', '2023-01-02'])
        })
        
        result = dataframe_to_json(df)
        
        assert result['data'][0]['int_col'] == 1
        assert result['data'][0]['float_col'] == 1.5
        assert result['data'][0]['str_col'] == 'a'
        assert result['data'][0]['bool_col'] is True
        assert isinstance(result['data'][0]['date_col'], str)
        
        # Check all dtypes are captured
        assert len(result['metadata']['dtypes']) == 5


class TestJsonToDataFrame:
    """Tests for json_to_dataframe function."""
    
    def test_basic_reconstruction(self):
        """Test reconstruction of a basic DataFrame."""
        serialized = {
            'data': [
                {'a': 1, 'b': 4.0},
                {'a': 2, 'b': 5.0}
            ],
            'metadata': {
                'row_count': 2,
                'column_count': 2,
                'columns': ['a', 'b'],
                'dtypes': {'a': 'int64', 'b': 'float64'},
                'index_name': None
            }
        }
        
        df = json_to_dataframe(serialized)
        
        assert len(df) == 2
        assert list(df.columns) == ['a', 'b']
        assert df['a'].iloc[0] == 1
        assert df['b'].iloc[0] == 4.0
    
    def test_empty_dataframe_reconstruction(self):
        """Test reconstruction of an empty DataFrame."""
        serialized = {
            'data': [],
            'metadata': {
                'row_count': 0,
                'column_count': 2,
                'columns': ['x', 'y'],
                'dtypes': {},
                'index_name': None
            }
        }
        
        df = json_to_dataframe(serialized)
        
        assert len(df) == 0
        assert list(df.columns) == ['x', 'y']
    
    def test_datetime_reconstruction(self):
        """Test reconstruction of DataFrame with datetime column."""
        serialized = {
            'data': [
                {'timestamp': '2023-01-01T00:00:00', 'value': 10},
                {'timestamp': '2023-01-02T00:00:00', 'value': 20}
            ],
            'metadata': {
                'row_count': 2,
                'column_count': 2,
                'columns': ['timestamp', 'value'],
                'dtypes': {'timestamp': 'datetime64[ns]', 'value': 'int64'},
                'index_name': None
            }
        }
        
        df = json_to_dataframe(serialized)
        
        # Datetime should be reconstructed
        assert pd.api.types.is_datetime64_any_dtype(df['timestamp'])
        assert df['value'].iloc[0] == 10
    
    def test_none_values_reconstruction(self):
        """Test reconstruction of DataFrame with None values."""
        serialized = {
            'data': [
                {'a': 1.0, 'b': None},
                {'a': None, 'b': 5.0}
            ],
            'metadata': {
                'row_count': 2,
                'column_count': 2,
                'columns': ['a', 'b'],
                'dtypes': {'a': 'float64', 'b': 'float64'},
                'index_name': None
            }
        }
        
        df = json_to_dataframe(serialized)
        
        assert df['a'].iloc[0] == 1.0
        assert pd.isna(df['b'].iloc[0])
        assert pd.isna(df['a'].iloc[1])
        assert df['b'].iloc[1] == 5.0
    
    def test_invalid_data_format(self):
        """Test that invalid data format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid serialized data"):
            json_to_dataframe({'invalid': 'format'})
        
        with pytest.raises(ValueError, match="Invalid serialized data"):
            json_to_dataframe({'data': []})  # Missing metadata


class TestRoundTrip:
    """Tests for round-trip serialization and deserialization."""
    
    def test_basic_round_trip(self):
        """Test that basic DataFrame survives round-trip conversion."""
        original = pd.DataFrame({
            'a': [1, 2, 3],
            'b': [4.0, 5.0, 6.0],
            'c': ['x', 'y', 'z']
        })
        
        serialized = dataframe_to_json(original)
        reconstructed = json_to_dataframe(serialized)
        
        # Check shape
        assert reconstructed.shape == original.shape
        
        # Check values
        pd.testing.assert_frame_equal(
            reconstructed[['a', 'b', 'c']],
            original[['a', 'b', 'c']],
            check_dtype=False  # Allow dtype differences
        )
    
    def test_datetime_round_trip(self):
        """Test that DataFrame with datetime survives round-trip."""
        original = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
            'value': [10, 20, 30]
        })
        
        serialized = dataframe_to_json(original)
        reconstructed = json_to_dataframe(serialized)
        
        # Check datetime column is preserved
        assert pd.api.types.is_datetime64_any_dtype(reconstructed['timestamp'])
        assert len(reconstructed) == 3
        assert reconstructed['value'].iloc[0] == 10
    
    def test_nan_round_trip(self):
        """Test that NaN values survive round-trip conversion."""
        original = pd.DataFrame({
            'a': [1.0, np.nan, 3.0],
            'b': [np.nan, 5.0, np.nan]
        })
        
        serialized = dataframe_to_json(original)
        reconstructed = json_to_dataframe(serialized)
        
        # Check NaN positions are preserved
        assert not pd.isna(reconstructed['a'].iloc[0])
        assert pd.isna(reconstructed['a'].iloc[1])
        assert not pd.isna(reconstructed['a'].iloc[2])
        
        assert pd.isna(reconstructed['b'].iloc[0])
        assert not pd.isna(reconstructed['b'].iloc[1])
        assert pd.isna(reconstructed['b'].iloc[2])
    
    def test_mixed_types_round_trip(self):
        """Test that DataFrame with mixed types survives round-trip."""
        original = pd.DataFrame({
            'int_col': [1, 2, 3],
            'float_col': [1.5, 2.5, 3.5],
            'str_col': ['a', 'b', 'c'],
            'date_col': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03'])
        })
        
        serialized = dataframe_to_json(original)
        reconstructed = json_to_dataframe(serialized)
        
        assert len(reconstructed) == 3
        assert list(reconstructed.columns) == list(original.columns)
        
        # Check values are preserved
        assert reconstructed['int_col'].iloc[0] == 1
        assert reconstructed['float_col'].iloc[0] == 1.5
        assert reconstructed['str_col'].iloc[0] == 'a'
        assert pd.api.types.is_datetime64_any_dtype(reconstructed['date_col'])


class TestSerializeToolResult:
    """Tests for serialize_tool_result function."""
    
    def test_dataframe_result(self):
        """Test serialization of DataFrame tool result."""
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        
        result = serialize_tool_result(df)
        
        assert result['type'] == 'dataframe'
        assert 'data' in result['value']
        assert 'metadata' in result['value']
        assert len(result['value']['data']) == 2
    
    def test_dict_result(self):
        """Test serialization of dict tool result."""
        data = {'key1': 'value1', 'key2': 42}
        
        result = serialize_tool_result(data)
        
        assert result['type'] == 'dict'
        assert result['value'] == data
    
    def test_dict_with_datetime(self):
        """Test serialization of dict containing datetime."""
        data = {
            'timestamp': datetime(2023, 1, 1, 12, 0, 0),
            'value': 100
        }
        
        result = serialize_tool_result(data)
        
        assert result['type'] == 'dict'
        assert isinstance(result['value']['timestamp'], str)
        assert '2023-01-01' in result['value']['timestamp']
        assert result['value']['value'] == 100
    
    def test_list_result(self):
        """Test serialization of list tool result."""
        data = [1, 2, 3, 4, 5]
        
        result = serialize_tool_result(data)
        
        assert result['type'] == 'list'
        assert result['value'] == data
    
    def test_list_with_datetime(self):
        """Test serialization of list containing datetime."""
        data = [datetime(2023, 1, 1), datetime(2023, 1, 2)]
        
        result = serialize_tool_result(data)
        
        assert result['type'] == 'list'
        assert len(result['value']) == 2
        assert isinstance(result['value'][0], str)
        assert '2023-01-01' in result['value'][0]
    
    def test_string_result(self):
        """Test serialization of string tool result."""
        data = "test string"
        
        result = serialize_tool_result(data)
        
        assert result['type'] == 'str'
        assert result['value'] == data
    
    def test_numeric_result(self):
        """Test serialization of numeric tool results."""
        # Integer
        result = serialize_tool_result(42)
        assert result['type'] == 'int'
        assert result['value'] == 42
        
        # Float
        result = serialize_tool_result(3.14)
        assert result['type'] == 'float'
        assert result['value'] == 3.14
    
    def test_none_result(self):
        """Test serialization of None tool result."""
        result = serialize_tool_result(None)
        
        assert result['type'] == 'NoneType'
        assert result['value'] is None
    
    def test_numpy_types(self):
        """Test serialization of numpy types."""
        # Numpy integer
        result = serialize_tool_result(np.int64(42))
        assert result['value'] == 42
        
        # Numpy float
        result = serialize_tool_result(np.float64(3.14))
        assert result['value'] == 3.14
        
        # Numpy array
        result = serialize_tool_result(np.array([1, 2, 3]))
        assert result['value'] == [1, 2, 3]


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""
    
    def test_infinity_values(self):
        """Test handling of infinity values."""
        df = pd.DataFrame({
            'a': [1.0, np.inf, -np.inf]
        })
        
        serialized = dataframe_to_json(df)
        
        # Infinity should be converted to string
        assert serialized['data'][0]['a'] == 1.0
        assert serialized['data'][1]['a'] == 'inf'
        assert serialized['data'][2]['a'] == '-inf'
    
    def test_large_dataframe(self):
        """Test serialization of a large DataFrame."""
        df = pd.DataFrame({
            'a': range(1000),
            'b': range(1000, 2000),
            'c': [f'value_{i}' for i in range(1000)]
        })
        
        serialized = dataframe_to_json(df)
        reconstructed = json_to_dataframe(serialized)
        
        assert len(reconstructed) == 1000
        assert list(reconstructed.columns) == ['a', 'b', 'c']
        assert reconstructed['a'].iloc[999] == 999
    
    def test_special_column_names(self):
        """Test handling of special column names."""
        df = pd.DataFrame({
            'column with spaces': [1, 2],
            'column-with-dashes': [3, 4],
            'column_with_underscores': [5, 6]
        })
        
        serialized = dataframe_to_json(df)
        reconstructed = json_to_dataframe(serialized)
        
        assert list(reconstructed.columns) == list(df.columns)
        assert reconstructed['column with spaces'].iloc[0] == 1
    
    def test_single_row_dataframe(self):
        """Test serialization of single-row DataFrame."""
        df = pd.DataFrame({'a': [1], 'b': [2]})
        
        serialized = dataframe_to_json(df)
        reconstructed = json_to_dataframe(serialized)
        
        assert len(reconstructed) == 1
        assert reconstructed['a'].iloc[0] == 1
        assert reconstructed['b'].iloc[0] == 2
    
    def test_single_column_dataframe(self):
        """Test serialization of single-column DataFrame."""
        df = pd.DataFrame({'a': [1, 2, 3]})
        
        serialized = dataframe_to_json(df)
        reconstructed = json_to_dataframe(serialized)
        
        assert len(reconstructed) == 3
        assert list(reconstructed.columns) == ['a']
        assert reconstructed['a'].iloc[0] == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
