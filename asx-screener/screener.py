#!/usr/bin/env python3
"""
Deep Value ASX — live screener engine.

Screens ASX-listed shares for:
  1. Trailing P/E ratio below a threshold (default 10)
  2. Cash-flow positive (free cash flow > 0, else operating cash flow > 0)
  3. NOT pharmaceutical / biotech
  4. NOT a pre-revenue mining explorer

Pulls live fundamentals from Yahoo Finance via `yfinance` and writes
`data.json` (consumed by app.html) plus prints the first ten matches.

Usage:
    pip install yfinance
    python screener.py                 # default universe, P/E < 10
    python screener.py --pe-max 12     # widen the multiple
    python screener.py --universe my_tickers.txt   # one ASX code per line

Note: run this where Yahoo Finance is reachable (your own machine/phone).
Some managed/CI networks block finance.yahoo.com.
"""

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    sys.exit("Missing dependency. Run:  pip install yfinance")

HERE = Path(__file__).resolve().parent

# A broad ASX large/mid-cap universe. Edit freely or pass --universe <file>.
DEFAULT_UNIVERSE = [
    "ALD", "AMC", "ANZ", "APA", "ASX", "AZJ", "BEN", "BHP", "BOQ", "BSL",
    "BXB", "CAR", "CBA", "CGF", "CHC", "COL", "CPU", "CRN", "CSL", "DXS",
    "EDV", "EVN", "FMG", "GMG", "GNC", "GPT", "GQG", "HVN", "IAG", "IFL",
    "IGO", "ILU", "ING", "JBH", "JHX", "LLC", "MGR", "MIN", "MPL", "MQG",
    "MTS", "NAB", "NCK", "NEC", "NHC", "NST", "ORG", "ORI", "PMV", "PPT",
    "QAN", "QBE", "REA", "RGN", "RHC", "RIO", "RMD", "RRL", "S32", "SCG",
    "SDF", "SGM", "SGP", "SHL", "STO", "SUL", "SUN", "TAH", "TCL", "TLS",
    "TPG", "TWE", "VCX", "WBC", "WDS", "WES", "WHC", "WOR", "WOW", "YAL",
]

PHARMA_HINTS = ("drug", "pharmaceutic", "biotech", "medical device")
MINING_SECTORS = ("basic materials", "energy")
MINING_HINTS = ("mining", "metals", "coal", "gold", "copper", "iron",
                "lithium", "uranium", "nickel", "mineral")


def load_universe(path):
    if not path:
        return DEFAULT_UNIVERSE
    codes = []
    for line in Path(path).read_text().splitlines():
        c = line.strip().upper().replace(".AX", "")
        if c and not c.startswith("#"):
            codes.append(c)
    return codes


def looks_like_explorer(info):
    """Pre-revenue miner: a materials/energy resources name with no real
    revenue or negative earnings and no producing cash flow."""
    sector = (info.get("sector") or "").lower()
    industry = (info.get("industry") or "").lower()
    is_resources = sector in MINING_SECTORS and any(h in industry for h in MINING_HINTS)
    if not is_resources:
        return False
    revenue = info.get("totalRevenue") or 0
    eps = info.get("trailingEps")
    ocf = info.get("operatingCashflow") or 0
    # Explorer proxy: negligible revenue, or losses with no operating cash.
    if revenue < 1_000_000:
        return True
    if (eps is not None and eps <= 0) and ocf <= 0:
        return True
    return False


def is_pharma(info):
    text = ((info.get("industry") or "") + " " + (info.get("sector") or "")).lower()
    return any(h in text for h in PHARMA_HINTS)


def cash_flow_positive(info):
    fcf = info.get("freeCashflow")
    if fcf is not None:
        return fcf > 0
    ocf = info.get("operatingCashflow")
    return ocf is not None and ocf > 0


def fetch(code):
    tkr = yf.Ticker(f"{code}.AX")
    info = tkr.info or {}
    if not info.get("shortName") and not info.get("longName"):
        return None
    pe = info.get("trailingPE")
    return {
        "ticker": code,
        "name": info.get("shortName") or info.get("longName") or code,
        "sector": info.get("sector") or "—",
        "industry": info.get("industry") or "—",
        "pe": round(pe, 2) if isinstance(pe, (int, float)) else None,
        "cashFlowPositive": cash_flow_positive(info),
        "isPharma": is_pharma(info),
        "isMiningExploration": looks_like_explorer(info),
        "note": "",
    }


def passes(s, pe_max):
    return (
        not s["isPharma"]
        and not s["isMiningExploration"]
        and s["cashFlowPositive"]
        and s["pe"] is not None
        and s["pe"] < pe_max
    )


def main():
    ap = argparse.ArgumentParser(description="Screen ASX shares for deep value.")
    ap.add_argument("--pe-max", type=float, default=10.0, help="Maximum trailing P/E (default 10)")
    ap.add_argument("--universe", help="File with one ASX code per line")
    ap.add_argument("--out", default=str(HERE / "data.json"), help="Output JSON path")
    args = ap.parse_args()

    codes = load_universe(args.universe)
    print(f"Screening {len(codes)} ASX codes (P/E < {args.pe_max}, cash-flow "
          f"positive, ex-pharma, ex-exploration)...\n", file=sys.stderr)

    rows = []
    for i, code in enumerate(codes, 1):
        try:
            r = fetch(code)
            if r:
                rows.append(r)
                print(f"  [{i}/{len(codes)}] {code:5} pe={r['pe']}", file=sys.stderr)
        except Exception as e:
            print(f"  [{i}/{len(codes)}] {code:5} skipped ({type(e).__name__})", file=sys.stderr)
        time.sleep(0.4)  # be gentle on the API

    matches = sorted([r for r in rows if passes(r, args.pe_max)], key=lambda r: r["pe"])

    payload = {
        "meta": {
            "asOf": dt.date.today().isoformat(),
            "market": "ASX (Australian Securities Exchange)",
            "criteria": {
                "peMax": args.pe_max,
                "cashFlowPositive": True,
                "excludeSectors": ["Pharmaceuticals", "Biotechnology", "Mining exploration"],
            },
            "source": f"Live pull from Yahoo Finance via yfinance on {dt.date.today().isoformat()}.",
            "disclaimer": "General information only, not financial advice. Verify before acting.",
        },
        # Keep passers first (ranked), then the rest so the app can show near-misses.
        "stocks": matches + [r for r in rows if r not in matches],
    }
    Path(args.out).write_text(json.dumps(payload, indent=2))

    print(f"\n=== First {min(10, len(matches))} matches (of {len(matches)}) ===")
    for i, r in enumerate(matches[:10], 1):
        print(f"{i:2}. {r['ticker']:5} P/E {r['pe']:>5}  {r['sector']:<22} {r['name']}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
