# Deep Value ASX — stock screener

A small mobile-first app that screens **Australian (ASX) shares** for:

1. **Cheap on owner's earnings** — `EV/EBIT` below 8, **or** an owner's-earnings
   yield of 10%+ . Either route in; failing both is not value on this method
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

P/E is no longer a gate — it is a crude proxy for what this actually measures,
and it is wrong in exactly the places that matter (leases, impairments,
intangibles). It remains available as an optional extra filter via `--pe-max`.

## Owner's earnings

The screener computes owner's earnings two ways, because the two disagree and
**the disagreement is the signal**:

```
NPAT route:  NPAT + D&A + impairments - increase in working capital - capex
CFO route:   cash from operations - capex
```

A capital-light business lands in much the same place on both. A lease-heavy or
working-capital-hungry one does not, and the gap is where the accounts need
reading. Two flags mark that:

| Flag | Meaning |
|------|---------|
| `DIVERGE` | The routes disagree by more than 40% — working capital or capex is doing the work |
| `LEASE` | Lease liabilities exceed 15% of enterprise value |

**A deliberate limitation, stated plainly.** Neither route subtracts cash lease
payments, because the split between the P&L charge and actual cash out is not
recoverable from filing-level data. For a lease-heavy business **both figures
overstate**, and by the same amount — so `DIVERGE` will *not* catch it. That is
what `LEASE` is for, and the lease line has to be entered by hand.

Maintenance-versus-growth capex is the same kind of problem: total capex is
used, which makes the result a **floor** rather than a target. A business with
genuine growth capex earns more than the screen shows.

Neither gap is a bug to be fixed later. The screener's job is to narrow a few
hundred names to a handful; the judgement happens after, by hand.

## The quality test

Cheapness is the entry ticket, not the thesis. The test that actually matters:

```
owner's earnings (cash flow after maintenance capex)
------------------------------------------------------
net tangible assets, adjusted for cash and debt
```

The denominator — **tangible capital employed** = NTA − cash + debt — is the
capital the operating business genuinely uses. Reported as
`oeReturnOnCapital`, and available as a gate via `--min-return-on-capital`.
It is **off by default**: the inputs are patchy on small caps and an
always-on gate would silently empty the screen rather than telling you why.
The run prints how many names clear 15% so the effect is visible before you
switch it on.

On growth: moderate growth is preferred over high, partly because it attracts
less attention. High growth is not disqualifying when the price is still
reasonable. `revenueCagr` is reported rather than gated — the judgement is
about price *relative* to growth, which is not a threshold.

## Warnings

Each flag marks a specific way a headline figure misleads. They come from
post-mortems on real mistakes, not from theory:

| Flag | What it catches |
|------|-----------------|
| `LEASE` | Lease liabilities material. Neither owner's-earnings figure subtracts cash lease payments, so both overstate — enter the lease line by hand |
| `PAYABLES` | Over 25% of operating cash flow came from working capital rather than trading. Stretching creditors is not earnings |
| `GM-FALL` | Gross margin fell more than 1.5pts. A thesis survives a weak year; it rarely survives the gross line eroding |
| `DIVERGE` | The two owner's-earnings routes disagree by more than 40% |

`LEASE` and `PAYABLES` exist because those two are the recurring reasons a
cheap-looking business gets rejected. `GM-FALL` exists because a position can
make money and still have been a mistake: if the gross line deteriorates, the
thesis was wrong even when the outcome was positive.

## Quality metrics

Also computed, as context rather than gates:

- **NTA** — equity stripped of goodwill and intangibles
- **Tangible capital employed** — NTA less cash plus debt
- **ROTE** and **ROTE ex-cash** — return on tangible equity
- **Gross margin** and its year-on-year change
- **Revenue CAGR** across the available statement years
- **Working-capital share of operating cash flow**
- **Lease liabilities** and enterprise value, so leverage is visible

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

## How this app works

Written down while it was fresh, mostly as notes for the next project.

### The shape: data, view, build

Three concerns kept deliberately separate:

```
  screener.py  ──►  data.json  ──►  app.html  ──►  build.py  ──►  docs/
  (the engine)      (the facts)     (the view)     (the wrap)     (what ships)
```

- **`screener.py`** is a data pipeline, not part of the app. It runs on your
  machine, talks to Yahoo Finance, and writes facts to a file.
- **`data.json`** is the contract between the two halves. The app never
  computes a P/E; it renders whatever the file says.
- **`app.html`** is the whole interface — markup, styles and logic in one file.
- **`build.py`** wraps it into `index.html` and copies the runtime assets into
  `docs/`, so there is exactly one source of truth for the UI.

The payoff: the screening rules changed five times in the session that built
this — resources excluded, dividends added, REITs and fund managers excluded —
and the interface was barely touched. **Separating the facts from the view is
what makes a small app cheap to change.** Any project with data behind it wants
this split.

### What makes it an app and not a web page

It is a **PWA** (progressive web app) — a website that declares itself
app-like. Three files do that work:

| File | Its job |
|------|---------|
| `manifest.webmanifest` | The app's identity card: name, icons, and `display: standalone`, the line that tells the OS to open it full-screen with no address bar |
| `sw.js` | The *service worker* — a script the browser keeps running in the background, caching the app's files so it opens with no signal |
| `apple-touch-icon.png` + the `apple-*` meta tags | The home-screen tile, and iOS's older pre-manifest way of being told the same thing |

Installed through the browser (Share ▸ Add to Home Screen), not an app store.

### PWA vs native, honestly

| | Native app | PWA (this) |
|---|---|---|
| What it is | Compiled binary in the platform's language — Swift, Kotlin | HTML, CSS and JavaScript served over HTTPS |
| Distribution | App Store, with review | A URL. Shareable by text message |
| Cost | ~$150/yr developer account | Nothing |
| Updates | Submit and wait for approval | Push a commit; live in a minute |
| Codebases | One per platform | One, everywhere |

What a PWA gives up, which matters more for some projects than others:

- **Notifications on iOS are weak** — only once installed, and unreliable.
  Anything whose job is to *remind* someone will feel this first.
- **No access to some hardware** — Bluetooth, NFC, HealthKit, background
  location.
- **Stored data can be evicted** by iOS if the app goes unused for weeks, so
  anything that must persist belongs on a server, not in browser storage.
- **No store presence.** Irrelevant for a personal tool, decisive for a product.

To go native later without starting over, **Capacitor** can wrap an existing
PWA into real store binaries; **React Native** or **Flutter** are the
write-once-compile-native alternatives.

### What a screener cannot do

Worth recording, because it is the real limit of this tool and not a missing
feature. The screen finds *candidates* by testing numbers that already exist.
It cannot hold a thesis.

The case in point: Acumentis was bought around 7c on the view that revenue
would revert toward pre-cyber-incident levels once client trust rebuilt. That
is a qualitative judgement about a change in business economics and a reversion
to mean — there is no field in any dataset that expresses it. A filter would
have to see the future to agree.

Two design consequences, both already in the app:

1. **The P/E ceiling is a slider, not a constant.** A hard cutoff at 10 hides
   something interesting at 11. The dial invites a second look instead of
   pretending the threshold is a verdict.
2. **A short list is a valid answer.** If one or two names a year clear a high
   bar, a screen returning five is working correctly. The app reports however
   many pass and never pads the count.

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
python screener.py                      # EV/EBIT < 8 or OE yield >= 10%
python screener.py --ev-ebit-max 6      # tighten the multiple
python screener.py --oe-yield-min 12    # demand a higher owner's-earnings yield
python screener.py --pe-max 12          # add a P/E gate on top
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
