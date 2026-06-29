"""
bitre_airport_import.py
-----------------------
Reads BITRE monthly airport traffic data (WebMonthlyAirportDecember2025.xlsx),
filters for CAIRNS, and loads into Paxday.db as table: airport_pax

Expected file structure:
  - Sheet:       "Airport Passengers"
  - Rows 1-6:    Metadata / headers (skipped)
  - Row 7:       Column headers
  - Column A:    AIRPORT (filter = 'CAIRNS')
  - Column B:    Year
  - Column C:    Month
  - Columns D-F: Domestic Inbound / Outbound / Total
  - Columns G-I: International Inbound / Outbound / Total
  - Columns J-L: Total Inbound / Outbound / Total (ALL pax)
"""

import pandas as pd
import sqlite3
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────
XLSX_PATH = r"C:\Users\penny\Desktop\SQL\DOWN UNDER DIVE\Spreadsheets\WebMonthlyAirportDecember2025.xlsx"
DB_PATH   = r"C:\Users\penny\Desktop\SQL\DOWN UNDER DIVE\SQL\Paxday.db"   # adjust if different
TABLE     = "airport_pax"
SHEET     = "Airport Passengers"
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"Reading: {XLSX_PATH}")
    if not os.path.exists(XLSX_PATH):
        raise FileNotFoundError(f"XLSX not found at: {XLSX_PATH}")

    # Read sheet — skip the 6 metadata rows, row 7 becomes header
    raw = pd.read_excel(
        XLSX_PATH,
        sheet_name=SHEET,
        header=6,          # 0-indexed, so row 7 in Excel = index 6
        dtype=str          # read everything as string first for safety
    )

    print(f"Raw shape: {raw.shape}")
    print(f"Columns found: {list(raw.columns)}")

    # ── Rename columns to something clean ────────────────────────────────────
    # BITRE has multi-level headers that collapse into one row when header=6
    # Actual column order (A→L):
    # AIRPORT, Year, Month,
    # Dom_Inbound, Dom_Outbound, Dom_Total,
    # Intl_Inbound, Intl_Outbound, Intl_Total,
    # Total_Inbound, Total_Outbound, Total_Pax

    col_map = {
        raw.columns[0]:  "airport",
        raw.columns[1]:  "year",
        raw.columns[2]:  "month",
        raw.columns[3]:  "dom_inbound",
        raw.columns[4]:  "dom_outbound",
        raw.columns[5]:  "dom_total",
        raw.columns[6]:  "intl_inbound",
        raw.columns[7]:  "intl_outbound",
        raw.columns[8]:  "intl_total",
        raw.columns[9]:  "total_inbound",
        raw.columns[10]: "total_outbound",
        raw.columns[11]: "total_pax",
    }
    raw = raw.rename(columns=col_map)

    # ── Filter CAIRNS only ────────────────────────────────────────────────────
    df = raw[raw["airport"].str.strip().str.upper() == "CAIRNS"].copy()
    print(f"CAIRNS rows found: {len(df)}")

    # ── Clean numeric columns ─────────────────────────────────────────────────
    numeric_cols = [
        "dom_inbound", "dom_outbound", "dom_total",
        "intl_inbound", "intl_outbound", "intl_total",
        "total_inbound", "total_outbound", "total_pax"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].str.replace(",", ""), errors="coerce")

    df["year"]  = pd.to_numeric(df["year"],  errors="coerce").astype("Int64")
    df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")

    # ── Add a date key to match dim_date (YYYY-MM-01 format) ─────────────────
    df["date_key"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    ).dt.strftime("%Y-%m-%d")

    # Drop rows where year/month are null (e.g. blank trailing rows)
    df = df.dropna(subset=["year", "month"])

    # Final column order
    df = df[[
        "date_key", "year", "month",
        "dom_inbound", "dom_outbound", "dom_total",
        "intl_inbound", "intl_outbound", "intl_total",
        "total_inbound", "total_outbound", "total_pax"
    ]]

    print(f"\nSample output:")
    print(df.head(5).to_string(index=False))
    print(f"\nDate range: {df['date_key'].min()} → {df['date_key'].max()}")
    print(f"Total rows to load: {len(df)}")

    # ── Load into SQLite ──────────────────────────────────────────────────────
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    df.to_sql(TABLE, conn, if_exists="replace", index=False)
    conn.close()

    print(f"\n✅ Done — {len(df)} rows loaded into table '{TABLE}' in {DB_PATH}")

if __name__ == "__main__":
    main()