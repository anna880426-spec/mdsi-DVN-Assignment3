# ============================================================
# Sydney Bus Reliability Dashboard
# MDSI DVN Assignment 3 - Group Project
# 
# BEGINNER'S GUIDE TO THIS FILE:
# - Every section is explained in plain English
# - Streamlit works top-to-bottom: whatever you write first
#   appears at the top of the page
# - To run this app: open your terminal, go to this folder,
#   and type:  streamlit run app.py
# ============================================================

import streamlit as st          # The main library that builds the web app
import pandas as pd             # For loading and working with our data
import plotly.graph_objects as go  # For building interactive charts
import plotly.express as px # Simpler chart-building on top of plotly

import pydeck as pdk
import json

import os
from dotenv import load_dotenv
import requests
from google.transit import gtfs_realtime_pb2
from datetime import datetime


load_dotenv()

API_KEY = os.getenv("TRANSPORT_API_KEY")

# ============================================================
# STEP 1: PAGE CONFIGURATION
# This must be the FIRST streamlit command in the file.
# It sets the browser tab title, icon, and layout width.
# ============================================================
st.set_page_config(
    page_title="Sydney Bus Reliability",
    page_icon="🚌",
    layout="wide"   # "wide" uses the full screen width
)

# ============================================================
# STEP 2: CUSTOM STYLING (CSS)
# This injects CSS into the page to control colours,
# spacing, and font styles. You don't need to touch this
# unless you want to change how things look visually.
# ============================================================
st.markdown("""
<style>
    /* Light grey background for the whole page */
    .main { background-color: #f8f9fa; }

    /* Blue narrative callout boxes */
    .narrative-box {
        background-color: #EBF3FF;
        border-left: 5px solid #1B5E96;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin: 12px 0 20px 0;
        line-height: 1.7;
        color: black;
    }

    /* Yellow warning box (for imputed data notice) */
    .imputed-warning {
        background-color: #FFF8E1;
        border-left: 5px solid #FFC107;
        padding: 10px 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
        font-size: 13px;
        color: black;
    }

    /* Section heading style */
    .section-header {
        color: #1B5E96;
        font-size: 22px;
        font-weight: 700;
        margin-top: 30px;
        padding-bottom: 6px;
        border-bottom: 2px solid #1B5E96;
        
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# STEP 3: LOAD DATA
#
# @st.cache_data is a "decorator" — it tells Streamlit to
# remember the result of this function after the first time
# it runs. Without it, the files would be re-read every
# time the user clicks anything. With it, the app is fast.
# ============================================================

@st.cache_data
def load_static_data():
    r_df = pd.read_csv('routes.txt', dtype={'route_short_name': str, 'agency_id': str})
    s_df = pd.read_csv('stops.txt', dtype={'stop_id': str})
    return r_df, s_df

# ---- Layer 3 (spatial map) loaders --------------------------
# These two functions feed the choropleth + stop-cloud map.
# They are cached for a day so the map renders instantly on
# subsequent reruns and the heavy stops.txt only parses once.
# -------------------------------------------------------------

# Map TfNSW contract codes to the GS / ROM buckets used elsewhere
# in the dashboard. "Freezone" overlays and unknowns are excluded.
REGION_MAP = {
    "GSBC":  "GS",   # Greater Sydney Bus Contracts
    "MBSC":  "GS",   # Metropolitan Bus Service Contract
    "OMBSC": "ROM",  # Outer Metropolitan Bus Service Contract
    "RURAL": "ROM",  # Rural zone
}

def _region_bucket(regiontype):
    return REGION_MAP.get((regiontype or "").upper())

@st.cache_data(ttl=86400, show_spinner=False)
def load_bus_contract_geojson():
    """NSW bus contract regions (36 polygons; regiontype maps to GS / ROM via REGION_MAP)."""
    with open("bus_contract.geojson", "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data(ttl=86400, show_spinner=False)
def load_map_stops(max_points=5000):
    """Load GTFS stops, restrict to the Sydney area, tag each by contract region, sample."""
    s_df = pd.read_csv(
        "stops.txt",
        dtype={"stop_id": str},
        usecols=["stop_id", "stop_name", "stop_lat", "stop_lon"],
    )
    s_df["stop_lat"] = pd.to_numeric(s_df["stop_lat"], errors="coerce")
    s_df["stop_lon"] = pd.to_numeric(s_df["stop_lon"], errors="coerce")
    s_df = s_df.dropna(subset=["stop_lat", "stop_lon"])
    # Sydney bbox: keeps the map focused and removes far-flung non-bus stops
    s_df = s_df[
        s_df["stop_lat"].between(-34.2, -33.4)
        & s_df["stop_lon"].between(150.5, 151.5)
    ].copy()

    # Build a bounding box per GS/ROM bucket from the contract polygons.
    # Bbox classification is a deliberate approximation near boundaries —
    # it avoids a shapely dependency and runs in milliseconds. GS is tested
    # first because the GS polygons sit inside the broader ROM footprint.
    geojson = load_bus_contract_geojson()
    bboxes = {"GS":  [90.0, -90.0, 180.0, -180.0],
              "ROM": [90.0, -90.0, 180.0, -180.0]}
    for feat in geojson["features"]:
        bucket = _region_bucket((feat.get("properties") or {}).get("regiontype"))
        if bucket is None:
            continue
        bb = bboxes[bucket]
        stack = [feat["geometry"]["coordinates"]]
        while stack:
            x = stack.pop()
            if isinstance(x, list) and x and isinstance(x[0], (int, float)):
                lo, la = x[0], x[1]
                if la < bb[0]: bb[0] = la
                if la > bb[1]: bb[1] = la
                if lo < bb[2]: bb[2] = lo
                if lo > bb[3]: bb[3] = lo
            elif isinstance(x, list):
                stack.extend(x)

    def _classify(lat, lon):
        for bucket in ("GS", "ROM"):
            mn_la, mx_la, mn_lo, mx_lo = bboxes[bucket]
            if mn_la <= lat <= mx_la and mn_lo <= lon <= mx_lo:
                return bucket
        return "UNKNOWN"

    s_df["region"] = [_classify(la, lo) for la, lo in zip(s_df["stop_lat"], s_df["stop_lon"])]

    # Sample so pydeck stays smooth even on slower machines
    if len(s_df) > max_points:
        s_df = s_df.sample(n=max_points, random_state=42)
    return s_df.reset_index(drop=True)


@st.cache_data(ttl=86400, show_spinner=False)
def load_data():
    # --- Bus Performance Data ---
    perf = pd.read_excel("busperformance_reports_feb26.xlsx", sheet_name="BusData")
    perf["Month"] = pd.to_datetime(perf["Month"])

    # Keep only 2024 onwards (as decided in our EDA)
    perf = perf[perf["Month"] >= "2024-01-01"].copy()

    # Mark imputed rows: the "Most recent month" column is 1.0 for the
    # last real data point (Feb 2026) and NaN for projected rows (Mar–Jun 2026)
    perf["is_imputed"] = perf["Most recent month"].isna()

    # --- Opal Trip Data (Demand Layer) ---
    opal = pd.read_csv("cleaned_df_bus.csv")
    opal["Year_Month"] = pd.to_datetime(opal["Year_Month"])
    opal = opal[opal["Year_Month"] >= "2024-01-01"].copy()

    # Simplify card type names for display
    label_map = {
        "CTP": "CTP (Community Transport)",
        "Adult": "Adult",
        "Senior/Pensioner": "Senior / Pensioner",
        "School Student": "School Student",
        "Concession": "Concession",
        "Child/Youth": "Child / Youth",
    }
    opal["Card_label"] = opal["Card_type"].map(label_map).fillna("Other")

    return perf, opal

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bus_alerts(api_key):
    url = 'https://api.transport.nsw.gov.au/v2/gtfs/alerts/buses'
    headers = {
        'Authorization': f'apikey {api_key}',
        'Accept': 'application/x-google-protobuf'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        #Easier to cache a list
        clean_data = []
        for entity in feed.entity:
            if entity.HasField('alert'):
                alert = entity.alert
                clean_data.append({
                    "id": entity.id,
                    "header": alert.header_text.translation[0].text if alert.header_text.translation else "No Header",
                    "desc": alert.description_text.translation[0].text if alert.description_text.translation else "",
                    "route_ids": [s.route_id for s in alert.informed_entity if s.HasField('route_id')],
                    "stop_ids": [s.stop_id for s in alert.informed_entity if s.HasField('stop_id')],
                    "active_periods": [{"start": p.start, "end": p.end} for p in alert.active_period]
                })
        return clean_data
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return []

def find_route_name(code):
    parts = code.split('_')
    if len(parts) == 2:
    #print(type(parts[0]), type(parts[1]))
    #print(routes_df.loc[(routes_df["agency_id"] == parts[0]) & (routes_df["route_short_name"] == parts[1]), "route_long_name"])
        results = routes_df.loc[(routes_df["agency_id"] == parts[0]) & (routes_df["route_short_name"] == parts[1]), "route_long_name"]
        if len(results.values) > 0:
            return parts[1], results.values[0]
    return code, "Could not find code"

def find_stop_name(code):
    #print(code)
    results = stops_df.loc[stops_df["stop_id"] == code, "stop_name"]
    if len(results.values) > 0:
        return results.values[0]
    return code

# Actually call the function to get our data
perf, opal = load_data()
routes_df, stops_df = load_static_data()

# ============================================================
# STEP 4: COLOUR PALETTE
# Define colours once here so they stay consistent across
# every chart. Change them here to restyle the whole app.
# ============================================================
COL_GS      = "#1B5E96"   # Deep blue → Greater Sydney
COL_ROM     = "#E87722"   # Orange    → Outer Metropolitan
#COL_GREY    = "#AAAAAA"   # Grey      → projected/imputed data


# ============================================================
# STEP 5: SIDEBAR (INTERACTIVE FILTERS)
#
# Everything inside "with st.sidebar:" appears in the
# collapsible panel on the left side of the screen.
#
# This is our ADVANCED FEATURE #1: Context-Aware Filtering.
# When the user changes the region or toggles the imputed
# data switch, ALL charts on the page update automatically
# because they all read from the same filtered dataframe.
# ============================================================
with st.sidebar:
    st.markdown("## Filters")
    st.markdown("Use these controls to explore the data. All charts update instantly.")
    st.markdown("---")

    # Dropdown to pick a region
    selected_region = st.selectbox(
        "Region",
        options=["Both Regions", "GS – Greater Sydney", "ROM – Outer Metropolitan"],
        index=0,
        help="GS = Greater Sydney | ROM = Outer Metropolitan (Blue Mountains, Hunter, Illawarra, etc.)"
    )

    st.markdown("---")
    st.markdown("### About this dashboard")
    st.markdown("""
    This dashboard explores **bus service reliability** across NSW and the impact on
    riders who depend on buses the most.

    **Data sources**
    - Transport for NSW Bus Performance Reports (2024–2026)
    - Opal Tap-On Trip Data (2024–2026)

    **Narrative structure:** What → So What → What Next
    """)


# ============================================================
# STEP 6: FILTER THE DATA BASED ON SIDEBAR SELECTION
#
# We create a filtered version of perf called perf_f.
# Every chart uses perf_f instead of the full dataset,
# so changing the sidebar instantly changes all charts.
# ============================================================
if selected_region == "GS – Greater Sydney":
    perf_f = perf[perf["Region"] == "GS"].copy()
elif selected_region == "ROM – Outer Metropolitan":
    perf_f = perf[perf["Region"] == "ROM"].copy()
else:
    perf_f = perf.copy()


# ============================================================
# STEP 7: HERO SECTION
# The title and four big "metric cards" at the very top.
# These give the reader the headline numbers immediately.
# ============================================================

st.markdown("""
<h1 style='color:#1B5E96; margin-bottom:4px'>
    Where Sydney's Bus Reliability Problems Hurt Riders Most
</h1>
<p style='color:#555; font-size:17px; margin-top:2px'>
    A data story about outer metropolitan communities left behind by unreliable bus services
</p>
""", unsafe_allow_html=True)

st.markdown("---")

# Calculate summary stats using only REAL data (not imputed)
real = perf[~perf["is_imputed"]]
gs_r  = real[real["Region"] == "GS"]
rom_r = real[real["Region"] == "ROM"]

# Four metric cards side by side
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="GS On-Time Rate (avg)",
        value=f"{gs_r['OTR'].mean():.1%}",
        delta=f"{(gs_r['OTR'].mean() - rom_r['OTR'].mean())*100:+.1f}pp vs ROM",
        delta_color="normal"
    )
with c2:
    st.metric(
        label="GS Cancellation Rate (avg)",
        value=f"{gs_r['% of services cancelled'].mean():.2%}",
        delta=f"{(gs_r['% of services cancelled'].mean() - rom_r['% of services cancelled'].mean())*100:+.2f}pp vs ROM",
        delta_color="inverse"   # red = bad = higher cancellations
    )
with c3:
    st.metric(
        label="GS Driver Vacancies (avg/month)",
        value=f"{gs_r['Driver Vacancies'].mean():.0f}",
        delta=f"ROM avg: {rom_r['Driver Vacancies'].mean():.0f}",
        delta_color="off"
    )
with c4:
    st.metric(
        label="ROM Complaints per 100K trips",
        value=f"{rom_r['Complaints per 100K'].mean():.1f}",
        delta=f"GS avg: {gs_r['Complaints per 100K'].mean():.1f}",
        delta_color="off"
    )

# Opening narrative — this is SCROLLYTELLING: guiding the reader
# before they see any data, framing what they're about to look at
st.markdown("""
<div class='narrative-box'>
<b>The story in one sentence:</b> Greater Sydney buses are cancelled more often and face severe driver shortages —
while Outer Metropolitan riders, despite better headline stats, have no alternatives when a service fails.
Together, these two regions paint a picture of a network under pressure, where the most vulnerable riders pay the price.
</div>
""", unsafe_allow_html=True)

# ============================================================
# ── LAYER 1: SERVICE RELIABILITY ────────────────────────────
# ============================================================
st.markdown("---")
st.markdown("<div class='section-header'>Layer 1 — How Reliable Are the Buses?</div>", unsafe_allow_html=True)

st.markdown("""
<div class='narrative-box'>
<b>On-Time Running (OTR)</b> is the share of services that departed within 59 seconds of schedule.
<b>Cancellations</b> are services that never ran at all.
Together they define whether a rider can trust the timetable.
The TfNSW target is <b>95% on-time running</b> — shown as a red dashed line below.
</div>
""", unsafe_allow_html=True)


# ── CHART 1: OTR over time ──────────────────────────────────
st.markdown("#### On-Time Running Rate Over Time")

fig1 = go.Figure()

# We loop over both regions so we can style them separately
for region, colour in [("GS", COL_GS), ("ROM", COL_ROM)]:

    # Only include this region's data if the filter allows it
    subset = perf_f[perf_f["Region"] == region]
    if subset.empty:
        continue

    real_rows = subset[~subset["is_imputed"]]

    # Solid line = actual measured data
    fig1.add_trace(go.Scatter(
        x=real_rows["Month"],
        y=real_rows["OTR"],
        mode="lines+markers",
        name=f"{region} (actual)",
        line=dict(color=colour, width=2.5),
        marker=dict(size=6),
        hovertemplate=(
            f"<b>{region}</b><br>"
            "Month: %{x|%b %Y}<br>"
            "OTR: %{y:.1%}<extra></extra>"
        )
    ))

# Red dotted reference line at 95% target
fig1.add_hline(
    y=0.95,
    line_dash="dot",
    line_color="red",
    line_width=1.5,
    annotation_text="95% TfNSW target",
    annotation_position="bottom right",
    annotation_font_color="red"
)

fig1.update_layout(
    yaxis=dict(tickformat=".0%", title="On-Time Running Rate", range=[0.88, 1.0], automargin = True),
    xaxis= dict(automargin = True),
    xaxis_title="Month",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="#0F1117",
    paper_bgcolor="#0F1117",
    height=380,
    margin=dict(t=10, b=20, l=10, r=10),
    font_color="white"
)

fig1.update_xaxes(showgrid = False)
fig1.update_yaxes(showgrid = False)

st.plotly_chart(fig1, use_container_width=True, theme = None)


# ── CHART 2: Cancellation rate over time ────────────────────
st.markdown("#### Cancellation Rate Over Time")

fig2 = go.Figure()

for region, colour in [("GS", COL_GS), ("ROM", COL_ROM)]:

    subset = perf_f[perf_f["Region"] == region]
    if subset.empty:
        continue

    real_rows = subset[~subset["is_imputed"]]

    # Convert to percentage for readability (0.01 → 1.0%)
    fig2.add_trace(go.Scatter(
        x=real_rows["Month"],
        y=real_rows["% of services cancelled"] * 100,
        mode="lines+markers",
        name=f"{region} (actual)",
        line=dict(color=colour, width=2.5),
        fill="tozeroy",
        fillcolor="rgba(27,94,150,0.12)" if region == "GS" else "rgba(232,119,34,0.12)",
        marker=dict(size=6),
        hovertemplate=(
            f"<b>{region}</b><br>"
            "Month: %{x|%b %Y}<br>"
            "Cancelled: %{y:.2f}%<extra></extra>"
        )
    ))

fig2.update_layout(
    yaxis_title="% of Services Cancelled",
    yaxis_automargin = True,
    xaxis_title="Month",
    xaxis= dict(automargin = True),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="#0F1117",
    paper_bgcolor="#0F1117",
    height=350,
    margin=dict(t=10, b=20, l=10, r=10),
    font_color = "white",
)
fig2.update_xaxes(showgrid = False)
fig2.update_yaxes(showgrid = False)

st.plotly_chart(fig2, use_container_width=True, theme = None)



# Narrative bridge between charts — scrollytelling in action
st.markdown("""
<div class='narrative-box'>
<b>What's driving cancellations?</b> A major structural cause is driver shortages.
Greater Sydney has consistently had <b>hundreds of unfilled driver positions</b> every month.
When there's no driver, the bus simply does not run.
</div>
""", unsafe_allow_html=True)


# ── CHART 3: Driver Vacancies ────────────────────────────────
st.markdown("#### Driver Vacancies by Region (Monthly)")

fig3 = go.Figure()

for region, colour in [("GS", COL_GS), ("ROM", COL_ROM)]:
    subset = perf_f[perf_f["Region"] == region]
    if subset.empty:
        continue
    real_rows = subset[~subset["is_imputed"]]

    fig3.add_trace(go.Bar(
        x=real_rows["Month"],
        y=real_rows["Driver Vacancies"],
        name=region,
        marker_color=colour,
        hovertemplate=(
            f"<b>{region}</b><br>"
            "Month: %{x|%b %Y}<br>"
            "Vacancies: %{y:.0f}<extra></extra>"
        ),
    ))

fig3.update_layout(
    barmode="group",
    yaxis_title="Unfilled Driver Positions",
    yaxis_automargin = True,
    xaxis_title="Month",
    xaxis_automargin = True,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    plot_bgcolor="#0F1117",
    paper_bgcolor="#0F1117",
    height=350,
    margin=dict(t=10, b=20, l=10, r=10),
    font_color = "white"
)

fig3.update_yaxes(color = "white")

st.plotly_chart(fig3, use_container_width=True, theme = None)


# ============================================================
# ── LAYER 2: RIDER DEMAND ────────────────────────────────────
# ============================================================
st.markdown("---")
st.markdown("<div class='section-header'>Layer 2 — Who's Riding, and Who Can't Afford a Bus Not Showing Up?</div>", unsafe_allow_html=True)

st.markdown("""
<div class='narrative-box'>
Opal tap-on data tells us <i>who</i> is riding buses. When we look at card types, a clear pattern emerges:
the majority of trips are taken by <b>CTP (Community Transport), Seniors, School Students, and Concession holders</b> —
people with the least ability to switch to taxis, rideshares, or private cars.
When their bus is cancelled or late, they wait. Or they miss the appointment.
</div>
""", unsafe_allow_html=True)


# ── CHART 4: Opal trips over time (area chart) ──────────────
st.markdown("#### Monthly Bus Trips by Passenger Type (All NSW)")

TOP_CARDS = [
    "CTP (Community Transport)",
    "Adult",
    "Senior / Pensioner",
    "School Student",
    "Concession",
    "Child / Youth",
]

# Aggregate trips by month and card label, keep only top 6 types
opal_agg = (
    opal[opal["Card_label"].isin(TOP_CARDS)]
    .groupby(["Year_Month", "Card_label"], as_index=False)["Trip"]
    .sum()
)

fig4 = px.area(
    opal_agg,
    x="Year_Month",
    y="Trip",
    color="Card_label",
    color_discrete_sequence=px.colors.qualitative.Bold,
    labels={
        "Year_Month": "Month",
        "Trip": "Number of Trips",
        "Card_label": "Passenger Type"
    },
)
fig4.update_layout(
    plot_bgcolor="#0F1117",
    yaxis_automargin = True,
    xaxis_automargin = True,
    paper_bgcolor="#0F1117",
    height=380,
    yaxis_tickformat=".2s",   # e.g. 20M instead of 20,000,000
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=10, b=20, l=10, r=10),
    font_color = "white"
)
fig4.update_traces(
    hovertemplate="<b>%{fullData.name}</b><br>Month: %{x|%b %Y}<br>Trips: %{y:,.0f}<extra></extra>"
)

st.plotly_chart(fig4, use_container_width=True, theme=None)


# ── CHART 5: Donut + insight text side by side ──────────────
st.markdown("#### Who Takes the Most Bus Trips? (2024–2026 total)")

col_pie, col_insight = st.columns([1, 1])

with col_pie:
    opal_total = (
        opal[opal["Card_label"].isin(TOP_CARDS)]
        .groupby("Card_label", as_index=False)["Trip"]
        .sum()
        .sort_values("Trip", ascending=False)
    )
    fig5 = px.pie(
        opal_total,
        names="Card_label",
        values="Trip",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    fig5.update_traces(
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>Total trips: %{value:,.0f}<extra></extra>"
    )
    fig5.update_layout(
        showlegend=False,
        plot_bgcolor="#0F1117",
        paper_bgcolor="#0F1117",
        height=380,
        margin=dict(t=5, b=60, l=10, r=10),
        font_color = "white"
    )
    st.plotly_chart(fig5, use_container_width=True, theme=None)

with col_insight:
    st.markdown("""
    <div class='narrative-box' style='margin-top:40px'>
    <b>Key insight:</b><br><br>
    CTP and Senior/Pensioner riders together account for the single largest share of all bus trips in NSW.
    These passengers are most likely to be:<br><br>
    &nbsp;&nbsp;• Elderly or living with disability<br>
    &nbsp;&nbsp;• Car-free <i>by necessity</i>, not by choice<br>
    &nbsp;&nbsp;• Travelling to medical appointments, schools, or work<br><br>
    <b>When their bus doesn't show up, there is no Plan B.</b>
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# ── LAYER 3: SPATIAL DISTRIBUTION ───────────────────────────
# A pydeck map combining two layers:
#   1) Bus contract region polygons coloured by GS vs ROM
#   2) A sampled cloud of GTFS bus stops (≤5,000 dots)
# Both layers respect the sidebar region filter so the user
# can isolate one region at a time.
# ============================================================
st.markdown("---")
st.markdown("<div class='section-header'>Layer 3 — Where Are the Buses?</div>", unsafe_allow_html=True)

st.markdown("""
<div class='narrative-box'>
This map shows the geographic spread of Sydney's bus network across the
<b>GS (Greater Sydney)</b> and <b>ROM (Outer Metropolitan)</b> contract regions.
Each polygon is one of the 36 contracted operating areas; each dot is an individual bus stop.
Use the region filter in the sidebar to focus on a single region — the boundary fill
and the stops update together.
</div>
""", unsafe_allow_html=True)

# Load (cached) and apply the sidebar filter
geojson_data = load_bus_contract_geojson()
map_stops    = load_map_stops(max_points=5000)

if selected_region == "GS – Greater Sydney":
    region_filter = {"GS"}
elif selected_region == "ROM – Outer Metropolitan":
    region_filter = {"ROM"}
else:
    region_filter = {"GS", "ROM"}

# Filter polygons to the selected region(s) and tag each with a fill colour
# that pydeck's GeoJsonLayer can read directly via "properties._fill".
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]

GS_FILL  = _hex_to_rgb(COL_GS)  + [70]   # last value = alpha (0–255), kept low for transparency
ROM_FILL = _hex_to_rgb(COL_ROM) + [70]

filtered_features = []
for feat in geojson_data["features"]:
    bucket = _region_bucket((feat.get("properties") or {}).get("regiontype"))
    if bucket not in region_filter:
        continue
    # Don't mutate the cached object — copy the feature first
    new_feat = dict(feat)
    new_feat["properties"] = dict(feat.get("properties") or {})
    new_feat["properties"]["_fill"] = GS_FILL if bucket == "GS" else ROM_FILL
    new_feat["properties"]["_bucket"] = bucket
    filtered_features.append(new_feat)

filtered_geojson = {"type": "FeatureCollection", "features": filtered_features}

# Filter stops to the selected region(s) and pre-compute per-row RGB values
stops_view = map_stops[map_stops["region"].isin(region_filter)].copy()
gs_rgb  = _hex_to_rgb(COL_GS)
rom_rgb = _hex_to_rgb(COL_ROM)
stops_view["fill_r"] = [gs_rgb[0] if r == "GS" else rom_rgb[0] for r in stops_view["region"]]
stops_view["fill_g"] = [gs_rgb[1] if r == "GS" else rom_rgb[1] for r in stops_view["region"]]
stops_view["fill_b"] = [gs_rgb[2] if r == "GS" else rom_rgb[2] for r in stops_view["region"]]

polygon_layer = pdk.Layer(
    "GeoJsonLayer",
    data=filtered_geojson,
    stroked=True,
    filled=True,
    get_fill_color="properties._fill",
    get_line_color=[80, 80, 80],
    line_width_min_pixels=1,
    pickable=True,
)

stops_layer = pdk.Layer(
    "ScatterplotLayer",
    data=stops_view,
    get_position="[stop_lon, stop_lat]",
    get_fill_color="[fill_r, fill_g, fill_b, 170]",
    get_radius=40,
    radius_min_pixels=2,
    radius_max_pixels=4,
    pickable=False,
)

view_state = pdk.ViewState(latitude=-33.85, longitude=151.05, zoom=8.4, pitch=0)

st.pydeck_chart(
    pdk.Deck(
        map_provider="carto",
        map_style="light",
        layers=[polygon_layer, stops_layer],
        initial_view_state=view_state,
        tooltip={"html": "<b>Contract:</b> {contract}<br/><b>Region:</b> {_bucket}"},
    ),
    use_container_width=True,
    height=500,
)

st.caption(
    f"Showing {len(filtered_features)} contract polygon(s) and {len(stops_view):,} bus stops "
    "(sampled from a Sydney-area subset of GTFS stops.txt). Stop-to-region tagging uses "
    "polygon bounding boxes — accurate away from boundaries, approximate at the edges."
)


# ============================================================
# ── WHAT NEXT: WHAT-IF PARAMETERISATION ─────────────────────
#
# ADVANCED FEATURE #2: What-If Parameterisation
# A slider lets the user explore different improvement
# scenarios and see the estimated impact in real time.
# ============================================================
st.markdown("---")
st.markdown("<div class='section-header'>What Next — Modelling the Impact of Improvement</div>", unsafe_allow_html=True)

st.markdown("""
<div class='narrative-box'>
If Transport for NSW were to reduce cancellation rates in Greater Sydney — the region with the most driver vacancies
and highest cancellation rates — how many additional trips would be completed each month?
Use the slider below to explore different improvement scenarios.
</div>
""", unsafe_allow_html=True)

col_slide, col_card = st.columns([1, 1])

with col_slide:
    reduction_pct = st.slider(
        "Reduce GS cancellation rate by:",
        min_value=5,
        max_value=80,
        value=30,
        step=5,
        format="%d%%",
        help=(
            "Example: 30% means cutting the average GS cancellation rate "
            "from ~1.05% down to ~0.73%."
        )
    )

    # ── What-If Calculation ──────────────────────────────────
    # Step 1: Get the current average GS cancellation rate (real data only)
    gs_real = perf[(perf["Region"] == "GS") & (~perf["is_imputed"])]
    avg_cancel = gs_real["% of services cancelled"].mean()
    new_cancel  = avg_cancel * (1 - reduction_pct / 100)

    # Step 2: Estimate monthly GS bus trips
    # Opal doesn't split by region, so we use ~60% as a GS proxy
    # (GS has roughly 60% of NSW bus patronage based on network size)
    avg_monthly_trips = (
        opal.groupby("Year_Month")["Trip"].sum().mean()
    )
    gs_trips_est = avg_monthly_trips * 0.60

    # Step 3: How many extra trips if cancellations drop?
    trips_saved_monthly = gs_trips_est * (avg_cancel - new_cancel)
    trips_saved_annual  = trips_saved_monthly * 12

    st.markdown(f"""
    <br>
    <div style='font-size:14px; color:#555; line-height:1.8'>
    <b>Current GS avg cancellation rate:</b> {avg_cancel:.2%}<br>
    <b>Improved cancellation rate:</b> {new_cancel:.2%}<br>
    <b>Rate reduction:</b> {(avg_cancel - new_cancel)*100:.3f} percentage points
    </div>
    """, unsafe_allow_html=True)

with col_card:
    st.markdown(f"""
    <div style='
        background: linear-gradient(135deg, #1B5E96, #2980b9);
        color: white;
        padding: 30px 25px;
        border-radius: 12px;
        text-align: center;
        margin-top: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    '>
        <div style='font-size:13px; opacity:0.8; letter-spacing:1px; text-transform:uppercase'>
            Estimated additional trips per month
        </div>
        <div style='font-size:48px; font-weight:800; margin:8px 0'>
            +{trips_saved_monthly:,.0f}
        </div>
        <hr style='border-color:rgba(255,255,255,0.25); margin:12px 0'>
        <div style='font-size:13px; opacity:0.8; letter-spacing:1px; text-transform:uppercase'>
            That's per year
        </div>
        <div style='font-size:32px; font-weight:700'>
            +{trips_saved_annual:,.0f} trips
        </div>
    </div>
    """, unsafe_allow_html=True)

st.caption(
    "⚠️ Methodology note: Monthly trips saved are estimated using the average GS cancellation rate "
    "and an assumed 60% GS share of total NSW bus trips (Opal data does not include a region split). "
    "This is an illustrative model, not a precise forecast. Treat as directional."
)


# ============================================================
# ── CONCLUSION & CALL TO ACTION ──────────────────────────────
# ============================================================
st.markdown("---")
st.markdown("""
<div style='
    background: linear-gradient(135deg, #1B5E96, #154f80);
    color: white;
    padding: 32px 30px;
    border-radius: 12px;
    margin-top: 10px;
'>
    <h2 style='color:white; margin-top:0'>The Ask: Prioritise Where It Hurts Most</h2>
    <p style='font-size:16px; line-height:1.8; opacity:0.95'>
        Greater Sydney carries the heaviest cancellation burden and the most severe driver shortages —
        while its riders include hundreds of thousands of CTP, Senior, and School Student passengers
        with no viable alternatives when a service fails.
    </p>
    <p style='font-size:16px; line-height:1.8; opacity:0.95'>
        <b>Transport for NSW should:</b><br>
        1. &nbsp;Target driver recruitment and retention in Greater Sydney as an <b>immediate priority</b><br>
        2. &nbsp;Set <b>region-specific cancellation benchmarks</b> rather than a single state-wide target<br>
        3. &nbsp;Track complaint rates <i>alongside</i> OTR — ROM's higher complaint rate signals
               rider frustration that headline punctuality figures don't reveal
    </p>
</div>
""", unsafe_allow_html=True)
st.markdown("<div class='section-header'> Layer 4 — Real time alerts </div>", unsafe_allow_html=True)
data = fetch_bus_alerts(API_KEY)

#Find usable stats from data
for entity in data:
    with st.expander(f"Alert: {entity['header'][:100]}..."):
        st.write(f"**Description:** {entity['desc']}")
        
        # Routes Affected
        st.markdown("---")
        st.subheader("Affected Services")
        for route_id in entity['route_ids']:
            short, long = find_route_name(route_id)
            st.info(f"**Route {short}:** {long}")
        for stop_id in entity['stop_ids']:
            st.info(f"**Stop: {find_stop_name(stop_id)}**")
        # Dates
        for period in entity['active_periods']:
            start = datetime.fromtimestamp(period['start']).strftime('%Y-%m-%d %H:%M') if period['start'] else "Unknown"
            end = datetime.fromtimestamp(period['end']).strftime('%Y-%m-%d %H:%M') if period['end'] else "Until further notice"
            st.caption(f"📅 Active from {start} to {end}")


# Footer
st.markdown("""
<br>
<div style='color:#aaa; font-size:12px; text-align:center; padding-bottom:20px'>
    Data: Transport for NSW Bus Performance Reports & Opal Trip Data (2024–2026) &nbsp;|&nbsp;
    MDSI DVN Assignment 3 &nbsp;
</div>
""", unsafe_allow_html=True)
