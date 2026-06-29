"""
Seasonal-adjusted (quarter-over-quarter) analysis of rainfall as a
second-order driver of reef demand and airport arrivals.

Tropical rainfall and tourism are both strongly seasonal (wet summer,
dry/peak winter), so a RAW rainfall-vs-visits correlation mostly captures
that shared seasonal cycle. To isolate rainfall's own effect we remove the
seasonal pattern: for each metric we compute the average for each
quarter-of-year (Q1..Q4) across non-COVID years, then express every quarter
as its deviation (anomaly) from that seasonal norm, and correlate the
anomalies. COVID years 2020-2021 are excluded from baselines and correlations.
"""

import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import pearsonr

DB = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
CSV = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets\quarterly_anomalies.csv'
conn = sqlite3.connect(DB)

# Reef visits per quarter (Full + Part day = total reef trips)
reef = pd.read_sql("SELECT year_qtr_sort, Year as year, (Full_Day + Part_Day) AS reef_visits FROM emc_cairns", conn)

# Airport inbound per quarter (aggregate monthly)
air = pd.read_sql("SELECT year, month, total_inbound FROM airport_pax", conn)
air['quarter'] = (air['month'] - 1) // 3 + 1
air['year_qtr_sort'] = air['year'] * 10 + air['quarter']
air = air.groupby('year_qtr_sort', as_index=False)['total_inbound'].sum().rename(columns={'total_inbound': 'airport_inbound'})

# Rainfall per quarter
rain = pd.read_sql("SELECT year_qtr_sort, rainfall_mm FROM cairns_rainfall_qtr", conn)

# Merge into one quarterly panel
df = rain.merge(air, on='year_qtr_sort', how='left').merge(reef, on='year_qtr_sort', how='left')
df['year'] = df['year_qtr_sort'] // 10
df['quarter'] = df['year_qtr_sort'] % 10
df = df.sort_values('year_qtr_sort').reset_index(drop=True)

COVID = [2020, 2021]
base = df[~df['year'].isin(COVID)]


def seasonalise(frame, col):
    """Return anomaly = value - mean(value) for that quarter-of-year (non-COVID baseline)."""
    norms = base.groupby('quarter')[col].mean()
    return frame[col] - frame['quarter'].map(norms)


for col in ['rainfall_mm', 'airport_inbound', 'reef_visits']:
    df[col + '_anom'] = seasonalise(df, col)

df.to_csv(CSV, index=False)
df.to_sql('quarterly_anomalies', conn, if_exists='replace', index=False)
conn.close()


def corr(frame, a, b):
    sub = frame.dropna(subset=[a, b])
    sub = sub[~sub['year'].isin(COVID)]
    r, p = pearsonr(sub[a], sub[b])
    return r, p, len(sub)


print("=" * 64)
print("  RAINFALL vs DEMAND  (non-COVID quarters; 2020-2021 excluded)")
print("=" * 64)

pairs = [
    ("Reef visits",      "reef_visits",     "rainfall_mm"),
    ("Airport inbound",  "airport_inbound", "rainfall_mm"),
]
for label, metric, rainf in pairs:
    r_raw, p_raw, n1 = corr(df, metric, rainf)
    r_adj, p_adj, n2 = corr(df, metric + '_anom', rainf + '_anom')
    print(f"\n{label} vs rainfall:")
    print(f"  RAW correlation            r = {r_raw:+.3f}  (p={p_raw:.3f}, n={n1})  <- inflated by shared seasonality")
    print(f"  SEASONALLY-ADJUSTED        r = {r_adj:+.3f}  (p={p_adj:.3f}, n={n2})  <- rainfall's own signal")

print("\nInterpretation:")
print("  A near-zero adjusted r means rainfall has little extra effect once")
print("  the normal wet/dry season is accounted for. A negative adjusted r")
print("  means wetter-than-normal quarters see fewer visits than that quarter")
print("  usually gets - genuine rain dampening, beyond seasonality.")
print(f"\nWrote quarterly_anomalies ({len(df)} quarters) to DB + {CSV}")
