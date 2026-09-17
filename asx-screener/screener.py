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

Valuation is driven by EV/EBIT and owner's earnings rather than P/E.
Owner's earnings are computed two ways, because the two disagree and the
disagreement is itself the signal:

  NPAT method:  NPAT + D&A + impairments - increase in working capital - capex
  CFO method:   cash from operations - lease payments - capex

A lease-heavy business can look strongly cash generative on the first and
barely break even on the second. Where they diverge, the accounts need
reading by hand — the screener flags it rather than picking a winner.

Two inputs genuinely cannot be automated and are left to manual work:
splitting maintenance from growth capex, and isolating cash lease payments
above what runs through the P&L. The screener narrows a few hundred names
to a handful; the judgement happens after.

Dividend yield and payout ratio are collected and reported for whatever
passes, as extra context — they are not screening criteria.

Pulls live fundamentals from Yahoo Finance via `yfinance` and writes
`data.json` (consumed by app.html) plus prints the first ten matches.

Usage (Windows PowerShell or Command Prompt):
    py -m pip install yfinance
    py screener.py                      # EV/EBIT < 8 or OE yield >= 10%
    py screener.py --ev-ebit-max 6      # tighten the multiple
    py screener.py --min-return-on-capital 15   # gate on return on capital
    py screener.py --universe my_tickers.txt    # one ASX code per line

On macOS or Linux substitute `python3` for `py`. The `py` launcher ships with
the python.org Windows installer; if it is missing, use `python` instead.

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
    # Common trap: a second Python is installed later, and `py` now launches
    # that one while yfinance sits in the older interpreter's site-packages.
    # `py -m pip` installs into whichever Python `py` currently resolves to.
    sys.exit("yfinance is not installed for this Python "
             f"({sys.version.split()[0]}).\n"
             "Install it for THIS interpreter:  py -m pip install -U yfinance\n"
             "(If you recently installed a newer Python, packages added before "
             "that belong to the old one and must be reinstalled.)")

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
    # Small and micro caps. Deep value on the ASX mostly lives down here,
    # not in the ASX 200 — a large-cap-only universe screens out the very
    # part of the market this strategy hunts in.
    "3PL", "ABB", "ACF", "ACU", "AMA", "ASG", "AX1", "BFG", "BRI", "CAT",
    "CDA", "CIA", "CLG", "CSS", "CVL", "CWP", "DDR", "DRO", "DUR", "DVR",
    "EGL", "EMC", "ENN", "EOL", "EQT", "EVS", "EZL", "FGR", "FWD", "GDG",
    "GNG", "GTK", "HIT", "HLO", "HSN", "IMD", "IPD", "JAN", "JLG", "JYC",
    "KME", "KSL", "LAU", "LBL", "LGP", "MAD", "MAH", "MDR", "MGH", "MP1",
    "MXI", "NWH", "OCL", "PFP", "PGC", "PPE", "PPS", "PSI", "PTB", "PWH",
    "RDX", "RFG", "RUL", "SDR", "SGI", "SHM", "SIQ", "SLC", "SNL", "SRG",
    "SSG", "SSM", "SVR", "TEA", "TNE", "TOP", "TRS", "TWD", "VEE", "VNT",
    "WGN", "WLL", "XRF", "ZNO",
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

# Statement line items are labelled inconsistently across filings, so every
# lookup tries a list of aliases and gives up cleanly rather than guessing.
LINES = {
    "npat": ("Net Income", "Net Income Common Stockholders",
             "Net Income From Continuing Operation Net Minority Interest"),
    "dand_a": ("Depreciation And Amortization", "Depreciation Amortization Depletion",
               "Depreciation And Amortization In Income Statement", "Depreciation"),
    "impairment": ("Impairment Of Capital Assets", "Asset Impairment Charge",
                   "Impairment Of Intangibles", "Goodwill Impairment"),
    "cfo": ("Operating Cash Flow", "Total Cash From Operating Activities",
            "Cash Flow From Continuing Operating Activities"),
    "capex": ("Capital Expenditure", "Purchase Of PPE", "Net PPE Purchase And Sale"),
    "wc_change": ("Change In Working Capital", "Changes In Working Capital"),
    "ebit": ("EBIT", "Operating Income", "Total Operating Income As Reported"),
    "ebitda": ("EBITDA", "Normalized EBITDA"),
    "equity": ("Stockholders Equity", "Total Equity Gross Minority Interest",
               "Common Stock Equity"),
    "goodwill": ("Goodwill",),
    "intangibles": ("Other Intangible Assets", "Goodwill And Other Intangible Assets"),
    "cash": ("Cash And Cash Equivalents",
             "Cash Cash Equivalents And Short Term Investments"),
    "lease_lt": ("Long Term Capital Lease Obligation",),
    "lease_st": ("Current Capital Lease Obligation",),
    "revenue": ("Total Revenue", "Operating Revenue"),
    "gross_profit": ("Gross Profit",),
    "debt": ("Total Debt", "Total Debt Net"),
    "payables": ("Payables", "Accounts Payable", "Payables And Accrued Expenses"),
    "wc_payables": ("Change In Payable", "Change In Account Payable",
                    "Changes In Account Receivables"),
}


def line(df, key):
    """Most recent value for a statement line, or None when not reported."""
    if df is None or getattr(df, "empty", True):
        return None
    for alias in LINES[key]:
        for label in df.index:
            if str(label).strip().lower() == alias.lower():
                try:
                    v = df.loc[label].dropna()
                    if len(v):
                        return float(v.iloc[0])
                except Exception:
                    pass
    return None


def series(df, key, n=4):
    """Up to n most recent values for a line, newest first."""
    if df is None or getattr(df, "empty", True):
        return []
    for alias in LINES[key]:
        for label in df.index:
            if str(label).strip().lower() == alias.lower():
                try:
                    v = df.loc[label].dropna()
                    return [float(x) for x in v.iloc[:n]]
                except Exception:
                    pass
    return []


def gross_margin_trend(inc):
    """Gross margin now and a year earlier. A thesis can survive a weak year
    and not survive the gross line eroding — that is a different failure, and
    it does not show up in the headline multiple."""
    gp, rev = series(inc, "gross_profit", 2), series(inc, "revenue", 2)
    if len(gp) < 1 or len(rev) < 1 or not rev[0]:
        return None, None
    now = round(100 * gp[0] / rev[0], 1)
    prior = round(100 * gp[1] / rev[1], 1) if len(gp) > 1 and len(rev) > 1 and rev[1] else None
    return now, (round(now - prior, 1) if prior is not None else None)


def revenue_cagr(inc):
    """Compound revenue growth across the available statement years."""
    rev = series(inc, "revenue", 4)
    if len(rev) < 2 or rev[-1] <= 0:
        return None
    years = len(rev) - 1
    try:
        return round(100 * ((rev[0] / rev[-1]) ** (1 / years) - 1), 1)
    except (ValueError, ZeroDivisionError):
        return None


def working_capital_flattery(cf):
    """How much of operating cash flow came from working capital rather than
    trading — stretching payables inflates CFO without earning anything. A
    large positive share is the 'excess payables' tell."""
    cfo, wc = line(cf, "cfo"), line(cf, "wc_change")
    if cfo is None or wc is None or cfo <= 0:
        return None
    return round(100 * wc / cfo, 1)


def owner_earnings(inc, cf, bs):
    """Both routes to owner's earnings, plus the lease context needed to
    judge them. Maintenance-vs-growth capex is not separable from the
    filings, so total capex is used and the result is a floor, not a
    target: a business with real growth capex earns more than this shows."""
    npat = line(inc, "npat")
    da = line(cf, "dand_a") or line(inc, "dand_a")
    imp = line(cf, "impairment") or 0.0
    wc = line(cf, "wc_change")          # negative when working capital grows
    capex = line(cf, "capex")           # reported negative
    cfo = line(cf, "cfo")

    capex_out = abs(capex) if capex is not None else None
    lease = sum(x for x in (line(bs, "lease_lt"), line(bs, "lease_st")) if x)

    oe_npat = None
    if None not in (npat, da) and capex_out is not None:
        oe_npat = npat + da + imp + (wc or 0.0) - capex_out

    # Neither route subtracts cash lease payments: the split between the P&L
    # charge and actual cash out is not recoverable from filing-level data.
    # For a lease-heavy business BOTH figures therefore overstate, and by the
    # same amount — so oeDivergence will NOT catch it. leaseHeavy is the flag
    # that matters there, and the lease line has to be entered by hand.
    oe_cfo = None
    if cfo is not None and capex_out is not None:
        oe_cfo = cfo - capex_out

    return oe_npat, oe_cfo, (lease or None)


def tangible_equity(bs):
    """Net tangible assets: equity stripped of goodwill and intangibles."""
    eq = line(bs, "equity")
    if eq is None:
        return None, None
    intang = (line(bs, "goodwill") or 0.0) + (line(bs, "intangibles") or 0.0)
    return eq - intang, line(bs, "cash")


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


def ratio(num, den):
    """Guard every division: a zero or missing denominator yields None."""
    if num is None or not den:
        return None
    try:
        return round(num / den, 4)
    except (TypeError, ZeroDivisionError):
        return None


def fetch(code):
    tkr = yf.Ticker(f"{code}.AX")
    info = tkr.info or {}
    if not info.get("shortName") and not info.get("longName"):
        return None
    pe = info.get("trailingPE")

    try:
        inc, cf, bs = tkr.income_stmt, tkr.cashflow, tkr.balance_sheet
    except Exception:
        inc = cf = bs = None

    ev = info.get("enterpriseValue")
    mcap = info.get("marketCap")
    ebit = line(inc, "ebit")
    if ebit is None and line(inc, "ebitda") is not None:
        da = line(cf, "dand_a")
        ebit = line(inc, "ebitda") - da if da is not None else None

    oe_npat, oe_cfo, lease = owner_earnings(inc, cf, bs)
    nta, cash = tangible_equity(bs)
    npat = line(inc, "npat")
    debt = line(bs, "debt") or info.get("totalDebt")

    # Tangible capital employed: net tangible assets with cash taken out and
    # debt added back, i.e. the capital the operating business actually uses.
    # This is the denominator for "return on NTA adjusted for cash and debt".
    tce = None
    if nta is not None:
        tce = nta - (cash or 0.0) + (debt or 0.0)

    gm, gm_delta = gross_margin_trend(inc)

    # A wide gap between the two owner's-earnings routes means leases or
    # working capital are doing heavy lifting — read the accounts by hand.
    divergence = None
    if oe_npat and oe_cfo and max(abs(oe_npat), abs(oe_cfo)) > 0:
        divergence = round(abs(oe_npat - oe_cfo) / max(abs(oe_npat), abs(oe_cfo)), 3)

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
        # --- valuation on the owner's-earnings basis ---
        "evEbit": ratio(ev, ebit) if (ev and ebit and ebit > 0) else None,
        "ownerEarningsNpat": oe_npat,
        "ownerEarningsCfo": oe_cfo,
        "oeYieldNpat": pct(ratio(oe_npat, mcap)),
        "oeYieldCfo": pct(ratio(oe_cfo, mcap)),
        "oeDivergence": divergence,
        "leaseLiabilities": lease,
        "leaseHeavy": bool(lease and ev and lease / ev > 0.15),
        "nta": nta,
        "tangibleCapitalEmployed": tce,
        "rote": pct(ratio(npat, nta)) if (nta and nta > 0) else None,
        "roteExCash": pct(ratio(npat, nta - cash)) if (nta and cash and nta - cash > 0) else None,
        # The core quality test: cash earnings after capex against the
        # tangible capital that produced them.
        "oeReturnOnCapital": pct(ratio(oe_cfo, tce)) if (tce and tce > 0) else None,
        "grossMargin": gm,
        "grossMarginDelta": gm_delta,
        "revenueCagr": revenue_cagr(inc),
        "wcFlattery": working_capital_flattery(cf),
        "marketCap": mcap,
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


def preflight():
    """Report the environment and whether it can actually do the job.

    An old yfinance may not expose company statements at all. fetch() catches
    that and carries on with None, which would quietly produce a screen with
    no owner's earnings, no EV/EBIT and no return on capital — and no clue
    why. Better to say so up front."""
    import platform
    ver = getattr(yf, "__version__", "unknown")
    print(f"Python {platform.python_version()} · yfinance {ver}", file=sys.stderr)

    ok = True
    if sys.version_info < (3, 9):
        ok = False
        print("  ! Python 3.8 reached end of life in October 2024. pip can only\n"
              "    install an old yfinance for it, which may not provide company\n"
              "    statements. Install Python 3.12 from python.org (tick 'Add\n"
              "    Python to PATH'), then re-run: py -m pip install -U yfinance",
              file=sys.stderr)

    missing = [a for a in ("income_stmt", "cashflow", "balance_sheet")
               if not hasattr(yf.Ticker, a)]
    if missing:
        ok = False
        print(f"  ! This yfinance does not expose: {', '.join(missing)}.\n"
              "    Owner's earnings, EV/EBIT and return on capital cannot be\n"
              "    computed — the screen would fall back to P/E only.",
              file=sys.stderr)
    return ok


def main():
    ap = argparse.ArgumentParser(description="Screen ASX shares for deep value.")
    # Defaults anchored on the NPV workbook's own buy cases, which sat at
    # EV/EBIT 5-6 against a 10% cost of capital — so a 10% owner's-earnings
    # yield is that same hurdle expressed as a yield.
    ap.add_argument("--ev-ebit-max", type=float, default=8.0,
                    help="Maximum EV/EBIT (default 8)")
    ap.add_argument("--oe-yield-min", type=float, default=10.0,
                    help="Minimum owner's-earnings yield %%, CFO basis (default 10)")
    ap.add_argument("--min-return-on-capital", type=float, default=None,
                    help="Minimum owner's-earnings return on tangible capital %%. "
                         "Off by default because the inputs are patchy on small "
                         "caps and it would silently empty the screen; 15 is a "
                         "sensible setting once you trust the data.")
    ap.add_argument("--pe-max", type=float, default=None,
                    help="Optional extra gate on trailing P/E (off by default)")
    ap.add_argument("--include-resources", action="store_true",
                    help="Keep mining, commodity and energy names in the results")
    ap.add_argument("--include-reits", action="store_true",
                    help="Keep property trusts in the results")
    ap.add_argument("--include-fund-managers", action="store_true",
                    help="Keep asset managers in the results")
    ap.add_argument("--universe", help="File with one ASX code per line")
    ap.add_argument("--out", default=str(HERE / "data.json"), help="Output JSON path")
    args = ap.parse_args()

    preflight()
    codes = load_universe(args.universe)
    excl = ", ".join(["ex-pharma"]
                     + ([] if args.include_resources else ["ex-mining/energy"])
                     + ([] if args.include_reits else ["ex-REITs"])
                     + ([] if args.include_fund_managers else ["ex-fund-managers"]))
    gates = f"EV/EBIT < {args.ev_ebit_max} or OE yield >= {args.oe_yield_min}%"
    print(f"Screening {len(codes)} ASX codes ({gates}, cash-flow positive, "
          f"{excl})...\n", file=sys.stderr)

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
        if args.pe_max is not None and (s["pe"] is None or s["pe"] >= args.pe_max):
            return False
        # Cheap on EV/EBIT *or* on owner's-earnings yield — either route in.
        # Failing both is not value on this methodology.
        cheap_multiple = s["evEbit"] is not None and s["evEbit"] < args.ev_ebit_max
        cheap_yield = s["oeYieldCfo"] is not None and s["oeYieldCfo"] >= args.oe_yield_min
        if not (cheap_multiple or cheap_yield):
            return False
        if args.min_return_on_capital is not None:
            roc = s["oeReturnOnCapital"]
            if roc is None or roc < args.min_return_on_capital:
                return False
        if not args.include_resources and (s["isResourcesEnergy"] or s["isMiningExploration"]):
            return False
        if not args.include_reits and s["isREIT"]:
            return False
        if not args.include_fund_managers and s["isFundManager"]:
            return False
        return True

    priced = sum(1 for r in rows if r["evEbit"] is not None)
    withoe = sum(1 for r in rows if r["oeYieldCfo"] is not None)
    print(f"\nStatements resolved: EV/EBIT for {priced}/{len(rows)}, "
          f"owner's earnings for {withoe}/{len(rows)}.", file=sys.stderr)
    if rows and priced == 0 and withoe == 0:
        print("  ! None resolved. Every owner's-earnings metric will be empty and\n"
              "    the app will fall back to showing P/E. This is almost always an\n"
              "    out-of-date yfinance — see the warnings above.", file=sys.stderr)

    # Cheapest on EV/EBIT first; names without one sort to the back.
    matches = sorted([r for r in rows if keep(r)],
                     key=lambda r: (r["evEbit"] is None, r["evEbit"] or 0))

    payload = {
        "meta": {
            "asOf": dt.date.today().isoformat(),
            "market": "ASX (Australian Securities Exchange)",
            "criteria": {
                "evEbitMax": args.ev_ebit_max,
                "oeYieldMin": args.oe_yield_min,
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

    def fmt(v, suffix="", dp=1):
        return f"{v:.{dp}f}{suffix}" if isinstance(v, (int, float)) else "-"

    def warnings_for(r):
        """The two ways reported earnings get flattered, plus the thesis-breaker."""
        w = []
        if r["leaseHeavy"]:
            w.append("LEASE")          # cash lease payments not in the figures
        if (r["wcFlattery"] or 0) > 25:
            w.append("PAYABLES")       # CFO propped up by working capital
        if (r["grossMarginDelta"] or 0) < -1.5:
            w.append("GM-FALL")        # gross line eroding
        if (r["oeDivergence"] or 0) > 0.4:
            w.append("DIVERGE")
        return w

    print(f"\n=== {min(15, len(matches))} of {len(matches)} matches ===")
    print(f"{'#':>2}  {'CODE':5} {'EV/EBIT':>8} {'OE%cfo':>7} {'RoTC':>6} "
          f"{'GM':>6} {'dGM':>6} {'REV%':>6}  {'WARNINGS':<22} NAME")
    for i, r in enumerate(matches[:15], 1):
        print(f"{i:2}. {r['ticker']:5} {fmt(r['evEbit']):>8} "
              f"{fmt(r['oeYieldCfo'],'%'):>7} {fmt(r['oeReturnOnCapital'],'%',0):>6} "
              f"{fmt(r['grossMargin'],'%',0):>6} {fmt(r['grossMarginDelta'],'',1):>6} "
              f"{fmt(r['revenueCagr'],'%',0):>6}  "
              f"{','.join(warnings_for(r)) or '-':<22} {r['name']}")

    roc = [r["oeReturnOnCapital"] for r in matches if r["oeReturnOnCapital"] is not None]
    if roc:
        print(f"\nReturn on tangible capital: {sum(1 for x in roc if x >= 15)} of "
              f"{len(roc)} priced names clear 15%. Re-run with "
              f"--min-return-on-capital 15 to screen on it.")

    flagged = [r for r in matches[:15] if warnings_for(r)]
    if flagged:
        print("\nWarnings — each marks a way the headline figure misleads:")
        print("  LEASE     lease liabilities are material. NEITHER owner's-earnings")
        print("            figure subtracts cash lease payments, so both OVERSTATE.")
        print("            Enter the lease line from the accounts yourself.")
        print("  PAYABLES  a large share of operating cash flow came from working")
        print("            capital, not trading. Stretching creditors is not earnings.")
        print("  GM-FALL   gross margin fell more than 1.5pts. A thesis survives a")
        print("            weak year; it rarely survives the gross line eroding.")
        print("  DIVERGE   the two owner's-earnings routes disagree by over 40%.")
        for r in flagged:
            print(f"  {r['ticker']:5} {','.join(warnings_for(r)):<22} "
                  f"OE(npat)={fmt(r['ownerEarningsNpat'],'',0):>13} "
                  f"OE(cfo)={fmt(r['ownerEarningsCfo'],'',0):>13} "
                  f"WC={fmt(r['wcFlattery'],'%',0):>6} dGM={fmt(r['grossMarginDelta'],'',1):>6}")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
