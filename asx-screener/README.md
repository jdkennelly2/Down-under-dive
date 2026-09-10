# Deep Value ASX — stock screener

A small mobile-first app that screens **Australian (ASX) shares** for:

1. **Price-to-earnings ratio under 10**
2. **Cash-flow positive** (free cash flow > 0, else operating cash flow > 0)
3. **Not pharmaceutical / biotech**
4. **Not mining, commodities or energy** — producers and explorers alike
5. **Not a REIT** — property trusts, whose earnings are distorted by
   revaluations. Real-estate *services* businesses (valuers, agents) are kept:
   they are operating companies, not trusts
6. **Not a fund manager** — asset managers specifically, not financials
   broadly, so banks, insurers, lenders and leasing businesses still qualify

**Dividend yield** and **payout ratio** are shown for everything that passes, as
extra context rather than screening criteria. A payout ratio above 100% is
flagged: the dividend exceeds earnings and may not be sustainable.

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

## What passes today (as of 2026-09-10)

Compiled from public sources (GuruFocus, StockAnalysis, Simply Wall St,
Stockopedia, Kalkine, company results). Indicative, ranked by P/E:

| # | Code | Company | Sector | ~P/E | Yield | Payout |
|---|------|---------|--------|-----:|------:|-------:|
| 1 | HLI | Helia Group | Financials (mortgage insurance) | 6.6 | 6.1% | — |
| 2 | GNC | GrainCorp | Consumer Staples | 8.0 | 7.2% | 154% ⚠ |
| 3 | ASG | Autosports Group | Consumer Discretionary | 8.4 | 2.7% | 44% |
| 4 | MTO | MotorCycle Holdings | Consumer Discretionary | 8.5 | 5.4% | 54% |
| 5 | QAN | Qantas Airways | Industrials | 9.9 | 5.4% | — |

**Five, not ten** — and that is the honest output, not a gap to be padded. Each
exclusion is individually reasonable, but stacked they remove most of what
trades under 10× on the ASX: resources take the cyclicals, the REIT rule takes
the property trusts, and the fund-manager rule takes the asset managers. The app
shows however many pass and says so.

Nudging the P/E ceiling shows what is just out of reach:

| Ceiling | Adds |
|---------|------|
| 11 | HVN (10.4), PWR (10.5) |
| 12 | MMS (11.4), SWM (11.6) |
| 15 | **ACU Acumentis (14.4)** |

**On Acumentis:** it clears every sector rule — a property *valuation and
advisory* business, not a trust, so the REIT filter correctly leaves it in — and
it is cash-flow positive with a comfortable 34% payout. It fails on one thing
only: a P/E of ~14.4. If it belongs in the screen, the P/E ceiling is the
setting to revisit, not the sector rules.

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
