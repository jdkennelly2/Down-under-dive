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
| `index.html` | **The installable app.** Full PWA — add to your iPhone home screen (see below). Generated from `app.html` by `build.py`. |
| `app.html` | The shared UI / Claude Artifact copy. Edit this one, then run `build.py`. |
| `manifest.webmanifest`, `sw.js`, `*.png` | PWA plumbing: app metadata, offline cache, and home-screen icons. |
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

## Install it on your iPhone (home-screen app)

`index.html` is a full PWA: installed, it launches full-screen with its own
icon and no Safari chrome, and works offline.

**1. Publish the folder once (GitHub Pages)**

In the repo on GitHub: **Settings ▸ Pages**, set *Source* to **Deploy from a
branch**, choose the branch holding this folder and folder **`/ (root)`**, then
**Save**. After a minute the app is live at:

```
https://jdkennelly2.github.io/Down-under-dive/asx-screener/
```

**2. Add it to the home screen**

Open that URL in **Safari** on the iPhone (it must be Safari — Chrome can't
install web apps on iOS), then **Share ▸ Add to Home Screen ▸ Add**. You'll get
a "P/E <10" icon named **Deep Value** that opens full-screen like any app.

To update the app later, push a change and pull-to-refresh once inside it (the
service worker caches the shell, so bump `CACHE` in `sw.js` for a hard refresh).

## Editing the UI

`app.html` is the single source of the interface (it doubles as the Claude
Artifact copy). After editing it, regenerate the installable page:

```bash
python build.py        # app.html -> index.html (adds the iOS/PWA head)
python make_icon.py    # only if you want to redraw the icons
```

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
