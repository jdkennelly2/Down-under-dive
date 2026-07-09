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
- Source: **BITRE** monthly "Airport traffic data" (top-twenty airports), CAIRNS rows only
- Download page: https://www.bitre.gov.au/publications/ongoing/airport_traffic_data
- File naming (changed 2026): `aviation-airport_traffic_data-<month>_<year>.xlsx` (older: `WebMonthlyAirport<Month><Year>.xlsx`)
- Loader: `Spreadsheets/import_airport.py` — auto-finds newest file in `Airport data/`, loads `airport_pax` table + refreshes `airport_pax.csv`
- **Coverage as of July 2026: loaded through Feb 2026** (BITRE runs ~4 months in arrears; refresh monthly)
- Note: BITRE back-revises recent months (e.g. Dec 2025 revised 201,302 → 193,358)

## Billy Tea Dashboard (BillyTea/ module)
Separate product line (Billy Tea Safaris) — day tours to **Daintree Cape Tribulation**
and **Chillagoe Caves**. Goal: monthly pax dashboard in Power BI, compared against
external demand drivers (airport, rainfall, weather, economic). **Not** compared to
reef/EMC/Down Under Dive pax — that's a separate model.

### Data flow
```
  Month-end "Summary Report.xlsx" (STATS tab, wide matrix, OneDrive)
        │  rebuild_pax.py  (auto-finds newest, unpivots to tidy long)
        ▼
  Pax Numbers.xlsx  ──────────────┐
                                  ├─► Power BI (star schema, dim_date shared)
  drivers_monthly.csv ────────────┤   build_drivers_monthly.py (from Paxday.db)
  dim_year.csv / dim_product.csv ─┘   make_colour_dims.py (colour lock)
```

### Scripts (BillyTea/)
- `rebuild_pax.py` — rebuild the tidy Pax master from the newest month-end Summary Report. **Run monthly.**
- `build_drivers_monthly.py` — flatten airport/rainfall/weather/oil/inflation from Paxday.db to monthly `drivers_monthly.csv`. Run monthly after `import_airport.py`.
- `make_colour_dims.py` — write `dim_year.csv` / `dim_product.csv` (hex colour lock). Run once / rarely.
- `billytea_theme.json` — Power BI theme (import via View ▸ Themes ▸ Browse).

### Power BI source files (live in the OneDrive Billy Tea folder for gateway-free refresh)
`...\Billy Tea Month End\` : `Pax Numbers.xlsx`, `drivers_monthly.csv`, `dim_year.csv`, `dim_product.csv`

### Model plan
- Fact `PAX_DATA` (month × product) + fact `drivers_monthly` (month), joined **only via `dim_date`**.
- Key measures: `Total Pax`, `Airport Inbound`, `Pax per 1k arrivals` (capture rate), `Pax YoY %`.
- Colour lock: "Format by field value" → `dim_year[Hex]` / `dim_product[Hex]` (theme palette maps by order, not value).

### Data gaps to close (July 2026)
- Airport: loaded to Feb 2026 (latest BITRE). Rainfall/weather/oil/core-CPI current.
- CPI `inflation_qtr` stops Q1 2025 — needs 2025–26 ABS quarters (core inflation already current).

### Known path issues (legacy scripts)
- `SQL/reef_airport_correlation.py` and `Spreadsheets/Airport import.py` (old) hard-code
  `C:\Users\penny\Desktop\DA\Projects\...` or `...\Desktop\SQL\...` — **stale**. Canonical DB is
  `Down-under-dive\SQL\Paxday.db`. Power BI `.pbix` files live under `Desktop\DA\Projects\DOWN UNDER DIVE\POWER BI\`.

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
