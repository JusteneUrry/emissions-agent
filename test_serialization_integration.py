"""
Integration tests for serialization with actual emissions module DataFrames.

This module tests that serialization works correctly with real DataFrames
from the emissions modules (io.py, interval.py, factors.py).
"""

import pytest
import pandas as pd
from io import BytesIO
from emissions.serialization import (
    dataframe_to_json,
    json_to_dataframe,
    serialize_tool_result
)


class TestEmissionsDataFrameSerialization:
    """Test serialization with emissions-specific DataFrame structures."""
    
    def test_consumption_data_serialization(self):
        """Test serialization of consumption data DataFrame."""
        # Simulate consumption data structure
        consumption_df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01 00:00', '2023-01-01 00:05', '2023-01-01 00:10']),
            'consumption_kwh': [10.5, 12.3, 11.8],
            'time_period': [1, 2, 3]
        })
        
        # Serialize
        serialized = dataframe_to_json(consumption_df)
        
        # Verify structure
        assert serialized['metadata']['row_count'] == 3
        assert 'timestamp' in serialized['metadata']['columns']
        assert 'consumption_kwh' in serialized['metadata']['columns']
        
        # Verify data
        assert serialized['data'][0]['consumption_kwh'] == 10.5
        assert serialized['data'][0]['time_period'] == 1
        
        # Round-trip
        reconstructed = json_to_dataframe(serialized)
        assert len(reconstructed) == 3
        assert pd.api.types.is_datetime64_any_dtype(reconstructed['timestamp'])
    
    def test_emissions_period_code_serialization(self):
        """Test serialization of data with emissions_period_code."""
        df = pd.DataFrame({
            'emissions_period_code': ['20230101001', '20230101002', '20230101003'],
            'consumption_kwh': [10.0, 15.0, 12.0],
            'factor_g_per_kwh': [750.5, 755.2, 748.9]
        })
        
        serialized = dataframe_to_json(df)
        reconstructed = json_to_dataframe(serialized)
        
        # Verify string codes are preserved
        assert reconstructed['emissions_period_code'].iloc[0] == '20230101001'
        assert reconstructed['consumption_kwh'].iloc[0] == 10.0
        assert reconstructed['factor_g_per_kwh'].iloc[0] == 750.5
    
    def test_interval_factors_serialization(self):
        """Test serialization of interval emissions factors DataFrame."""
        factors_df = pd.DataFrame({
            'state': ['NSW', 'NSW', 'VIC'],
            'interval_minutes': [5, 5, 5],
            'emissions_period_code': ['20230101001', '20230101002', '20230101001'],
            'factor_g_per_kwh': [750.5, 755.2, 890.3],
            'source': ['AEMO', 'AEMO', 'AEMO'],
            'dataset_version': ['2023.1', '2023.1', '2023.1']
        })
        
        serialized = dataframe_to_json(factors_df)
        reconstructed = json_to_dataframe(serialized)
        
        assert len(reconstructed) == 3
        assert list(reconstructed.columns) == list(factors_df.columns)
        assert reconstructed['state'].iloc[0] == 'NSW'
        assert reconstructed['interval_minutes'].iloc[0] == 5
    
    def test_annual_factors_serialization(self):
        """Test serialization of annual emissions factors DataFrame."""
        annual_df = pd.DataFrame({
            'state': ['NSW', 'VIC', 'QLD'],
            'year': [2023, 2023, 2023],
            'annual_factor_g_per_kwh': [720.0, 890.0, 810.0],
            'source': ['AEMO', 'AEMO', 'AEMO'],
            'dataset_version': ['2023.1', '2023.1', '2023.1']
        })
        
        serialized = dataframe_to_json(annual_df)
        reconstructed = json_to_dataframe(serialized)
        
        assert len(reconstructed) == 3
        assert reconstructed['year'].iloc[0] == 2023
        assert reconstructed['annual_factor_g_per_kwh'].iloc[0] == 720.0
    
    def test_emissions_results_serialization(self):
        """Test serialization of emissions calculation results."""
        results_df = pd.DataFrame({
            'datetime': pd.to_datetime(['2023-01-01 00:00', '2023-01-01 00:05']),
            'emissions_period_code': ['20230101001', '20230101002'],
            'consumption_kwh': [10.0, 15.0],
            'factor_g_per_kwh': [750.5, 755.2],
            'emissions_g': [7505.0, 11328.0],
            'emissions_tonnes': [0.007505, 0.011328]
        })
        
        serialized = dataframe_to_json(results_df)
        reconstructed = json_to_dataframe(serialized)
        
        assert len(reconstructed) == 2
        assert pd.api.types.is_datetime64_any_dtype(reconstructed['datetime'])
        assert reconstructed['emissions_tonnes'].iloc[0] == pytest.approx(0.007505)
    
    def test_daily_aggregated_serialization(self):
        """Test serialization of daily aggregated emissions."""
        daily_df = pd.DataFrame({
            'date': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']).date,
            'total_consumption_kwh': [240.5, 235.8, 242.1],
            'total_emissions_tonnes': [0.180, 0.177, 0.182]
        })
        
        serialized = dataframe_to_json(daily_df)
        reconstructed = json_to_dataframe(serialized)
        
        assert len(reconstructed) == 3
        assert reconstructed['total_consumption_kwh'].iloc[0] == 240.5
        assert reconstructed['total_emissions_tonnes'].iloc[0] == 0.180
    
    def test_tool_result_with_metadata(self):
        """Test serialize_tool_result with DataFrame and metadata dict."""
        df = pd.DataFrame({
            'state': ['NSW', 'VIC'],
            'factor': [720.0, 890.0]
        })
        
        # Simulate a tool result that includes both DataFrame and metadata
        tool_output = {
            'factors': df,
            'count': len(df),
            'states': ['NSW', 'VIC']
        }
        
        serialized = serialize_tool_result(tool_output)
        
        assert serialized['type'] == 'dict'
        assert 'factors' in serialized['value']
        assert serialized['value']['count'] == 2
        assert serialized['value']['states'] == ['NSW', 'VIC']
    
    def test_empty_consumption_data(self):
        """Test serialization of empty consumption DataFrame."""
        empty_df = pd.DataFrame(columns=['timestamp', 'consumption_kwh', 'time_period'])
        
        serialized = dataframe_to_json(empty_df)
        reconstructed = json_to_dataframe(serialized)
        
        assert len(reconstructed) == 0
        assert list(reconstructed.columns) == ['timestamp', 'consumption_kwh', 'time_period']
    
    def test_missing_values_in_consumption(self):
        """Test serialization with missing consumption values."""
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(['2023-01-01 00:00', '2023-01-01 00:05', '2023-01-01 00:10']),
            'consumption_kwh': [10.5, None, 11.8],
            'time_period': [1, 2, 3]
        })
        
        serialized = dataframe_to_json(df)
        reconstructed = json_to_dataframe(serialized)
        
        assert not pd.isna(reconstructed['consumption_kwh'].iloc[0])
        assert pd.isna(reconstructed['consumption_kwh'].iloc[1])
        assert not pd.isna(reconstructed['consumption_kwh'].iloc[2])


class TestToolResultFormats:
    """Test various tool result formats for agent integration."""
    
    def test_column_identification_result(self):
        """Test serialization of column identification result."""
        result = {
            'timestamp': 'datetime',
            'time_period': 'period',
            'date': None
        }
        
        serialized = serialize_tool_result(result)
        
        assert serialized['type'] == 'dict'
        assert serialized['value']['timestamp'] == 'datetime'
        assert serialized['value']['date'] is None
    
    def test_interval_detection_result(self):
        """Test serialization of interval detection result."""
        result = {
            'interval_minutes': 5,
            'detection_method': 'time_periods',
            'confidence': 'high'
        }
        
        serialized = serialize_tool_result(result)
        
        assert serialized['type'] == 'dict'
        assert serialized['value']['interval_minutes'] == 5
    
    def test_validation_warnings_result(self):
        """Test serialization of validation warnings."""
        warnings = [
            'Missing 5 time periods in sequence',
            'Found 2 duplicate periods (possible DST transition)',
            'Detected 1 negative consumption value'
        ]
        
        serialized = serialize_tool_result(warnings)
        
        assert serialized['type'] == 'list'
        assert len(serialized['value']) == 3
        assert 'Missing' in serialized['value'][0]
    
    def test_calculation_summary_result(self):
        """Test serialization of calculation summary."""
        summary = {
            'total_consumption_kwh': 1250.5,
            'interval_emissions_tonnes': 0.938,
            'annual_emissions_tonnes': 0.900,
            'percentage_difference': 4.22,
            'unmatched_records': 0
        }
        
        serialized = serialize_tool_result(summary)
        
        assert serialized['type'] == 'dict'
        assert serialized['value']['total_consumption_kwh'] == 1250.5
        assert serialized['value']['percentage_difference'] == 4.22


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
