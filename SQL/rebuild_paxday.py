"""
Rebuilds Paxday.db from CSV exports.
Run once from the SQL folder.
"""

import sqlite3
import pandas as pd
import os

DB_PATH = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
CSV_DIR = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets'

# Remove empty db if it exists
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)

def iso_date(series, dayfirst=False):
    """Parse to datetime then store as clean ISO YYYY-MM-DD text (no time)."""
    return pd.to_datetime(series, dayfirst=dayfirst).dt.strftime('%Y-%m-%d')

# --- airport_pax ---
airport = pd.read_csv(os.path.join(CSV_DIR, 'airport_pax.csv'))
airport['date_key'] = iso_date(airport['date_key'], dayfirst=True)
airport = airport.sort_values(['year', 'month']).reset_index(drop=True)
airport.to_sql('airport_pax', conn, if_exists='replace', index=False)
print(f"airport_pax: {len(airport)} rows loaded")

# --- emc_cairns ---
# Use emc_cairns_clean.csv which has clean column names without duplicates
emc = pd.read_csv(os.path.join(CSV_DIR, 'emc_cairns_clean.csv'))
emc.columns = [c.strip() for c in emc.columns]
# Drop any unnamed/empty trailing columns
emc = emc.loc[:, ~emc.columns.str.startswith('Unnamed')]
# Keep only rows with actual data
emc = emc[emc['Full_Day'].notna()].copy()
# quarter_num = the quarter code (Q1..Q4) — the model renames this to "Qrt".
# Extract it from Quarter_Label (e.g. '2016-Q1'), NOT from the 'Quarter' date-range label.
emc['quarter_num'] = emc['Quarter_Label'].str.extract(r'(Q\d)')[0]
qmap = {'Q1': 1, 'Q2': 2, 'Q3': 3, 'Q4': 4}
qn = emc['quarter_num'].map(qmap)
# year_qtr_sort = join key to dim_date, e.g. 20161 — must be a clean INTEGER
emc['year_qtr_sort'] = (emc['Year'].astype(int) * 10 + qn).astype(int)
# Force integer dtype on numeric columns so they don't store as REAL/float
for col in ['Year', 'Total_Visits', 'Full_Day', 'Part_Day', 'Exempt', 'Scenic_Flights']:
    if col in emc.columns:
        emc[col] = emc[col].astype('int64')
emc = emc.sort_values('year_qtr_sort').reset_index(drop=True)
emc.to_sql('emc_cairns', conn, if_exists='replace', index=False)
print(f"emc_cairns: {len(emc)} rows loaded (year_qtr_sort {emc['year_qtr_sort'].min()}-{emc['year_qtr_sort'].max()})")

# --- PAX_DATA ---
# Use Pax.csv — contains boat_raw column that Power BI expects
pax = pd.read_csv(os.path.join(CSV_DIR, 'Pax.csv'))
pax['date'] = iso_date(pax['date'])
pax = pax.sort_values('date').reset_index(drop=True)
pax.to_sql('PAX_DATA', conn, if_exists='replace', index=False)
print(f"PAX_DATA: {len(pax)} rows loaded (sorted by date)")

# --- dim_date ---
dim = pd.read_csv(os.path.join(CSV_DIR, 'dim_date.csv'))
dim['date'] = iso_date(dim['date'])
# Rename 'Qtr Label' (with space) to 'quarter_label' as Power BI expects
dim = dim.rename(columns={'Qtr Label': 'quarter_label'})
# Drop COVID_Period — it's a Power BI calculated column, not a stored one.
# Keeping it in the source collides with the model's calculated column.
dim = dim.drop(columns=['COVID_Period'], errors='ignore')
dim = dim.sort_values('date').reset_index(drop=True)
dim.to_sql('dim_date', conn, if_exists='replace', index=False)
print(f"dim_date: {len(dim)} rows loaded")

# --- cairns_rainfall + severe_weather (if present) ---
# Produced by add_weather.py from the SILO/BOM rainfall extract.
for tbl, fname in [('cairns_rainfall', 'cairns_rainfall.csv'),
                   ('cairns_rainfall_qtr', 'cairns_rainfall_qtr.csv'),
                   ('severe_weather', 'severe_weather.csv')]:
    fpath = os.path.join(CSV_DIR, fname)
    if os.path.exists(fpath):
        df = pd.read_csv(fpath)
        df.to_sql(tbl, conn, if_exists='replace', index=False)
        print(f"{tbl}: {len(df)} rows loaded")

conn.close()
print("\nPaxday.db rebuilt successfully.")
