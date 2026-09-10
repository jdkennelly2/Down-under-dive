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
| `build.py` | Builds the deployable site into `../docs/` (what GitHub Pages serves). |

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

It rewrites `data.json` and prints the first ten to the terminal. Run `build.py`
afterwards to publish the refreshed figures to the installed app.

## Install it on your iPhone (home-screen app)

The built app lives in **`../docs/`** — a self-contained bundle holding only the
screener, so the published site exposes nothing else from this repo.

**1. Turn on GitHub Pages (once)**

On GitHub: **Settings ▸ Pages ▸ Source = "Deploy from a branch"**, then pick the
branch that has this work and folder **`/docs`**, and **Save**. A minute later
the app is live at:

```
https://jdkennelly2.github.io/Down-under-dive/
```

Only `docs/` is served. The pax spreadsheets, PDFs, `SQL/`, `BillyTea/` and
`Airport data/` are not part of the site.

**2. Add it to the home screen**

Open that URL in **Safari** on the iPhone — it must be Safari, as Chrome cannot
install web apps on iOS — then **Share ▸ Add to Home Screen**.

> **On iOS 26+, check the "Open as Web App" toggle before tapping Add.**
> It must be **ON**. Switched off, iOS creates a plain bookmark that opens in
> Safari no matter what the page declares — correct icon, correct metadata, but
> not an app. iOS remembers the choice per site, so if a shortcut is stuck
> opening in Safari: delete the icon, clear the site under *Settings ▸ Safari ▸
> Advanced ▸ Website Data*, then re-add with the toggle on.

You get a "P/E <10" icon named **Deep Value** that launches full-screen, with no
browser chrome, and keeps working offline.

The strip at the top of the app reports which mode it is running in, and the
footer shows the build — useful for confirming a phone picked up a new deploy.

## Editing the UI or refreshing the data

`app.html` is the single source of the interface (it doubles as the Claude
Artifact copy). `docs/` is generated — never edit it by hand:

```bash
python screener.py     # optional: pull live figures -> data.json
python build.py        # app.html + assets -> ../docs/
python make_icon.py    # only if you want to redraw the icons
```

Commit and push, and the live app updates. Inside an already-installed app the
service worker serves the cached shell, so bump `CACHE` in `sw.js` when you
change the interface to force a refresh.

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
