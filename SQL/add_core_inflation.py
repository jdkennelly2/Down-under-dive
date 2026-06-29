"""
Replace headline CPI with the RBA TRIMMED-MEAN inflation (year-ended) - the
underlying measure that EXCLUDES volatile items including fuel. This decouples
'inflation' from oil, so we can cleanly test whether underlying cost-of-living
drives demand independently of the oil/travel-cost channel.

Source: RBA Statistical Table G1, series GCPIOCPMTMYP (col index 10).
Builds inflation_core_qtr, then re-runs the driver models.
"""
import sqlite3, pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor
import statsmodels.api as sm

DB = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
SS = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\Spreadsheets'
SCR = r'C:\Users\penny\AppData\Local\Temp\claude\C--Users-penny-Desktop-Claude\d2b63235-3106-45af-91fa-b5a695660f58\scratchpad'
COVID = [2020, 2021]

rows = []
with open(SCR + r'\rba_g1.csv', encoding='utf-8-sig') as f:
    for line in f:
        p = line.rstrip('\n').split(',')
        if len(p) < 11 or '/' not in p[0]:
            continue
        try:
            dd, mm, yy = p[0].split('/')
            yy, mm = int(yy), int(mm)
        except ValueError:
            continue
        tm = p[10].strip()
        if yy >= 2009 and tm:
            q = (mm - 1) // 3 + 1
            rows.append((yy * 10 + q, yy, q, float(tm)))

core = pd.DataFrame(rows, columns=['year_qtr_sort', 'year', 'quarter', 'trimmed_mean_yoy'])
conn = sqlite3.connect(DB)
core.to_sql('inflation_core_qtr', conn, if_exists='replace', index=False)
core.to_csv(f'{SS}\\inflation_core_qtr.csv', index=False)
print(f"inflation_core_qtr: {len(core)} quarters ({core['year'].min()}-{core['year'].max()})")
print("Trimmed-mean inflation sample (year-ended %):")
print(core.tail(6).to_string(index=False))

# --- Re-run models with trimmed-mean inflation ---
qa = pd.read_sql("SELECT year_qtr_sort, year, quarter, reef_visits, airport_inbound, rainfall_mm FROM quarterly_anomalies", conn)
oil = pd.read_sql("SELECT year_qtr_sort, brent_usd FROM oil_qtr", conn)
conn.close()
df = qa.merge(oil, on='year_qtr_sort').merge(core[['year_qtr_sort', 'trimmed_mean_yoy']], on='year_qtr_sort')
df = df[~df['year'].isin(COVID)].copy()
for c in ['reef_visits', 'airport_inbound', 'rainfall_mm', 'brent_usd', 'trimmed_mean_yoy']:
    df[c + '_z'] = (df[c] - df[c].mean()) / df[c].std()


def fit(title, formula, terms, need):
    m = smf.ols(formula, data=df.dropna(subset=need)).fit()
    print(f"\n{title}  (n={int(m.nobs)}, R2={m.rsquared:.2f})")
    for t, lab in terms:
        b, pv = m.params.get(t), m.pvalues.get(t)
        sig = 'strong' if pv < 0.01 else 'moderate' if pv < 0.05 else 'weak' if pv < 0.1 else 'none'
        print(f"   {lab:18}{b:+.2f}  (p={pv:.3f})  {sig}")


print("\n" + "=" * 60)
print("  WITH TRIMMED-MEAN (ex-fuel) INFLATION")
print("=" * 60)
fit("Model A: Reef visits",
    "reef_visits_z ~ airport_inbound_z + brent_usd_z + trimmed_mean_yoy_z + rainfall_mm_z + C(quarter)",
    [('airport_inbound_z', 'Airport arrivals'), ('brent_usd_z', 'Oil price'),
     ('trimmed_mean_yoy_z', 'Core inflation'), ('rainfall_mm_z', 'Rainfall')],
    ['reef_visits_z', 'airport_inbound_z', 'brent_usd_z', 'trimmed_mean_yoy_z', 'rainfall_mm_z'])
fit("Model B: Airport arrivals",
    "airport_inbound_z ~ brent_usd_z + trimmed_mean_yoy_z + C(quarter)",
    [('brent_usd_z', 'Oil price'), ('trimmed_mean_yoy_z', 'Core inflation')],
    ['airport_inbound_z', 'brent_usd_z', 'trimmed_mean_yoy_z'])

# VIF oil vs core inflation
X = sm.add_constant(df.dropna(subset=['brent_usd_z', 'trimmed_mean_yoy_z'])[['brent_usd_z', 'trimmed_mean_yoy_z']])
print("\nVIF (oil vs core inflation):")
for i, c in enumerate(X.columns):
    if c != 'const':
        print(f"   {c:20} {variance_inflation_factor(X.values, i):.2f}")
