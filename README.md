# Where Sydney’s Bus Reliability Problems Hurt Riders Most

A persuasive **data narrative dashboard** exploring bus service reliability across NSW and where unreliable services hurt riders the most. The dashboard is designed for a **Transport for NSW Service Planning Manager** and follows a **What → So What → What Next** narrative structure to move from operational performance, to rider vulnerability, to an action-oriented recommendation.

## Live App

**Streamlit Cloud:** [https://mdsi-dvn-assignment3-4a9frg2mix273fspyzwxnl.streamlit.app/](https://mdsi-dvn-assignment3-4a9frg2mix273fspyzwxnl.streamlit.app/) [web:58]

## Project overview

This project was developed for the MDSI Data Visualisation and Narrative assignment as an interactive, human-centered data story rather than a static dashboard. The core argument is that bus reliability problems should not be judged only by headline punctuality metrics, because cancellation burden, driver shortages, and rider dependence reveal a more serious equity issue across Greater Sydney and Outer Metropolitan communities.

### Stakeholder hat
**Transport for NSW Service Planning Manager**

### Narrative arc
**What → So What → What Next**

### Core question
Where do bus reliability problems cause the greatest public impact, and what action should Transport for NSW prioritise first?

## Persuasive claim

The dashboard argues that **Greater Sydney carries the heaviest cancellation burden and the most severe driver shortages**, while many of the people relying on buses are riders with limited alternatives such as CTP passengers, seniors, school students, and concession users. It also shows that Outer Metropolitan areas may look better on some headline reliability measures, but rider harm can still be substantial because service alternatives are weaker and complaints remain high.

## Dashboard structure

The app is organised into four narrative layers:

1. **Layer 1 — How reliable are the buses?**  
   Shows on-time running, cancellation rates, and driver vacancies over time to establish the operational problem.

2. **Layer 2 — Who is riding, and who cannot afford a bus not showing up?**  
   Uses Opal trip data to show which rider groups depend most on buses, especially vulnerable passenger categories.

3. **What Next — Modelling improvement**  
   Uses an interactive slider to estimate additional completed trips if Greater Sydney cancellation rates were reduced.

4. **Layer 4 — Real-time alerts**  
   Connects the static historical story to current operational disruptions using live GTFS Realtime service alerts.

## Advanced features

This dashboard implements at least three advanced features required by the brief:

1. **Context-aware filtering**  
   A sidebar region selector allows users to switch between **Both Regions**, **GS Greater Sydney**, and **ROM Outer Metropolitan**, updating charts and metrics dynamically.

2. **What-if parameterisation**  
   A slider allows users to model a reduction in Greater Sydney cancellation rates and estimates the number of additional completed trips per month and per year.

3. **Narrative scrollytelling**  
   The dashboard uses narrative callout boxes between visual layers to guide the user through the argument in sequence rather than leaving them to interpret disconnected charts alone.

4. **Live data integration**  
   A real-time alerts section connects the dashboard to current GTFS alert feeds through the TfNSW API, adding a live operational layer on top of historical reporting data.

## Design system

The app uses a consistent Streamlit-based design system defined through theme configuration and custom CSS. The draft documentation states that the theme is defined in `.streamlit/config.toml`, with a palette using blue for Greater Sydney, orange for ROM, and red for alerts, while app-level CSS styles narrative boxes, section headers, and call-to-action areas for visual consistency.

### Visual palette
- **Greater Sydney:** `#1B5E96`
- **Outer Metropolitan:** `#E87722`
- **Alerts / emphasis:** `#E74C3C`

## Repository structure

- `app.py` — Main Streamlit application containing dashboard logic, charts, filters, styling, and API integration.
- `.streamlit/config.toml` — Streamlit theme and configuratio
- `busperformancereportsfeb26.xlsx` — Source bus performance dataset used for operational reliability metrics.
- `cleaneddfbus.csv` — Cleaned Opal bus trip dataset used for rider demand analysis.
- `allmodes.csv` — All-mode Opal trip dataset used for broader transport comparison.
- `buscontract.geojson` — Bus contract region boundaries.
- `stops.txt` — GTFS static stop dataset.
- `routes.txt` — GTFS static routes dataset.
- `datacleaning.ipynb` — Data cleaning and preparation notebook.
- `datadictionary.xlsx` — Supplementary spreadsheet version of the data dictionary.
- `requirements.txt` — Python dependencies for local execution.

## How to run locally

Clone the repository and install dependencies:

```bash
git clone <your-repo-url>
cd <your-repo-folder>
python -m venv venv
```

Activate the environment:

**Windows**
```bash
venv\Scripts\activate
```

**macOS / Linux**
```bash
source venv/bin/activate
```

Install required packages:

```bash
pip install -r requirements.txt
```

Create a `.envthe project root and add your Transport for NSW API key:

```env
TRANSPORTAPIKEY=your_api_key_here
```

Then launch the app:

```bash
streamlit run app.py
```

The project relies on a TfNSW API key for the live alerts section, and the app code loads this value from environment variables before fetching GTFS Realtime bus alerts.

## Data sources

This dashboard combines multiple Transport for NSW data sources to move beyond a single CSV and produce a richer narrative:

1. **Transport for NSW Bus Performance Reports** — monthly bus reliability and staffing indicators.
2. **Transport for NSW Opal Tap-On Data** — monthly ridership by passenger card type.
3. **Transport for NSW Opal All Modes Data** — broader public transport usage across bus, train, ferry, light rail, and metro.
4. **Transport for NSW GTFS Static Feeds** — route and stop referenc
5. **Transport for NSW GTFS Realtime API** — live service disruption alerts.
6. **Transport for NSW Bus Contract Region Boundaries** — geographic operating boundaries.

## Data preparation notes

The app code filters performance and Opal datasets to **2024 onward**, matching the assignment’s recent-data requirement. In the performance data, rows where `Most recent month` is null are treated as imputed/projected rows rather than observed values, and the app separates real versus imputed values in the analysis logic.

For the rider-demand layer, Opal card types are simplified into cleaner display labels such as Adult, Senior Pensioner, School Student, Concession, Child Youth, and CTP Community Transport. The app also aggregates trips over time to produce the area chart and total-share breakdown used in the narrative.

## Data dictionary

### Dataset 1 — Bus Performance Reports
**Source:** Transport for NSW Bus Performance Reports  
**File:** `busperformancereportsfeb26.xlsx`  
**Purpose in dashboard:** Measures reliability and operational pressure across regions.

| Variable | Type | Definition |
|---|---|---|
| `Month` | datetime | Reporting month for each observation. |
| `OTR` | float64 | Proportion of bus services that operated on time. In the dashboard narrative, this is explained as departures within 59 seconds of schedule. |
| `% of services cancelled` | float64 | Percentage of scheduled services that did not operate. |
| `Untracked trips` | float64 | Proportion of trips without tracking data, usually due to equipment or data issues. |
| `Complaints per 100K` | float64 | Number of customer complaints per 100,000 bus trips. |
| `Driver Vacancies` | float64 | Number of unfilled bus driver positions in that month. |
| `Region` | object | Service region label, such as GS or ROM. |
| `Year` | int64 | Calendar year. |
| `Most recent month` | string / null | Used in the app to identify actual versus imputed/projected rows. |

### Dataset 2 — Cleaned Bus Opal Trips
**Source:** Transport for NSW Opal Tap-On Data  
**File:** `cleaneddfbus.csv`  
**Purpose in dashboard:** Shows who relies on buses and which rider groups are most affected when reliability drops.

| Variable | Type | Definition |
|---|---|---|
| `YearMonth` | datetime64 | Reporting month for trip counts. |
| `Cardtype` | object | Passenger card category such as Adult, Concession, ChildYouth, CTP, School Student, or SeniorPensioner. |
| `Trip` | float64 | Total number of tap-on trips for that card type in that month. |
| `Cardlabel` | derived categorical | Simplified display label created in the app for clearer storytelling. |

### Dataset 3 — All Transport Modes
**Source:** Transport for NSW Opal Tap-On Data  
**File:** `allmodes.csv`  
**Purpose in dashboard:** Provides broader multi-modal transport context beyond buses.

| Variable | Type | Definition |
|---|---|---|
| `YearMonth` | string | Reporting month, stored in month-year text format in the ra |
| `Cardtype` | categorical | Same passenger card categories used in the bus-only Opal dataset. |
| `TravelMode` | categorical | Public transport mode such as Bus, Train, Ferry, Light Rail, or Metro. |
| `Trip` | float | Number of trips for that card type and mode in the given month. |

### Dataset 4 — Bus Contract Region Boundaries
**Source:** Transport for NSW Metro / Outer Metro Bus Contract Boundaries  
**File:** `buscontract.geojson`  
**Purpose in dashboard:** Supports geographic context for contract regions.

| Variable | Type | Definition |
|---|---|---|
| `regiontype` | categorical | Contract type code such as GSBC, OMBSC, MBSC, RURAL, or FREEZONE. |
| `contract` | string | Contract area name. |
| `description` | string | Human-readable contract region description. |
| `geometry` | polygon | Boundary geometry for mapping and spatial context. |

### Dataset 5 — GTFS Stops
**Source:** Transport for NSW GTFS Static Feed  
**File:** `stops.txt`  
**Purpose in dashboard:** Resolves stop IDs from live alerts into location context.

| Variable | Type | Definition |
|---|---|---|
| `stopid` / `stop_id` | string | Unique stop identifier. The app uses stop IDs to match alert information to stop names. |
| `stopname` / `stop_name` | string | Human-readable stop name. |
| `stoplat` / `stop_lat` | float | Latitude in WGS84. |
| `stoplon` / `stop_lon` | float | Longitude in WGS84. |

### Dataset 6 — GTFS Routes
**Source:** Transport for NSW GTFS Static Feed  
**File:** `routes.txt`  
**Purpose in dashboard:** Resolves route IDs from live alerts into route names and labels.

| Variable | Type | Definition |
|---|---|---|
| `routeid` / `route_id` | string | Unique route identifier. |
| `routeshortname` / `route_short_name` | string | Public-facing short route number. |
| `routelongname` / `route_long_name` | string | Full route description. |

### Dataset 7 — GTFS Realtime Service Alerts
**Source:** Transport for NSW GTFS Realtime API  
**Purpose in dashboard:** Adds live disruption information to complement historical reporting data.

| Variable | Type | Definition |
|---|---|---|
| `headertext` / `header_text` | string | Alert headline shown to users. |
| `routeids` / `route_ids` | list[string] | List of affected route IDs. |
| `stopids` / `stop_ids` | list[string] | List of affected stop IDs. |
| `activeperiods` | list | Start and end time windows when the alert is active. |

## Key assumptions and caveats

The app’s what-if model estimates additional completed trips by applying a reduction in Greater Sydney cancellation rates to an assumed **60% Greater Sydney share of NSW bus trips**, and the app explicitly labels this as an illustrative directional model rather than a precise forecast.

The live alerts section depends on API access and current feed availability, while historical charts depend on cleaned local sourccluded in the repository. Some performance rows after the most recent actual month are treated as imputed or projected rather than observed values.

## Credits

**Data providers**
- Transport for NSW Open Data Portal.
- Transport for NSW GTFS Static and Realtime feeds.

**Tools and libraries**
- Streamlit for dashboard delivery.
- Plotly for interactive charts.
- Pandas and NumPy for data transformation.
- PyDeck for geospatial display support.

## Submission notes

This repository is structured so that it can be submitted directly together with the walkthrough video. The README includes the live app link, project explanation, advanced features, technical setup, and integrated data dictionary, which means the marker can understand the project without opening a separate documentatiost.[web:56]