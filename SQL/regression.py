"""
Multivariate regression to disentangle the drivers of demand and rank them.

Two models (quarterly, COVID 2020-2021 excluded, seasonal quarter controls):
  Model A - Reef visits ~ airport arrivals + oil + inflation + rainfall
  Model B - Airport arrivals ~ oil + inflation

All continuous variables are standardized (z-scores), so each coefficient is a
'standardized beta' = how many SD the outcome moves per 1 SD of that driver,
holding the others fixed. That makes the drivers directly comparable / rankable.
VIF flags multicollinearity (drivers explaining each other).
"""
import sqlite3, pandas as pd, numpy as np
import statsmodels.formula.api as smf
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

DB = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
conn = sqlite3.connect(DB)
COVID = [2020, 2021]

qa = pd.read_sql("SELECT year_qtr_sort, year, quarter, reef_visits, airport_inbound, rainfall_mm FROM quarterly_anomalies", conn)
oil = pd.read_sql("SELECT year_qtr_sort, brent_usd FROM oil_qtr", conn)
infl = pd.read_sql("SELECT year_qtr_sort, inflation_yoy FROM inflation_qtr", conn)
conn.close()

df = qa.merge(oil, on='year_qtr_sort', how='left').merge(infl, on='year_qtr_sort', how='left')
df = df[~df['year'].isin(COVID)].copy()

def z(s):
    return (s - s.mean()) / s.std()

for c in ['reef_visits', 'airport_inbound', 'rainfall_mm', 'brent_usd', 'inflation_yoy']:
    df[c + '_z'] = z(df[c])


def run(title, formula, data, drivers, need):
    data = data.dropna(subset=need)
    m = smf.ols(formula, data=data).fit()
    print(f"\n{'='*66}\n  {title}   (n={int(m.nobs)},  R-squared={m.rsquared:.2f})\n{'='*66}")
    print(f"{'driver':22}{'std beta':>10}{'p-value':>10}   effect")
    rows = []
    for d, lab in drivers:
        b, p = m.params.get(d, np.nan), m.pvalues.get(d, np.nan)
        sig = 'strong' if p < 0.01 else 'moderate' if p < 0.05 else 'weak' if p < 0.1 else 'none'
        arrow = '+' if b > 0 else '-'
        print(f"{lab:22}{b:>+10.2f}{p:>10.3f}   {arrow} {sig}")
        rows.append((title, lab, round(b, 3), round(p, 3), sig))
    return rows


rows = []
rows += run("Model A: REEF VISITS",
    "reef_visits_z ~ airport_inbound_z + brent_usd_z + inflation_yoy_z + rainfall_mm_z + C(quarter)",
    df, [('airport_inbound_z', 'Airport arrivals'), ('brent_usd_z', 'Oil price'),
         ('inflation_yoy_z', 'Inflation'), ('rainfall_mm_z', 'Rainfall')],
    need=['reef_visits_z', 'airport_inbound_z', 'brent_usd_z', 'inflation_yoy_z', 'rainfall_mm_z'])

rows += run("Model B: AIRPORT ARRIVALS",
    "airport_inbound_z ~ brent_usd_z + inflation_yoy_z + C(quarter)",
    df, [('brent_usd_z', 'Oil price'), ('inflation_yoy_z', 'Inflation')],
    need=['airport_inbound_z', 'brent_usd_z', 'inflation_yoy_z'])

# Multicollinearity check (reef model predictors)
print(f"\n{'='*66}\n  Multicollinearity (VIF > 5 = drivers explain each other)\n{'='*66}")
X = df.dropna(subset=['airport_inbound_z','brent_usd_z','inflation_yoy_z','rainfall_mm_z'])[
    ['airport_inbound_z','brent_usd_z','inflation_yoy_z','rainfall_mm_z']]
X = sm.add_constant(X)
for i, col in enumerate(X.columns):
    if col == 'const':
        continue
    print(f"  {col:20} VIF = {variance_inflation_factor(X.values, i):.1f}")

pd.DataFrame(rows, columns=['model','driver','std_beta','p_value','strength']).to_sql(
    'driver_regression', sqlite3.connect(DB), if_exists='replace', index=False)
print("\nSaved driver_regression to DB.")
