"""
Plain-language version of the rainfall finding (no correlation/p-value jargon).
For each metric, split periods into 'wetter than usual' vs 'drier than usual'
(relative to that season/month) and express demand as % of normal (100 = typical).
If rain mattered, wetter periods would sit well below 100.
Builds rainfall_wet_dry for Power BI.
"""
import sqlite3, pandas as pd, numpy as np

DB = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
RAW = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets\silo_daily.txt'
conn = sqlite3.connect(DB)
COVID = [2020, 2021]

out = []

# ---- Quarterly reef + airport ----
qa = pd.read_sql("SELECT * FROM quarterly_anomalies", conn)
qa = qa[~qa['year'].isin(COVID)]
for metric, col in [("Reef visits", "reef_visits"), ("Airport arrivals", "airport_inbound")]:
    sub = qa.dropna(subset=[col, 'rainfall_mm']).copy()
    norm = sub.groupby('quarter')[col].transform('mean')      # seasonal norm
    sub['idx'] = sub[col] / norm * 100
    wetter = sub[sub['rainfall_mm_anom'] > 0]['idx'].mean()
    drier = sub[sub['rainfall_mm_anom'] < 0]['idx'].mean()
    out.append((metric, round(drier, 1), round(wetter, 1)))

# ---- Daily boat passengers ----
rows = []
with open(RAW) as f:
    for line in f:
        p = line.split()
        if len(p) < 8 or not (p[0].isdigit() and len(p[0]) == 8):
            continue
        if int(p[0][:4]) < 2018:
            continue
        rows.append((f"{p[0][:4]}-{p[0][4:6]}-{p[0][6:8]}", float(p[7])))
rain = pd.DataFrame(rows, columns=['date', 'rain_mm'])
pax = pd.read_sql("SELECT date, passengers FROM PAX_DATA", conn)
d = pax.merge(rain, on='date').query("passengers > 0").copy()
d['month'] = pd.to_datetime(d['date']).dt.month
pnorm = d.groupby('month')['passengers'].transform('mean')
rnorm = d.groupby('month')['rain_mm'].transform('mean')
d['idx'] = d['passengers'] / pnorm * 100
wetter = d[d['rain_mm'] > rnorm]['idx'].mean()
drier = d[d['rain_mm'] <= rnorm]['idx'].mean()
out.append(("Boat passengers (daily)", round(drier, 1), round(wetter, 1)))

wd = pd.DataFrame(out, columns=['metric', 'drier_than_usual', 'wetter_than_usual'])
wd.to_sql('rainfall_wet_dry', conn, if_exists='replace', index=False)
wd.to_csv(r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets\rainfall_wet_dry.csv', index=False)
conn.close()
print("Demand as % of normal (100 = typical for that season):\n")
print(wd.to_string(index=False))
