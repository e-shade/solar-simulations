import streamlit as st
import requests
import pandas as pd
import numpy as np
import pvlib
import plotly.express as px
import os
import pickle

# --- CONFIGURATION ---
CACHE_FILE = "pv_data_cache.pkl"
BASE_URL = "https://developer.nlr.gov/api/pvwatts/v8.json"
API_KEY = '6UGQKK7Q3p4pEKZXbbvYEnYXzAegBJnzm3vNss38' 

# --- CACHING LOGIC ---
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)

# Initialize Cache
if 'db' not in st.session_state:
    st.session_state.db = load_cache()

# --- PAGE CONFIG ---
st.set_page_config(page_title="PV Window Optimizer", layout="wide")
st.title("☀️ Interactive Window PV Harvester")

# --- SIDEBAR GUI ---
st.sidebar.header("System Parameters")
window_w = st.sidebar.slider("Window Width (mm)", 500, 2000, 1000)
window_h = st.sidebar.slider("Window Height (mm)", 500, 2000, 1000)
eff = st.sidebar.slider("Cell Efficiency (E)", 0.10, 0.30, 0.22)
alpha = st.sidebar.slider("Azimuth (180=South)", 0, 359, 180)
ir_loss_const = st.sidebar.slider("IR Cut Coating Loss", 0.0, 0.50, 0.15)

st.sidebar.header("PV Border Geometry (mm)")
t_bw = st.sidebar.number_input("Top Border", value=25)
b_bw = st.sidebar.number_input("Bottom Border", value=30)
lr_bw = st.sidebar.number_input("Left/Right Border", value=25)

selected_month = st.sidebar.select_slider("Select Month for Map", 
    options=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])

# --- CALCULATIONS ---
# Geometric Area in m^2
top_a = window_w * t_bw / 100
bot_a = window_w * b_bw / 100
side_a = (window_h - t_bw - b_bw) * lr_bw / 100 * 2
total_area_m2 = (top_a + bot_a + side_a) / 10000

us_states = {
    "AL": (32.31, -86.90, "Alabama"), "AK": (61.37, -152.40, "Alaska"), "AZ": (33.44, -112.07, "Arizona"),
    "AR": (34.74, -92.28, "Arkansas"), "CA": (36.77, -119.41, "California"), "CO": (39.55, -104.85, "Colorado"),
    "CT": (41.60, -73.08, "Connecticut"), "DE": (38.91, -75.52, "Delaware"), "FL": (27.66, -81.51, "Florida"),
    "GA": (32.16, -82.90, "Georgia"), "HI": (19.89, -155.58, "Hawaii"), "ID": (44.06, -114.74, "Idaho"),
    "IL": (40.63, -89.39, "Illinois"), "IN": (40.26, -86.12, "Indiana"), "IA": (41.87, -93.09, "Iowa"),
    "KS": (38.52, -96.72, "Kansas"), "KY": (37.83, -84.27, "Kentucky"), "LA": (30.98, -91.96, "Louisiana"),
    "ME": (45.25, -69.44, "Maine"), "MD": (39.04, -76.64, "Maryland"), "MA": (42.40, -71.38, "Massachusetts"),
    "MI": (44.31, -85.60, "Michigan"), "MN": (46.72, -94.68, "Minnesota"), "MS": (32.74, -89.67, "Mississippi"),
    "MO": (37.96, -91.83, "Missouri"), "MT": (46.87, -110.36, "Montana"), "NE": (41.49, -99.90, "Nebraska"),
    "NV": (38.50, -117.02, "Nevada"), "NH": (43.19, -71.57, "New Hampshire"), "NJ": (40.05, -74.40, "New Jersey"),
    "NM": (34.51, -105.87, "New Mexico"), "NY": (43.00, -75.00, "New York"), "NC": (35.75, -79.01, "North Carolina"),
    "ND": (47.55, -101.00, "North Dakota"), "OH": (40.41, -82.90, "Ohio"), "OK": (35.00, -98.00, "Oklahoma"),
    "OR": (43.80, -120.55, "Oregon"), "PA": (41.20, -77.19, "Pennsylvania"), "RI": (41.58, -71.47, "Rhode Island"),
    "SC": (33.83, -81.16, "South Carolina"), "SD": (44.36, -100.35, "South Dakota"), "TN": (35.51, -86.58, "Tennessee"),
    "TX": (31.96, -99.90, "Texas"), "UT": (39.32, -111.09, "Utah"), "VT": (44.00, -72.70, "Vermont"),
    "VA": (37.43, -78.65, "Virginia"), "WA": (47.75, -120.74, "Washington"), "WV": (38.59, -80.45, "West Virginia"),
    "WI": (43.78, -88.78, "Wisconsin"), "WY": (43.07, -107.29, "Wyoming")
}

def get_psh_data_cached(lat, lon, alpha):
    key = f"{lat}_{lon}_{alpha}"
    if key in st.session_state.db:
        return st.session_state.db[key]
    
    # Network fallback
    params = {'api_key': API_KEY, 'lat': lat, 'lon': lon, 'system_capacity': 1.0, 
              'azimuth': alpha, 'tilt': 90, 'array_type': 1, 'module_type': 0, 'losses': 0}
    try:
        r = requests.get(BASE_URL, params=params).json()
        data = r['outputs']['solrad_monthly']
        st.session_state.db[key] = data
        save_cache(st.session_state.db)
        return data
    except:
        return [0]*12

def get_physics_mod(lat, lon, month_idx, alpha):
    # Using lowercase 'h' for modern pandas compatibility
    times = pd.date_range(f'2026-{month_idx+1:02d}-15', periods=24, freq='h', tz='UTC')
    solpos = pvlib.solarposition.get_solarposition(times, lat, lon)
    aoi = pvlib.irradiance.aoi(90, alpha, solpos['zenith'], solpos['azimuth'])
    iam = pvlib.iam.physical(aoi)
    mask = (solpos['elevation'] > 0) & (aoi < 90)
    return iam[mask].mean() if mask.any() else 0.1

# --- PROCESSING ---
month_map = {"Jan":0,"Feb":1,"Mar":2,"Apr":3,"May":4,"Jun":5,"Jul":6,"Aug":7,"Sep":8,"Oct":9,"Nov":10,"Dec":11}
m_idx = month_map[selected_month]

data_rows = []
progress_text = "Updating Map..."
my_bar = st.progress(0, text=progress_text)

for i, (code, (lat, lon, name)) in enumerate(us_states.items()):
    psh_list = get_psh_data_cached(lat, lon, alpha)
    psh = psh_list[m_idx]
    phys_mod = get_physics_mod(lat, lon, m_idx, alpha)
    
    # Energy Logic
    raw_wh = (psh * 1000) * total_area_m2 * eff
    aoi_loss = raw_wh * (1 - phys_mod)
    final_wh = (raw_wh - aoi_loss) * (1 - ir_loss_const)
    
    data_rows.append({"State": code, "Full Name": name, "Final Wh": round(final_wh, 2)})
    my_bar.progress((i + 1) / len(us_states))

my_bar.empty()
df = pd.DataFrame(data_rows)

# --- UI LAYOUT ---
c1, c2 = st.columns([3, 1])

with c1:
    fig = px.choropleth(df, 
        locations='State', 
        locationmode="USA-states", 
        color='Final Wh',
        scope="usa",
        hover_name="Full Name",
        title=f"Daily Average Harvest (Wh) - {selected_month}",
        color_continuous_scale="Plasma",
        labels={'Final Wh':'Wh/Day'})
    fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.metric("Total PV Area", f"{total_area_m2:.4f} m²")
    st.metric("Peak Potential (US)", f"{df['Final Wh'].max()} Wh")
    st.write("#### Performance Leaderboard")
    st.table(df.sort_values("Final Wh", ascending=False).head(8)[["Full Name", "Final Wh"]])

st.caption("Calculations include: STC Efficiency, Cosine Angle, Fresnel Reflection (Glass), and Spectral IR Filtering.")