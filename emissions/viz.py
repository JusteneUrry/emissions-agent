"""
Visualization module for the Emissions Dashboard.

This module provides functions for creating charts and visualizations of emissions data
using Plotly. It supports time series charts, comparisons, and other visual analytics.
"""

import pandas as pd
import plotly.graph_objects as go


def create_daily_emissions_chart(
    daily_df: pd.DataFrame,
    date_col: str = "date",
    emissions_col: str = "total_emissions_tonnes"
) -> go.Figure:
    """
    Create time series chart of daily emissions.
    
    This function generates a Plotly line chart showing emissions over time.
    The chart displays daily emissions values with properly labeled axes and title.
    
    Args:
        daily_df: DataFrame with daily aggregated emissions data (from aggregate_daily_emissions)
        date_col: Name of the date column (default: "date")
        emissions_col: Name of the emissions column (default: "total_emissions_tonnes")
        
    Returns:
        Plotly figure with line chart
        - X-axis: Date
        - Y-axis: Emissions (tonnes CO2-e)
        - Title: "Daily Emissions Over Time"
        
    Raises:
        ValueError: If required columns are missing from input DataFrame
        
    Examples:
        >>> daily_data = pd.DataFrame({
        ...     'date': [datetime.date(2023, 1, 1), datetime.date(2023, 1, 2)],
        ...     'total_emissions_tonnes': [0.5, 0.6]
        ... })
        >>> fig = create_daily_emissions_chart(daily_data)
        >>> fig.layout.title.text
        'Daily Emissions Over Time'
    """
    # Validate input DataFrame
    if daily_df.empty:
        # Return empty figure with proper layout
        fig = go.Figure()
        fig.update_layout(
            title="Daily Emissions Over Time",
            xaxis_title="Date",
            yaxis_title="Emissions (tonnes CO2-e)"
        )
        return fig
    
    # Validate required columns
    if date_col not in daily_df.columns:
        raise ValueError(f"Date column '{date_col}' not found in DataFrame")
    
    if emissions_col not in daily_df.columns:
        raise ValueError(f"Emissions column '{emissions_col}' not found in DataFrame")
    
    # Create line chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_df[date_col],
        y=daily_df[emissions_col],
        mode='lines',
        name='Daily Emissions'
    ))
    
    # Update layout with title and axis labels
    fig.update_layout(
        title="Daily Emissions Over Time",
        xaxis_title="Date",
        yaxis_title="Emissions (tonnes CO2-e)"
    )
    
    return fig


def create_comparison_chart(
    interval_total: float,
    annual_total: float
) -> go.Figure:
    """
    Create bar chart comparing calculation methods.
    
    This function generates a Plotly grouped bar chart comparing total emissions
    calculated using interval-based method versus annual average method.
    The chart displays both values side-by-side for easy comparison.
    
    Args:
        interval_total: Total emissions calculated from interval data (tonnes CO2-e)
        annual_total: Total emissions calculated from annual average (tonnes CO2-e)
        
    Returns:
        Plotly figure with grouped bar chart
        - Categories: "Interval-Based", "Annual Average"
        - Y-axis: Total Emissions (tonnes CO2-e)
        - Title: "Emissions Calculation Method Comparison"
        
    Examples:
        >>> fig = create_comparison_chart(interval_total=12.5, annual_total=13.2)
        >>> fig.layout.title.text
        'Emissions Calculation Method Comparison'
    """
    # Create bar chart with two categories
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=["Interval-Based", "Annual Average"],
        y=[interval_total, annual_total],
        name='Total Emissions'
    ))
    
    # Update layout with title and axis labels
    fig.update_layout(
        title="Emissions Calculation Method Comparison",
        xaxis_title="Calculation Method",
        yaxis_title="Total Emissions (tonnes CO2-e)"
    )
    
    return fig


def create_summary_metrics(
    total_consumption: float,
    interval_emissions: float,
    annual_emissions: float,
    percentage_diff: float
) -> dict[str, str]:
    """
    Format summary metrics for display.
    
    This function takes raw numeric values for consumption, emissions, and percentage
    difference, and formats them as human-readable strings with appropriate units
    and precision for display in the dashboard.
    
    Args:
        total_consumption: Total energy consumption in kWh
        interval_emissions: Emissions calculated from interval data in tonnes CO2-e
        annual_emissions: Emissions calculated from annual average in tonnes CO2-e
        percentage_diff: Percentage difference between methods (positive or negative)
        
    Returns:
        Dictionary with formatted strings:
        - total_consumption_kwh: Consumption formatted with 2 decimals and " kWh" unit
        - interval_emissions_tonnes: Interval emissions with 2 decimals and " tonnes CO2-e" unit
        - annual_emissions_tonnes: Annual emissions with 2 decimals and " tonnes CO2-e" unit
        - percentage_difference: Percentage with 2 decimals, +/- sign, and "%" symbol
        
    Examples:
        >>> metrics = create_summary_metrics(
        ...     total_consumption=1234.567,
        ...     interval_emissions=0.456,
        ...     annual_emissions=0.489,
        ...     percentage_diff=7.23
        ... )
        >>> metrics['total_consumption_kwh']
        '1234.57 kWh'
        >>> metrics['percentage_difference']
        '+7.23%'
    """
    # Format total consumption with 2 decimal places and unit
    total_consumption_kwh = f"{total_consumption:.2f} kWh"
    
    # Format interval emissions with 2 decimal places and unit
    interval_emissions_tonnes = f"{interval_emissions:.2f} tonnes CO2-e"
    
    # Format annual emissions with 2 decimal places and unit
    annual_emissions_tonnes = f"{annual_emissions:.2f} tonnes CO2-e"
    
    # Format percentage difference with sign and 2 decimal places
    sign = "+" if percentage_diff >= 0 else ""
    percentage_difference = f"{sign}{percentage_diff:.2f}%"
    
    return {
        "total_consumption_kwh": total_consumption_kwh,
        "interval_emissions_tonnes": interval_emissions_tonnes,
        "annual_emissions_tonnes": annual_emissions_tonnes,
        "percentage_difference": percentage_difference
    }
