# Interval Factors Data Summary

## File: `interval_factors.csv`

### Overview
Generated emissions factor data for NEM states with realistic time-of-day variations.

### Data Specifications

**Total Rows:** 5,040 data rows (plus 1 header row)

**Coverage:**
- **States:** 5 (TAS, SA, NSW, QLD, VIC)
- **Intervals:** 2 (5-minute and 30-minute)
- **Date Range:** January 1-3, 2023
- **Periods per day:** 288 (5-min) or 48 (30-min)

**Calculation:** 5 states × 2 intervals × 3 days × 288 periods = 8,640 total period combinations
- 5-minute data: 5 states × 3 days × 288 periods = 4,320 rows
- 30-minute data: 5 states × 3 days × 48 periods = 720 rows
- **Total: 5,040 rows**

### Column Format

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `state` | String | NEM state code | NSW, VIC, QLD, SA, TAS |
| `interval_minutes` | Integer | Interval duration | 5 or 30 |
| `emissions_period_code` | String | Date + period code | 20230101001 |
| `factor_g_per_kwh` | Float | Emissions factor | 637.5 |
| `source` | String | Data source | AEMO |
| `dataset_version` | String | Dataset version | 2023.1 |

### State Baseline Factors

Baseline emissions factors (g CO2-e per kWh) with ±18% time-of-day variation:

| State | Baseline | Min | Max | Avg | Rationale |
|-------|----------|-----|-----|-----|-----------|
| TAS | 150 | 123.0 | 177.0 | 150.0 | High hydro generation |
| SA | 650 | 533.0 | 767.0 | 650.0 | High renewable penetration |
| NSW | 750 | 615.0 | 885.0 | 750.0 | Mixed generation portfolio |
| QLD | 820 | 672.4 | 967.6 | 820.0 | Coal-heavy generation |
| VIC | 890 | 729.8 | 1050.2 | 890.0 | Brown coal dominance |

### Time-of-Day Variation

Emissions factors vary throughout the day using a sinusoidal pattern:
- **Peak:** 6 PM (18:00) - highest demand, more fossil fuel generation
- **Trough:** 4 AM (04:00) - lowest demand, more renewable/baseload
- **Variation:** ±18% from baseline (realistic for NEM grid dynamics)

### Data Alignment

The date range (Jan 1-3, 2023) matches the sample consumption data in:
- `data/sample/sample_5min_period.csv`
- `data/sample/sample_30min_period.csv`

This ensures emissions calculations can be performed on the sample data.

### Generation

Generated using `generate_interval_factors.py` script.

### Verification

Verified using:
- `verify_interval_factors.py` - Data structure and statistics
- `test_interval_factors_file.py` - Integration with `emissions/factors.py`

All tests passed successfully.
