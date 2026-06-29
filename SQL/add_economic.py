"""
Adds economic drivers to Paxday.db and runs a first-pass (exploratory) check
of how they relate to reef visits and airport arrivals.

Sources (FRED, US Federal Reserve / OECD / IMF):
  - Brent crude oil, USD/barrel, monthly  (POILBREUSDM)  -> travel-cost proxy
  - Australia CPI, quarterly index (AUSCPIALLQINMEI)      -> inflation_yoy
Both are CC0/public. Tables: oil_monthly, oil_qtr, inflation_qtr.

CAVEATS (stated honestly): small quarterly sample, strong shared trends
(everything fell in COVID and recovered after), and these drivers are
intertwined with each other and with airport arrivals. Correlations below
exclude 2020-2021 and are EXPLORATORY, not causal.
"""
import sqlite3, pandas as pd, numpy as np
from scipy.stats import pearsonr

DB = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
SS = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets'
SCR = r'C:\Users\penny\AppData\Local\Temp\claude\C--Users-penny-Desktop-Claude\d2b63235-3106-45af-91fa-b5a695660f58\scratchpad'
conn = sqlite3.connect(DB)
COVID = [2020, 2021]


def qsort(y, m):
    return y * 10 + ((m - 1) // 3 + 1)

# ---- Brent oil ----
oil = pd.read_csv(SCR + r'\brent.csv', parse_dates=['observation_date'])
oil.columns = ['date', 'brent_usd']
oil = oil[oil['date'].dt.year >= 2009].copy()
oil['year'] = oil['date'].dt.year
oil['month'] = oil['date'].dt.month
oil['date_key'] = oil['date'].dt.strftime('%Y-%m-01')
oil['year_qtr_sort'] = oil.apply(lambda r: qsort(r.year, r.month), axis=1)
oil['brent_usd'] = oil['brent_usd'].round(2)
oil_m = oil[['date_key', 'year', 'month', 'year_qtr_sort', 'brent_usd']]
oil_q = oil.groupby('year_qtr_sort', as_index=False)['brent_usd'].mean().round(2)

# ---- Australia CPI -> inflation ----
cpi = pd.read_csv(SS.replace(SS, SCR) + r'\auscpi.csv', parse_dates=['observation_date'])
cpi.columns = ['date', 'cpi_index']
cpi = cpi.sort_values('date').reset_index(drop=True)
cpi['inflation_yoy'] = (cpi['cpi_index'] / cpi['cpi_index'].shift(4) - 1) * 100
cpi = cpi[cpi['date'].dt.year >= 2009].copy()
cpi['year'] = cpi['date'].dt.year
cpi['quarter'] = cpi['date'].dt.quarter
cpi['year_qtr_sort'] = cpi.apply(lambda r: qsort(r.year, r['date'].month), axis=1)
cpi['cpi_index'] = cpi['cpi_index'].round(2)
cpi['inflation_yoy'] = cpi['inflation_yoy'].round(2)
infl_q = cpi[['year_qtr_sort', 'year', 'quarter', 'cpi_index', 'inflation_yoy']]

for name, frame in [('oil_monthly', oil_m), ('oil_qtr', oil_q), ('inflation_qtr', infl_q)]:
    frame.to_sql(name, conn, if_exists='replace', index=False)
    frame.to_csv(f'{SS}\\{name}.csv', index=False)

# ---- First-pass analysis (quarterly, non-COVID) ----
qa = pd.read_sql("SELECT year_qtr_sort, year, reef_visits, airport_inbound FROM quarterly_anomalies", conn)
df = qa.merge(oil_q, on='year_qtr_sort', how='left').merge(
    infl_q[['year_qtr_sort', 'inflation_yoy']], on='year_qtr_sort', how='left')
df = df[~df['year'].isin(COVID)]


def report(metric):
    print(f"\n{metric} vs ... (quarters excl. COVID):")
    for drv in ['brent_usd', 'inflation_yoy']:
        s = df.dropna(subset=[metric, drv])
        # YoY % change to strip trend
        s = s.sort_values('year_qtr_sort').copy()
        s['m_g'] = s[metric].pct_change(4) * 100
        s['d_g'] = s[drv].diff(4) if drv == 'inflation_yoy' else s[drv].pct_change(4) * 100
        lvl = pearsonr(s[metric], s[drv])[0]
        g = s.dropna(subset=['m_g', 'd_g'])
        yoy = pearsonr(g['m_g'], g['d_g'])[0] if len(g) > 5 else float('nan')
        print(f"  {drv:14}  level r={lvl:+.2f}   year-on-year-change r={yoy:+.2f}   (n={len(s)})")


conn.close()
print("oil_monthly / oil_qtr / inflation_qtr written to DB + CSV.")
report('airport_inbound')
report('reef_visits')
print("\n(Exploratory only - small sample, shared trends, intertwined drivers.)")
