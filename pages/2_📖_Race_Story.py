"""
Race Story Page
Automatic narrative generation from telemetry data.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.story_generator import RaceStoryGenerator
from utils.visualizations import format_lap_time, create_lap_time_chart
from config import config

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title=f"{config.PAGE_TITLE} - Race Story",
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

vehicle_id = st.session_state.get('selected_vehicle', 'Unknown Vehicle')
track_name = st.session_state.get('track_name', 'Unknown Track')

# =============================================================================
# HEADER
# =============================================================================

st.title("📖 Race Story")
st.markdown(f"### 🏎️ Vehicle: **{vehicle_id}** | 🏁 Track: **{track_name}**")
st.markdown("*Automatic narrative generation from your telemetry data*")

st.divider()

# =============================================================================
# GENERATE STORY
# =============================================================================

# Create story generator
story_gen = RaceStoryGenerator(track_name=track_name)

# Generate complete story
with st.spinner("Generating race story..."):
    story = story_gen.generate_session_narrative(
        telemetry=telemetry,
        lap_times=lap_times,
        sector_times=sector_times,
        vehicle_id=vehicle_id
    )

# =============================================================================
# EXECUTIVE SUMMARY
# =============================================================================

st.header("📋 Executive Summary")

# Hero card
st.info(story['executive_summary'])

# Quick metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Consistency Score",
        f"{story['consistency_score']['score']}/10",
        story['consistency_score']['rating']
    )

with col2:
    st.metric(
        "Risk Index",
        f"{story['risk_index']['score']}/10",
        story['risk_index']['rating']
    )

with col3:
    if story['optimal_lap']['potential_gain'] is not None:
        st.metric(
            "Potential Gain",
            f"{story['optimal_lap']['potential_gain']:.3f}s",
            "vs. optimal lap"
        )

with col4:
    st.metric(
        "Performance Trend",
        story['performance_trajectory']['trend'].title(),
        f"{abs(story['performance_trajectory']['improvement_rate']):.3f}s/lap"
    )

st.divider()

# =============================================================================
# DETAILED NARRATIVE
# =============================================================================

st.header("📝 Detailed Analysis")

st.markdown(story['detailed_narrative'])

st.divider()

# =============================================================================
# BREAKTHROUGH MOMENT
# =============================================================================

if story['breakthrough_moment']:
    st.header("⚡ Key Moment")

    breakthrough = story['breakthrough_moment']

    # Highlight card
    if breakthrough['type'] == 'breakthrough':
        st.success(f"**Lap {breakthrough['lap']}**: {breakthrough['narrative']}")
    else:
        st.info(f"**Lap {breakthrough['lap']}**: {breakthrough['narrative']}")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Lap Number",
            breakthrough['lap']
        )

    with col2:
        if breakthrough['improvement'] > 0:
            st.metric(
                "Improvement",
                f"{breakthrough['improvement']:.3f}s",
                "Time gained"
            )

    st.markdown(f"**Impact:** {breakthrough['impact']}")

st.divider()

# =============================================================================
# PERFORMANCE TRAJECTORY
# =============================================================================

st.header("📈 Performance Trajectory")

col1, col2 = st.columns([2, 1])

with col1:
    # Show lap time chart with trend
    if len(lap_times) > 0:
        lap_chart = create_lap_time_chart(lap_times, highlight_best=True)
        st.plotly_chart(lap_chart, width='stretch')

with col2:
    st.markdown("### Trajectory Analysis")
    st.markdown(story['performance_trajectory']['narrative'])

    if story['performance_trajectory']['fastest_stint']:
        stint = story['performance_trajectory']['fastest_stint']
        st.info(
            f"**Fastest Stint:**\n\n"
            f"Laps {stint['start_lap']}-{stint['end_lap']}\n\n"
            f"Avg: {format_lap_time(stint['avg_time'])}"
        )

st.divider()

# =============================================================================
# SECTOR INSIGHTS
# =============================================================================

st.header("🎯 Sector Performance")

if len(story['sector_insights']) > 0:
    # Create columns for sector cards
    cols = st.columns(min(3, len(story['sector_insights'])))

    for idx, sector_insight in enumerate(story['sector_insights'][:6]):  # Show up to 6 sectors
        col_idx = idx % 3
        with cols[col_idx]:
            # Color-code by performance
            if sector_insight['performance'] == 'strength':
                card_type = "success"
                emoji = "✅"
            elif sector_insight['performance'] == 'weakness':
                card_type = "error"
                emoji = "⚠️"
            else:
                card_type = "info"
                emoji = "➖"

            # Create card
            with st.container():
                st.markdown(f"### {emoji} {sector_insight['sector']}")
                st.markdown(f"**Performance:** {sector_insight['performance'].title()}")
                st.markdown(f"**Best:** {format_lap_time(sector_insight['best_time'])}")
                st.markdown(f"**Range:** {sector_insight['range']:.3f}s")
                st.caption(sector_insight['narrative'])

else:
    st.info("No sector data available for analysis.")

st.divider()

# =============================================================================
# OPTIMAL LAP
# =============================================================================

st.header("🏆 Optimal Theoretical Lap")

optimal = story['optimal_lap']

col1, col2, col3 = st.columns(3)

with col1:
    if optimal['optimal_time'] is not None:
        st.metric(
            "Optimal Lap",
            format_lap_time(optimal['optimal_time']),
            "Best sectors combined"
        )

with col2:
    if optimal['actual_best'] is not None:
        st.metric(
            "Actual Best",
            format_lap_time(optimal['actual_best']),
            "Current best lap"
        )

with col3:
    if optimal['potential_gain'] is not None:
        st.metric(
            "Available Time",
            f"{optimal['potential_gain']:.3f}s",
            "Improvement potential"
        )

st.markdown(optimal['narrative'])

# Gap breakdown
if len(optimal.get('gap_breakdown', [])) > 0:
    st.markdown("### Time Distribution")

    gap_df = pd.DataFrame(optimal['gap_breakdown'])
    gap_df['gap'] = gap_df['gap'].apply(lambda x: f"{x:.3f}s")

    st.dataframe(
        gap_df.rename(columns={'sector': 'Sector', 'gap': 'Potential Gain'}),
        width='stretch',
        hide_index=True
    )

st.divider()

# =============================================================================
# TECHNICAL INSIGHTS
# =============================================================================

st.header("🔧 Technical Insights")

if len(story['technical_insights']) > 0:
    for insight in story['technical_insights']:
        st.markdown(f"- {insight}")
else:
    st.info("Limited technical data available.")

st.divider()

# =============================================================================
# RECOMMENDATIONS
# =============================================================================

st.header("💡 Recommendations")

if len(story['recommendations']) > 0:
    for idx, recommendation in enumerate(story['recommendations'], 1):
        st.markdown(f"**{idx}.** {recommendation}")
else:
    st.info("Performance is strong across all metrics.")

st.divider()

# =============================================================================
# DETAILED METRICS
# =============================================================================

with st.expander("📊 Detailed Metrics"):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Consistency Breakdown")
        st.json({
            "Score": f"{story['consistency_score']['score']}/10",
            "Rating": story['consistency_score']['rating'],
            "Standard Deviation": f"{story['consistency_score']['std_dev']}s",
            "Lap Time Range": f"{story['consistency_score']['range']}s",
            "Coefficient of Variation": f"{story['consistency_score']['coefficient_of_variation']}%"
        })

    with col2:
        st.markdown("### Risk Index Breakdown")
        st.json({
            "Score": f"{story['risk_index']['score']}/10",
            "Rating": story['risk_index']['rating'],
            "Components": story['risk_index']['components']
        })

# =============================================================================
# EXPORT OPTIONS
# =============================================================================

st.divider()

st.header("📥 Export Options")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📄 Download Story (Text)", width='stretch'):
        # Create text export
        export_text = f"""
{story['title']}
{'=' * 60}

EXECUTIVE SUMMARY
{story['executive_summary']}

DETAILED ANALYSIS
{story['detailed_narrative']}

KEY MOMENT
{story['breakthrough_moment']['narrative'] if story['breakthrough_moment'] else 'N/A'}

PERFORMANCE TRAJECTORY
{story['performance_trajectory']['narrative']}

OPTIMAL LAP
{optimal['narrative']}

RECOMMENDATIONS
{chr(10).join(f"{i}. {rec}" for i, rec in enumerate(story['recommendations'], 1))}

{'=' * 60}
Generated by LapLens - Stories Behind Every Lap
"""

        st.download_button(
            label="Download Text File",
            data=export_text,
            file_name=f"race_story_{vehicle_id}.txt",
            mime="text/plain"
        )

with col2:
    st.button("📊 Export Data (CSV)", width='stretch', disabled=True)
    st.caption("Coming in Phase 5")

with col3:
    st.button("📄 Generate PDF Report", width='stretch', disabled=True)
    st.caption("Coming in Phase 5")

# =============================================================================
# FOOTER
# =============================================================================

st.divider()

st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>
        Race story automatically generated from telemetry data.<br>
        Consistency score based on lap time variation. Risk index based on braking/throttle aggression.
    </small>
</div>
""", unsafe_allow_html=True)
