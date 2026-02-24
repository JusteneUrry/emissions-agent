# Emissions Factors Data Sourcing Guide

This guide explains how to obtain and format real emissions factor data for the Australian National Electricity Market (NEM).

## Overview

The emissions factors in this directory are **sample data for testing and development**. For production use, you should source real data from official AEMO sources.

## Data Files

### 1. interval_factors.csv
Contains time-varying emissions factors for 5-minute and 30-minute intervals.

**Format:**
```csv
state,date,interval_type,time_period,emissions_factor_g_per_kwh
NSW,2023-01-01,5MIN,001,637.5
NSW,2023-01-01,30MIN,001,645.2
```

**Fields:**
- `state`: NEM state code (NSW, VIC, QLD, SA, TAS)
- `date`: Date in YYYY-MM-DD format
- `interval_type`: Either "5MIN" or "30MIN"
- `time_period`: Period number (001-288 for 5MIN, 001-048 for 30MIN)
- `emissions_factor_g_per_kwh`: Emissions intensity in grams CO2-e per kWh

### 2. annual_factors.csv
Contains annual average emissions factors by state and year.

**Format:**
```csv
state,year,annual_factor_g_per_kwh,source,dataset_version
NSW,2023,720.0,AEMO,2023.1
```

**Fields:**
- `state`: NEM state code
- `year`: Calendar year
- `annual_factor_g_per_kwh`: Annual average emissions intensity
- `source`: Data source (e.g., "AEMO")
- `dataset_version`: Version identifier for the dataset

## Official Data Sources

### AEMO Carbon Dioxide Equivalent Intensity Index (CDEII)

**Primary Source:** Australian Energy Market Operator (AEMO)

**Website:** https://aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/data-dashboard-nem

**Key Datasets:**

1. **Real-time Emissions Data**
   - URL: https://aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/market-data-nemweb
   - Navigate to: Current Reports > CDEII
   - File format: CSV files updated every 5 minutes
   - Contains: State-by-state emissions intensity in real-time

2. **Historical Emissions Data**
   - URL: https://aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/aggregated-data
   - Dataset: "Carbon Dioxide Equivalent Intensity Index"
   - Available: Historical data back to 2009
   - Granularity: 5-minute and 30-minute intervals

3. **Annual Emissions Factors**
   - URL: https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/market-operations/settlements-and-payments/settlements/carbon-dioxide-equivalent-intensity-index
   - Published: Annually in technical reports
   - Contains: State-level annual average factors

### Alternative Sources

1. **National Greenhouse Accounts Factors**
   - Published by: Department of Climate Change, Energy, the Environment and Water
   - URL: https://www.dcceew.gov.au/climate-change/publications/national-greenhouse-accounts-factors
   - Contains: Official emissions factors for reporting
   - Updated: Annually

2. **Clean Energy Regulator**
   - URL: https://www.cleanenergyregulator.gov.au/
   - Contains: Emissions factors for compliance reporting
   - Use case: Regulatory compliance calculations

## Data Processing Steps

### For Interval Data (5MIN/30MIN)

1. **Download from AEMO NEMWeb**
   ```
   Navigate to: https://nemweb.com.au/Reports/Current/CDEII/
   Download: CO2EII_SUMMARY_[DATE].CSV files
   ```

2. **Extract Required Fields**
   - REGIONID → state (map: NSW1→NSW, VIC1→VIC, QLD1→QLD, SA1→SA, TAS1→TAS)
   - SETTLEMENTDATE → date (convert to YYYY-MM-DD)
   - PERIODID → time_period (format as 3-digit: 001-288)
   - CO2II_ADJUSTED → emissions_factor_g_per_kwh (convert from kg/MWh to g/kWh)

3. **Format Conversion**
   ```python
   # Convert kg CO2-e/MWh to g CO2-e/kWh
   g_per_kwh = kg_per_mwh  # They're numerically equal (1000/1000)
   ```

4. **Add Interval Type**
   - Determine from source file or period count
   - 288 periods/day = 5MIN
   - 48 periods/day = 30MIN

### For Annual Data

1. **Download Annual Reports**
   - Source: AEMO annual emissions reports
   - Or calculate from interval data: `annual_factor = mean(all_intervals_in_year)`

2. **Format as CSV**
   ```csv
   state,year,annual_factor_g_per_kwh,source,dataset_version
   NSW,2023,720.0,AEMO,2023.1
   ```

## Sample vs Production Data

### Current Sample Data

The files in this directory contain **synthetic sample data** with these characteristics:

- **Date Range:** January 1-3, 2023 (3 days only)
- **Purpose:** Testing and development
- **Realism:** Factors vary by time-of-day to simulate real patterns
- **State Baselines:** Based on approximate 2023 averages
  - TAS: ~150 g/kWh (high hydro)
  - SA: ~650 g/kWh (high renewables)
  - NSW: ~750 g/kWh (mixed)
  - QLD: ~820 g/kWh (coal-heavy)
  - VIC: ~890 g/kWh (brown coal)

### Production Data Requirements

For production use, you need:

- **Complete Date Coverage:** All dates in your analysis period
- **Real Values:** Actual AEMO-published emissions factors
- **Regular Updates:** New data as it becomes available
- **Data Quality:** Validated against AEMO sources
- **Metadata:** Source attribution and version tracking

## Automation

### Recommended Approach

1. **Set up automated downloads** from AEMO NEMWeb
2. **Process files** to match the required CSV format
3. **Validate data** against expected ranges
4. **Update files** on a regular schedule (daily/weekly)
5. **Version control** to track data updates

### Example Python Script

```python
import pandas as pd
import requests
from datetime import datetime

def download_aemo_cdeii(date):
    """Download CDEII data from AEMO for a specific date."""
    url = f"https://nemweb.com.au/Reports/Current/CDEII/CO2EII_SUMMARY_{date}.CSV"
    response = requests.get(url)
    # Process CSV...
    return data

def convert_to_interval_factors(aemo_data):
    """Convert AEMO format to interval_factors.csv format."""
    df = pd.DataFrame(aemo_data)
    
    # Map region IDs to state codes
    region_map = {'NSW1': 'NSW', 'VIC1': 'VIC', 'QLD1': 'QLD', 
                  'SA1': 'SA', 'TAS1': 'TAS'}
    df['state'] = df['REGIONID'].map(region_map)
    
    # Format date and period
    df['date'] = pd.to_datetime(df['SETTLEMENTDATE']).dt.strftime('%Y-%m-%d')
    df['time_period'] = df['PERIODID'].apply(lambda x: f'{x:03d}')
    
    # Emissions factor (already in g/kWh)
    df['emissions_factor_g_per_kwh'] = df['CO2II_ADJUSTED']
    
    # Determine interval type
    df['interval_type'] = '5MIN'  # or '30MIN' based on data
    
    return df[['state', 'date', 'interval_type', 'time_period', 
               'emissions_factor_g_per_kwh']]
```

## Data Quality Checks

Before using emissions factor data, validate:

1. **Completeness:** All required dates and periods present
2. **Range Checks:** Factors within expected bounds (50-1200 g/kWh typically)
3. **State Consistency:** Each state has appropriate baseline levels
4. **Time Patterns:** Factors show expected daily variation
5. **No Gaps:** No missing periods or dates

## Support and Questions

For questions about:
- **AEMO Data:** Contact AEMO support or check their data documentation
- **This System:** Refer to the main README.md or emissions factor module documentation
- **Regulatory Compliance:** Consult the Clean Energy Regulator

## Updates and Maintenance

This guide should be updated when:
- AEMO changes their data format or access methods
- New data sources become available
- Regulatory requirements change
- System requirements evolve

**Last Updated:** 2024
**Version:** 1.0
