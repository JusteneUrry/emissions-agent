"""Basic unit tests for emissions calculation module."""

import pandas as pd
import pytest
from emissions.calc import calculate_interval_emissions


def test_calculate_interval_emissions_basic():
    """Test basic interval emissions calculation with matching factors."""
    # Create sample consumption data
    consumption = pd.DataFrame({
        'emissions_period_code': ['20230101001', '20230101002', '20230101003'],
        'consumption_kwh': [10.0, 15.0, 20.0]
    })
    
    # Create sample emissions factors
    factors = pd.DataFrame({
        'emissions_period_code': ['20230101001', '20230101002', '20230101003'],
        'factor_g_per_kwh': [750.0, 800.0, 850.0]
    })
    
    # Calculate emissions
    results, total = calculate_interval_emissions(
        consumption, factors, 'consumption_kwh', 'emissions_period_code'
    )
    
    # Verify results DataFrame has expected columns
    assert 'factor_g_per_kwh' in results.columns
    assert 'emissions_g' in results.columns
    assert 'emissions_tonnes' in results.columns
    
    # Verify calculations
    # Record 1: 10.0 * 750.0 = 7500.0 g = 0.0075 tonnes
    # Record 2: 15.0 * 800.0 = 12000.0 g = 0.012 tonnes
    # Record 3: 20.0 * 850.0 = 17000.0 g = 0.017 tonnes
    # Total: 0.0365 tonnes
    expected_total = (10.0 * 750.0 + 15.0 * 800.0 + 20.0 * 850.0) / 1_000_000
    assert abs(total - expected_total) < 0.0001
    assert abs(total - 0.0365) < 0.0001


def test_calculate_interval_emissions_with_unmatched():
    """Test emissions calculation with some unmatched records."""
    # Create consumption data with some records that won't match
    consumption = pd.DataFrame({
        'emissions_period_code': ['20230101001', '20230101002', '20230101003', '20230101004'],
        'consumption_kwh': [10.0, 15.0, 20.0, 25.0]
    })
    
    # Create factors that only match first 2 records
    factors = pd.DataFrame({
        'emissions_period_code': ['20230101001', '20230101002'],
        'factor_g_per_kwh': [750.0, 800.0]
    })
    
    # Calculate emissions
    results, total = calculate_interval_emissions(
        consumption, factors, 'consumption_kwh', 'emissions_period_code'
    )
    
    # Verify only matched records contribute to total
    # Record 1: 10.0 * 750.0 = 7500.0 g = 0.0075 tonnes
    # Record 2: 15.0 * 800.0 = 12000.0 g = 0.012 tonnes
    # Records 3 and 4 should be excluded (no matching factors)
    expected_total = (10.0 * 750.0 + 15.0 * 800.0) / 1_000_000
    assert abs(total - expected_total) < 0.0001
    
    # Verify unmatched records have NaN for factor and emissions
    assert pd.isna(results.iloc[2]['factor_g_per_kwh'])
    assert pd.isna(results.iloc[3]['factor_g_per_kwh'])


def test_calculate_interval_emissions_empty_consumption():
    """Test handling of empty consumption DataFrame."""
    consumption = pd.DataFrame()
    factors = pd.DataFrame({
        'emissions_period_code': ['20230101001'],
        'factor_g_per_kwh': [750.0]
    })
    
    results, total = calculate_interval_emissions(
        consumption, factors, 'consumption_kwh', 'emissions_period_code'
    )
    
    assert results.empty
    assert total == 0.0


def test_calculate_interval_emissions_empty_factors():
    """Test handling of empty factors DataFrame."""
    consumption = pd.DataFrame({
        'emissions_period_code': ['20230101001'],
        'consumption_kwh': [10.0]
    })
    factors = pd.DataFrame()
    
    results, total = calculate_interval_emissions(
        consumption, factors, 'consumption_kwh', 'emissions_period_code'
    )
    
    assert results.empty
    assert total == 0.0


def test_calculate_interval_emissions_missing_column():
    """Test error handling for missing required columns."""
    consumption = pd.DataFrame({
        'emissions_period_code': ['20230101001'],
        'wrong_column': [10.0]
    })
    factors = pd.DataFrame({
        'emissions_period_code': ['20230101001'],
        'factor_g_per_kwh': [750.0]
    })
    
    with pytest.raises(ValueError, match="Consumption column"):
        calculate_interval_emissions(
            consumption, factors, 'consumption_kwh', 'emissions_period_code'
        )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])



def test_calculate_annual_emissions_basic():
    """Test basic annual emissions calculation with financial year mapping."""
    from emissions.calc import calculate_annual_emissions
    
    # Create sample consumption data spanning financial year boundary
    # FY runs July-June, so dates in July-Dec map to current year, Jan-Jun map to previous year
    consumption = pd.DataFrame({
        'datetime': pd.to_datetime([
            '2022-08-15 00:05:00',  # Aug 2022 → FY2022
            '2022-12-20 00:10:00',  # Dec 2022 → FY2022
            '2023-03-10 00:05:00'   # Mar 2023 → FY2022
        ]),
        'consumption_kwh': [10.0, 15.0, 20.0]
    })
    
    # Create sample annual emissions factors
    factors = pd.DataFrame({
        'year': [2022, 2023],
        'annual_factor_g_per_kwh': [720.0, 730.0]
    })
    
    # Calculate emissions
    results, total = calculate_annual_emissions(
        consumption, factors, 'consumption_kwh', 'datetime'
    )
    
    # Verify results DataFrame has expected columns
    assert 'financial_year' in results.columns
    assert 'annual_factor_g_per_kwh' in results.columns
    assert 'annual_emissions_g' in results.columns
    assert 'annual_emissions_tonnes' in results.columns
    
    # Verify financial year extraction
    # Aug 2022 → FY2022, Dec 2022 → FY2022, Mar 2023 → FY2022
    assert results.iloc[0]['financial_year'] == 2022
    assert results.iloc[1]['financial_year'] == 2022
    assert results.iloc[2]['financial_year'] == 2022
    
    # Verify calculations - all use FY2022 factor (720.0)
    # Record 1: 10.0 * 720.0 = 7200.0 g = 0.0072 tonnes
    # Record 2: 15.0 * 720.0 = 10800.0 g = 0.0108 tonnes
    # Record 3: 20.0 * 720.0 = 14400.0 g = 0.0144 tonnes
    # Total: 0.0324 tonnes
    expected_total = (10.0 * 720.0 + 15.0 * 720.0 + 20.0 * 720.0) / 1_000_000
    assert abs(total - expected_total) < 0.0001
    assert abs(total - 0.0324) < 0.0001


def test_calculate_annual_emissions_multi_year():
    """Test annual emissions calculation across financial year boundaries."""
    from emissions.calc import calculate_annual_emissions
    
    # Create consumption data testing FY boundary
    # June 2022 → FY2021, August 2022 → FY2022, June 2023 → FY2022
    consumption = pd.DataFrame({
        'datetime': pd.to_datetime([
            '2022-06-15 12:00:00',  # June 2022 → FY2021
            '2022-08-15 12:00:00',  # Aug 2022 → FY2022
            '2023-06-15 12:00:00'   # June 2023 → FY2022
        ]),
        'consumption_kwh': [100.0, 150.0, 200.0]
    })
    
    # Create annual factors for each financial year
    factors = pd.DataFrame({
        'year': [2021, 2022, 2023],
        'annual_factor_g_per_kwh': [700.0, 720.0, 730.0]
    })
    
    # Calculate emissions
    results, total = calculate_annual_emissions(
        consumption, factors, 'consumption_kwh', 'datetime'
    )
    
    # Verify financial year mapping
    assert results.iloc[0]['financial_year'] == 2021  # June 2022 → FY2021
    assert results.iloc[1]['financial_year'] == 2022  # Aug 2022 → FY2022
    assert results.iloc[2]['financial_year'] == 2022  # June 2023 → FY2022
    
    # Verify each record matched to correct year's factor
    assert results.iloc[0]['annual_factor_g_per_kwh'] == 700.0  # FY2021 factor
    assert results.iloc[1]['annual_factor_g_per_kwh'] == 720.0  # FY2022 factor
    assert results.iloc[2]['annual_factor_g_per_kwh'] == 720.0  # FY2022 factor
    
    # Verify total
    expected_total = (100.0 * 700.0 + 150.0 * 720.0 + 200.0 * 720.0) / 1_000_000
    assert abs(total - expected_total) < 0.0001


def test_calculate_annual_emissions_financial_year_boundary():
    """Test financial year mapping across FY boundary."""
    from emissions.calc import calculate_annual_emissions
    
    # Test dates around FY2022-23 boundary
    consumption = pd.DataFrame({
        'datetime': pd.to_datetime([
            '2022-06-30 23:55:00',  # Last day of FY2021-22 → FY2021
            '2022-07-01 00:05:00',  # First day of FY2022-23 → FY2022
            '2022-12-15 12:00:00',  # Mid FY2022-23 → FY2022
            '2023-01-15 12:00:00',  # Mid FY2022-23 → FY2022
            '2023-06-30 23:55:00',  # Last day of FY2022-23 → FY2022
            '2023-07-01 00:05:00',  # First day of FY2023-24 → FY2023
        ]),
        'consumption_kwh': [10.0, 10.0, 10.0, 10.0, 10.0, 10.0]
    })
    
    # Create factors for FY2021-22, FY2022-23, FY2023-24
    factors = pd.DataFrame({
        'year': [2021, 2022, 2023],
        'annual_factor_g_per_kwh': [700.0, 720.0, 730.0]
    })
    
    # Calculate emissions
    results, total = calculate_annual_emissions(
        consumption, factors, 'consumption_kwh', 'datetime'
    )
    
    # Verify financial year mapping
    assert results.iloc[0]['financial_year'] == 2021  # June 2022 → FY2021
    assert results.iloc[1]['financial_year'] == 2022  # July 2022 → FY2022
    assert results.iloc[2]['financial_year'] == 2022  # Dec 2022 → FY2022
    assert results.iloc[3]['financial_year'] == 2022  # Jan 2023 → FY2022
    assert results.iloc[4]['financial_year'] == 2022  # June 2023 → FY2022
    assert results.iloc[5]['financial_year'] == 2023  # July 2023 → FY2023
    
    # Verify correct factors applied
    assert results.iloc[0]['annual_factor_g_per_kwh'] == 700.0
    assert results.iloc[1]['annual_factor_g_per_kwh'] == 720.0
    assert results.iloc[5]['annual_factor_g_per_kwh'] == 730.0
    
    # Verify total calculation
    expected_total = (10.0 * 700.0 + 4 * 10.0 * 720.0 + 10.0 * 730.0) / 1_000_000
    assert abs(total - expected_total) < 0.0001


def test_calculate_annual_emissions_with_unmatched():
    """Test annual emissions calculation with some unmatched years."""
    from emissions.calc import calculate_annual_emissions
    
    # Create consumption data with a year that has no factor
    # Use dates that will map to specific financial years
    consumption = pd.DataFrame({
        'datetime': pd.to_datetime([
            '2023-08-01',  # Aug 2023 → FY2023
            '2024-08-01',  # Aug 2024 → FY2024
            '2025-08-01'   # Aug 2025 → FY2025 (no factor)
        ]),
        'consumption_kwh': [10.0, 15.0, 20.0]
    })
    
    # Create factors that only match first 2 financial years
    factors = pd.DataFrame({
        'year': [2023, 2024],
        'annual_factor_g_per_kwh': [720.0, 730.0]
    })
    
    # Calculate emissions
    results, total = calculate_annual_emissions(
        consumption, factors, 'consumption_kwh', 'datetime'
    )
    
    # Verify only matched records contribute to total
    expected_total = (10.0 * 720.0 + 15.0 * 730.0) / 1_000_000
    assert abs(total - expected_total) < 0.0001
    
    # Verify unmatched record has NaN for factor and emissions
    assert pd.isna(results.iloc[2]['annual_factor_g_per_kwh'])
    assert pd.isna(results.iloc[2]['annual_emissions_g'])


def test_calculate_annual_emissions_empty_consumption():
    """Test handling of empty consumption DataFrame."""
    from emissions.calc import calculate_annual_emissions
    
    consumption = pd.DataFrame()
    factors = pd.DataFrame({
        'year': [2023],
        'annual_factor_g_per_kwh': [720.0]
    })
    
    results, total = calculate_annual_emissions(
        consumption, factors, 'consumption_kwh', 'datetime'
    )
    
    assert results.empty
    assert total == 0.0


def test_calculate_annual_emissions_empty_factors():
    """Test handling of empty factors DataFrame."""
    from emissions.calc import calculate_annual_emissions
    
    consumption = pd.DataFrame({
        'datetime': pd.to_datetime(['2023-01-01']),
        'consumption_kwh': [10.0]
    })
    factors = pd.DataFrame()
    
    results, total = calculate_annual_emissions(
        consumption, factors, 'consumption_kwh', 'datetime'
    )
    
    assert results.empty
    assert total == 0.0


def test_calculate_annual_emissions_missing_column():
    """Test error handling for missing required columns."""
    from emissions.calc import calculate_annual_emissions
    
    consumption = pd.DataFrame({
        'datetime': pd.to_datetime(['2023-01-01']),
        'wrong_column': [10.0]
    })
    factors = pd.DataFrame({
        'year': [2023],
        'annual_factor_g_per_kwh': [720.0]
    })
    
    with pytest.raises(ValueError, match="Consumption column"):
        calculate_annual_emissions(
            consumption, factors, 'consumption_kwh', 'datetime'
        )



def test_calculate_percentage_difference_positive():
    """Test percentage difference when interval > annual."""
    from emissions.calc import calculate_percentage_difference
    
    # Interval emissions higher than annual
    result = calculate_percentage_difference(105.0, 100.0)
    assert abs(result - 5.0) < 0.0001


def test_calculate_percentage_difference_negative():
    """Test percentage difference when interval < annual."""
    from emissions.calc import calculate_percentage_difference
    
    # Interval emissions lower than annual
    result = calculate_percentage_difference(95.0, 100.0)
    assert abs(result - (-5.0)) < 0.0001


def test_calculate_percentage_difference_zero():
    """Test percentage difference when interval equals annual."""
    from emissions.calc import calculate_percentage_difference
    
    # Interval emissions equal to annual
    result = calculate_percentage_difference(100.0, 100.0)
    assert abs(result - 0.0) < 0.0001


def test_calculate_percentage_difference_large_difference():
    """Test percentage difference with large differences."""
    from emissions.calc import calculate_percentage_difference
    
    # Interval emissions 50% higher
    result = calculate_percentage_difference(150.0, 100.0)
    assert abs(result - 50.0) < 0.0001
    
    # Interval emissions 50% lower
    result = calculate_percentage_difference(50.0, 100.0)
    assert abs(result - (-50.0)) < 0.0001


def test_calculate_percentage_difference_zero_annual():
    """Test error handling when annual total is zero."""
    from emissions.calc import calculate_percentage_difference
    
    with pytest.raises(ValueError, match="Annual total cannot be zero"):
        calculate_percentage_difference(100.0, 0.0)


def test_calculate_percentage_difference_small_values():
    """Test percentage difference with small emission values."""
    from emissions.calc import calculate_percentage_difference
    
    # Small values with 2% difference
    result = calculate_percentage_difference(0.0102, 0.01)
    assert abs(result - 2.0) < 0.0001
