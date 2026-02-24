# Emissions Factors Documentation

## Source

The emissions factors in this dataset are derived from the Australian Energy Market Operator (AEMO) National Electricity Market (NEM) data. These factors represent the greenhouse gas emissions intensity of electricity generation across different states and time periods.

## Version

**Dataset Version:** regional_intensity_v1

**Last Updated:** February 2026

## Methodology

The emissions factors are calculated using the following methodology:

1. **Interval Factors**: Time-specific emissions factors that reflect the actual grid intensity at different times of day. These factors account for variations in the generation mix (coal, gas, renewables) throughout the day.

2. **Annual Factors**: Yearly average emissions factors calculated as the weighted average of all interval factors across the year, weighted by generation volume.

3. **State-Specific Factors**: Each Australian NEM state (NSW, VIC, QLD, SA, TAS) has different generation mixes, resulting in different emissions intensities.

## Data Files

### interval_factors.csv

Contains time-interval-specific emissions factors with the following columns:
- `state`: NEM state code (NSW, VIC, QLD, SA, TAS)
- `interval_minutes`: Interval duration (5 or 30 minutes)
- `emissions_period_code`: Combined date and time period code (YYYYMMDDTTT)
- `factor_g_per_kwh`: Emissions factor in grams CO2-equivalent per kilowatt-hour
- `source`: Data source (AEMO)
- `dataset_version`: Version identifier

### annual_factors.csv

Contains annual average emissions factors with the following columns:
- `state`: NEM state code (NSW, VIC, QLD, SA, TAS)
- `year`: Calendar year
- `annual_factor_g_per_kwh`: Annual average emissions factor in grams CO2-e per kWh
- `source`: Data source (AEMO)
- `dataset_version`: Version identifier

## Usage Notes

- Factors vary by state due to different generation mixes
- Tasmania (TAS) has the lowest factors due to high hydroelectric generation
- South Australia (SA) has moderate factors due to high wind generation
- Victoria (VIC) has higher factors due to brown coal generation
- Queensland (QLD) and New South Wales (NSW) have moderate-to-high factors

## References

- Australian Energy Market Operator (AEMO): https://www.aemo.com.au/
- National Greenhouse Accounts Factors: https://www.industry.gov.au/
