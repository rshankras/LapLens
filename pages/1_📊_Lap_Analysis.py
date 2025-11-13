"""
Lap Analysis Page
Detailed telemetry analysis and visualization for individual laps.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.visualizations import (
    create_lap_time_chart,
    create_sector_delta_chart,
    create_speed_trace_chart,
    create_telemetry_comparison_chart,
    create_multi_telemetry_chart,
    format_lap_time
)
from config import config

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title=f"{config.PAGE_TITLE} - Lap Analysis",
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
sector_times = processed_data['sector_times']

# Get selected vehicle and track
vehicle_id = st.session_state.get('selected_vehicle', 'Unknown Vehicle')
track_name = st.session_state.get('track_name', 'Unknown Track')

# =============================================================================
# HEADER
# =============================================================================

st.title("📊 Lap Analysis")
st.markdown(f"### 🏎️ Vehicle: **{vehicle_id}** | 🏁 Track: **{track_name}**")
st.markdown("Detailed telemetry insights and performance metrics")

st.divider()

# =============================================================================
# SECTION 1: LAP TIME CHART
# =============================================================================

st.header("Lap Time Progression")

if len(lap_times) > 0:
    # Create lap time chart
    lap_chart = create_lap_time_chart(lap_times, highlight_best=True)
    st.plotly_chart(lap_chart, width='stretch')

    # Quick stats below the chart
    col1, col2, col3 = st.columns(3)

    with col1:
        fastest_lap = lap_times.loc[lap_times['lap_time'].idxmin()]
        st.metric(
            "Fastest Lap",
            f"Lap {int(fastest_lap['lap'])}",
            format_lap_time(fastest_lap['lap_time'])
        )

    with col2:
        slowest_lap = lap_times.loc[lap_times['lap_time'].idxmax()]
        st.metric(
            "Slowest Lap",
            f"Lap {int(slowest_lap['lap'])}",
            format_lap_time(slowest_lap['lap_time'])
        )

    with col3:
        delta = slowest_lap['lap_time'] - fastest_lap['lap_time']
        st.metric(
            "Lap Time Range",
            f"{delta:.3f}s",
            f"{(delta / fastest_lap['lap_time'] * 100):.1f}%"
        )

else:
    st.warning("No lap time data available.")

st.divider()

# =============================================================================
# SECTION 2: SECTOR ANALYSIS
# =============================================================================

st.header("Sector Analysis")

if len(sector_times) > 0:
    # Lap selector for sector analysis
    available_laps = sorted(sector_times['lap'].unique())

    selected_lap_sector = st.selectbox(
        "Select a lap to view sector breakdown:",
        options=available_laps,
        index=0,
        key='sector_lap_selector'
    )

    # Create sector delta chart
    sector_chart = create_sector_delta_chart(sector_times, selected_lap_sector)
    st.plotly_chart(sector_chart, width='stretch')

    # Sector times table
    lap_sector_data = sector_times[sector_times['lap'] == selected_lap_sector].sort_values('sector')

    if len(lap_sector_data) > 0:
        st.subheader(f"Sector Times - Lap {selected_lap_sector}")

        # Format sector data for display
        sector_display = lap_sector_data[['sector', 'sector_time', 'delta_to_best', 'avg_speed']].copy()
        sector_display['sector_time_formatted'] = sector_display['sector_time'].apply(format_lap_time)
        sector_display['delta_formatted'] = sector_display['delta_to_best'].apply(
            lambda x: f"+{x:.3f}s" if x > 0 else f"{x:.3f}s" if x < 0 else "0.000s (BEST)"
        )

        sector_display = sector_display.rename(columns={
            'sector': 'Sector',
            'sector_time_formatted': 'Time',
            'delta_formatted': 'Delta to Best',
            'avg_speed': 'Avg Speed (km/h)'
        })

        st.dataframe(
            sector_display[['Sector', 'Time', 'Delta to Best', 'Avg Speed (km/h)']],
            width='stretch',
            hide_index=True
        )

else:
    st.warning("No sector data available.")

st.divider()

# =============================================================================
# SECTION 3: SPEED VS DISTANCE
# =============================================================================

st.header("Speed Trace")

if 'Speed' in telemetry.columns and 'Laptrigger_lapdist_dls' in telemetry.columns:
    # Lap selector for speed trace
    available_laps_telem = sorted(telemetry['lap'].unique())

    col1, col2 = st.columns([3, 1])

    with col1:
        selected_laps_speed = st.multiselect(
            "Select laps to compare (up to 3):",
            options=available_laps_telem,
            default=[available_laps_telem[0]] if len(available_laps_telem) > 0 else [],
            max_selections=3,
            key='speed_lap_selector'
        )

    with col2:
        show_zones = st.checkbox("Show braking zones", value=True, key='show_zones')

    if selected_laps_speed:
        # Create speed trace chart
        speed_chart = create_speed_trace_chart(telemetry, selected_laps_speed, show_zones=show_zones)
        st.plotly_chart(speed_chart, width='stretch')

        # Speed statistics for selected laps
        st.subheader("Speed Statistics")

        speed_stats = []
        for lap_num in selected_laps_speed:
            lap_data = telemetry[telemetry['lap'] == lap_num]
            if len(lap_data) > 0:
                speed_stats.append({
                    'Lap': lap_num,
                    'Avg Speed (km/h)': lap_data['Speed'].mean(),
                    'Max Speed (km/h)': lap_data['Speed'].max(),
                    'Min Speed (km/h)': lap_data['Speed'].min(),
                    'Speed Range (km/h)': lap_data['Speed'].max() - lap_data['Speed'].min()
                })

        if speed_stats:
            speed_df = pd.DataFrame(speed_stats)
            st.dataframe(speed_df, width='stretch', hide_index=True)

    else:
        st.info("Select at least one lap to view speed trace.")

else:
    st.warning("Speed or distance data not available in telemetry.")

st.divider()

# =============================================================================
# SECTION 4: TELEMETRY COMPARISON
# =============================================================================

st.header("Telemetry Comparison")

if len(telemetry) > 0:
    available_laps_comp = sorted(telemetry['lap'].unique())

    # Lap selectors
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        lap1 = st.selectbox(
            "Lap 1:",
            options=available_laps_comp,
            index=0,
            key='telemetry_lap1'
        )

    with col2:
        lap2 = st.selectbox(
            "Lap 2:",
            options=available_laps_comp,
            index=min(1, len(available_laps_comp) - 1),
            key='telemetry_lap2'
        )

    with col3:
        # Metric selector
        available_metrics = []
        metric_labels = {
            'ath': 'Throttle Position',
            'brake_intensity': 'Brake Intensity',
            'pbrake_f': 'Front Brake Pressure',
            'pbrake_r': 'Rear Brake Pressure',
            'Steering_Angle': 'Steering Angle',
            'accx_can': 'Longitudinal G-Force',
            'accy_can': 'Lateral G-Force'
        }

        for metric, label in metric_labels.items():
            if metric in telemetry.columns:
                available_metrics.append((label, metric))

        if available_metrics:
            selected_metric_label = st.selectbox(
                "Metric:",
                options=[label for label, _ in available_metrics],
                index=0,
                key='telemetry_metric'
            )

            # Get actual metric name
            selected_metric = next(metric for label, metric in available_metrics if label == selected_metric_label)

            # Create comparison chart
            comp_chart = create_telemetry_comparison_chart(telemetry, lap1, lap2, selected_metric)
            st.plotly_chart(comp_chart, width='stretch')

        else:
            st.warning("No telemetry metrics available for comparison.")

else:
    st.warning("No telemetry data available.")

st.divider()

# =============================================================================
# SECTION 5: DETAILED LAP VIEW
# =============================================================================

st.header("Detailed Lap View")

if len(telemetry) > 0:
    available_laps_detail = sorted(telemetry['lap'].unique())

    selected_lap_detail = st.selectbox(
        "Select a lap for detailed analysis:",
        options=available_laps_detail,
        index=0,
        key='detail_lap_selector'
    )

    # Create multi-telemetry chart
    available_detail_metrics = []
    for metric in ['ath', 'brake_intensity', 'Steering_Angle', 'Speed']:
        if metric in telemetry.columns:
            available_detail_metrics.append(metric)

    if available_detail_metrics:
        detail_chart = create_multi_telemetry_chart(
            telemetry,
            selected_lap_detail,
            metrics=available_detail_metrics
        )
        st.plotly_chart(detail_chart, width='stretch')

        # Additional lap statistics
        st.subheader(f"Lap {selected_lap_detail} Statistics")

        lap_data = telemetry[telemetry['lap'] == selected_lap_detail]

        if len(lap_data) > 0:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if 'ath' in lap_data.columns:
                    avg_throttle = lap_data['ath'].mean()
                    st.metric("Avg Throttle", f"{avg_throttle:.1f}%")

            with col2:
                if 'brake_intensity' in lap_data.columns:
                    max_brake = lap_data['brake_intensity'].max()
                    st.metric("Max Brake", f"{max_brake:.1f} bar")

            with col3:
                if 'accx_can' in lap_data.columns:
                    max_decel_g = lap_data['accx_can'].min()
                    st.metric("Max Braking G", f"{abs(max_decel_g):.2f}g")

            with col4:
                if 'accy_can' in lap_data.columns:
                    max_lateral_g = lap_data['accy_can'].abs().max()
                    st.metric("Max Lateral G", f"{max_lateral_g:.2f}g")

    else:
        st.warning("No detailed metrics available for display.")

else:
    st.warning("No telemetry data available.")

# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>💡 Tip: Use the charts above to identify areas for improvement in braking, throttle application, and racing line.</small>
</div>
""", unsafe_allow_html=True)
