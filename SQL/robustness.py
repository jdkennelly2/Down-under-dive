"""
Is it OIL or INFLATION? They overlap (fuel is in CPI), so test whether each
driver's effect survives when the other is present.

Logic: if inflation is significant ALONE but loses significance once oil is
added - while oil stays significant either way - then oil is the true driver
and inflation was just proxying for it. (And vice-versa.)
Standardized betas; quarterly; COVID excluded; seasonal controls.
"""
import sqlite3, pandas as pd
import statsmodels.formula.api as smf

DB = r'C:\Users\penny\Desktop\DA\Projects\DOWN UNDER DIVE\SQL\Paxday.db'
conn = sqlite3.connect(DB)
COVID = [2020, 2021]
qa = pd.read_sql("SELECT year_qtr_sort, year, quarter, reef_visits, airport_inbound FROM quarterly_anomalies", conn)
oil = pd.read_sql("SELECT year_qtr_sort, brent_usd FROM oil_qtr", conn)
infl = pd.read_sql("SELECT year_qtr_sort, inflation_yoy FROM inflation_qtr", conn)
conn.close()
df = qa.merge(oil, on='year_qtr_sort').merge(infl, on='year_qtr_sort')
df = df[~df['year'].isin(COVID)].copy()
for c in ['reef_visits', 'airport_inbound', 'brent_usd', 'inflation_yoy']:
    df[c+'_z'] = (df[c]-df[c].mean())/df[c].std()


def beta(formula, term, data):
    m = smf.ols(formula, data=data.dropna(subset=[c for c in data.columns if c.endswith('_z')])).fit()
    return m.params.get(term), m.pvalues.get(term)


def show(label, base):
    print(f"\n--- {label} ---")
    for tag, f in [
        ("oil alone     ", f"{base} + brent_usd_z + C(quarter)"),
        ("inflation alone", f"{base} + inflation_yoy_z + C(quarter)"),
        ("both together  ", f"{base} + brent_usd_z + inflation_yoy_z + C(quarter)"),
    ]:
        m = smf.ols(f, data=df.dropna(subset=[c for c in df.columns if c.endswith('_z')])).fit()
        ob, op = m.params.get('brent_usd_z'), m.pvalues.get('brent_usd_z')
        ib, ip = m.params.get('inflation_yoy_z'), m.pvalues.get('inflation_yoy_z')
        os = f"oil {ob:+.2f} (p={op:.3f})" if ob is not None else "oil   --      "
        isf = f"inflation {ib:+.2f} (p={ip:.3f})" if ib is not None else "inflation --"
        print(f"  {tag}:  {os}   {isf}")


show("REEF VISITS  (controlling for airport arrivals)", "reef_visits_z ~ airport_inbound_z")
show("AIRPORT ARRIVALS", "airport_inbound_z ~ 1")
