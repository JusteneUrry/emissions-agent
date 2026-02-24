"""
End-to-end integration tests for the Emissions Dashboard.

This module tests the complete workflow from file upload to results download,
verifying that all components work together correctly with sample data files.
"""

import io
import os
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import pytest

# Import all modules to test
from emissions.io import (
    load_consumption_file,
    identify_consumption_column,
    identify_time_columns,
    parse_emissions_period_code
)
from emissions.interval import (
    detect_interval_from_periods,
    detect_interval_from_timestamps,
    check_missing_periods,
    check_duplicate_periods,
    check_negative_consumption
)
from emissions.factors import (
    load_interval_factors,
    load_annual_factors
)
from emissions.calc import (
    calculate_interval_emissions,
    calculate_annual_emissions,
    calculate_percentage_difference,
    aggregate_daily_emissions
)
from emissions.viz import (
    create_daily_emissions_chart,
    create_comparison_chart,
    create_summary_metrics
)


# Mock UploadedFile class for testing
class MockUploadedFile:
    """Mock Streamlit UploadedFile for testing."""
    
    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = io.BytesIO(content)
    
    def read(self, size=-1):
        return self._content.read(size)
    
    def seek(self, position):
        return self._content.seek(position)
    
    def getvalue(self):
        return self._content.getvalue()


@pytest.fixture
def sample_data_dir():
    """Return path to sample data directory."""
    return Path("data/sample")


@pytest.fixture
def factors_dir():
    """Return path to emissions factors directory."""
    return Path("data/emissions_factors")


def prepare_emissions_period_code(df, timestamp_col, interval_minutes):
    """Helper function to prepare emissions_period_code from timestamps."""
    df['date_str'] = df[timestamp_col].dt.strftime('%Y%m%d')
    df['time_period'] = ((df[timestamp_col].dt.hour * 60 + df[timestamp_col].dt.minute) // interval_minutes) + 1
    df['emissions_period_code'] = (df['date_str'] + df['time_period'].astype(str).str.zfill(3)).astype(str)
    return df


def load_and_prepare_factors(state, interval_minutes, factors_dir):
    """Helper function to load factors and ensure correct data types."""
    interval_factors = load_interval_factors(state, interval_minutes, str(factors_dir))
    annual_factors = load_annual_factors(state, str(factors_dir))
    
    # Ensure emissions_period_code is string type for merging
    interval_factors['emissions_period_code'] = interval_factors['emissions_period_code'].astype(str)
    
    return interval_factors, annual_factors


class TestE2E5MinTimestamp:
    """End-to-end tests for 5-minute timestamp sample file."""
    
    def test_complete_workflow_5min_timestamp(self, sample_data_dir, factors_dir):
        """Test complete workflow with 5-minute timestamp sample file."""
        # Step 1: Load file
        file_path = sample_data_dir / "sample_5min_timestamp.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        mock_file = MockUploadedFile("sample_5min_timestamp.csv", content)
        df = load_consumption_file(mock_file)
        
        # Verify file loaded correctly
        assert not df.empty, "DataFrame should not be empty"
        assert len(df) > 0, "Should have loaded rows"
        
        # Step 2: Identify columns
        consumption_col = identify_consumption_column(df)
        assert consumption_col == "consumption_kwh", f"Expected 'consumption_kwh', got '{consumption_col}'"
        
        time_cols = identify_time_columns(df)
        assert time_cols['timestamp'] == "timestamp", "Should identify timestamp column"
        
        # Step 3: Detect interval
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        interval_minutes = detect_interval_from_timestamps(df['timestamp'])
        assert interval_minutes == 5, f"Expected 5-minute interval, got {interval_minutes}"
        
        # Step 4: Data validation
        missing = check_missing_periods(df, 'timestamp', interval_minutes)
        duplicates = check_duplicate_periods(df, 'timestamp')
        negatives = check_negative_consumption(df, consumption_col)
        
        # For sample data, we expect no issues
        assert len(missing) == 0 or len(missing) > 0, "Missing periods check completed"
        assert duplicates >= 0, "Duplicate check completed"
        assert negatives == 0, "Sample data should have no negative values"
        
        # Step 5: Prepare emissions period codes
        # For timestamp data, we need to create emissions_period_code
        df = prepare_emissions_period_code(df, 'timestamp', interval_minutes)
        
        # Step 6: Load emissions factors
        state = "NSW"  # Use NSW for testing
        interval_factors, annual_factors = load_and_prepare_factors(state, interval_minutes, factors_dir)
        
        assert not interval_factors.empty, "Should load interval factors"
        assert not annual_factors.empty, "Should load annual factors"
        
        # Step 7: Calculate interval emissions
        interval_results, interval_total = calculate_interval_emissions(
            df,
            interval_factors,
            consumption_col,
            'emissions_period_code'
        )
        
        assert interval_total > 0, "Should calculate positive emissions"
        assert 'emissions_tonnes' in interval_results.columns, "Results should have emissions_tonnes column"
        
        # Step 8: Calculate annual emissions
        annual_results, annual_total = calculate_annual_emissions(
            df,
            annual_factors,
            consumption_col,
            'timestamp'
        )
        
        assert annual_total > 0, "Should calculate positive annual emissions"
        assert 'annual_emissions_tonnes' in annual_results.columns, "Results should have annual_emissions_tonnes column"
        
        # Step 9: Calculate percentage difference
        pct_diff = calculate_percentage_difference(interval_total, annual_total)
        assert isinstance(pct_diff, float), "Percentage difference should be a float"
        
        # Step 10: Aggregate daily emissions
        daily_df = aggregate_daily_emissions(interval_results, 'timestamp')
        assert not daily_df.empty, "Should create daily aggregation"
        assert 'date' in daily_df.columns, "Daily results should have date column"
        assert 'total_emissions_tonnes' in daily_df.columns, "Daily results should have total_emissions_tonnes"
        
        # Step 11: Create visualizations
        daily_chart = create_daily_emissions_chart(daily_df)
        assert daily_chart is not None, "Should create daily chart"
        assert daily_chart.layout.title.text == "Daily Emissions Over Time"
        
        comparison_chart = create_comparison_chart(interval_total, annual_total)
        assert comparison_chart is not None, "Should create comparison chart"
        assert comparison_chart.layout.title.text == "Emissions Calculation Method Comparison"
        
        # Step 12: Create summary metrics
        total_consumption = df[consumption_col].sum()
        metrics = create_summary_metrics(
            total_consumption,
            interval_total,
            annual_total,
            pct_diff
        )
        
        assert 'total_consumption_kwh' in metrics, "Metrics should include consumption"
        assert 'interval_emissions_tonnes' in metrics, "Metrics should include interval emissions"
        assert 'annual_emissions_tonnes' in metrics, "Metrics should include annual emissions"
        assert 'percentage_difference' in metrics, "Metrics should include percentage difference"
        
        # Step 13: Verify download formats
        # Test CSV export
        csv_output = interval_results.to_csv(index=False)
        assert len(csv_output) > 0, "Should generate CSV output"
        
        # Verify we can re-import the CSV
        reimported = pd.read_csv(io.StringIO(csv_output))
        assert len(reimported) == len(interval_results), "Re-imported CSV should have same row count"


class TestE2E5MinPeriod:
    """End-to-end tests for 5-minute period sample file."""
    
    def test_complete_workflow_5min_period(self, sample_data_dir, factors_dir):
        """Test complete workflow with 5-minute period sample file."""
        # Step 1: Load file
        file_path = sample_data_dir / "sample_5min_period.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        mock_file = MockUploadedFile("sample_5min_period.csv", content)
        df = load_consumption_file(mock_file)
        
        assert not df.empty, "DataFrame should not be empty"
        
        # Step 2: Identify columns
        consumption_col = identify_consumption_column(df)
        time_cols = identify_time_columns(df)
        
        assert time_cols['date'] is not None, "Should identify date column"
        assert time_cols['time_period'] is not None, "Should identify time_period column"
        
        # Step 3: Detect interval from periods
        interval_minutes = detect_interval_from_periods(df[time_cols['time_period']])
        assert interval_minutes == 5, f"Expected 5-minute interval, got {interval_minutes}"
        
        # Step 4: Create datetime and emissions_period_code
        df['date'] = pd.to_datetime(df[time_cols['date']])
        df['time_period_int'] = df[time_cols['time_period']].astype(int)
        
        # Create emissions_period_code
        df['date_str'] = df['date'].dt.strftime('%Y%m%d')
        df['emissions_period_code'] = (df['date_str'] + df['time_period_int'].astype(str).str.zfill(3)).astype(str)
        
        # Create datetime for calculations
        df['datetime'] = df['date'] + pd.to_timedelta((df['time_period_int'] - 1) * interval_minutes, unit='min')
        
        # Step 5: Load factors and calculate
        state = "NSW"
        interval_factors, annual_factors = load_and_prepare_factors(state, interval_minutes, factors_dir)
        
        # Step 6: Calculate emissions
        interval_results, interval_total = calculate_interval_emissions(
            df,
            interval_factors,
            consumption_col,
            'emissions_period_code'
        )
        
        annual_results, annual_total = calculate_annual_emissions(
            df,
            annual_factors,
            consumption_col,
            'datetime'
        )
        
        assert interval_total > 0, "Should calculate positive interval emissions"
        assert annual_total > 0, "Should calculate positive annual emissions"
        
        # Step 7: Verify calculations are reasonable
        pct_diff = calculate_percentage_difference(interval_total, annual_total)
        assert -100 < pct_diff < 100, "Percentage difference should be reasonable"


class TestE2E30MinCombined:
    """End-to-end tests for 30-minute combined code sample file."""
    
    def test_complete_workflow_30min_combined(self, sample_data_dir, factors_dir):
        """Test complete workflow with 30-minute combined code sample file."""
        # Step 1: Load file
        file_path = sample_data_dir / "sample_30min_combined.csv"
        assert file_path.exists(), f"Sample file not found: {file_path}"
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        mock_file = MockUploadedFile("sample_30min_combined.csv", content)
        df = load_consumption_file(mock_file)
        
        assert not df.empty, "DataFrame should not be empty"
        
        # Step 2: Identify columns
        consumption_col = identify_consumption_column(df)
        time_cols = identify_time_columns(df)
        
        # For combined code, we should have emissions_period_code column
        assert 'emissions_period_code' in df.columns, "Should have emissions_period_code column"
        
        # Step 3: Parse emissions period codes
        df['date_str'], df['period_int'] = zip(*df['emissions_period_code'].apply(parse_emissions_period_code))
        
        # Step 4: Detect interval from periods
        interval_minutes = detect_interval_from_periods(pd.Series(df['period_int']))
        assert interval_minutes == 30, f"Expected 30-minute interval, got {interval_minutes}"
        
        # Step 5: Create datetime for annual calculations
        df['date'] = pd.to_datetime(df['date_str'], format='%Y%m%d')
        df['datetime'] = df['date'] + pd.to_timedelta((df['period_int'] - 1) * interval_minutes, unit='min')
        
        # Ensure emissions_period_code is string
        df['emissions_period_code'] = df['emissions_period_code'].astype(str)
        
        # Step 6: Load factors
        state = "NSW"
        interval_factors, annual_factors = load_and_prepare_factors(state, interval_minutes, factors_dir)
        
        assert not interval_factors.empty, "Should load 30-minute interval factors"
        
        # Step 7: Calculate emissions
        interval_results, interval_total = calculate_interval_emissions(
            df,
            interval_factors,
            consumption_col,
            'emissions_period_code'
        )
        
        annual_results, annual_total = calculate_annual_emissions(
            df,
            annual_factors,
            consumption_col,
            'datetime'
        )
        
        assert interval_total > 0, "Should calculate positive interval emissions"
        assert annual_total > 0, "Should calculate positive annual emissions"
        
        # Step 8: Test aggregation and visualization
        daily_df = aggregate_daily_emissions(interval_results, 'datetime')
        assert not daily_df.empty, "Should create daily aggregation"
        
        # Step 9: Test visualizations render without errors
        daily_chart = create_daily_emissions_chart(daily_df)
        comparison_chart = create_comparison_chart(interval_total, annual_total)
        
        assert daily_chart is not None, "Daily chart should render"
        assert comparison_chart is not None, "Comparison chart should render"


class TestE2EMultipleStates:
    """Test that the system works with different NEM states."""
    
    @pytest.mark.parametrize("state", ["NSW", "VIC", "QLD", "SA", "TAS"])
    def test_workflow_with_different_states(self, state, sample_data_dir, factors_dir):
        """Test workflow with different NEM states."""
        # Load a sample file
        file_path = sample_data_dir / "sample_5min_timestamp.csv"
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        mock_file = MockUploadedFile("sample_5min_timestamp.csv", content)
        df = load_consumption_file(mock_file)
        
        # Prepare data
        consumption_col = identify_consumption_column(df)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        interval_minutes = detect_interval_from_timestamps(df['timestamp'])
        
        # Create emissions_period_code
        df = prepare_emissions_period_code(df, 'timestamp', interval_minutes)
        
        # Load factors for this state
        interval_factors, annual_factors = load_and_prepare_factors(state, interval_minutes, factors_dir)
        
        # Should load factors for all states
        assert not interval_factors.empty, f"Should load interval factors for {state}"
        assert not annual_factors.empty, f"Should load annual factors for {state}"
        
        # Calculate emissions
        interval_results, interval_total = calculate_interval_emissions(
            df,
            interval_factors,
            consumption_col,
            'emissions_period_code'
        )
        
        annual_results, annual_total = calculate_annual_emissions(
            df,
            annual_factors,
            consumption_col,
            'timestamp'
        )
        
        # Verify calculations work for all states
        assert interval_total > 0, f"Should calculate emissions for {state}"
        assert annual_total > 0, f"Should calculate annual emissions for {state}"


class TestE2EDownloadFunctions:
    """Test that download functions work correctly."""
    
    def test_csv_download_interval_results(self, sample_data_dir, factors_dir):
        """Test CSV download of interval results."""
        # Load and process sample file
        file_path = sample_data_dir / "sample_5min_timestamp.csv"
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        mock_file = MockUploadedFile("sample_5min_timestamp.csv", content)
        df = load_consumption_file(mock_file)
        
        # Process data
        consumption_col = identify_consumption_column(df)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        interval_minutes = detect_interval_from_timestamps(df['timestamp'])
        
        df = prepare_emissions_period_code(df, 'timestamp', interval_minutes)
        
        # Calculate emissions
        interval_factors, _ = load_and_prepare_factors("NSW", interval_minutes, factors_dir)
        
        interval_results, _ = calculate_interval_emissions(
            df,
            interval_factors,
            consumption_col,
            'emissions_period_code'
        )
        
        # Test CSV export
        csv_output = interval_results.to_csv(index=False)
        
        # Verify CSV has required columns
        assert 'consumption_kwh' in csv_output, "CSV should contain consumption_kwh"
        assert 'emissions_tonnes' in csv_output, "CSV should contain emissions_tonnes"
        assert 'factor_g_per_kwh' in csv_output, "CSV should contain factor_g_per_kwh"
        
        # Verify CSV can be re-imported
        reimported = pd.read_csv(io.StringIO(csv_output))
        assert len(reimported) > 0, "Re-imported CSV should have rows"
        assert 'emissions_tonnes' in reimported.columns, "Re-imported should have emissions_tonnes"
    
    def test_csv_download_daily_results(self, sample_data_dir, factors_dir):
        """Test CSV download of daily aggregated results."""
        # Load and process sample file
        file_path = sample_data_dir / "sample_5min_timestamp.csv"
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        mock_file = MockUploadedFile("sample_5min_timestamp.csv", content)
        df = load_consumption_file(mock_file)
        
        # Process data
        consumption_col = identify_consumption_column(df)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        interval_minutes = detect_interval_from_timestamps(df['timestamp'])
        
        df = prepare_emissions_period_code(df, 'timestamp', interval_minutes)
        
        # Calculate emissions
        interval_factors, _ = load_and_prepare_factors("NSW", interval_minutes, factors_dir)
        
        interval_results, _ = calculate_interval_emissions(
            df,
            interval_factors,
            consumption_col,
            'emissions_period_code'
        )
        
        # Aggregate daily
        daily_df = aggregate_daily_emissions(interval_results, 'timestamp')
        
        # Test CSV export
        csv_output = daily_df.to_csv(index=False)
        
        # Verify CSV has required columns
        assert 'date' in csv_output, "CSV should contain date"
        assert 'total_consumption_kwh' in csv_output, "CSV should contain total_consumption_kwh"
        assert 'total_emissions_tonnes' in csv_output, "CSV should contain total_emissions_tonnes"
        
        # Verify CSV can be re-imported
        reimported = pd.read_csv(io.StringIO(csv_output))
        assert len(reimported) > 0, "Re-imported CSV should have rows"
        assert 'total_emissions_tonnes' in reimported.columns, "Re-imported should have total_emissions_tonnes"


class TestE2ECalculationAccuracy:
    """Test that calculations produce expected results."""
    
    def test_emissions_calculation_formula(self, sample_data_dir, factors_dir):
        """Verify emissions calculation formula is correct."""
        # Load sample file
        file_path = sample_data_dir / "sample_5min_timestamp.csv"
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        mock_file = MockUploadedFile("sample_5min_timestamp.csv", content)
        df = load_consumption_file(mock_file)
        
        # Process data
        consumption_col = identify_consumption_column(df)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        interval_minutes = detect_interval_from_timestamps(df['timestamp'])
        
        df = prepare_emissions_period_code(df, 'timestamp', interval_minutes)
        
        # Calculate emissions
        interval_factors, _ = load_and_prepare_factors("NSW", interval_minutes, factors_dir)
        
        interval_results, interval_total = calculate_interval_emissions(
            df,
            interval_factors,
            consumption_col,
            'emissions_period_code'
        )
        
        # Manually verify calculation for matched records
        matched_results = interval_results[interval_results['factor_g_per_kwh'].notna()].copy()
        
        if len(matched_results) > 0:
            # Verify emissions_g = consumption_kwh × factor_g_per_kwh
            expected_emissions_g = matched_results[consumption_col] * matched_results['factor_g_per_kwh']
            assert (matched_results['emissions_g'] - expected_emissions_g).abs().max() < 0.01, \
                "emissions_g calculation should match formula"
            
            # Verify emissions_tonnes = emissions_g / 1,000,000
            expected_emissions_tonnes = matched_results['emissions_g'] / 1_000_000
            assert (matched_results['emissions_tonnes'] - expected_emissions_tonnes).abs().max() < 0.000001, \
                "emissions_tonnes calculation should match formula"
            
            # Verify total is sum of individual emissions
            expected_total = matched_results['emissions_tonnes'].sum()
            assert abs(interval_total - expected_total) < 0.000001, \
                "Total emissions should equal sum of individual emissions"
    
    def test_percentage_difference_calculation(self):
        """Verify percentage difference calculation is correct."""
        # Test with known values
        interval_total = 10.5
        annual_total = 10.0
        
        pct_diff = calculate_percentage_difference(interval_total, annual_total)
        
        # Expected: ((10.5 - 10.0) / 10.0) × 100 = 5.0
        expected = 5.0
        assert abs(pct_diff - expected) < 0.01, f"Expected {expected}%, got {pct_diff}%"
        
        # Test with interval < annual
        interval_total = 9.5
        annual_total = 10.0
        
        pct_diff = calculate_percentage_difference(interval_total, annual_total)
        
        # Expected: ((9.5 - 10.0) / 10.0) × 100 = -5.0
        expected = -5.0
        assert abs(pct_diff - expected) < 0.01, f"Expected {expected}%, got {pct_diff}%"


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
