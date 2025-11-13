"""
LapLens - Stories Behind Every Lap
Main application entry point and Home page.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from utils.data_loader import TelemetryDataLoader
from utils.telemetry_processor import TelemetryProcessor
from utils.visualizations import format_lap_time
from config import config

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title=config.PAGE_TITLE,
    page_icon=config.PAGE_ICON,
    layout=config.LAYOUT,
    initial_sidebar_state=config.INITIAL_SIDEBAR_STATE
)

# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

if 'data_loader' not in st.session_state:
    st.session_state.data_loader = TelemetryDataLoader()

if 'selected_dataset' not in st.session_state:
    st.session_state.selected_dataset = None

if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None

if 'processed_data' not in st.session_state:
    st.session_state.processed_data = None

if 'selected_vehicle' not in st.session_state:
    st.session_state.selected_vehicle = None

# =============================================================================
# HEADER
# =============================================================================

st.title("🏁 LapLens")
st.markdown("### *Stories Behind Every Lap*")

st.markdown("""
Discover what truly happened between the start and finish line. LapLens transforms
Toyota GR Cup telemetry data into compelling insights, revealing key overtakes,
strategy moments, braking consistency, and driver performance evolution.
""")

st.divider()

# =============================================================================
# DATASET SELECTION
# =============================================================================

st.header("📁 Dataset Selection")

# List available datasets
datasets = st.session_state.data_loader.list_available_datasets()

if not datasets:
    st.error("No datasets found in the `datasets/` folder. Please add telemetry data files (CSV or ZIP).")
    st.stop()

# Dataset selector
dataset_options = {
    f"{ds['name']} ({ds['size'] / 1024 / 1024:.2f} MB)": ds['path']
    for ds in datasets
}

selected_dataset_name = st.selectbox(
    "Select a dataset to analyze:",
    options=list(dataset_options.keys()),
    index=0
)

selected_dataset_path = dataset_options[selected_dataset_name]

# Load dataset button
col1, col2 = st.columns([1, 3])

with col1:
    load_button = st.button("Load Dataset", type="primary", width='stretch')

with col2:
    if st.session_state.selected_dataset:
        st.success(f"Loaded: {Path(st.session_state.selected_dataset).stem}")

# =============================================================================
# DATA LOADING AND PROCESSING
# =============================================================================

if load_button or (st.session_state.selected_dataset == selected_dataset_path
                    and st.session_state.raw_data is not None):

    if load_button:
        with st.spinner("Loading dataset..."):
            try:
                # Load raw data
                raw_df = st.session_state.data_loader.load_dataset(selected_dataset_path)

                # Preprocess data
                preprocessed_df = st.session_state.data_loader.preprocess_dataset(raw_df)

                # Extract track name
                track_name = st.session_state.data_loader.extract_track_name(selected_dataset_path)

                # Store in session state
                st.session_state.selected_dataset = selected_dataset_path
                st.session_state.raw_data = preprocessed_df
                st.session_state.track_name = track_name

                st.success(f"Loaded {len(preprocessed_df):,} telemetry records from {track_name}!")

            except Exception as e:
                st.error(f"Error loading dataset: {str(e)}")
                st.stop()

    # =============================================================================
    # VEHICLE SELECTION
    # =============================================================================

    if st.session_state.raw_data is not None:
        st.divider()
        st.header("🏎️ Vehicle Selection")

        # Get unique vehicles
        vehicles = st.session_state.data_loader.get_unique_vehicles(st.session_state.raw_data)

        # Vehicle display names
        vehicle_display = {
            st.session_state.data_loader.get_vehicle_display_name(v): v
            for v in vehicles
        }

        selected_vehicle_display = st.selectbox(
            "Select a vehicle/driver:",
            options=list(vehicle_display.keys()),
            index=0
        )

        selected_vehicle = vehicle_display[selected_vehicle_display]
        st.session_state.selected_vehicle = selected_vehicle

        # Filter data by vehicle
        with st.spinner("Processing telemetry data..."):
            vehicle_data = st.session_state.data_loader.filter_by_vehicle(
                st.session_state.raw_data,
                selected_vehicle
            )

            # Process telemetry
            processor = TelemetryProcessor(track_name="default")  # Will improve track detection later
            processed = processor.process_full_session(vehicle_data)

            st.session_state.processed_data = processed

        # =============================================================================
        # SESSION SUMMARY
        # =============================================================================

        st.divider()
        st.header("📊 Session Summary")

        telemetry = processed['telemetry']
        lap_times = processed['lap_times']

        if len(lap_times) > 0:
            # Calculate summary statistics
            total_laps = len(lap_times)
            best_lap_time = lap_times['lap_time'].min()
            avg_lap_time = lap_times['lap_time'].mean()
            best_lap_num = lap_times.loc[lap_times['lap_time'].idxmin(), 'lap']

            # Display metrics in columns
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    label="Total Laps",
                    value=total_laps
                )

            with col2:
                st.metric(
                    label="Best Lap Time",
                    value=format_lap_time(best_lap_time)
                )

            with col3:
                st.metric(
                    label="Average Lap Time",
                    value=format_lap_time(avg_lap_time),
                    delta=format_lap_time(avg_lap_time - best_lap_time),
                    delta_color="inverse"
                )

            with col4:
                st.metric(
                    label="Best Lap",
                    value=f"Lap {int(best_lap_num)}"
                )

            # Additional metrics
            st.markdown("---")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if 'avg_speed' in lap_times.columns:
                    avg_speed = lap_times['avg_speed'].mean()
                    st.metric("Avg Speed", f"{avg_speed:.1f} km/h")

            with col2:
                if 'max_speed' in lap_times.columns:
                    max_speed = lap_times['max_speed'].max()
                    st.metric("Top Speed", f"{max_speed:.1f} km/h")

            with col3:
                # Consistency (std dev of lap times)
                consistency = lap_times['lap_time'].std()
                st.metric("Consistency (σ)", f"{consistency:.3f}s")

            with col4:
                # Total session time
                session_duration = lap_times['lap_time'].sum()
                st.metric("Total Session Time", format_lap_time(session_duration))

            # =============================================================================
            # LAP TIMES TABLE
            # =============================================================================

            st.divider()
            st.subheader("Lap Times")

            # Format lap times for display
            lap_display = lap_times[['lap', 'lap_time', 'delta_to_best', 'avg_speed', 'max_speed']].copy()
            lap_display['lap_time_formatted'] = lap_display['lap_time'].apply(format_lap_time)
            lap_display['delta_formatted'] = lap_display['delta_to_best'].apply(
                lambda x: f"+{x:.3f}s" if x > 0 else f"{x:.3f}s"
            )

            # Rename columns for display
            lap_display = lap_display.rename(columns={
                'lap': 'Lap',
                'lap_time_formatted': 'Lap Time',
                'delta_formatted': 'Delta',
                'avg_speed': 'Avg Speed (km/h)',
                'max_speed': 'Max Speed (km/h)'
            })

            # Display table
            st.dataframe(
                lap_display[['Lap', 'Lap Time', 'Delta', 'Avg Speed (km/h)', 'Max Speed (km/h)']],
                width='stretch',
                hide_index=True
            )

        else:
            st.warning("No lap data available. The dataset may not contain complete lap information.")

# =============================================================================
# NAVIGATION INSTRUCTIONS
# =============================================================================

if st.session_state.processed_data is not None:
    st.divider()
    st.info("📊 Navigate to **Lap Analysis** in the sidebar to explore detailed telemetry insights!")

# =============================================================================
# FOOTER
# =============================================================================

st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <small>
        LapLens - Automatic race storytelling from Toyota GR telemetry<br>
        Built with Streamlit
    </small>
</div>
""", unsafe_allow_html=True)
