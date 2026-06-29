"""
Correlation analysis: Reef visitor numbers (EMC Cairns) vs Airport inbound passengers
Splits into PRE-COVID and POST-COVID periods, excluding the full 2020 disruption year.

Pre-COVID:  2016 - 2019 (inclusive)
Post-COVID: 2022 - 2025 (inclusive)  -- 2021 also excluded as a transitional/recovery year
                                          with extreme volatility (adjust if you want it included)

Requires: pandas, numpy, scipy
"""

import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import pearsonr, linregress

DB_PATH = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'

conn = sqlite3.connect(DB_PATH)

# --- Pull quarterly EMC reef data (Full Day + Part Day = total reef trips) ---
emc_query = """
SELECT
    Year,
    quarter_num,
    year_qtr_sort,
    Full_Day,
    Part_Day,
    (Full_Day + Part_Day) AS Total_Reef_Visits
FROM emc_cairns
ORDER BY year_qtr_sort
"""
emc = pd.read_sql(emc_query, conn)

# --- Pull monthly airport data, aggregate to quarterly ---
airport_query = """
SELECT year, month, dom_inbound, intl_inbound, total_inbound
FROM airport_pax
ORDER BY year, month
"""
airport = pd.read_sql(airport_query, conn)
conn.close()

# Build quarter + year_qtr_sort on airport data
airport['quarter'] = ((airport['month'] - 1) // 3) + 1
airport['year_qtr_sort'] = airport['year'] * 10 + airport['quarter']

airport_qtr = airport.groupby('year_qtr_sort').agg(
    year=('year', 'first'),
    quarter=('quarter', 'first'),
    dom_inbound=('dom_inbound', 'sum'),
    intl_inbound=('intl_inbound', 'sum'),
    total_inbound=('total_inbound', 'sum')
).reset_index()

# --- Merge EMC and airport data on year_qtr_sort ---
merged = pd.merge(emc, airport_qtr, on='year_qtr_sort', suffixes=('_emc', '_air'))

print("=== Merged Quarterly Dataset (first 5 rows) ===")
print(merged[['year_qtr_sort', 'Total_Reef_Visits', 'dom_inbound', 'intl_inbound', 'total_inbound']].head())
print(f"\nTotal quarters in merged dataset: {len(merged)}")

# --- Define PRE and POST covid periods, excluding 2020 entirely (and 2021 as transitional) ---
pre_covid = merged[merged['Year'] <= 2019].copy()
post_covid = merged[merged['Year'] >= 2022].copy()

print(f"\nPre-COVID quarters (2016-2019): {len(pre_covid)}")
print(f"Post-COVID quarters (2022-2025): {len(post_covid)}")


def run_correlation(df, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    print(f"\n--- Diagnostic: scale/spread of each variable ---")
    print(f"Total_Reef_Visits : mean={df['Total_Reef_Visits'].mean():,.0f}  std={df['Total_Reef_Visits'].std():,.0f}  range=[{df['Total_Reef_Visits'].min():,.0f} - {df['Total_Reef_Visits'].max():,.0f}]")
    for col, name in [('dom_inbound', 'Domestic Inbound'),
                       ('intl_inbound', 'International Inbound'),
                       ('total_inbound', 'Total Inbound')]:
        print(f"{name:18}: mean={df[col].mean():,.0f}  std={df[col].std():,.0f}  range=[{df[col].min():,.0f} - {df[col].max():,.0f}]")

    for col, name in [('dom_inbound', 'Domestic Inbound'),
                       ('intl_inbound', 'International Inbound'),
                       ('total_inbound', 'Total Inbound')]:

        r, p_value = pearsonr(df['Total_Reef_Visits'], df[col])
        r_squared = r ** 2

        # Regression: how much do Total_Reef_Visits change per unit increase in inbound arrivals
        slope, intercept, r_lr, p_lr, std_err = linregress(df[col], df['Total_Reef_Visits'])

        print(f"\n{name} vs Total Reef Visits:")
        print(f"  Pearson r       = {r:.3f}")
        print(f"  R-squared       = {r_squared:.3f}  (i.e. {r_squared*100:.1f}% of variance explained)")
        print(f"  p-value         = {p_value:.4f}  ({'significant' if p_value < 0.05 else 'NOT significant'} at 0.05 level)")
        print(f"  Regression slope = {slope:.4f}  (i.e. +1 {name.lower()} arrival ~= +{slope:.4f} reef visits)")
        print(f"  ...or scaled: +1,000 {name.lower()} arrivals ~= +{slope*1000:,.0f} reef visits")
        print(f"  Intercept       = {intercept:,.0f}")


run_correlation(pre_covid, "PRE-COVID (2016-2019)")
run_correlation(post_covid, "POST-COVID (2022-2025)")

# --- Save merged dataset to CSV for reference / Power BI if needed ---
import os
output_dir = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL'
output_path = os.path.join(output_dir, 'reef_airport_merged.csv')
os.makedirs(output_dir, exist_ok=True)
merged.to_csv(output_path, index=False)
print(f"\nMerged dataset also saved to: {output_path}")