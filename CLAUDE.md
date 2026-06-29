# Down Under Dive — Claude Context

## Project Overview
Passenger and booking analytics for a dive tourism operation. Key outputs are forecasting models and Power BI reports used to understand and predict visitor/passenger volumes.

## Models

### Reef Pax Model
- Purpose: Tracks and forecasts reef passenger volumes
- Location: Local desktop (path TBC)
- Data coverage: Update this when confirmed

### Paxday Model
- Purpose: Daily passenger breakdown model
- Location: Local desktop (path TBC)
- Data coverage: Update this when confirmed

### Power BI Reports
- Published to Power BI Service
- Connected to the above models as data sources
- Local .pbix files also on desktop

## Airport Passenger Data
- Source: BITRE monthly airport traffic data (WebMonthlyAirport xlsx files)
- Current coverage in repo: **January 2009 – December 2025** (BITRE source only)
- File: `Spreadsheets/airport_pax.csv` — monthly Cairns airport pax (dom/intl inbound/outbound); BITRE data only, do not mix with Cairns Airport / economy.id source
- Raw source extract: `Airport data/claude extract/cairns_airport_passengers.csv` (goes to Apr 2026, Cairns Airport source — use for reference/early indicator only, not for loading into models)
- SQLite DB table `airport_pax` in `SQL/Paxday.db` — needs local update via `Spreadsheets/Airport import.py` when new BITRE xlsx is downloaded
- `SQL/reef_airport_merged.csv` — quarterly reef+airport combined; airport columns current to Q4 2025; needs reef pax data for 2026 Q1+ before updating

## Common Tasks
- Check whether a model has data for a given year/period
- Add or update airport passenger data in models
- Refresh Power BI reports with new data
- Analyse trends and insights from passenger volumes

## File Locations
- Local desktop files: [add paths here]
- Power BI Service workspace: [add workspace name/URL here]
- Airport pax source data: [add path or source here]

## Notes
- Always check data coverage dates before running forecasts
- When working from mobile/web sessions, local desktop files are not accessible — commit key data files to this repo to make them available cross-device
