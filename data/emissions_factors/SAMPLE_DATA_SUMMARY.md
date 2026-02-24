# Sample Emissions Factors Data Summary

This document summarizes the sample emissions factor data created for testing and development.

## Files Created

### 1. interval_factors.csv
**Purpose:** Time-varying emissions factors for interval-based calculations

**Statistics:**
- Total rows: 5,040
- States: NSW, VIC, QLD, SA, TAS (all 5 NEM states)
- Date range: January 1-3, 2023 (3 days)
- Interval types: 5MIN (288 periods/day), 30MIN (48 periods/day)

**Data Characteristics:**

#### State-Specific Baselines (g CO2-e per kWh)
- TAS: 150 (lowest - high hydro generation)
- SA: 650 (low-medium - high renewable penetration)
- NSW: 750 (medium - mixed generation)
- QLD: 820 (medium-high - coal-heavy)
- VIC: 890 (highest - brown coal)

#### Time-of-Day Variation
The emissions factors vary realistically throughout the day:

**NSW Example (5MIN intervals, 2023-01-01):**
- Period 1 (midnight): 637.5 g/kWh (85% of baseline - low demand)
- Period 100 (8:20 AM): 806.25 g/kWh (107% of baseline - morning ramp)
- Period 216 (6:00 PM): 887.23 g/kWh (118% of baseline - evening peak)

**State Comparison (Period 100, morning):**
```
State  Factor (g/kWh)
TAS    161.25
SA     698.75
NSW    806.25
QLD    881.50
VIC    956.75
```

#### Pattern Logic
- **Overnight (0-6 AM):** 85% of baseline (low demand, more renewables)
- **Morning ramp (6-9 AM):** 85% → 115% (demand increasing)
- **Daytime (9 AM-5 PM):** 110-115% (high demand, more fossil fuels)
- **Evening peak (5-9 PM):** 115-120% (highest demand period)
- **Night (9 PM-midnight):** 110% → 85% (demand decreasing)

### 2. annual_factors.csv
**Purpose:** Annual average emissions factors for year-level calculations

**Content:**
- All 5 NEM states
- Years: 2023, 2024
- Source: AEMO
- Dataset versions tracked

**Annual Factors (2023):**
```
State  Factor (g/kWh)
TAS    145
SA     640
NSW    720
QLD    810
VIC    890
```

### 3. DATA_SOURCING_GUIDE.md
**Purpose:** Comprehensive guide for obtaining real production data

**Contents:**
- Official AEMO data sources and URLs
- Data processing steps and format conversion
- Sample vs production data comparison
- Automation recommendations
- Data quality checks
- Python code examples

## Usage Notes

### For Testing
These sample files provide realistic data patterns for:
- Unit testing emissions calculations
- Integration testing with consumption data
- UI/visualization development
- Algorithm validation

### For Production
**Important:** These are sample files only. For production use:
1. Follow the DATA_SOURCING_GUIDE.md to obtain real AEMO data
2. Ensure complete date coverage for your analysis period
3. Implement regular data updates
4. Validate data quality against AEMO sources

## Data Validation

### Completeness Check
```python
import pandas as pd

df = pd.read_csv('interval_factors.csv')

# Check coverage
states = df['state'].unique()
dates = df['date'].unique()
intervals = df['interval_type'].unique()

print(f"States: {len(states)} (expected: 5)")
print(f"Dates: {len(dates)} (expected: 3)")
print(f"Interval types: {len(intervals)} (expected: 2)")

# Check periods per day
for interval_type in intervals:
    periods = df[df['interval_type'] == interval_type].groupby('date')['time_period'].count()
    expected = 288 if interval_type == '5MIN' else 48
    print(f"{interval_type}: {periods.values[0]} periods/day (expected: {expected})")
```

### Range Validation
All emissions factors fall within expected ranges:
- Minimum: ~127.5 g/kWh (TAS overnight)
- Maximum: ~1068 g/kWh (VIC evening peak)
- Typical range: 150-1000 g/kWh

## Alignment with Sample Consumption Data

The interval factors align with the sample consumption data:
- **Date range:** Both cover January 1-3, 2023
- **Interval type:** 5MIN intervals match sample_5min_period.csv
- **Period numbering:** Both use 001-288 format

This allows for immediate testing of emissions calculations without data mismatches.

## Generation Script

The `generate_interval_factors.py` script can be used to:
- Regenerate the sample data if needed
- Modify date ranges or state coverage
- Adjust time-of-day variation patterns
- Create additional test scenarios

## Next Steps

1. **For Development:** Use these files as-is for testing
2. **For Production:** Follow DATA_SOURCING_GUIDE.md to obtain real data
3. **For Validation:** Run the data validation checks above
4. **For Updates:** Modify generate_interval_factors.py as needed

## References

- AEMO Carbon Dioxide Equivalent Intensity Index: https://aemo.com.au/
- Sample consumption data: `../sample/sample_5min_period.csv`
- Data sourcing guide: `DATA_SOURCING_GUIDE.md`
- Emissions factor module: `../../emissions/factors.py`

---

**Generated:** 2024
**Version:** 1.0
**Status:** Sample data for testing only
