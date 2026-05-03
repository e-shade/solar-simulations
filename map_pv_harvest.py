import streamlit as st
import requests
import pandas as pd
import numpy as np
import pvlib
import plotly.express as px
import plotly.graph_objects as go
import os
import pickle

# --- CONFIGURATION ---
CACHE_FILE = "pv_data_cache.pkl"
BASE_URL = "https://developer.nlr.gov/api/pvwatts/v8.json"
API_KEY = '6UGQKK7Q3p4pEKZXbbvYEnYXzAegBJnzm3vNss38' 

STC_IRRADIANCE = 1000  # Standard Test Condition solar irradiance (W/m^2)

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

# --- UI COMPRESSION (CSS) ---
st.markdown("""
    <style>
    /* Reduce top padding of the main container */
    .block-container {
        padding-top: 1rem;
    }
    /* Widen the sidebar to accommodate two columns of controls */
    [data-testid="stSidebar"] {
        min-width: 580px !important;
    }
    /* Reduce vertical gaps in the sidebar widgets */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.5rem !important;
    }
    /* Specifically target slider containers to reduce bottom margin */
    div[data-testid="stSlider"] {
        margin-bottom: -18px;
    }
    /* Reduce spacing for headers in sidebar */
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        padding-top: 0.5rem;
        padding-bottom: 1.2rem;
    }
    /* Change the color of the metric labels */
    [data-testid="stMetricLabel"] {
        color: #6c757d !important;
        font-size: 0.75rem !important;
    }
    /* Change the color of the metric values */
    [data-testid="stMetricValue"] > div {
        color: #FF4B4B;
        font-size: 1.0rem !important;
    }
    /* Center LaTeX equations */
    .katex-display {
        text-align: center !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("☀️ Interactive Window PV Harvester")
st.caption("Calculations include: STC Efficiency, Cosine Angle, Fresnel Reflection (Glass), and Spectral IR Filtering.")

# --- SIDEBAR GUI ---
with st.sidebar:
    sb_col1, sb_col2 = st.columns(2)
    
    with sb_col1:

        st.header("Window Geometry")
        window_w = st.slider("Width (mm)", 100, 2000, 1000, step=100)
        window_h = st.slider("Height (mm)", 100, 2000, 1000, step=100)
        t_bw = st.slider("Top Border Height (mm)", 10, 100, 25)
        b_bw = st.slider("Bottom Border Height (mm)", 10, 100, 30)
        lr_bw = st.slider("Side Borders Width (mm)", 0, 100, 25)
        tb_thickness = st.slider("Top and Bottom Thickness (mm)", 5, 20, 10)
        batt_loc = st.radio("Battery Location", ["Bottom Only", "Top & Bottom"], index=1)

        st.header("Glass Properties")
        glass_thickness = st.slider("Thickness (mm)", 1.0, 10.0, 2.0, step=0.5)
        glass_extinction = st.slider("Extinction (K)", 1.0, 32.0, 4.0, step=1.0)

    with sb_col2:
        alpha = st.slider("Window Orientation (Azimuth) [0°=N, 180°=S]", 0, 359, 180)
        
        selected_month = st.select_slider("Month Selector", 
            options=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], value="Jun")

        st.header("System Params")
        film_power_consumption = st.slider("Film Power (W/sqm)", 1, 20, 2)
        active_hours_per_day = st.slider("Active Hours", 1, 24, 8)
        lipoly_energy_density = st.slider("Bat Density (Wh/L)", 200, 600, 350)
        eff = st.slider("Cell Efficiency (E)", 0.10, 0.30, 0.22)
        ir_loss_const = st.slider("IR Blocking Loss", 0.0, 0.50, 0.15)
        soiling_loss = st.slider("Soiling/Dirt Loss (%)", 0, 10, 2)
        system_loss = st.slider("Electrical Losses (%)", 0, 30, 10)

# --- CALCULATIONS ---
# 1. Areas in mm^2
top_area_mm2 = window_w * t_bw
bot_area_mm2 = window_w * b_bw
side_area_mm2 = (window_h - t_bw - b_bw) * lr_bw * 2

# 2. Total PV Area in m^2 (for solar harvest logic)
total_area_m2 = (top_area_mm2 + bot_area_mm2 + side_area_mm2) / 1_000_000

# 3. Battery Volume Logic (Corrected Units)
# Calculate active area used for battery storage based on user selection
if batt_loc == "Bottom Only":
    batt_area_mm2 = bot_area_mm2
else:
    batt_area_mm2 = top_area_mm2 + bot_area_mm2

total_vol_mm3 = batt_area_mm2 * tb_thickness
# Convert mm^3 to Liters: (1 L = 1,000,000 mm^3)
total_battery_volume_l = total_vol_mm3 / 1_000_000
total_battery_capacity_wh = total_battery_volume_l * lipoly_energy_density

# 4. Film Power Consumption (for reference, not used in map)
total_film_area_m2 = (window_w * window_h) / 1_000_000
film_power_consumption_w = total_film_area_m2 * film_power_consumption
film_total_daily_consumption_wh = film_power_consumption_w * active_hours_per_day

# --- STATE DATA ---
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
    
    params = {'api_key': API_KEY, 'lat': lat, 'lon': lon, 'system_capacity': 1.0, 
              'azimuth': alpha, 'tilt': 90, 'array_type': 0, 'module_type': 0, 'losses': 0}
    try:
        r = requests.get(BASE_URL, params=params).json()
        data = r['outputs']['solrad_monthly']
        st.session_state.db[key] = data
        return data
    except:
        return [0]*12

@st.cache_data
def get_physics_mod(lat, lon, month_idx, alpha, K, L_mm):
    L_m = L_mm / 1000.0  # Convert mm to meters for pvlib
    times = pd.date_range(f'2026-{month_idx+1:02d}-15', periods=24, freq='h', tz='UTC')
    solpos = pvlib.solarposition.get_solarposition(times, lat, lon)
    aoi = pvlib.irradiance.aoi(90, alpha, solpos['zenith'], solpos['azimuth'])
    
    # Calculate detailed components for hover data
    n = 1.526 # Refractive index of glass
    theta = np.radians(aoi)
    # Snell's Law for internal angle
    theta_r = np.arcsin(np.sin(theta) / n)
    
    # Fresnel Reflection
    # Handle normal incidence (0°) to avoid division by zero
    refl_normal = ((n - 1) / (n + 1))**2
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = np.sin(theta_r - theta) / np.sin(theta_r + theta)
        rp = np.tan(theta_r - theta) / np.tan(theta_r + theta)
        tau_refl = 1 - 0.5 * (rs**2 + rp**2)
        tau_refl = np.where(aoi == 0, 1 - refl_normal, tau_refl)

    # Beer-Lambert Absorption
    tau_abs = np.exp(-K * (L_m) / np.cos(theta_r))
    
    # Calculate normalized modifier: F(theta) = T(theta) / T(0)
    t_0 = (1 - refl_normal) * np.exp(-K * L_m)
    iam = (tau_refl * tau_abs) / t_0
    
    mask = (solpos['elevation'] > 0) & (aoi < 90)
    if not mask.any():
        return 0.1, 0.0, 0.0
    return iam[mask].mean(), (1 - tau_refl[mask]).mean() * 100, (1 - tau_abs[mask]).mean() * 100

# --- PROCESSING ---
tab1, tab2, tab3, tab4 = st.tabs(["Interactive Map", "Window Geometry", "Monthly Sufficiency", "Technical Reference"])

with tab1:
    # Create progress bar at the top of the tab for maximum visibility
    my_bar = st.progress(0, text="Preparing simulation...")

    c1, c2 = st.columns([5, 1])

    with c1:
        map_container = st.container() # This container will hold the map

    month_map = {"Jan":0,"Feb":1,"Mar":2,"Apr":3,"May":4,"Jun":5,"Jul":6,"Aug":7,"Sep":8,"Oct":9,"Nov":10,"Dec":11}
    m_idx = month_map[selected_month]
    data_rows = []

    for i, (code, (lat, lon, name)) in enumerate(us_states.items()):
        psh_list = get_psh_data_cached(lat, lon, alpha)
        psh = psh_list[m_idx]
        phys_mod, f_loss, a_loss = get_physics_mod(lat, lon, m_idx, alpha, glass_extinction, glass_thickness)
        raw_wh = (psh * STC_IRRADIANCE) * total_area_m2 * eff
        # Combine all derate factors: IAM * IR Loss * Soiling * System
        final_wh = raw_wh * phys_mod * (1 - ir_loss_const) * (1 - soiling_loss/100) * (1 - system_loss/100)
        status = "Insufficient" if final_wh < film_total_daily_consumption_wh else "Sufficient"
        data_rows.append({"State": code, "Full Name": name, "Final Wh": round(final_wh, 2), "Status": status, 
                          "PSH": round(psh, 2), "Fresnel Loss": round(f_loss, 2), "Absorption": round(a_loss, 2)})
        # Update progress and show current state name to user
        my_bar.progress((i + 1) / len(us_states), text=f"Processing {name}...")

    # Save cache to disk once after batch processing is complete
    save_cache(st.session_state.db)
    my_bar.empty()
    df = pd.DataFrame(data_rows)

    # --- FILL UI LAYOUT ---
    with map_container:
        # Calculate dynamic color scale centered at the consumption threshold
        min_val_df = df['Final Wh'].min()
        max_val_df = df['Final Wh'].max()
        
        diff = max_val_df - min_val_df
        if diff <= 0:
            z_mid = 0.5
        else:
            z_mid = (film_total_daily_consumption_wh - min_val_df) / diff
            z_mid = np.clip(z_mid, 0, 1)

        custom_scale = [
            [0, "#FF4B4B"],      # Insufficient (Red)
            [z_mid, "#f0f0f0"],  # Threshold (Neutral Gray/White)
            [1, "#09ab3b"]       # Sufficient (Green)
        ]

        fig = px.choropleth(df, 
            locations='State', 
            locationmode="USA-states", 
            color='Final Wh',
            scope="usa",
            hover_name="Full Name",
            hover_data={"Status": True, "Final Wh": ":.2f", "PSH": ":.2f", 
                        "Fresnel Loss": ":.2f", "Absorption": ":.2f", "State": False},
            title=f"Daily Average Harvest (Wh) - {selected_month}",
            color_continuous_scale=custom_scale,
            labels={'Final Wh':'Wh/Day', 'PSH': 'Peak Sun Hours', 
                    'Fresnel Loss': 'Fresnel Loss (%)', 'Absorption': 'Absorption (%)'})
        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig, width='stretch')

    with c2:
        min_val = df['Final Wh'].min()
        status_color = "#09ab3b" if min_val > film_total_daily_consumption_wh else "#FF4B4B"
        st.markdown(f"""
            <style>
            div[data-testid="stMetric"]:nth-of-type(6) [data-testid="stMetricValue"] > div {{
                color: {status_color} !important;
            }}
            </style>
        """, unsafe_allow_html=True)

        st.metric("Total PV Area", f"{total_area_m2:.4f} m²")
        st.metric("Battery Capacity", f"{total_battery_capacity_wh:.3f} Wh")
        st.metric("Battery Autonomy", f"{total_battery_capacity_wh/film_total_daily_consumption_wh:.1f} Days")
        st.metric("Film Power Consumption", f"{film_power_consumption_w:.3f} W")
        st.metric("Film Daily Energy", f"{film_total_daily_consumption_wh:.3f} Wh")
        st.metric("Peak Daily Harvesting Potential (US)", f"{df['Final Wh'].max():.3f} Wh")
        st.metric("Minimum Daily Harvesting Potential (US)", f"{min_val:.3f} Wh")
        # st.write("#### Bottom 8 States (Min Production)")
        # st.table(df.sort_values("Final Wh", ascending=True).head(8)[["Full Name", "Final Wh"]])

with tab2:
    st.header("Window Design Visualization")
    # 2D Window Drawing (Scaled)
    fig_win = go.Figure()
    
    # White Outer Frame (40mm wide, placed behind)
    frame_w = 40
    fig_win.add_shape(type="rect", x0=-frame_w, y0=-frame_w, x1=window_w+frame_w, y1=window_h+frame_w,
                      fillcolor="white", line=dict(width=0))

    # Draw PV Border Area (Dark Grey)
    fig_win.add_shape(type="rect", x0=0, y0=0, x1=window_w, y1=window_h,
                      fillcolor="#444444", line=dict(width=0))
    # Draw PDLC Active Film Area (Light Blue)
    fig_win.add_shape(type="rect", x0=lr_bw, y0=b_bw, x1=window_w-lr_bw, y1=window_h-t_bw,
                      fillcolor="#87CEEB", line=dict(width=0))

    # Add Dimension Labels
    # Overall Dimensions (Outer)
    fig_win.add_annotation(x=window_w/2, y=40+t_bw, text=f"Width:  {window_w} mm", showarrow=False, font=dict(color="black", size=14))
    fig_win.add_annotation(x=30+lr_bw, y=window_h/2, text=f"Height: {window_h} mm", textangle=-90, showarrow=False, font=dict(color="black", size=14))

    # Border Dimensions (Inner)
    fig_win.add_annotation(x=window_w/2, y=window_h - t_bw/2, text=f"Top: {t_bw}mm", showarrow=False, font=dict(color="white", size=10))
    fig_win.add_annotation(x=window_w/2, y=b_bw/2, text=f"Bottom: {b_bw}mm", showarrow=False, font=dict(color="white", size=10))
    fig_win.add_annotation(x=lr_bw/2, y=window_h/2, text=f"{lr_bw}mm", textangle=-90, showarrow=False, font=dict(color="white", size=10))
    fig_win.add_annotation(x=window_w - lr_bw/2, y=window_h/2, text=f"{lr_bw}mm", textangle=-90, showarrow=False, font=dict(color="white", size=10))

    fig_win.update_layout(
        xaxis=dict(visible=False, range=[-110, window_w+110]),
        yaxis=dict(visible=False, range=[-110, window_h+110], scaleanchor="x", scaleratio=1),
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        autosize=True
    )
    st.plotly_chart(fig_win, width='stretch', config={'displayModeBar': False})

with tab3:
    st.header("Monthly Harvesting Sufficiency")
    show_values = st.toggle("Show raw Watt-hour values", value=False)
    st.caption("🟩/Green = Sufficient harvest | 🟥/Red = Insufficient harvest")
    
    # This matrix calculation involves 600 data points (50 states * 12 months)
    with st.spinner("Calculating annual sufficiency matrix..."):
        months_list = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        matrix_rows = []
        for code, (lat, lon, name) in us_states.items():
            state_row = {"State": name}
            psh_list = get_psh_data_cached(lat, lon, alpha)
            for m_i, m_name in enumerate(months_list):
                p_mod, _, _ = get_physics_mod(lat, lon, m_i, alpha, glass_extinction, glass_thickness)
                m_psh = psh_list[m_i]
                m_raw_wh = (m_psh * STC_IRRADIANCE) * total_area_m2 * eff
                m_final_wh = m_raw_wh * p_mod * (1 - ir_loss_const) * (1 - soiling_loss/100) * (1 - system_loss/100)
                
                # Determine status icon or numerical value
                if show_values:
                    state_row[m_name] = round(m_final_wh, 3)
                else:
                    state_row[m_name] = "🟩" if m_final_wh >= film_total_daily_consumption_wh else "🟥"
            matrix_rows.append(state_row)
        
        matrix_df = pd.DataFrame(matrix_rows)

        # Use a large height to ensure all states are visible without nested scrollbars
        if show_values:
            styled_df = matrix_df.style.map(
                lambda v: f"color: {'#09ab3b' if v >= film_total_daily_consumption_wh else '#FF4B4B'}",
                subset=months_list
            ).format("{:.3f}", subset=months_list)
            st.dataframe(styled_df, width='stretch', hide_index=True, height=800)
        else:
            st.dataframe(matrix_df, width='stretch', hide_index=True, height=800)

with tab4:
    help_path = os.path.join(os.path.dirname(__file__), "help.md")
    if os.path.exists(help_path):
        with open(help_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.error("Help file not found.")