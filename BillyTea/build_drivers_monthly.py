"""
build_drivers_monthly.py  --  Billy Tea driver table (monthly grain)
====================================================================
Reads the external demand-driver data out of Paxday.db and flattens it all to a
single MONTHLY table aligned to the Billy Tea pax series, then writes
"drivers_monthly.csv" next to the Pax master so Power BI can consume both.

Drivers included (all keyed by month):
  - airport inbound pax (domestic / international / total)   [BITRE]
  - rainfall_mm + rain_days                                  [BoM/SILO]
  - severe_weather_events (count, by start month)            [manual/BoM]
  - brent_usd (oil)                                          [EIA]
  - cpi_index, inflation_yoy, core_inflation_yoy (broadcast from quarterly)

Grain = calendar month, 2010-01 .. latest available.
"""

import os
import shutil
import sqlite3
import tempfile
from datetime import datetime

import pandas as pd

REPO = r"C:\Users\penny\Desktop\Data Analysis\DOWN UNDER DIVE\Down-under-dive"
DB   = os.path.join(REPO, "SQL", "Paxday.db")
DEST_DIR = r"C:\Users\penny\Down Under Cruise and Dive\Files - DUD-SHARED\Accounts\Month End\END OF MONTH\MONTH END - BILLY TEA\Billy Tea Month End"
OUT  = os.path.join(DEST_DIR, "drivers_monthly.csv")

START = "2010-01-01"     # Billy Tea history start
END   = "2026-06-01"     # extend as data grows


def _conn():
    tmp = os.path.join(tempfile.gettempdir(), "paxday_drivers_tmp.db")
    shutil.copy2(DB, tmp)
    return sqlite3.connect(tmp)


def build():
    conn = _conn()

    # month spine
    spine = pd.DataFrame({"Date": pd.date_range(START, END, freq="MS")})
    spine["Year"] = spine["Date"].dt.year
    spine["MonthNo"] = spine["Date"].dt.month
    spine["Quarter"] = spine["Date"].dt.quarter

    # airport (monthly)
    air = pd.read_sql("SELECT year, month, dom_inbound, intl_inbound, total_inbound FROM airport_pax", conn)
    air = air.rename(columns={"year": "Year", "month": "MonthNo",
                              "dom_inbound": "airport_dom_inbound",
                              "intl_inbound": "airport_intl_inbound",
                              "total_inbound": "airport_total_inbound"})

    # rainfall (monthly)
    rain = pd.read_sql("SELECT year, month, rainfall_mm FROM cairns_rainfall", conn)
    rain = rain.rename(columns={"year": "Year", "month": "MonthNo"})

    # rain days from daily (>= 1mm), available 2018+
    daily = pd.read_sql("SELECT date, rain_mm FROM cairns_rainfall_daily", conn)
    daily["date"] = pd.to_datetime(daily["date"], errors="coerce")
    daily = daily.dropna(subset=["date"])
    daily["Year"] = daily["date"].dt.year
    daily["MonthNo"] = daily["date"].dt.month
    raindays = (daily[daily["rain_mm"] >= 1.0]
                .groupby(["Year", "MonthNo"]).size().reset_index(name="rain_days"))

    # severe weather events per month (by start month)
    sev = pd.read_sql("SELECT year, month FROM severe_weather", conn)
    sev = sev.rename(columns={"year": "Year", "month": "MonthNo"})
    sev = sev.dropna(subset=["Year", "MonthNo"])
    sev["Year"] = sev["Year"].astype(int); sev["MonthNo"] = sev["MonthNo"].astype(int)
    sevcnt = sev.groupby(["Year", "MonthNo"]).size().reset_index(name="severe_weather_events")

    # oil (monthly)
    oil = pd.read_sql("SELECT year, month, brent_usd FROM oil_monthly", conn)
    oil = oil.rename(columns={"year": "Year", "month": "MonthNo"})

    # inflation (quarterly -> broadcast to month)
    cpi  = pd.read_sql("SELECT year, quarter, cpi_index, inflation_yoy FROM inflation_qtr", conn)
    core = pd.read_sql("SELECT year, quarter, trimmed_mean_yoy AS core_inflation_yoy FROM inflation_core_qtr", conn)
    infl = pd.merge(cpi, core, on=["year", "quarter"], how="outer")
    infl = infl.rename(columns={"year": "Year", "quarter": "Quarter"})

    conn.close()

    # ---- assemble ----
    df = (spine
          .merge(air,     on=["Year", "MonthNo"], how="left")
          .merge(rain,    on=["Year", "MonthNo"], how="left")
          .merge(raindays,on=["Year", "MonthNo"], how="left")
          .merge(sevcnt,  on=["Year", "MonthNo"], how="left")
          .merge(oil,     on=["Year", "MonthNo"], how="left")
          .merge(infl,    on=["Year", "Quarter"], how="left"))

    df["severe_weather_events"] = df["severe_weather_events"].fillna(0).astype(int)
    df = df.rename(columns={"rainfall_mm": "rainfall_mm"})

    ordered = ["Date", "Year", "MonthNo", "Quarter",
               "airport_dom_inbound", "airport_intl_inbound", "airport_total_inbound",
               "rainfall_mm", "rain_days", "severe_weather_events",
               "brent_usd", "cpi_index", "inflation_yoy", "core_inflation_yoy"]
    df = df[ordered]

    tmp_out = os.path.join(tempfile.gettempdir(), "drivers_monthly_tmp.csv")
    df.to_csv(tmp_out, index=False, date_format="%Y-%m-%d")
    shutil.copy2(tmp_out, OUT)

    print(f"Rows: {len(df)}  ({df['Date'].min().date()} .. {df['Date'].max().date()})")
    print("Coverage (last non-null month per driver):")
    for c in ordered[4:]:
        s = df.dropna(subset=[c])
        last = s["Date"].max()
        print(f"  {c:24}: {last.date() if pd.notna(last) else 'NONE'}")
    print(f"\nSaved -> {OUT}")
    return df


if __name__ == "__main__":
    build()
