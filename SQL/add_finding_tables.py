"""
Builds two small summary tables that make the 'rainfall is not a real driver'
finding easy to visualise in Power BI:
  - rainfall_corr_summary : raw vs seasonally-adjusted correlation per metric
  - rainfall_pax_buckets   : avg daily boat passengers by rainfall bucket
Recomputed from the data (not hardcoded) so they stay accurate.
"""
import sqlite3, pandas as pd, numpy as np
from scipy.stats import pearsonr

DB = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
RAW = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets\silo_daily.txt'
conn = sqlite3.connect(DB)
COVID = [2020, 2021]

# ---- Quarterly correlations (reef, airport) raw vs de-seasonalised ----
qa = pd.read_sql("SELECT * FROM quarterly_anomalies", conn)
base = qa[~qa['year'].isin(COVID)]


def rr(frame, a, b):
    s = frame.dropna(subset=[a, b]); s = s[~s['year'].isin(COVID)]
    return pearsonr(s[a], s[b])[0]


rows = []
rows.append(("Reef visits", "Quarterly",
             rr(qa, 'reef_visits', 'rainfall_mm'),
             rr(qa, 'reef_visits_anom', 'rainfall_mm_anom')))
rows.append(("Airport arrivals", "Quarterly",
             rr(qa, 'airport_inbound', 'rainfall_mm'),
             rr(qa, 'airport_inbound_anom', 'rainfall_mm_anom')))

# ---- Daily boat passengers (raw vs de-seasonalised) + buckets ----
drows = []
with open(RAW) as f:
    for line in f:
        p = line.split()
        if len(p) < 8 or not (p[0].isdigit() and len(p[0]) == 8):
            continue
        if int(p[0][:4]) < 2018:
            continue
        drows.append((f"{p[0][:4]}-{p[0][4:6]}-{p[0][6:8]}", float(p[7])))
rain = pd.DataFrame(drows, columns=['date', 'rain_mm'])
pax = pd.read_sql("SELECT date, passengers FROM PAX_DATA", conn)
d = pax.merge(rain, on='date').query("passengers > 0").copy()
d['month'] = pd.to_datetime(d['date']).dt.month
d['pax_anom'] = d['passengers'] - d.groupby('month')['passengers'].transform('mean')
d['rain_anom'] = d['rain_mm'] - d.groupby('month')['rain_mm'].transform('mean')
rows.append(("Boat passengers", "Daily",
             pearsonr(d['rain_mm'], d['passengers'])[0],
             pearsonr(d['rain_anom'], d['pax_anom'])[0]))

corr = pd.DataFrame(rows, columns=['metric', 'grain', 'raw_r', 'adjusted_r'])
corr['raw_r'] = corr['raw_r'].round(3)
corr['adjusted_r'] = corr['adjusted_r'].round(3)

bins = [-0.01, 1, 10, 25, 50, 1e9]
labels = ['Dry (0-1mm)', 'Light (1-10)', 'Moderate (10-25)', 'Heavy (25-50)', 'Extreme (50+)']
d['bucket'] = pd.cut(d['rain_mm'], bins=bins, labels=labels)
buck = d.groupby('bucket', observed=True)['passengers'].agg(avg_passengers='mean', days='size').reset_index()
buck['avg_passengers'] = buck['avg_passengers'].round(1)
buck['sort'] = range(1, len(buck) + 1)

corr.to_sql('rainfall_corr_summary', conn, if_exists='replace', index=False)
buck.to_sql('rainfall_pax_buckets', conn, if_exists='replace', index=False)
corr.to_csv(r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets\rainfall_corr_summary.csv', index=False)
buck.to_csv(r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets\rainfall_pax_buckets.csv', index=False)
conn.close()

print(corr.to_string(index=False))
print()
print(buck.to_string(index=False))
