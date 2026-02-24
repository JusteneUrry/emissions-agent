"""
Deterministic emissions calculation workflow.
"""

import logging
from typing import Dict, Any
import pandas as pd
from streamlit.runtime.uploaded_file_manager import UploadedFile

from emissions.io import (
    load_consumption_file,
    identify_consumption_column,
    identify_time_columns,
    parse_emissions_period_code
)
from emissions.interval import (
    detect_interval_from_periods,
    detect_interval_from_timestamps
)
from emissions.factors import (
    load_interval_factors,
    load_annual_factors
)
from emissions.calc import (
    calculate_interval_emissions,
    calculate_annual_emissions,
    calculate_percentage_difference
)

logger = logging.getLogger('emissions.workflow')


def prepare_emissions_period_code(df: pd.DataFrame, timestamp_col: str, interval_minutes: int) -> pd.DataFrame:
    """Create emissions_period_code column from timestamps."""
    df = df.copy()
    
    if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    
    df['date_str'] = df[timestamp_col].dt.strftime('%Y%m%d')
    df['time_period'] = ((df[timestamp_col].dt.hour * 60 + df[timestamp_col].dt.minute) // interval_minutes) + 1
    df['emissions_period_code'] = (df['date_str'] + df['time_period'].astype(str).str.zfill(3)).astype(str)
    df = df.drop(columns=['date_str', 'time_period'])
    
    return df

def prepare_emissions_period_code_from_date_period(df: pd.DataFrame, date_col: str, period_col: str) -> pd.DataFrame:
    """Create emissions_period_code column from separate date and time_period columns."""
    df = df.copy()
    
    # Convert date to datetime if needed, then format as YYYYMMDD
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df['temp_date'] = pd.to_datetime(df[date_col], format='mixed', dayfirst=True)
    else:
        df['temp_date'] = df[date_col]
    
    df['date_str'] = df['temp_date'].dt.strftime('%Y%m%d')
    
    # Ensure period is string and zero-padded to 3 digits
    df['period_str'] = df[period_col].astype(str).str.zfill(3)
    
    # Combine into emissions_period_code
    df['emissions_period_code'] = (df['date_str'] + df['period_str']).astype(str)
    
    # Clean up temporary columns
    df = df.drop(columns=['temp_date', 'date_str', 'period_str'])
    
    return df

def calculate_emissions_deterministic(
    uploaded_file: UploadedFile,
    state: str,
    factors_dir: str = "data/emissions_factors"
) -> Dict[str, Any]:
    """
    Perform complete emissions calculation workflow deterministically.
    Bypasses LLM and directly calculates emissions using real factors.
    """
    logger.info(f"Starting deterministic calculation for {uploaded_file.name}, state={state}")
    
    reasoning_trace = []
    
    try:
        # Step 1: Load file
        # Reset file pointer to beginning (in case it was read before)
        uploaded_file.seek(0)
        df = load_consumption_file(uploaded_file)
        reasoning_trace.append({
            'step': 'file_loading',
            'decision': 'Load consumption data',
            'explanation': f"Loaded {len(df)} rows with columns: {', '.join(df.columns)}",
            'tool_calls': []
        })
        
        # Step 2: Identify consumption column
        consumption_col = identify_consumption_column(df)
        reasoning_trace.append({
            'step': 'column_identification',
            'decision': 'Identify consumption column',
            'explanation': f"Identified consumption column: '{consumption_col}'",
            'tool_calls': []
        })
        
        # Step 3: Identify time columns
        time_cols = identify_time_columns(df)
        
        # Step 4: Detect interval and prepare data
        interval_minutes = None
        datetime_col = None
        
        if 'emissions_period_code' in df.columns:
            # FORMAT 1: emissions_period_code column already exists
            # Ensure emissions_period_code is string type
            df['emissions_period_code'] = df['emissions_period_code'].astype(str)
            
            # Parse to detect interval
            df['temp_period'] = df['emissions_period_code'].apply(lambda x: parse_emissions_period_code(str(x))[1])
            interval_minutes = detect_interval_from_periods(df['temp_period'])
            df = df.drop(columns=['temp_period'])
            
            # Create datetime for annual calculation
            df['temp_date_str'] = df['emissions_period_code'].str[:8]
            df['temp_period_int'] = df['emissions_period_code'].str[8:].astype(int)
            df['datetime'] = pd.to_datetime(df['temp_date_str'], format='%Y%m%d')
            df['datetime'] = df['datetime'] + pd.to_timedelta((df['temp_period_int'] - 1) * interval_minutes, unit='min')
            datetime_col = 'datetime'
            df = df.drop(columns=['temp_date_str', 'temp_period_int'])
            
        elif time_cols['timestamp']:
            # FORMAT 2: timestamp column exists
            datetime_col = time_cols['timestamp']
            if not pd.api.types.is_datetime64_any_dtype(df[datetime_col]):
                df[datetime_col] = pd.to_datetime(df[datetime_col])
            interval_minutes = detect_interval_from_timestamps(df[datetime_col])
            df = prepare_emissions_period_code(df, datetime_col, interval_minutes)
            
        elif time_cols['date'] and time_cols['time_period']:
            # FORMAT 3: separate date and time_period columns
            date_col = time_cols['date']
            period_col = time_cols['time_period']
            
            # Detect interval from period column
            interval_minutes = detect_interval_from_periods(df[period_col].astype(int))
            
            # Create emissions_period_code from date and period
            df = prepare_emissions_period_code_from_date_period(df, date_col, period_col)
            
            # Create datetime for annual calculation
            df['temp_date_str'] = df['emissions_period_code'].str[:8]
            df['temp_period_int'] = df['emissions_period_code'].str[8:].astype(int)
            df['datetime'] = pd.to_datetime(df['temp_date_str'], format='%Y%m%d')
            df['datetime'] = df['datetime'] + pd.to_timedelta((df['temp_period_int'] - 1) * interval_minutes, unit='min')
            datetime_col = 'datetime'
            df = df.drop(columns=['temp_date_str', 'temp_period_int'])
            
        else:
            raise ValueError("Could not find timestamp, emissions_period_code, or date+time_period columns")

        
        reasoning_trace.append({
            'step': 'interval_detection',
            'decision': 'Detect data interval',
            'explanation': f"Detected {interval_minutes}-minute interval data",
            'tool_calls': []
        })
        
        # Step 5: Load emissions factors
        interval_factors = load_interval_factors(state, interval_minutes, factors_dir)
        annual_factors = load_annual_factors(state, factors_dir)
        
        # Ensure string types for merging
        interval_factors['emissions_period_code'] = interval_factors['emissions_period_code'].astype(str)
        df['emissions_period_code'] = df['emissions_period_code'].astype(str)
        
        reasoning_trace.append({
            'step': 'factor_loading',
            'decision': f'Load emissions factors for {state}',
            'explanation': f"Loaded {len(interval_factors)} interval factors and {len(annual_factors)} annual factors",
            'tool_calls': []
        })
        
        # Step 6: Calculate interval-based emissions
        interval_results_df, interval_total = calculate_interval_emissions(
            df, interval_factors, consumption_col, 'emissions_period_code'
        )
        
        reasoning_trace.append({
            'step': 'interval_calculation',
            'decision': 'Calculate interval-based emissions',
            'explanation': f"Calculated {interval_total:.6f} tonnes CO2-e",
            'tool_calls': []
        })
        
        # Step 7: Calculate annual-based emissions
        annual_results_df, annual_total = calculate_annual_emissions(
            df, annual_factors, consumption_col, datetime_col
        )
        
        reasoning_trace.append({
            'step': 'annual_calculation',
            'decision': 'Calculate annual average emissions',
            'explanation': f"Calculated {annual_total:.6f} tonnes CO2-e",
            'tool_calls': []
        })
        
        # Step 8: Calculate percentage difference
        percentage_diff = calculate_percentage_difference(interval_total, annual_total) if annual_total > 0 else 0.0
        
        total_consumption = df[consumption_col].sum()
        
        results = {
            'interval_total': interval_total,
            'annual_total': annual_total,
            'percentage_diff': percentage_diff,
            'total_consumption': total_consumption
        }
        
        # Generate insights
        insights = f"""## Emissions Analysis Results

Your electricity consumption of **{total_consumption:.2f} kWh** resulted in:

- **Interval-based emissions**: {interval_total:.2f} tonnes CO2-e
- **Annual average emissions**: {annual_total:.2f} tonnes CO2-e
- **Difference**: {abs(percentage_diff):.1f}% {'higher' if percentage_diff > 0 else 'lower'}

The interval-based calculation uses time-specific emissions factors from the Australian electricity market.
"""
        
        return {
            'success': True,
            'results': results,
            'insights': insights,
            'reasoning_trace': reasoning_trace,
            'state': state,
            'filename': uploaded_file.name,
            'interval_results_df': interval_results_df,
            'annual_results_df': annual_results_df
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__,
            'reasoning_trace': reasoning_trace,
            'message': f"Calculation failed: {str(e)}"
        }
