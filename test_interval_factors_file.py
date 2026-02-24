#!/usr/bin/env python3
"""Test that interval_factors.csv works with emissions/factors.py"""
from emissions.factors import load_interval_factors

# Test loading for each state and interval combination
print("Testing load_interval_factors():\n")

for state in ['TAS', 'SA', 'NSW', 'QLD', 'VIC']:
    for interval in [5, 30]:
        df = load_interval_factors(state, interval)
        print(f"✓ {state} @ {interval}min: {len(df)} rows")
        
        # Verify columns
        expected_cols = ['state', 'interval_minutes', 'emissions_period_code', 
                        'factor_g_per_kwh', 'source', 'dataset_version']
        assert list(df.columns) == expected_cols, f"Column mismatch for {state}/{interval}"
        
        # Verify all rows match the filter
        assert (df['state'] == state).all(), f"State mismatch in {state}/{interval}"
        assert (df['interval_minutes'] == interval).all(), f"Interval mismatch in {state}/{interval}"
        
        # Verify data types
        assert df['factor_g_per_kwh'].dtype in ['float64', 'float32'], f"Factor should be float"
        assert df['interval_minutes'].dtype in ['int64', 'int32'], f"Interval should be int"

print("\n✓ All tests passed! File format is correct.")
