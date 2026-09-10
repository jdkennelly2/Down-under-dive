#!/usr/bin/env python3
"""
Deep Value ASX — live screener engine.

Screens ASX-listed shares for:
  1. Trailing P/E ratio below a threshold (default 10)
  2. Cash-flow positive (free cash flow > 0, else operating cash flow > 0)
  3. NOT pharmaceutical / biotech
  4. NOT mining, commodities or energy (producers and explorers alike)
  5. NOT a REIT — property trusts, whose earnings are distorted by
     revaluations. Real-estate *services* businesses (valuers, agents)
     are kept: they are operating companies, not trusts.
  6. NOT a fund manager — asset managers specifically, not financials
     broadly, so banks, insurers and lenders still qualify.

Dividend yield and payout ratio are collected and reported for whatever
passes, as extra context — they are not screening criteria.

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
    # Financials
    "ANZ", "AMP", "ASX", "BEN", "BOQ", "CBA", "CGF", "COG", "CPU", "GQG",
    "HLI", "HUB", "IAG", "IFL", "JHG", "MFG", "MPL", "MQG", "MYS", "NAB",
    "NWL", "PNI", "PPT", "PXA", "QBE", "SDF", "SUN", "WBC",
    # Real estate / REITs
    "ABG", "BWP", "CHC", "CIP", "CLW", "CMW", "CNI", "CQR", "DXS", "GMG",
    "GOZ", "GPT", "HDN", "HMC", "INA", "LLC", "MGR", "NSR", "RGN", "SCG",
    "SGP", "VCX", "WPR",
    # Consumer discretionary & retail
    "ACL", "ADH", "APE", "AX1", "BAP", "BRG", "CCX", "DSK", "GUD", "HVN",
    "JBH", "KGN", "LOV", "MTO", "NCK", "PMV", "PWR", "SNL", "SUL", "UNI",
    "WEB",
    # Consumer staples & agri
    "A2M", "COL", "ELD", "EDV", "GNC", "ING", "MTS", "RIC", "TWE", "WOW",
    # Industrials, transport & services
    "ALQ", "AZJ", "BXB", "CAR", "CWY", "DOW", "IPH", "LNW", "MND", "MMS",
    "QAN", "QUB", "REH", "SEK", "SGM", "SVW", "TCL", "WOR", "WTC",
    # Communication services, tech & utilities
    "APA", "CAT", "NEC", "NXT", "ORG", "REA", "SWM", "TLS", "TPG", "XRO",
    # Health care (mostly filtered out by the pharma rule, kept for coverage)
    "COH", "CSL", "FPH", "RHC", "RMD", "SHL", "SIG",
    # Resources & energy (kept so the exclusion is visible in the output)
    "ALD", "BHP", "EVN", "FMG", "IGO", "MIN", "NHC", "NST", "PLS", "RIO",
    "S32", "STO", "WDS", "WHC", "YAL",
]

PHARMA_HINTS = ("drug", "pharmaceutic", "biotech", "medical device")
MINING_SECTORS = ("basic materials", "energy")
MINING_HINTS = ("mining", "metals", "coal", "gold", "copper", "iron",
                "lithium", "uranium", "nickel", "mineral", "steel", "aluminum",
                "aluminium", "commodit")
ENERGY_HINTS = ("oil", "gas", "petroleum", "refin", "drilling", "coking",
                "thermal coal", "energy")
# A trust, not a property business: "REIT" in the industry is the reliable
# marker. Deliberately does NOT match real-estate services — a valuation or
# agency firm is an operating company and should still be screened in.
REIT_HINTS = ("reit", "real estate investment trust")
# Asset managers specifically. Kept narrow so banks, insurers, lenders,
# exchanges and leasing businesses are not swept up as "financials".
FUND_MANAGER_HINTS = ("asset management", "fund manage", "investment manage")

def pct(v, already_pct=False):
    """Normalise a rate to a percentage, or None when not reported."""
    if not isinstance(v, (int, float)):
        return None
    # yfinance returns some rates as fractions (0.0854) and some as percents.
    return round(v if already_pct or v > 1 else v * 100, 2)


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


def is_resources_or_energy(info):
    """Any miner, commodity producer or energy business — not just explorers."""
    sector = (info.get("sector") or "").lower()
    industry = (info.get("industry") or "").lower()
    if sector in MINING_SECTORS:
        return True
    return any(h in industry for h in MINING_HINTS + ENERGY_HINTS)


def is_reit(info):
    """A listed property trust. Real-estate services firms are not REITs."""
    industry = (info.get("industry") or "").lower()
    name = ((info.get("shortName") or "") + " " + (info.get("longName") or "")).lower()
    return any(h in industry for h in REIT_HINTS) or " reit" in name


def is_fund_manager(info):
    """An asset manager — not financials in general."""
    industry = (info.get("industry") or "").lower()
    return any(h in industry for h in FUND_MANAGER_HINTS)


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
        "dividendYield": pct(info.get("dividendYield")),
        "payoutRatio": pct(info.get("payoutRatio")),
        "isMiningExploration": looks_like_explorer(info),
        "isResourcesEnergy": is_resources_or_energy(info),
        "isREIT": is_reit(info),
        "isFundManager": is_fund_manager(info),
        "note": "",
    }


def passes(s, pe_max):
    return (
        not s["isPharma"]
        and not s["isResourcesEnergy"]
        and not s["isMiningExploration"]
        and not s["isREIT"]
        and not s["isFundManager"]
        and s["cashFlowPositive"]
        and s["pe"] is not None
        and s["pe"] < pe_max
    )


def main():
    ap = argparse.ArgumentParser(description="Screen ASX shares for deep value.")
    ap.add_argument("--pe-max", type=float, default=10.0, help="Maximum trailing P/E (default 10)")
    ap.add_argument("--include-resources", action="store_true",
                    help="Keep mining, commodity and energy names in the results")
    ap.add_argument("--include-reits", action="store_true",
                    help="Keep property trusts in the results")
    ap.add_argument("--include-fund-managers", action="store_true",
                    help="Keep asset managers in the results")
    ap.add_argument("--universe", help="File with one ASX code per line")
    ap.add_argument("--out", default=str(HERE / "data.json"), help="Output JSON path")
    args = ap.parse_args()

    codes = load_universe(args.universe)
    excl = ", ".join(["ex-pharma"]
                     + ([] if args.include_resources else ["ex-mining/energy"])
                     + ([] if args.include_reits else ["ex-REITs"])
                     + ([] if args.include_fund_managers else ["ex-fund-managers"]))
    print(f"Screening {len(codes)} ASX codes (P/E < {args.pe_max}, cash-flow "
          f"positive, {excl})...\n", file=sys.stderr)

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

    def keep(s):
        if s["isPharma"] or not s["cashFlowPositive"]:
            return False
        if s["pe"] is None or s["pe"] >= args.pe_max:
            return False
        if not args.include_resources and (s["isResourcesEnergy"] or s["isMiningExploration"]):
            return False
        if not args.include_reits and s["isREIT"]:
            return False
        if not args.include_fund_managers and s["isFundManager"]:
            return False
        return True

    matches = sorted([r for r in rows if keep(r)], key=lambda r: r["pe"])

    payload = {
        "meta": {
            "asOf": dt.date.today().isoformat(),
            "market": "ASX (Australian Securities Exchange)",
            "criteria": {
                "peMax": args.pe_max,
                "cashFlowPositive": True,
                "excludeSectors": ["Pharmaceuticals", "Biotechnology",
                                   "Mining & commodities", "Energy",
                                   "REITs", "Fund managers"],
            },
            "source": f"Live pull from Yahoo Finance via yfinance on {dt.date.today().isoformat()}.",
            "disclaimer": "General information only, not financial advice. Verify before acting.",
        },
        # Keep passers first (ranked), then the rest so the app can show near-misses.
        "stocks": matches + [r for r in rows if r not in matches],
    }
    Path(args.out).write_text(json.dumps(payload, indent=2))

    print(f"\n=== First {min(10, len(matches))} matches (of {len(matches)}) ===")
    print(f"{'#':>2}  {'CODE':5} {'P/E':>5} {'YIELD':>6} {'PAYOUT':>7}  {'SECTOR':<22} NAME")
    for i, r in enumerate(matches[:10], 1):
        y = f"{r['dividendYield']:.1f}%" if r["dividendYield"] is not None else "-"
        po = f"{r['payoutRatio']:.0f}%" if r["payoutRatio"] is not None else "-"
        print(f"{i:2}. {r['ticker']:5} {r['pe']:>5} {y:>6} {po:>7}  "
              f"{r['sector']:<22} {r['name']}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
