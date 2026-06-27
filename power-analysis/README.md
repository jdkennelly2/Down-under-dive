# 36 Orana — Home Power Analysis

Prepared 27 June 2026. Data through June 2026.

Open `power-analysis.html` in a browser for the full interactive report (charts, tariff
comparison, recommendations). This README is a text summary of the same findings.

## System

| Component | Detail |
|-----------|--------|
| Solar array | ~10 kW panels |
| Inverter | SolaX SK TL 5000E (5 kW) — SN `L50ED6021AU018` |
| Battery | LG RESU10 (10 kWh capacity, 5 kW output) |
| BMU | SolaX SK-BMU5000 — SN `H50ED2055AU055` |
| Commissioned | February 2021 |
| Retailer / tariff | Ergon — Tariff 11 (Residential Flat Rate), Regional QLD |

## Headline numbers

- **Latest bill:** $159.33 (26 Apr – 26 May 2026, 30 days)
- **2026 solar yield YTD:** 3,963 kWh (on track for ~7,900 kWh full year)
- **Self-consumption:** ~87% (only ~13% of generation exported)
- **Avg daily grid import:** 11.74 kWh/day · **avg export:** 2.90 kWh/day

## Latest bill breakdown (Tariff 11)

| Component | Quantity | Rate | Amount (inc GST) |
|-----------|----------|------|------------------|
| Usage | 352.34 kWh | 29.975¢/kWh | $116.17 |
| Daily supply fee | 30 days | $1.535/day | $50.66 |
| Solar export credit | 86.55 kWh | 8.66¢/kWh | −$7.50 |
| **Total due** | | | **$159.33** |

## Solar generation history (kWh/month)

| Month | 2024 | 2025 | 2026 |
|-------|------|------|------|
| Jan | 813.9 | 899.4 | 779.3 |
| Feb | 684.0 | 698.2 | 728.0 |
| Mar | 665.7 | 739.5 | 666.9 |
| Apr | 681.9 | 662.2 | 639.1 |
| May | 597.1 | 596.7 | 654.7 |
| Jun | 651.4 | 180.0 ⚠ | 494.7 (MTD) |
| Jul | 651.4 | 0 ⚠ | — |
| Aug | 758.3 | 0 ⚠ | — |
| Sep | 781.9 | 0 ⚠ | — |
| Oct | 931.0 | 0 ⚠ | — |
| Nov | 912.1 | 812.2 | — |
| Dec | 856.6 | 879.7 | — |

⚠ **2025 outage:** system produced nothing Jul–Oct 2025 (low in June). Estimated
~$800 in avoidable grid electricity during that period. Worth investigating —
check the SolaX portal Alarm Record tab; inverter may still be under warranty.

## Tariff comparison (estimated annual)

| Tariff | Import rate | Feed-in | Est. annual net | vs current |
|--------|-------------|---------|-----------------|------------|
| **T11 (current)** — flat | 29.98¢ flat | 8.66¢ | ~$1,780/yr | — |
| **T12A (recommended)** — time of use | ~44¢ peak (4–9pm), ~18¢ off-peak | 8.66¢ | ~$1,420–1,490/yr | **−$290–360/yr** |
| **T31 (add-on)** — controlled load | ~13¢ overnight | — | — | −$300–425/yr* |

\* T31 only helps if you have electric hot water or a pool pump not already on controlled load.
T12A rates are approximate — confirm with Ergon before switching.

## Recommendations

1. **Request interval data, then switch to Tariff 12A.** Call Ergon (13 10 46) for
   12 months of 30-min interval data (free). Your battery covers most of the 4–9pm
   peak window, so off-peak rates should win. Est. saving **$290–360/yr**.
2. **Add Tariff 31** if you have electric hot water or a pool pump. ~13¢ overnight
   vs 30¢ flat. Est. **$300–425/yr** if applicable.
3. **Investigate the 2025 outage** (~4 months offline). Check Alarm Record; possible
   warranty claim (5-yr inverter warranty from Feb 2021 commission).
4. **Protect the 87% self-consumption rate.** Export is worth 3.5× less than self-use.
   Run big loads (dishwasher, washing, pool pump) 9am–3pm; confirm battery mode is
   "Self Use" in the SolaX app.

## Data sources

- `data/solar-yield-2024.csv`, `2025.csv`, `2026.csv` — SolaX portal yearly reports
- Ergon bill dated 26 May 2026 (Tariff 11 rates)
- Tariff 12A rates approximate — verify at ergon.com.au before switching

*Note: "Energy (kWh)" in the SolaX yearly reports is **solar generation / yield**,
confirmed against the portal Overview (Monthly Yield 494.7 kWh = June 2026 figure).
It is not total household consumption.*
