"""
import_airport.py  --  load latest BITRE airport traffic into Paxday.db
=======================================================================
Auto-finds the newest BITRE monthly airport file in the "Airport data" folder,
filters for CAIRNS, and (re)loads table 'airport_pax' in Paxday.db + refreshes
Spreadsheets/airport_pax.csv.

BITRE file naming has changed over time; this matches both:
  - aviation-airport_traffic_data-<month>_<year>.xlsx   (current)
  - WebMonthlyAirport<Month><Year>.xlsx                 (older)

Sheet 'Airport Passengers', header on row 7 (0-indexed 6). Columns A-L:
  AIRPORT, Year, Month, Dom In/Out/Total, Intl In/Out/Total, Total In/Out/Pax
"""
import os
import glob
import sqlite3
import pandas as pd

REPO       = r"C:\Users\penny\Desktop\Data Analysis\DOWN UNDER DIVE\Down-under-dive"
AIRPORT_DIR = os.path.join(REPO, "Airport data")
DB_PATH    = os.path.join(REPO, "SQL", "Paxday.db")
CSV_OUT    = os.path.join(REPO, "Spreadsheets", "airport_pax.csv")
TABLE      = "airport_pax"
SHEET      = "Airport Passengers"


def newest_bitre_file():
    pats = ["aviation-airport_traffic_data-*.xlsx", "WebMonthlyAirport*.xlsx"]
    files = []
    for p in pats:
        files += glob.glob(os.path.join(AIRPORT_DIR, p))
    files = [f for f in files if "~$" not in f]
    if not files:
        raise FileNotFoundError(f"No BITRE airport file in {AIRPORT_DIR}")
    return max(files, key=os.path.getmtime)


def main():
    src = newest_bitre_file()
    print(f"Source: {src}")
    raw = pd.read_excel(src, sheet_name=SHEET, header=6, dtype=str)

    names = ["airport", "year", "month",
             "dom_inbound", "dom_outbound", "dom_total",
             "intl_inbound", "intl_outbound", "intl_total",
             "total_inbound", "total_outbound", "total_pax"]
    raw = raw.rename(columns={raw.columns[i]: n for i, n in enumerate(names)})

    df = raw[raw["airport"].astype(str).str.strip().str.upper() == "CAIRNS"].copy()

    num = names[3:]
    for c in num:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
    df["year"]  = pd.to_numeric(df["year"],  errors="coerce").astype("Int64")
    df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["year", "month"])

    df["date_key"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    ).dt.strftime("%Y-%m-%d")

    df = df[["date_key", "year", "month"] + num].sort_values(["year", "month"])

    conn = sqlite3.connect(DB_PATH)
    df.to_sql(TABLE, conn, if_exists="replace", index=False)
    conn.close()
    df.to_csv(CSV_OUT, index=False)

    print(f"Loaded {len(df)} CAIRNS rows -> {TABLE} + airport_pax.csv")
    print(f"Coverage: {df['date_key'].min()} .. {df['date_key'].max()}")
    print(df.tail(4)[["date_key", "dom_inbound", "intl_inbound", "total_inbound"]].to_string(index=False))


if __name__ == "__main__":
    main()
