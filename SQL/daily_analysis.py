"""
Daily-grain analysis: does rainfall affect Down Under Dive boat passengers?

Daily rainfall (mm) for Cairns Aero (SILO/BOM, station 31011) is matched to
PAX_DATA daily passengers. Boat passengers are strongly seasonal and have a
weekly pattern, and many days are simply non-operating (0 pax). So we:
  1. look at operating days only (pax > 0) for the demand signal,
  2. bucket days by rainfall and compare average passengers,
  3. de-seasonalise (passengers vs the month-of-year norm) and correlate,
  4. check whether the heaviest-rain days show more zero-pax (cancellations).

Also loads cairns_rainfall_daily into the DB for Power BI.
"""

import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import pearsonr

DB = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
RAW = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets\silo_daily.txt'
CSV = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets\cairns_rainfall_daily.csv'

# --- Parse SILO daily file: col0=YYYYMMDD, col7=Rain(mm) ---
rows = []
with open(RAW) as f:
    for line in f:
        p = line.split()
        if len(p) < 8 or not (p[0].isdigit() and len(p[0]) == 8):
            continue
        y = int(p[0][:4])
        if y < 2018:
            continue
        d = f"{p[0][:4]}-{p[0][4:6]}-{p[0][6:8]}"
        rows.append((d, float(p[7])))
rain = pd.DataFrame(rows, columns=['date', 'rain_mm'])

conn = sqlite3.connect(DB)
pax = pd.read_sql("SELECT date, passengers, total FROM PAX_DATA", conn)

# Save daily rainfall table for Power BI
rain.to_csv(CSV, index=False)
rain.to_sql('cairns_rainfall_daily', conn, if_exists='replace', index=False)
conn.close()

df = pax.merge(rain, on='date', how='inner')
df['date'] = pd.to_datetime(df['date'])
df['month'] = df['date'].dt.month
df['dow'] = df['date'].dt.weekday

print(f"Matched {len(df)} days ({df['date'].min().date()} to {df['date'].max().date()})")
print(f"Rainfall sanity - wettest day: {df['rain_mm'].max():.1f} mm on "
      f"{df.loc[df['rain_mm'].idxmax(),'date'].date()}")

op = df[df['passengers'] > 0].copy()
print(f"\nOperating days (pax>0): {len(op)}   Non-operating (pax=0): {(df['passengers']==0).sum()}")

# 1. Raw daily correlation
r_all, p_all = pearsonr(df['rain_mm'], df['passengers'])
r_op, p_op = pearsonr(op['rain_mm'], op['passengers'])
print(f"\nRaw daily correlation (all days)        r = {r_all:+.3f} (p={p_all:.3f})")
print(f"Raw daily correlation (operating days)  r = {r_op:+.3f} (p={p_op:.3f})")

# 2. Rainfall buckets (operating days)
bins = [-0.01, 1, 10, 25, 50, 1e9]
labels = ['Dry (0-1mm)', 'Light (1-10)', 'Moderate (10-25)', 'Heavy (25-50)', 'Extreme (50+)']
op['bucket'] = pd.cut(op['rain_mm'], bins=bins, labels=labels)
print("\nAverage passengers by rainfall (operating days):")
g = op.groupby('bucket', observed=True)['passengers'].agg(['mean', 'count'])
for b in labels:
    if b in g.index:
        print(f"  {b:18} mean={g.loc[b,'mean']:6.1f} pax   (n={int(g.loc[b,'count'])} days)")

# 3. De-seasonalised correlation (anomaly vs month-of-year norm, operating days)
norms = op.groupby('month')['passengers'].transform('mean')
op['pax_anom'] = op['passengers'] - norms
rnorms = op.groupby('month')['rain_mm'].transform('mean')
op['rain_anom'] = op['rain_mm'] - rnorms
r_adj, p_adj = pearsonr(op['rain_anom'], op['pax_anom'])
print(f"\nSeasonally-adjusted daily correlation    r = {r_adj:+.3f} (p={p_adj:.3f}, n={len(op)})")

# 4. Zero-pax rate by rainfall (cancellation signal)
df['heavy'] = df['rain_mm'] >= 50
print("\nShare of days with zero passengers:")
print(f"  rain <50mm : {(df[~df['heavy']]['passengers']==0).mean()*100:5.1f}%")
print(f"  rain >=50mm: {(df[df['heavy']]['passengers']==0).mean()*100:5.1f}%")
print("\nWrote cairns_rainfall_daily to DB + CSV.")
