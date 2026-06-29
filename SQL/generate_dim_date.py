"""
Regenerates dim_date as a full DAILY calendar dimension covering the
whole data range (2009-01-01 .. 2026-12-31) so the monthly rainfall and
airport-pax keys (1st of month) all have a matching date.

Writes dim_date.csv (consumed by rebuild_paxday.py) and loads dim_date
into Paxday.db. Same column schema the Power BI model expects.
COVID_Period is intentionally omitted (it's a PBI calculated column).
"""

import sqlite3
import pandas as pd

DB_PATH  = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
CSV_PATH = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets\dim_date.csv'

dates = pd.date_range('2009-01-01', '2026-12-31', freq='D')
d = pd.DataFrame({'dt': dates})
d['date']         = d['dt'].dt.strftime('%Y-%m-%d')
d['day_num']      = d['dt'].dt.weekday + 1                  # Mon=1 .. Sun=7
d['day_of_week']  = d['dt'].dt.day_name()
d['week_num']     = d['dt'].dt.isocalendar().week.astype(int)
d['month_num']    = d['dt'].dt.month
d['month_name']   = d['dt'].dt.month_name()
d['quarter']      = (d['dt'].dt.month - 1) // 3 + 1
d['year']         = d['dt'].dt.year
d['is_weekend']   = (d['dt'].dt.weekday >= 5).astype(int)
d['quarter_label'] = 'Q' + d['quarter'].astype(str)
d['year_qtr_sort'] = d['year'] * 10 + d['quarter']
d['year_qtr_label'] = 'Q' + d['quarter'].astype(str) + ' ' + d['year'].astype(str)

dim = d[['date', 'day_num', 'day_of_week', 'week_num', 'month_num', 'month_name',
         'quarter', 'year', 'is_weekend', 'quarter_label', 'year_qtr_sort', 'year_qtr_label']]

dim.to_csv(CSV_PATH, index=False)

conn = sqlite3.connect(DB_PATH)
dim.to_sql('dim_date', conn, if_exists='replace', index=False)
# sanity: do all monthly keys now resolve?
rk = [r[0] for r in conn.execute("SELECT date_key FROM cairns_rainfall").fetchall()]
dd = set(r[0] for r in conn.execute("SELECT date FROM dim_date").fetchall())
ak = [r[0] for r in conn.execute("SELECT date_key FROM airport_pax").fetchall()]
conn.close()

print(f"dim_date: {len(dim)} rows, {dim['date'].min()} to {dim['date'].max()}")
print(f"rainfall keys matched: {sum(k in dd for k in rk)}/{len(rk)}")
print(f"airport keys matched : {sum(k in dd for k in ak)}/{len(ak)}")
