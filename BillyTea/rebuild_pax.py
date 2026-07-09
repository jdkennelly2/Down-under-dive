"""
rebuild_pax.py  --  Billy Tea PAX master rebuilder
==================================================
Finds the newest Billy Tea month-end "Summary Report.xlsx", reads its STATS tab,
unpivots the wide (months x years) matrix for both products into a tidy long
table, and (over)writes the master  "Pax Numbers.xlsx"  used as the Power BI source.

Run monthly after the new month-end Summary Report is saved.

Why it copies files to temp before opening: the live Summary Report / master often
sits in a OneDrive-synced, sometimes-locked location, which makes a direct openpyxl
read/write fail with PermissionError. Copying to a temp file sidesteps that.
"""

import os
import re
import glob
import shutil
import tempfile
from datetime import datetime

import openpyxl
from openpyxl import Workbook

# ---------------------------------------------------------------------------
# CONFIG  --  the only two paths you'd ever need to change
# ---------------------------------------------------------------------------
SEARCH_ROOT = r"C:\Users\penny\Down Under Cruise and Dive\Files - DUD-SHARED\Accounts\Month End\END OF MONTH\MONTH END - BILLY TEA\Billy Tea Month End"
DEST        = os.path.join(SEARCH_ROOT, "Pax Numbers.xlsx")

# Product blocks are auto-detected in the STATS sheet by these header labels
PRODUCTS = {
    "DAINTREE CAPE TRIBULATION": "Daintree Cape Tribulation",
    "CHILLAGOE CAVES":           "Chillagoe Caves",
}
MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
          "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]
MONTH_IDX = {m: i + 1 for i, m in enumerate(MONTHS)}


def _open_readonly(path):
    """Copy to a temp file first (handles OneDrive locks), then load values-only."""
    tmp = os.path.join(tempfile.gettempdir(), "billytea_src_tmp.xlsx")
    shutil.copy2(path, tmp)
    return openpyxl.load_workbook(tmp, data_only=True)


def _latest_data_month(ws):
    """Return the latest (year, month_no) that has a Daintree value, for ranking files."""
    hdr = _find_blocks(ws)
    if "DAINTREE CAPE TRIBULATION" not in hdr:
        return (0, 0)
    year_cols, first_month_row = hdr["DAINTREE CAPE TRIBULATION"]
    latest = (0, 0)
    for i in range(12):
        r = first_month_row + i
        for year, col in year_cols.items():
            v = ws.cell(r, col).value
            if isinstance(v, (int, float)):
                latest = max(latest, (year, i + 1))
    return latest


def _find_blocks(ws):
    """
    Locate each product block. Returns {HEADER: (year_cols dict, first_month_row)}.
    A block = a header cell in col A, followed by a 'PAX NO' row carrying the year
    columns, followed by the 12 month rows.
    """
    blocks = {}
    for r in range(1, ws.max_row + 1):
        label = ws.cell(r, 1).value
        if not isinstance(label, str):
            continue
        key = label.strip().upper()
        if key in PRODUCTS:
            # find the 'PAX NO' row at or just below the header
            pax_row = None
            for rr in range(r, min(r + 3, ws.max_row) + 1):
                v = ws.cell(rr, 1).value
                if isinstance(v, str) and v.strip().upper() == "PAX NO":
                    pax_row = rr
                    break
            if pax_row is None:
                continue
            year_cols = {}
            for c in range(2, ws.max_column + 1):
                yv = ws.cell(pax_row, c).value
                if isinstance(yv, (int, float)) and 2000 <= int(yv) <= 2100:
                    year_cols[int(yv)] = c
            blocks[key] = (year_cols, pax_row + 1)
    return blocks


def find_newest_summary():
    """Pick the Summary Report with the most recent data month (falls back to mtime)."""
    candidates = glob.glob(os.path.join(SEARCH_ROOT, "**", "*Summary Report.xlsx"),
                           recursive=True)
    candidates = [c for c in candidates if "~$" not in c]  # skip Excel lock stubs
    if not candidates:
        raise FileNotFoundError(f"No '*Summary Report.xlsx' found under {SEARCH_ROOT}")

    def rank(path):
        # Prefer YYYY MM parsed from filename (e.g. "2026 05 May Summary Report.xlsx")
        m = re.match(r"(\d{4})\D+(\d{2})", os.path.basename(path))
        if m:
            return (int(m.group(1)), int(m.group(2)), os.path.getmtime(path))
        return (0, 0, os.path.getmtime(path))

    return max(candidates, key=rank)


def build(src=None):
    src = src or find_newest_summary()
    print(f"Source Summary Report : {src}")
    wb = _open_readonly(src)
    if "STATS" not in wb.sheetnames:
        raise ValueError(f"No 'STATS' sheet in {src}")
    ws = wb["STATS"]
    blocks = _find_blocks(ws)

    rows = []
    for header, product in PRODUCTS.items():
        if header not in blocks:
            print(f"  WARNING: block '{header}' not found -- skipped")
            continue
        year_cols, first_row = blocks[header]
        for i in range(12):
            r = first_row + i
            month_no = i + 1
            for year, col in year_cols.items():
                v = ws.cell(r, col).value
                if not isinstance(v, (int, float)):
                    continue
                fy = year + 1 if month_no >= 7 else year   # Australian FY (Jul-Jun)
                rows.append({
                    "Date": datetime(year, month_no, 1),
                    "Year": year,
                    "MonthNo": month_no,
                    "Month": MONTHS[i].title(),
                    "FY": f"FY{fy}",
                    "Product": product,
                    "Pax": int(v),
                })

    rows.sort(key=lambda x: (x["Product"], x["Date"]))

    out = Workbook()
    sh = out.active
    sh.title = "PAX_DATA"
    cols = ["Date", "Year", "MonthNo", "Month", "FY", "Product", "Pax"]
    sh.append(cols)
    for row in rows:
        sh.append([row[c] for c in cols])
    for cell in sh["A"][1:]:
        cell.number_format = "yyyy-mm-dd"
    for c, w in zip("ABCDEFG", [12, 7, 9, 11, 9, 26, 8]):
        sh.column_dimensions[c].width = w

    # save to temp then copy to DEST (handles locked/synced destination)
    tmp_out = os.path.join(tempfile.gettempdir(), "Pax Numbers_tmp.xlsx")
    out.save(tmp_out)
    shutil.copy2(tmp_out, DEST)

    latest = max((r["Year"], r["MonthNo"]) for r in rows)
    print(f"Rows written          : {len(rows)}  ({len(rows)//2} per product)")
    print(f"Latest data month     : {latest[0]}-{latest[1]:02d}")
    print(f"Master saved to       : {DEST}")
    return rows


if __name__ == "__main__":
    build()
