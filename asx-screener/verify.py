# No shebang, for the reason given at the top of screener.py.
"""
Reconcile the screener's data source against lodged financial statements.

The screener reads Yahoo Finance. Yahoo does not publish the accounts — it
re-maps them onto a standardised template, and the mapping is where figures
go wrong: an ASX filer's statements are AASB, the template is broadly US
GAAP, and lines that do not correspond get folded, dropped or renamed. The
screen is only worth what that mapping is worth, so this checks it against
the source document, one company at a time.

    py verify.py --template ACU     # writes verify/ACU.json, pre-filled
    <open it and type the lodged figures beside Yahoo's>
    py verify.py ACU                # prints the variance report

The report has two halves, and the second is the one that matters:

  LINE ITEMS   every input, Yahoo against the annual report, with the gap
  VERDICT      owner's earnings, EV/EBIT and return on capital recomputed
               from BOTH sets — does the screen's answer actually change?

A 3% gap on a line nobody's decision turns on is noise. A 3% gap on capex
that moves the owner's-earnings yield through the hurdle is the whole game.
"""

import argparse
import json
import sys
from pathlib import Path

import screener as sc

HERE = Path(__file__).resolve().parent
VERIFY = HERE / "verify"

# The inputs the method actually consumes, in the order they appear in a set
# of accounts. `where` is the note to look under in the annual report — the
# point is to make the manual entry quick and unambiguous.
FIELDS = [
    ("revenue",       "inc", "Revenue from continuing operations"),
    ("npat",          "inc", "Profit after tax attributable to members"),
    ("ebit",          "inc", "Profit before interest and tax"),
    ("dand_a",        "cf",  "Depreciation and amortisation"),
    ("cfo",           "cf",  "Net cash from operating activities"),
    ("capex",         "cf",  "Payments for property, plant and equipment"),
    ("capex_intangibles", "cf", "Payments for intangibles / capitalised software"),
    ("wc_change",     "cf",  "Movement in working capital (indirect method only)"),
    ("cash",          "bs",  "Cash and cash equivalents"),
    ("debt",          "bs",  "Borrowings, current + non-current"),
    ("lease_total",   "bs",  "Lease liabilities, current + non-current"),
    ("liabilities",   "bs",  "Total liabilities"),
    ("equity",        "bs",  "Total equity"),
    ("intangibles",   "bs",  "Intangible assets"),
    ("goodwill",      "bs",  "Goodwill"),
    ("shares",        "bs",  "Ordinary shares on issue"),
]


def pull(code):
    """Yahoo's figures for one company, by the same lookups the screener uses."""
    import yfinance as yf
    tkr = yf.Ticker(f"{code}.AX")
    info = tkr.info or {}
    inc, cf, bs = tkr.income_stmt, tkr.cashflow, tkr.balance_sheet
    sc._REACHED_BACK.clear()
    frames = {"inc": inc, "cf": cf, "bs": bs}

    out = {}
    for key, where, _ in FIELDS:
        out[key] = sc.line(frames[where], key)
    if out["ebit"] is None and sc.line(inc, "ebitda") is not None:
        da = sc.line(cf, "dand_a")
        out["ebit"] = sc.line(inc, "ebitda") - da if da is not None else None

    period = None
    for df in (inc, cf, bs):
        if df is not None and not getattr(df, "empty", True) and len(df.columns):
            period = str(df.columns[0])[:10]
            break

    return out, {
        "period": period,
        "currency": (info.get("financialCurrency") or "AUD").upper(),
        "marketCap": info.get("marketCap"),
        "enterpriseValue": info.get("enterpriseValue"),
        "sharesOutstanding": info.get("sharesOutstanding"),
        "reachedBack": sorted(sc._REACHED_BACK),
    }


def template(code):
    """Write a reconciliation file pre-filled with Yahoo, blank for lodged."""
    yahoo, meta = pull(code)
    VERIFY.mkdir(exist_ok=True)
    path = VERIFY / f"{code}.json"
    if path.exists():
        sys.exit(f"{path} already exists — delete it first if you mean to start over.")

    doc = {
        "ticker": code,
        "period": meta["period"],
        "currency": meta["currency"],
        "source": "<annual report name, year, and the page or note numbers>",
        "marketCap": meta["marketCap"],
        "enterpriseValue": meta["enterpriseValue"],
        "_howto": "Fill in `lodged` from the annual report. Leave a figure null "
                  "to skip it. Sign convention: capex POSITIVE as a cash "
                  "outflow; wc_change signed as its cash effect (negative when "
                  "working capital grows).",
        "yahoo": {k: yahoo[k] for k, _, _ in FIELDS},
        "lodged": {k: None for k, _, _ in FIELDS},
        "where": {k: w for k, _, w in FIELDS},
    }
    path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"Wrote {path}")
    print(f"  Yahoo's newest period: {meta['period']}  ({meta['currency']})")
    if meta["reachedBack"]:
        print(f"  ! these lines were not on the newest statement and came from an "
              f"earlier one: {', '.join(meta['reachedBack'])}")
    print("\nOpen it, put the lodged figures in `lodged`, then run:")
    print(f"  py verify.py {code}")


def owner_earnings_from(f):
    """The screener's own two routes, run over a flat dict of figures so the
    same arithmetic can be applied to Yahoo and to the accounts."""
    capex = abs(f["capex"]) if f.get("capex") is not None else None
    if capex is not None and f.get("capex_intangibles"):
        capex += abs(f["capex_intangibles"])

    oe_npat = None
    if None not in (f.get("npat"), f.get("dand_a")) and capex is not None:
        oe_npat = f["npat"] + f["dand_a"] + (f.get("wc_change") or 0.0) - capex
    oe_cfo = None
    if f.get("cfo") is not None and capex is not None:
        oe_cfo = f["cfo"] - capex
    return oe_npat, oe_cfo, capex


def tce_from(f):
    """Tangible capital employed, the quality test's denominator."""
    if f.get("equity") is None:
        return None
    nta = f["equity"] - (f.get("goodwill") or 0.0) - (f.get("intangibles") or 0.0)
    return nta - (f.get("cash") or 0.0) + (f.get("debt") or 0.0)


def money(v):
    if v is None:
        return "        —"
    return f"{v/1e6:>9,.1f}"


# Cash outflows are reported negative by the provider and read naturally as
# positive off a cash flow statement. Comparing them signed turns a perfect
# match into a -193% variance and buries the real differences.
UNSIGNED = {"capex", "capex_intangibles"}


def gap(a, b, key=None):
    """Yahoo against lodged, as a percentage of the lodged figure."""
    if a is None or b is None or not b:
        return None
    if key in UNSIGNED:
        a, b = abs(a), abs(b)
    return 100 * (a - b) / abs(b)


def report(code):
    path = VERIFY / f"{code}.json"
    if not path.exists():
        sys.exit(f"No {path}. Create it with:  py verify.py --template {code}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    lodged = {k: v for k, v in doc["lodged"].items() if v is not None}
    if not lodged:
        sys.exit(f"{path} has no lodged figures in it yet — nothing to compare.")

    live, meta = pull(code)
    stored = doc.get("yahoo", {})

    print(f"\n{code} — Yahoo Finance vs lodged accounts")
    print(f"period {doc.get('period')}   currency {doc.get('currency')}")
    print(f"source {doc.get('source')}")
    if meta["period"] != doc.get("period"):
        print(f"\n! Yahoo is now showing {meta['period']}, not {doc.get('period')}.")
        print("  A newer set of accounts has landed. The comparison below uses the")
        print("  figures stored in the file, which match the period you entered.")
    print()

    print(f"{'line':<20}{'Yahoo':>10}{'lodged':>10}{'gap':>9}   note")
    print("-" * 78)
    material = []
    for key, _, where in FIELDS:
        if key not in lodged:
            continue
        y = stored.get(key)
        a = lodged[key]
        g = gap(y, a, key)
        drift = ""
        if key in live and live[key] is not None and y is not None and abs(live[key] - y) > abs(y) * 0.005:
            drift = " (restated since)"
        flag = ""
        if y is None:
            flag = "MISSING from Yahoo"
        elif g is not None and abs(g) >= 2:
            flag = "DIFFERS"
            material.append((key, g))
        if key in UNSIGNED:
            y = None if y is None else abs(y)
            a = abs(a)
        print(f"{key:<20}{money(y)}{money(a)}"
              f"{('' if g is None else f'{g:>+8.1f}%')}   {flag}{drift}")

    # ---- what the screen would actually have said, on each set of figures ---
    y_oe_npat, y_oe_cfo, y_capex = owner_earnings_from(stored)
    a_oe_npat, a_oe_cfo, a_capex = owner_earnings_from(lodged)
    mcap = doc.get("marketCap")
    ev = doc.get("enterpriseValue")

    print("\n" + "=" * 78)
    print("VERDICT — the same arithmetic on each set of figures")
    print("=" * 78)
    rows = [
        ("capex (incl. intangibles)", y_capex, a_capex, money),
        ("owner's earnings, NPAT route", y_oe_npat, a_oe_npat, money),
        ("owner's earnings, CFO route", y_oe_cfo, a_oe_cfo, money),
        ("OE yield on market cap %", sc.as_pct(y_oe_cfo, mcap),
         sc.as_pct(a_oe_cfo, mcap), lambda v: "        —" if v is None else f"{v:>9.1f}"),
        ("EV/EBIT", sc.ratio(ev, stored.get("ebit")), sc.ratio(ev, lodged.get("ebit")),
         lambda v: "        —" if v is None else f"{v:>9.2f}"),
        ("return on tangible capital %",
         sc.as_pct(y_oe_cfo, tce_from(stored)), sc.as_pct(a_oe_cfo, tce_from(lodged)),
         lambda v: "        —" if v is None else f"{v:>9.1f}"),
    ]
    print(f"{'measure':<32}{'Yahoo':>10}{'lodged':>10}{'gap':>9}")
    print("-" * 78)
    for label, y, a, fmt in rows:
        g = gap(y, a)
        print(f"{label:<32}{fmt(y)}{fmt(a)}"
              f"{('' if g is None else f'{g:>+8.1f}%')}")

    print()
    if material:
        worst = max(material, key=lambda t: abs(t[1]))
        print(f"{len(material)} line(s) differ by 2% or more; the largest is "
              f"{worst[0]} at {worst[1]:+.1f}%.")
    else:
        print("Every line entered agrees with Yahoo inside 2%.")
    print("What matters is the VERDICT block: a line can be wrong and change")
    print("nothing, and a line can be nearly right and move the answer through")
    print("the hurdle. Judge the mapping on the measures, not the inputs.")


def main():
    ap = argparse.ArgumentParser(
        description="Reconcile Yahoo Finance figures against lodged accounts.")
    ap.add_argument("code", nargs="?", help="ASX code to report on")
    ap.add_argument("--template", metavar="CODE",
                    help="Write a blank reconciliation file for one code, "
                         "pre-filled with Yahoo's figures")
    args = ap.parse_args()

    if args.template:
        template(args.template.upper().replace(".AX", ""))
    elif args.code:
        report(args.code.upper().replace(".AX", ""))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
