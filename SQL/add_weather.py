"""
Adds Cairns rainfall + severe-weather data to Paxday.db.

Rainfall source: SILO Patched Point Dataset (Queensland Govt / Long Paddock),
  station 31011 CAIRNS AERO, sourced from the Bureau of Meteorology,
  CC BY 4.0. Raw file: Spreadsheets\\cairns_rainfall_silo_raw.txt
Severe weather: compiled from BOM cyclone histories, the Queensland
  Reconstruction Authority and the Australian Disaster Resilience Hub.

Creates two tables (replaces only these — other tables untouched):
  - cairns_rainfall : monthly rainfall (mm), 2009-2026
  - severe_weather  : verified cyclone / flood events affecting Cairns / FNQ

Re-runnable. Also writes cairns_rainfall.csv and severe_weather.csv.
"""

import sqlite3
import pandas as pd
import os

DB_PATH  = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
CSV_DIR  = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets'
SILO_RAW = os.path.join(CSV_DIR, 'cairns_rainfall_silo_raw.txt')


def qtr_sort(year, month):
    q = (month - 1) // 3 + 1
    return year * 10 + q


# --- Parse the SILO space-delimited monthly file ---
# Columns: YYYYMM00  TMax  TMin  Rain(mm)  Evap  Rad  VP
rows = []
with open(SILO_RAW, 'r') as f:
    for line in f:
        parts = line.split()
        if len(parts) < 4:
            continue
        key = parts[0]
        if not (key.isdigit() and len(key) == 8):
            continue
        year, month = int(key[:4]), int(key[4:6])
        if year < 2009 or month == 0:
            continue
        rainfall = float(parts[3])
        rows.append((year, month, rainfall))

rain = pd.DataFrame(rows, columns=['year', 'month', 'rainfall_mm'])
rain['date_key'] = rain.apply(lambda r: f"{int(r.year)}-{int(r.month):02d}-01", axis=1)
rain['year_qtr_sort'] = rain.apply(lambda r: qtr_sort(int(r.year), int(r.month)), axis=1)

# --- Verified severe-weather events affecting Cairns / Far North Queensland ---
# (cyclones + intense rain/flood; heat & fire deliberately excluded)
events = [
    # name, type, category, start, end, relevance, notes
    ("TC Tasha + Dec 2010 floods", "Cyclone + flooding", "Cat 1",
     "2010-12-25", "2011-01-10", "Direct",
     "Crossed coast near Gordonvale just south of Cairns; ~250mm, triggered major regional flooding."),
    ("Severe TC Yasi", "Cyclone", "Cat 5",
     "2011-02-02", "2011-02-03", "Regional",
     "Landfall near Mission Beach ~138km south of Cairns; est. wind gusts to 285km/h. Costliest Australian cyclone on record at the time."),
    ("Severe TC Ita", "Cyclone + flooding", "Cat 4",
     "2014-04-11", "2014-04-14", "Regional",
     "Landfall near Cape Flattery (north of Cooktown) as Cat 4; flooding and rescues between Cooktown and Cairns."),
    ("Ex-TC Winston (regional rain)", "Ex-cyclone flooding", None,
     "2016-03-03", "2016-03-05", "Regional",
     "Remnants of Cat 5 Winston (which devastated Fiji) crossed near Cairns; heaviest falls SOUTH of Cairns (Feluga 215mm). Cairns city rainfall stayed moderate (~258mm for the month)."),
    ("Ex-TC Nora flash flooding", "Ex-cyclone flooding", "Cat 3",
     "2018-03-26", "2018-03-28", "Direct",
     "Nora crossed Cape York as Cat 3; its remnant low caused severe flash flooding in Cairns 26-27 Mar - 40+ swift-water rescues, shopping centre & hotel inundated, Port Douglas 593mm in 24h."),
    ("TC Owen", "Cyclone + flooding", "Cat 3",
     "2018-12-11", "2018-12-15", "Regional",
     "Landfall in Far North Queensland mid-Dec; flooding rains across the region (Halifax 681mm in 24h)."),
    ("2019 NQ monsoon floods", "Monsoon flooding", None,
     "2019-01-25", "2019-02-10", "Regional",
     "Prolonged monsoon low; record flooding centred on Townsville with heavy rain across FNQ (Cairns ~826mm in January)."),
    ("TC Niran", "Cyclone", None,
     "2021-03-02", "2021-03-05", "Regional",
     "Developed off Cairns then tracked offshore to the SE (intensifying to Cat 5 over open water); main FNQ impact was wind and ~A$200m banana-crop damage near Innisfail. Limited Cairns rainfall."),
    ("March 2024 monsoon floods", "Monsoon flooding", None,
     "2024-03-01", "2024-03-10", "Direct",
     "Monsoon flooding across FNQ; Captain Cook Hwy (Cairns-Port Douglas) closed, Tully and surrounds inundated. Cairns ~892mm for the month."),
    ("Ex-TC Jasper flooding", "Ex-cyclone flooding", "Cat 2",
     "2023-12-13", "2023-12-28", "Direct",
     "Landfall near Wujal Wujal as Cat 2; wettest cyclone in Australian history. Barron River broke its 1977 record, Cairns Airport inundated, ~40,000 without power."),
    ("Jan 2026 NQ monsoon floods", "Monsoon flooding", None,
     "2026-01-01", "2026-01-31", "Regional",
     "Prolonged monsoonal rain and flooding across northern Queensland (lower-confidence event detail; flag for review)."),
]
sev = pd.DataFrame(events, columns=[
    'event_name', 'event_type', 'category', 'start_date', 'end_date', 'cairns_relevance', 'notes'])
sev['year'] = sev['start_date'].str[:4].astype(int)
sev['month'] = sev['start_date'].str[5:7].astype(int)
sev['year_qtr_sort'] = sev.apply(lambda r: qtr_sort(int(r.year), int(r.month)), axis=1)

# --- Flag rainfall months that contain a severe-weather event ---
sev_months = {(r.year, r.month): r.event_name for r in sev.itertuples()}
rain['severe_event'] = rain.apply(
    lambda r: sev_months.get((int(r.year), int(r.month))), axis=1)
rain['is_severe'] = rain['severe_event'].notna().astype(int)

# Order columns
rain = rain[['date_key', 'year', 'month', 'year_qtr_sort', 'rainfall_mm', 'severe_event', 'is_severe']]
sev = sev[['event_name', 'event_type', 'category', 'start_date', 'end_date',
           'year', 'month', 'year_qtr_sort', 'cairns_relevance', 'notes']]

# --- Quarterly rollup (joins to dim_date / emc_cairns on year_qtr_sort) ---
rain_q = (rain.groupby('year_qtr_sort')
          .agg(rainfall_mm=('rainfall_mm', 'sum'),
               months_in_qtr=('rainfall_mm', 'size'),
               year=('year', 'first'))
          .reset_index())
rain_q['quarter'] = rain_q['year_qtr_sort'] % 10
rain_q['year_qtr_label'] = rain_q.apply(lambda r: f"Q{int(r.quarter)} {int(r.year)}", axis=1)
rain_q['rainfall_mm'] = rain_q['rainfall_mm'].round(1)
# Any severe event in the quarter -> list the event name(s)
ev_by_qtr = (sev.groupby('year_qtr_sort')['event_name']
             .apply(lambda s: '; '.join(s)).to_dict())
rain_q['severe_event'] = rain_q['year_qtr_sort'].map(ev_by_qtr)
rain_q['is_severe'] = rain_q['severe_event'].notna().astype(int)
rain_q = rain_q[['year_qtr_sort', 'year', 'quarter', 'year_qtr_label',
                 'rainfall_mm', 'months_in_qtr', 'severe_event', 'is_severe']]

# --- Write CSVs (for the rebuild safety-net) ---
rain.to_csv(os.path.join(CSV_DIR, 'cairns_rainfall.csv'), index=False)
rain_q.to_csv(os.path.join(CSV_DIR, 'cairns_rainfall_qtr.csv'), index=False)
sev.to_csv(os.path.join(CSV_DIR, 'severe_weather.csv'), index=False)

# --- Load into the database (only these tables) ---
conn = sqlite3.connect(DB_PATH)
rain.to_sql('cairns_rainfall', conn, if_exists='replace', index=False)
rain_q.to_sql('cairns_rainfall_qtr', conn, if_exists='replace', index=False)
sev.to_sql('severe_weather', conn, if_exists='replace', index=False)
conn.close()

# --- Sanity checks ---
print(f"cairns_rainfall: {len(rain)} months  ({rain['date_key'].min()} to {rain['date_key'].max()})")
print(f"severe_weather : {len(sev)} events")
print("\nWettest 5 months on record (mm):")
print(rain.nlargest(5, 'rainfall_mm')[['date_key', 'rainfall_mm', 'severe_event']].to_string(index=False))
print("\nRainfall in known event months:")
for (y, m) in [(2010,12),(2011,2),(2014,4),(2023,12)]:
    val = rain[(rain.year==y)&(rain.month==m)]['rainfall_mm'].iloc[0]
    print(f"  {y}-{m:02d}: {val:.1f} mm")
print("\nDone.")
