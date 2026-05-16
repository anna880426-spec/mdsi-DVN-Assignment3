# Where Sydney's Bus Reliability Problems Hurt Riders Most

## Project Description
A persuasive data narrative dashboard exploring bus service reliability across NSW. Built for a Transport for NSW Service Planning Manager, this dashboard follows a What → So What → What Next narrative arc to identify where unreliable bus services hurt riders most and drive action on driver recruitment and regional benchmarks.

**Live Dashboard:** [link to be added after deployment]
**Narrative Structure:** What → So What → What Next
**Stakeholder Hat:** NSW Transport Service Planning Manager


## Data Dictionary

### Dataset 1: Bus Performance Reports
**Source:** Transport for NSW — Bus Performance Reports (2024–2026)
**File:** `busperformance_reports_feb26.xlsx`
**Provenance:** Downloaded from the TfNSW open data portal. Contains monthly operational metrics for contracted bus services across NSW.

| Variable | Type | Definition |
|----------|------|-----------|
| Month | datetime | Reporting month (YYYY-MM-DD format) |
| Region | categorical | Bus contract region: GS (Greater Sydney) or ROM (Rest of Metropolitan) |
| On Time Running | float | Percentage of services departing within 59 seconds of scheduled time (OTR) |
| % of services cancelled | float | Percentage of scheduled services that did not operate |
| Driver Vacancies | integer | Number of unfilled driver positions in the reporting month |
| Complaints per 100K | float | Number of complaints received per 100,000 passenger journeys |
| Most recent month | string/NaN | Flag indicating whether the row contains actual (non-null) or imputed (NaN) data |

### Dataset 2: Opal Tap-On Trip Data
**Source:** Transport for NSW — Opal Tap-On Data (2024–2026)
**File:** `cleaned_df_bus.csv`
**Provenance:** Cleaned from TfNSW Opal data. Filtered to bus-only trips.

| Variable | Type | Definition |
|----------|------|-----------|
| Year_Month | datetime | Trip month (YYYY-MM-DD format) |
| Card_type | categorical | Opal card category: Adult, CTP (Community Transport Program), Child/Youth, Concession, Employee, Free Travel, Pensioner Excursion, School Student, Senior/Pensioner, Single Trip, Unknown |
| Trip | float | Total number of tap-on trips for that card type in that month |

### Dataset 3: All Transport Modes
**Source:** Transport for NSW — Opal Tap-On Data (all modes, 2017–2025)
**File:** `all_modes.csv`
**Provenance:** Broader Opal dataset covering all public transport modes. Used in Layer 3b for cross-modal comparison.

| Variable | Type | Definition |
|----------|------|-----------|
| Year_Month | string | Trip month (Mon-YYYY format, e.g. "Jul-2016") |
| Card_type | categorical | Same card types as Dataset 2 |
| Travel_Mode | categorical | Transport mode: Bus, Train, Ferry, Light Rail, Metro |
| Trip | float | Total tap-on trips for that mode, card type, and month |

### Dataset 4: Bus Contract Region Boundaries
**Source:** Transport for NSW — Metro / Outer Metro Bus Contract Boundaries
**File:** `bus_contract.geojson`
**Provenance:** GeoJSON downloaded from TfNSW open data portal. Contains 36 polygon features representing NSW bus contract operating areas.

| Property | Type | Definition |
|----------|------|-----------|
| regiontype | categorical | Contract type code: GSBC (Greater Sydney Bus Contract), OMBSC (Outer Metropolitan Bus Service Contract), MBSC (Metropolitan Bus Service Contract), RURAL, FREEZONE |
| contract | string | Name of the specific contract area (e.g. "Region 6") |
| description | string | Human-readable description of the contract area |
| geometry | Polygon | Geographic boundary coordinates of the contract region |

### Dataset 5: GTFS Bus Stops
**Source:** Transport for NSW — GTFS Static Feed
**File:** `stops.txt`
**Provenance:** GTFS static feed containing all public transport stop locations in NSW.

| Variable | Type | Definition |
|----------|------|-----------|
| stop_id | string | Unique identifier for each stop |
| stop_name | string | Human-readable stop name |
| stop_lat | float | Latitude coordinate (WGS84) |
| stop_lon | float | Longitude coordinate (WGS84) |

### Dataset 6: GTFS Bus Routes
**Source:** Transport for NSW — GTFS Static Feed
**File:** `routes.txt`
**Provenance:** GTFS static feed containing all contracted route definitions.

| Variable | Type | Definition |
|----------|------|-----------|
| route_id | string | Unique route identifier |
| route_short_name | string | Short public-facing route number (e.g. "333") |
| route_long_name | string | Full route description |

### Dataset 7: GTFS Realtime Service Alerts
**Source:** Transport for NSW — GTFS Realtime API
**Provenance:** Live API feed providing current service disruption alerts. Accessed via API key. Cached for 1 hour (ttl=3600).

| Field | Type | Definition |
|-------|------|-----------|
| header_text | string | Alert headline (e.g. "Sydney CBD diversions for fun run event") |
| stop_ids | list[string] | List of affected stop IDs, cross-referenced with stops.txt for coordinates |
| route_ids | list[string] | List of affected route IDs, cross-referenced with routes.txt for names |

## Advanced Features

1. **Context-Aware Filtering:** Sidebar region selector (GS / ROM / Both) dynamically updates all charts, the Layer 3 map, and the metrics panel simultaneously.
2. **What-If Parameterisation:** Interactive slider (5–80%) lets users model the impact of reducing GS cancellation rates, displaying estimated additional monthly and annual trips.
3. **Narrative Scrollytelling:** Narrative boxes between each layer guide the user through the What → So What → What Next arc with contextual transitions.

## Design System
- **Theme:** Defined in `.streamlit/config.toml` with primaryColor, backgroundColor, secondaryBackgroundColor, textColor, and font.
- **Palette:** GS = #1B5E96 (blue), ROM = #E87722 (orange), Alerts = #E74C3C (red)
- **CSS Components:** .section-header, .narrative-box, .cta-box, .metric-card — all defined in app.py inline CSS.

## File Structure
- `app.py` — Main Streamlit dashboard application (~1230 lines, annotated)
- `.streamlit/config.toml` — Streamlit server config and design system theme
- `busperformance_reports_feb26.xlsx` — Bus performance dataset (source)
- `cleaned_df_bus.csv` — Cleaned Opal bus trip data
- `all_modes.csv` — All transport modes Opal data (bus, train, ferry, light rail, metro)
- `bus_contract.geojson` — GS/ROM contract region boundaries (GeoJSON)
- `stops.txt` — GTFS static bus stop locations (170K stops)
- `routes.txt` — GTFS static route definitions (10K routes)
- `datacleaning.ipynb` — Data cleaning notebook
- `data_dictionary.xlsx` — Supplementary data dictionary (Excel format)
- `requirements.txt` — Python package dependencies
- `.env` — Local API key storage (not committed)

## How to Run

### Local Development
```bash
git clone https://github.com/anna880426-spec/mdsi-DVN-Assignment3.git
cd mdsi-DVN-Assignment3
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

Create a `.env` file in the project root:
TRANSPORT_API_KEY=your_api_key_here

Get your API key from [TfNSW Open Data Hub](https://opendata.transport.nsw.gov.au) (Profile → API Tokens).

```bash
streamlit run app.py
```

### Streamlit Cloud
https://mdsi-dvn-assignment3-4a9frg2mix273fspyzwxnl.streamlit.app/

## Data Sources
- [Transport for NSW — Bus Performance Reports](https://opendata.transport.nsw.gov.au)
- [Transport for NSW — Opal Tap-On Trip Data](https://opendata.transport.nsw.gov.au)
- [Transport for NSW — GTFS Static & Realtime Feeds](https://opendata.transport.nsw.gov.au)
- [Transport for NSW — Bus Contract Region Boundaries](https://opendata.transport.nsw.gov.au/dataset/metro-outer-metro-bus-contract-boundaries)
