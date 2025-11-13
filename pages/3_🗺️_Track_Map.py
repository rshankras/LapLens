"""
Track Map Page
GPS-based track visualization with speed heatmaps.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.gps_processor import create_gps_track_visualization, calculate_track_statistics
from utils.visualizations import format_lap_time
from config import config

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title=f"{config.PAGE_TITLE} - Track Map",
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT
)

# =============================================================================
# CHECK SESSION STATE
# =============================================================================

if 'processed_data' not in st.session_state or st.session_state.processed_data is None:
    st.warning("⚠️ No data loaded. Please return to the Home page and load a dataset first.")
    st.stop()

# Get data from session state
processed_data = st.session_state.processed_data
telemetry = processed_data['telemetry']
lap_times = processed_data['lap_times']

# Get selected vehicle and track
vehicle_id = st.session_state.get('selected_vehicle', 'Unknown Vehicle')
track_name = st.session_state.get('track_name', 'Unknown Track')

# =============================================================================
# HEADER
# =============================================================================

st.title("🗺️ Track Map")
st.markdown(f"### 🏎️ Vehicle: **{vehicle_id}** | 🏁 Track: **{track_name}**")
st.markdown("GPS-based track visualization with performance heatmaps")

st.divider()

# Check if GPS data is available
has_gps = 'VBOX_Lat_Min' in telemetry.columns and 'VBOX_Long_Minutes' in telemetry.columns

if not has_gps:
    st.error("❌ GPS data not available in this dataset. Track map visualization requires GPS coordinates.")
    st.info("💡 GPS data is available in the Toyota GR Cup telemetry datasets. Make sure you've loaded a dataset with GPS telemetry.")
    st.stop()

# =============================================================================
# VISUALIZATION OPTIONS
# =============================================================================

st.header("🎨 Visualization Options")

col1, col2, col3 = st.columns(3)

with col1:
    # Visualization mode
    viz_mode = st.radio(
        "Mode:",
        options=["Full Session", "Specific Laps", "Best Lap"],
        index=0
    )

with col2:
    # Color by
    available_color_metrics = ['Speed']
    if 'brake_intensity' in telemetry.columns:
        available_color_metrics.append('brake_intensity')
    if 'ath' in telemetry.columns:
        available_color_metrics.append('ath')

    color_by = st.selectbox(
        "Color by:",
        options=available_color_metrics,
        index=0
    )

with col3:
    # Show start/finish
    show_start_finish = st.checkbox("Show Start/Finish", value=True)

# Lap selection for specific laps mode
selected_laps = None
if viz_mode == "Specific Laps":
    available_laps = sorted(telemetry['lap'].unique())
    selected_laps = st.multiselect(
        "Select laps to compare (up to 5):",
        options=available_laps,
        default=[available_laps[0]] if len(available_laps) > 0 else [],
        max_selections=5
    )
elif viz_mode == "Best Lap":
    if len(lap_times) > 0:
        best_lap_num = lap_times.loc[lap_times['lap_time'].idxmin(), 'lap']
        selected_laps = [int(best_lap_num)]
        st.info(f"📊 Showing best lap: Lap {int(best_lap_num)} ({format_lap_time(lap_times['lap_time'].min())})")

st.divider()

# =============================================================================
# TRACK MAP VISUALIZATION
# =============================================================================

st.header("🗺️ GPS Track Visualization")

# Prepare data for visualization
if viz_mode == "Full Session":
    viz_telemetry = telemetry
elif selected_laps is not None and len(selected_laps) > 0:
    viz_telemetry = telemetry[telemetry['lap'].isin(selected_laps)]
else:
    st.warning("⚠️ Please select at least one lap to visualize.")
    st.stop()

# Create visualization
with st.spinner("Generating track map..."):
    track_fig = create_gps_track_visualization(
        telemetry=viz_telemetry,
        laps=selected_laps if viz_mode == "Specific Laps" else None,
        color_by=color_by,
        show_start_finish=show_start_finish
    )

st.plotly_chart(track_fig, width='stretch')

# =============================================================================
# TRACK STATISTICS
# =============================================================================

st.divider()
st.header("📊 Track Statistics")

col1, col2, col3, col4 = st.columns(4)

track_stats = calculate_track_statistics(telemetry)

if track_stats:
    with col1:
        st.metric(
            "Track Width",
            f"{track_stats.get('track_width_m', 0):.0f}m"
        )

    with col2:
        st.metric(
            "Track Length",
            f"{track_stats.get('track_height_m', 0):.0f}m"
        )

    with col3:
        if 'Speed' in telemetry.columns:
            st.metric(
                "Max Speed",
                f"{telemetry['Speed'].max():.1f} km/h"
            )

    with col4:
        if 'Speed' in telemetry.columns:
            st.metric(
                "Avg Speed",
                f"{telemetry['Speed'].mean():.1f} km/h"
            )

# =============================================================================
# TRACK INSIGHTS
# =============================================================================

st.divider()
st.header("💡 Track Insights")

insights = []

# Speed analysis
if 'Speed' in viz_telemetry.columns:
    max_speed = viz_telemetry['Speed'].max()
    min_speed = viz_telemetry['Speed'].min()
    speed_range = max_speed - min_speed

    insights.append(f"🏎️ **Speed Range:** {min_speed:.1f} - {max_speed:.1f} km/h (range: {speed_range:.1f} km/h)")

# Braking analysis
if 'brake_intensity' in viz_telemetry.columns:
    heavy_braking_points = (viz_telemetry['brake_intensity'] > config.HEAVY_BRAKE_THRESHOLD).sum()
    braking_pct = (heavy_braking_points / len(viz_telemetry)) * 100

    insights.append(f"🔴 **Heavy Braking:** {heavy_braking_points:,} data points ({braking_pct:.1f}% of track)")

# Throttle analysis
if 'ath' in viz_telemetry.columns:
    full_throttle_points = (viz_telemetry['ath'] > config.THROTTLE_FULL_THRESHOLD).sum()
    throttle_pct = (full_throttle_points / len(viz_telemetry)) * 100

    insights.append(f"🟢 **Full Throttle:** {full_throttle_points:,} data points ({throttle_pct:.1f}% of track)")

# GPS data points
insights.append(f"📍 **GPS Data Points:** {len(viz_telemetry):,} telemetry records")

# Display insights
for insight in insights:
    st.markdown(f"- {insight}")

# =============================================================================
# TRACK MAP REFERENCE
# =============================================================================

st.divider()
st.header("📸 Official Track Map Reference")

track_map_file = None
track_name_lower = track_name.lower()

# Map track names to files
track_map_mapping = {
    'barber': 'Barber_Circuit_Map.pdf',
    'cota': 'COTA_Circuit_Map.pdf',
    'circuit of the americas': 'COTA_Circuit_Map.pdf',
    'indianapolis': 'Indy_Circuit_Map.pdf',
    'road america': 'Road_America_Map.pdf',
    'sebring': 'Sebring_Track_Sector_Map.pdf',
    'sonoma': 'Sonoma_Map.pdf',
    'virginia': 'VIR_map.pdf',
    'vir': 'VIR_map.pdf'
}

for key, filename in track_map_mapping.items():
    if key in track_name_lower:
        track_map_file = Path('trackmaps') / filename
        break

if track_map_file and track_map_file.exists():
    st.info(f"📄 Official track map available: `{track_map_file.name}`")
    st.markdown(f"*Track maps are reference diagrams showing the official circuit layout. The GPS visualization above shows your actual driving line.*")

    # Offer download
    with open(track_map_file, 'rb') as f:
        st.download_button(
            label="📥 Download Official Track Map (PDF)",
            data=f,
            file_name=track_map_file.name,
            mime="application/pdf",
            type="secondary"
        )
else:
    st.info("📄 Official track map not available for this circuit.")

# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>
        💡 Tip: Use the track map to identify fast/slow corners, braking zones, and racing line consistency.<br>
        Compare multiple laps to see where you gained or lost time visually.
    </small>
</div>
""", unsafe_allow_html=True)
