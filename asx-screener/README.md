# Deep Value ASX — stock screener

A small mobile-first app that screens **Australian (ASX) shares** for:

1. **Price-to-earnings ratio under 10**
2. **Cash-flow positive** (free cash flow > 0, else operating cash flow > 0)
3. **Not pharmaceutical / biotech**
4. **Not a pre-revenue mining explorer** (producing miners are allowed)

It ships with a **live screening engine** (`screener.py`) and a **mobile web
app** (`app.html`) that presents the results and lets you adjust the filters.

> ⚠️ **General information only — not financial advice.** P/E ratios and cash-flow
> figures change daily and vary by data source and methodology (trailing vs
> forward). Always verify against a live source and consider your own
> circumstances before making any decision.

## Files

| File | What it is |
|------|------------|
| `app.html` | The mobile app. Open it in any browser (works offline). Adjust the P/E slider and toggles to re-screen. |
| `data.json` | The dataset the app reads. Schema below. |
| `screener.py` | Live engine — pulls fundamentals from Yahoo Finance and rewrites `data.json`. |

## The first ten (as of 2026-09-09)

Compiled from public sources (GuruFocus, StockAnalysis, Simply Wall St,
Stockopedia, company results). Indicative, ranked by P/E:

| # | Code | Company | Sector | ~P/E |
|---|------|---------|--------|-----:|
| 1 | ALD | Ampol | Energy (fuel refining) | 6.8 |
| 2 | GQG | GQG Partners | Financials (asset mgmt) | 7.2 |
| 3 | DXS | Dexus | Real Estate (REIT) | 7.3 |
| 4 | GNC | GrainCorp | Consumer Staples | 8.0 |
| 5 | YAL | Yancoal Australia | Energy (coal producer) | 8.0 |
| 6 | GPT | GPT Group | Real Estate (REIT) | 8.3 |
| 7 | RGN | Region Group | Real Estate (REIT) | 8.8 |
| 8 | WHC | Whitehaven Coal | Energy (coal producer) | 9.5 |
| 9 | RRL | Regis Resources | Materials (gold producer) | 9.9 |
| 10 | QAN | Qantas Airways | Industrials (airline) | 9.9 |

Note: coal/gold/iron-ore *producers* pass the "no mining exploration" rule —
only pre-revenue explorers are excluded. Qantas has strong operating cash flow,
but its free cash flow swings with aircraft capex — check the latest report.

## Run the live screener

Run this on a machine/phone where `finance.yahoo.com` is reachable (some managed
or CI networks block it):

```bash
pip install yfinance
python screener.py                 # default ASX universe, P/E < 10
python screener.py --pe-max 12     # widen the multiple
python screener.py --universe my_codes.txt   # one ASX code per line, e.g. "BHP"
```

It rewrites `data.json` and prints the first ten to the terminal. Reopen
`app.html` (served over http, e.g. `python -m http.server`) to see the refresh.

## Use it as a mobile app

- **Quick:** open `app.html` on your phone's browser and tap **Share ▸ Add to
  Home Screen**. It runs offline using the bundled dataset.
- **Live:** serve the folder (`python -m http.server 8000`) and browse to it so
  the app loads the freshly generated `data.json`.

## `data.json` schema

```jsonc
{
  "meta": { "asOf": "YYYY-MM-DD", "criteria": { ... }, "source": "...", "disclaimer": "..." },
  "stocks": [
    {
      "ticker": "ALD",
      "name": "Ampol",
      "sector": "Energy",
      "industry": "Fuel refining & marketing",
      "pe": 6.8,                    // null if loss-making
      "cashFlowPositive": true,
      "isPharma": false,
      "isMiningExploration": false,
      "note": "..."
    }
  ]
}
```

The app shows the top ten passers ranked by P/E, and lists near-misses and
rule-excluded names under "Why others didn't make the cut".
