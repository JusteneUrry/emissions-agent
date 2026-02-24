#!/usr/bin/env python3
"""
Generate interval_factors.csv with realistic emissions factors for NEM states.
"""
import csv
import math
from pathlib import Path


def generate_interval_factors():
    """Generate emissions factors for all states, intervals, and time periods."""
    
    # State baseline factors (g CO2-e per kWh)
    state_baselines = {
        'TAS': 150,  # Lowest - high hydro
        'SA': 650,   # High renewables
        'NSW': 750,  # Mixed
        'QLD': 820,  # Coal-heavy
        'VIC': 890,  # Highest - brown coal
    }
    
    # Output file path
    output_path = Path(__file__).parent / 'data' / 'emissions_factors' / 'interval_factors.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # CSV header
    fieldnames = [
        'state',
        'interval_minutes',
        'emissions_period_code',
        'factor_g_per_kwh',
        'source',
        'dataset_version'
    ]
    
    rows = []
    
    # Generate data for each state
    for state, baseline in state_baselines.items():
        # Generate for both interval types
        for interval_minutes in [5, 30]:
            periods_per_day = 288 if interval_minutes == 5 else 48
            
            # Generate for 3 days (Jan 1-3, 2023)
            for day in range(1, 4):
                date_str = f'202301{day:02d}'
                
                # Generate for each period in the day
                for period in range(1, periods_per_day + 1):
                    # Create emissions period code
                    emissions_period_code = f'{date_str}{period:03d}'
                    
                    # Calculate time-of-day variation
                    # Use sinusoidal pattern: lower at night, higher during day
                    hour_of_day = (period - 1) * interval_minutes / 60
                    
                    # Peak at 6 PM (18:00), trough at 4 AM (04:00)
                    time_factor = 1.0 + 0.18 * math.sin((hour_of_day - 4) * math.pi / 12)
                    
                    # Calculate factor with variation
                    factor = baseline * time_factor
                    
                    # Round to 1 decimal place
                    factor = round(factor, 1)
                    
                    rows.append({
                        'state': state,
                        'interval_minutes': interval_minutes,
                        'emissions_period_code': emissions_period_code,
                        'factor_g_per_kwh': factor,
                        'source': 'AEMO',
                        'dataset_version': '2023.1'
                    })
    
    # Write to CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f'Generated {len(rows)} rows in {output_path}')
    print(f'Expected: {5 * 2 * 3 * 288} rows (5 states × 2 intervals × 3 days × 288 periods)')
    print(f'\nSample rows:')
    for i in [0, 1, 2, -1]:
        row = rows[i]
        print(f"  {row['state']},{row['interval_minutes']},{row['emissions_period_code']},"
              f"{row['factor_g_per_kwh']},{row['source']},{row['dataset_version']}")


if __name__ == '__main__':
    generate_interval_factors()
