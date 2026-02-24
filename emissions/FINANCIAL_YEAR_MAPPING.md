# Australian Financial Year Mapping

## Overview

The Emissions Dashboard uses Australian financial year (FY) mapping for annual emissions calculations. This ensures that consumption data is matched with the correct annual emissions factors as published by AEMO.

## Financial Year Definition

Australian financial year runs from **July 1 to June 30**.

The year label corresponds to the **starting year** of the FY period:
- **FY2022** = FY2022-23 = July 1, 2022 - June 30, 2023
- **FY2023** = FY2023-24 = July 1, 2023 - June 30, 2024
- **FY2024** = FY2024-25 = July 1, 2024 - June 30, 2025

## Mapping Logic

The `calculate_annual_emissions()` function maps each consumption record to its financial year:

```python
if month >= 7:  # July onwards (Jul, Aug, Sep, Oct, Nov, Dec)
    financial_year = calendar_year
else:  # January to June (Jan, Feb, Mar, Apr, May, Jun)
    financial_year = calendar_year - 1
```

## Examples

| Date | Calendar Year | Financial Year | Factor Used |
|------|--------------|----------------|-------------|
| 2022-06-30 | 2022 | 2021 | FY2021-22 factor (labeled 2021) |
| 2022-07-01 | 2022 | 2022 | FY2022-23 factor (labeled 2022) |
| 2022-12-15 | 2022 | 2022 | FY2022-23 factor (labeled 2022) |
| 2023-01-15 | 2023 | 2022 | FY2022-23 factor (labeled 2022) |
| 2023-06-30 | 2023 | 2022 | FY2022-23 factor (labeled 2022) |
| 2023-07-01 | 2023 | 2023 | FY2023-24 factor (labeled 2023) |

## Handling Different Data Uploads

### Calendar Year Data (Jan-Dec)
When users upload a full calendar year (e.g., Jan 2023 - Dec 2023):
- **Jan-Jun 2023** → uses FY2022 factor (FY2022-23)
- **Jul-Dec 2023** → uses FY2023 factor (FY2023-24)

The system automatically splits the data across the two relevant financial years.

### Financial Year Data (Jul-Jun)
When users upload a full financial year (e.g., Jul 2022 - Jun 2023):
- **All records** → use FY2022 factor (FY2022-23)

Perfect alignment with how factors are published.

### Partial Year Data
For any partial year upload (e.g., Mar-May 2023):
- Each record is mapped to its corresponding financial year
- **Mar-May 2023** → all use FY2022 factor (FY2022-23)

### Multi-Year Data
For data spanning multiple years:
- Each record gets the appropriate FY factor based on its date
- Transitions are handled automatically at the July 1 boundary

## Annual Factors CSV Format

The `annual_factors.csv` file uses the starting year of the FY period:

```csv
state,year,annual_factor_g_per_kwh,source,dataset_version
NSW,2021,710.0,AEMO,2021.1  # Applies to FY2021-22 (Jul 2021 - Jun 2022)
NSW,2022,720.0,AEMO,2022.1  # Applies to FY2022-23 (Jul 2022 - Jun 2023)
NSW,2023,730.0,AEMO,2023.1  # Applies to FY2023-24 (Jul 2023 - Jun 2024)
```

## Implementation Details

The financial year mapping is implemented in `emissions/calc.py` in the `calculate_annual_emissions()` function:

```python
# Extract financial year from datetime column
if pd.api.types.is_datetime64_any_dtype(results_df[datetime_col]):
    dt_series = results_df[datetime_col]
else:
    dt_series = pd.to_datetime(results_df[datetime_col])

# Map to financial year
results_df['financial_year'] = dt_series.apply(
    lambda dt: dt.year if dt.month >= 7 else dt.year - 1
)
```

## Testing

Comprehensive tests verify the FY mapping logic in `test_calc_basic.py`:
- `test_calculate_annual_emissions_basic`: Basic FY mapping
- `test_calculate_annual_emissions_multi_year`: Multi-year FY handling
- `test_calculate_annual_emissions_financial_year_boundary`: Exact FY boundary dates

## References

- AEMO National Greenhouse Accounts Factors: [https://www.aemo.com.au/](https://www.aemo.com.au/)
- Australian Government financial year definition: July 1 - June 30
