"""
Quick test for create_summary_metrics function.
"""

from emissions.viz import create_summary_metrics


def test_create_summary_metrics_basic():
    """Test basic summary metrics formatting."""
    metrics = create_summary_metrics(
        total_consumption=1234.567,
        interval_emissions=0.456,
        annual_emissions=0.489,
        percentage_diff=7.23
    )
    
    assert metrics['total_consumption_kwh'] == '1234.57 kWh'
    assert metrics['interval_emissions_tonnes'] == '0.46 tonnes CO2-e'
    assert metrics['annual_emissions_tonnes'] == '0.49 tonnes CO2-e'
    assert metrics['percentage_difference'] == '+7.23%'
    print("✓ Basic formatting test passed")


def test_create_summary_metrics_negative_percentage():
    """Test formatting with negative percentage difference."""
    metrics = create_summary_metrics(
        total_consumption=5000.0,
        interval_emissions=1.5,
        annual_emissions=1.2,
        percentage_diff=-20.0
    )
    
    assert metrics['total_consumption_kwh'] == '5000.00 kWh'
    assert metrics['interval_emissions_tonnes'] == '1.50 tonnes CO2-e'
    assert metrics['annual_emissions_tonnes'] == '1.20 tonnes CO2-e'
    assert metrics['percentage_difference'] == '-20.00%'
    print("✓ Negative percentage test passed")


def test_create_summary_metrics_zero_percentage():
    """Test formatting with zero percentage difference."""
    metrics = create_summary_metrics(
        total_consumption=1000.0,
        interval_emissions=0.5,
        annual_emissions=0.5,
        percentage_diff=0.0
    )
    
    assert metrics['percentage_difference'] == '+0.00%'
    print("✓ Zero percentage test passed")


def test_create_summary_metrics_large_values():
    """Test formatting with large values."""
    metrics = create_summary_metrics(
        total_consumption=123456.789,
        interval_emissions=45.678,
        annual_emissions=50.123,
        percentage_diff=9.75
    )
    
    assert metrics['total_consumption_kwh'] == '123456.79 kWh'
    assert metrics['interval_emissions_tonnes'] == '45.68 tonnes CO2-e'
    assert metrics['annual_emissions_tonnes'] == '50.12 tonnes CO2-e'
    assert metrics['percentage_difference'] == '+9.75%'
    print("✓ Large values test passed")


if __name__ == '__main__':
    test_create_summary_metrics_basic()
    test_create_summary_metrics_negative_percentage()
    test_create_summary_metrics_zero_percentage()
    test_create_summary_metrics_large_values()
    print("\n✅ All tests passed!")
