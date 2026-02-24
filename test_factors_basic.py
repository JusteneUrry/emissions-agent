"""
Basic tests for emissions factors module.
"""

import pytest
import pandas as pd
from pathlib import Path

from emissions.factors import (
    load_interval_factors,
    load_annual_factors,
    get_factor_metadata
)


def test_load_interval_factors_nsw_5min():
    """Test loading 5-minute interval factors for NSW."""
    df = load_interval_factors('NSW', 5)
    
    # Check that we got results
    assert len(df) > 0
    
    # Check that all rows are for NSW and 5-minute interval
    assert all(df['state'] == 'NSW')
    assert all(df['interval_minutes'] == 5)
    
    # Check required columns exist
    required_cols = [
        'state', 'interval_minutes', 'emissions_period_code',
        'factor_g_per_kwh', 'source', 'dataset_version'
    ]
    for col in required_cols:
        assert col in df.columns


def test_load_interval_factors_vic_30min():
    """Test loading 30-minute interval factors for VIC."""
    df = load_interval_factors('VIC', 30)
    
    # Check that we got results
    assert len(df) > 0
    
    # Check that all rows are for VIC and 30-minute interval
    assert all(df['state'] == 'VIC')
    assert all(df['interval_minutes'] == 30)


def test_load_interval_factors_missing_file():
    """Test that FileNotFoundError is raised for missing file."""
    with pytest.raises(FileNotFoundError):
        load_interval_factors('NSW', 5, factors_dir='nonexistent_directory')


def test_load_annual_factors_nsw():
    """Test loading annual factors for NSW."""
    df = load_annual_factors('NSW')
    
    # Check that we got results
    assert len(df) > 0
    
    # Check that all rows are for NSW
    assert all(df['state'] == 'NSW')
    
    # Check required columns exist
    required_cols = [
        'state', 'year', 'annual_factor_g_per_kwh',
        'source', 'dataset_version'
    ]
    for col in required_cols:
        assert col in df.columns


def test_load_annual_factors_all_states():
    """Test loading annual factors for all states."""
    states = ['NSW', 'VIC', 'QLD', 'SA', 'TAS']
    
    for state in states:
        df = load_annual_factors(state)
        assert len(df) > 0
        assert all(df['state'] == state)


def test_load_annual_factors_missing_file():
    """Test that FileNotFoundError is raised for missing file."""
    with pytest.raises(FileNotFoundError):
        load_annual_factors('NSW', factors_dir='nonexistent_directory')


def test_get_factor_metadata():
    """Test extracting metadata from README."""
    metadata = get_factor_metadata()
    
    # Check that metadata dictionary has expected keys
    assert 'source' in metadata
    assert 'version' in metadata
    assert 'methodology' in metadata
    assert 'raw_content' in metadata
    
    # Check that raw content is not empty
    assert len(metadata['raw_content']) > 0
    
    # Check that we extracted some information
    assert metadata['source'] is not None
    assert metadata['version'] is not None
    assert metadata['methodology'] is not None


def test_get_factor_metadata_missing_file():
    """Test that FileNotFoundError is raised for missing README."""
    with pytest.raises(FileNotFoundError):
        get_factor_metadata(factors_dir='nonexistent_directory')


def test_interval_factors_filtering():
    """Test that filtering works correctly for different states and intervals."""
    # Load NSW 5-minute factors
    nsw_5min = load_interval_factors('NSW', 5)
    
    # Load NSW 30-minute factors
    nsw_30min = load_interval_factors('NSW', 30)
    
    # They should be different
    assert len(nsw_5min) != len(nsw_30min)
    
    # Load VIC 5-minute factors
    vic_5min = load_interval_factors('VIC', 5)
    
    # NSW and VIC should be different
    assert not nsw_5min.equals(vic_5min)


def test_annual_factors_multiple_years():
    """Test that annual factors include multiple years."""
    df = load_annual_factors('NSW')
    
    # Check that we have multiple years
    years = df['year'].unique()
    assert len(years) > 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
