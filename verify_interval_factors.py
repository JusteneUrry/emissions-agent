#!/usr/bin/env python3
"""Verify interval_factors.csv meets all requirements."""
import csv
from pathlib import Path
from collections import Counter

csv_path = Path(__file__).parent / 'data' / 'emissions_factors' / 'interval_factors.csv'

with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"✓ Total rows: {len(rows)} (expected 5,040)")
print(f"✓ Columns: {list(rows[0].keys())}")

# Check states
states = Counter(row['state'] for row in rows)
print(f"\n✓ States: {dict(states)}")

# Check intervals
intervals = Counter(row['interval_minutes'] for row in rows)
print(f"✓ Intervals: {dict(intervals)}")

# Check date range
period_codes = [row['emissions_period_code'] for row in rows]
print(f"✓ Period code range: {min(period_codes)} to {max(period_codes)}")

# Check sources and versions
sources = set(row['source'] for row in rows)
versions = set(row['dataset_version'] for row in rows)
print(f"✓ Sources: {sources}")
print(f"✓ Versions: {versions}")

# Sample factors by state
print(f"\n✓ Sample factors by state:")
for state in ['TAS', 'SA', 'NSW', 'QLD', 'VIC']:
    state_rows = [r for r in rows if r['state'] == state]
    factors = [float(r['factor_g_per_kwh']) for r in state_rows]
    print(f"  {state}: min={min(factors):.1f}, max={max(factors):.1f}, avg={sum(factors)/len(factors):.1f}")

print(f"\n✓ First 3 rows:")
for i in range(3):
    r = rows[i]
    print(f"  {r['state']},{r['interval_minutes']},{r['emissions_period_code']},{r['factor_g_per_kwh']},{r['source']},{r['dataset_version']}")

print(f"\n✓ Last 3 rows:")
for i in range(-3, 0):
    r = rows[i]
    print(f"  {r['state']},{r['interval_minutes']},{r['emissions_period_code']},{r['factor_g_per_kwh']},{r['source']},{r['dataset_version']}")
