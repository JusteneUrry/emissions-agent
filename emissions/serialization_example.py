"""
Example usage of the serialization module for AWS Bedrock agent tools.

This file demonstrates how to use the serialization utilities to convert
pandas DataFrames and other Python types to JSON-serializable formats
suitable for AWS Bedrock agent tool integration.
"""

import pandas as pd
from datetime import datetime
from emissions.serialization import (
    dataframe_to_json,
    json_to_dataframe,
    serialize_tool_result
)


def example_basic_dataframe():
    """Example: Serialize a basic DataFrame."""
    print("=" * 60)
    print("Example 1: Basic DataFrame Serialization")
    print("=" * 60)
    
    # Create a sample DataFrame
    df = pd.DataFrame({
        'state': ['NSW', 'VIC', 'QLD'],
        'factor': [720.0, 890.0, 810.0],
        'year': [2023, 2023, 2023]
    })
    
    print("\nOriginal DataFrame:")
    print(df)
    
    # Serialize to JSON
    serialized = dataframe_to_json(df)
    
    print("\nSerialized format:")
    print(f"Row count: {serialized['metadata']['row_count']}")
    print(f"Columns: {serialized['metadata']['columns']}")
    print(f"First record: {serialized['data'][0]}")
    
    # Reconstruct DataFrame
    reconstructed = json_to_dataframe(serialized)
    
    print("\nReconstructed DataFrame:")
    print(reconstructed)
    print()


def example_datetime_handling():
    """Example: Serialize DataFrame with datetime columns."""
    print("=" * 60)
    print("Example 2: DateTime Handling")
    print("=" * 60)
    
    # Create DataFrame with datetime
    df = pd.DataFrame({
        'timestamp': pd.to_datetime(['2023-01-01 00:00', '2023-01-01 00:05']),
        'consumption_kwh': [10.5, 12.3]
    })
    
    print("\nOriginal DataFrame:")
    print(df)
    print(f"Timestamp dtype: {df['timestamp'].dtype}")
    
    # Serialize
    serialized = dataframe_to_json(df)
    
    print("\nSerialized timestamp (ISO format):")
    print(serialized['data'][0]['timestamp'])
    
    # Reconstruct
    reconstructed = json_to_dataframe(serialized)
    
    print("\nReconstructed DataFrame:")
    print(reconstructed)
    print(f"Timestamp dtype: {reconstructed['timestamp'].dtype}")
    print()


def example_nan_handling():
    """Example: Serialize DataFrame with NaN values."""
    print("=" * 60)
    print("Example 3: NaN Value Handling")
    print("=" * 60)
    
    # Create DataFrame with NaN
    df = pd.DataFrame({
        'consumption': [10.0, None, 15.0],
        'factor': [750.0, 755.0, None]
    })
    
    print("\nOriginal DataFrame:")
    print(df)
    
    # Serialize (NaN becomes None/null in JSON)
    serialized = dataframe_to_json(df)
    
    print("\nSerialized data (NaN → None):")
    for i, record in enumerate(serialized['data']):
        print(f"Record {i}: {record}")
    
    # Reconstruct
    reconstructed = json_to_dataframe(serialized)
    
    print("\nReconstructed DataFrame:")
    print(reconstructed)
    print()


def example_tool_result_dict():
    """Example: Serialize a tool result with mixed types."""
    print("=" * 60)
    print("Example 4: Tool Result with Mixed Types")
    print("=" * 60)
    
    # Simulate a tool result
    df = pd.DataFrame({
        'state': ['NSW', 'VIC'],
        'factor': [720.0, 890.0]
    })
    
    tool_result = {
        'factors': df,
        'count': len(df),
        'states': ['NSW', 'VIC'],
        'timestamp': datetime(2023, 1, 1, 12, 0, 0)
    }
    
    print("\nOriginal tool result:")
    print(f"- factors: DataFrame with {len(df)} rows")
    print(f"- count: {tool_result['count']}")
    print(f"- states: {tool_result['states']}")
    print(f"- timestamp: {tool_result['timestamp']}")
    
    # Serialize
    serialized = serialize_tool_result(tool_result)
    
    print("\nSerialized format:")
    print(f"Type: {serialized['type']}")
    print(f"Keys in value: {list(serialized['value'].keys())}")
    print(f"Timestamp (ISO): {serialized['value']['timestamp']}")
    print()


def example_emissions_calculation_result():
    """Example: Serialize emissions calculation results."""
    print("=" * 60)
    print("Example 5: Emissions Calculation Results")
    print("=" * 60)
    
    # Simulate emissions calculation results
    results_df = pd.DataFrame({
        'datetime': pd.to_datetime(['2023-01-01 00:00', '2023-01-01 00:05']),
        'emissions_period_code': ['20230101001', '20230101002'],
        'consumption_kwh': [10.0, 15.0],
        'factor_g_per_kwh': [750.5, 755.2],
        'emissions_tonnes': [0.007505, 0.011328]
    })
    
    summary = {
        'total_consumption_kwh': 25.0,
        'total_emissions_tonnes': 0.018833,
        'record_count': 2
    }
    
    print("\nResults DataFrame:")
    print(results_df)
    
    print("\nSummary:")
    print(summary)
    
    # Serialize both
    serialized_df = dataframe_to_json(results_df)
    serialized_summary = serialize_tool_result(summary)
    
    print("\nSerialized DataFrame metadata:")
    print(f"Rows: {serialized_df['metadata']['row_count']}")
    print(f"Columns: {serialized_df['metadata']['columns']}")
    
    print("\nSerialized summary:")
    print(serialized_summary['value'])
    print()


def example_agent_tool_wrapper():
    """Example: How to wrap an emissions function as an agent tool."""
    print("=" * 60)
    print("Example 6: Agent Tool Wrapper Pattern")
    print("=" * 60)
    
    # Simulate an emissions module function
    def load_interval_factors(state: str, interval_minutes: int) -> pd.DataFrame:
        """Mock function that returns emissions factors."""
        return pd.DataFrame({
            'state': [state, state],
            'interval_minutes': [interval_minutes, interval_minutes],
            'emissions_period_code': ['20230101001', '20230101002'],
            'factor_g_per_kwh': [750.5, 755.2]
        })
    
    # Agent tool wrapper
    def agent_tool_load_interval_factors(state: str, interval_minutes: int) -> dict:
        """
        Agent tool wrapper for load_interval_factors.
        
        This wrapper:
        1. Calls the original function
        2. Serializes the DataFrame result
        3. Returns JSON-serializable dict for Bedrock
        """
        try:
            # Call original function
            result_df = load_interval_factors(state, interval_minutes)
            
            # Serialize for agent
            serialized = dataframe_to_json(result_df)
            
            # Return with success status
            return {
                'success': True,
                'data': serialized,
                'message': f'Loaded {len(result_df)} factors for {state} at {interval_minutes}-minute interval'
            }
        except Exception as e:
            # Return structured error
            return {
                'success': False,
                'error': str(e),
                'message': f'Failed to load factors: {str(e)}'
            }
    
    # Use the agent tool
    print("\nCalling agent tool wrapper...")
    result = agent_tool_load_interval_factors('NSW', 5)
    
    print(f"\nSuccess: {result['success']}")
    print(f"Message: {result['message']}")
    print(f"Data rows: {result['data']['metadata']['row_count']}")
    print(f"Data columns: {result['data']['metadata']['columns']}")
    print()


if __name__ == '__main__':
    # Run all examples
    example_basic_dataframe()
    example_datetime_handling()
    example_nan_handling()
    example_tool_result_dict()
    example_emissions_calculation_result()
    example_agent_tool_wrapper()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
