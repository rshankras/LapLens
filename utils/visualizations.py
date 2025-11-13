"""
Visualization utilities for creating charts and graphs.
Uses Plotly for interactive visualizations and Streamlit native charts where appropriate.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import List, Optional, Dict
from pathlib import Path
import sys

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))
from config import config


def create_lap_time_chart(lap_times_df: pd.DataFrame,
                          highlight_best: bool = True) -> go.Figure:
    """
    Create an interactive lap time chart.

    Args:
        lap_times_df: DataFrame with lap time data
        highlight_best: Whether to highlight the best lap

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    if 'lap_time' not in lap_times_df.columns or len(lap_times_df) == 0:
        return fig

    # Determine pace categories
    best_time = lap_times_df['lap_time'].min()
    threshold_medium = best_time * 1.02  # Within 2% of best
    threshold_slow = best_time * 1.05    # Within 5% of best

    colors = []
    for time in lap_times_df['lap_time']:
        if time == best_time:
            colors.append(config.COLORS['best_lap'])
        elif time <= threshold_medium:
            colors.append(config.COLORS['fast_lap'])
        elif time <= threshold_slow:
            colors.append(config.COLORS['medium_lap'])
        else:
            colors.append(config.COLORS['slow_lap'])

    # Main line trace
    fig.add_trace(go.Scatter(
        x=lap_times_df['lap'],
        y=lap_times_df['lap_time'],
        mode='lines+markers',
        name='Lap Time',
        line=dict(color=config.COLORS['speed'], width=2),
        marker=dict(
            size=8,
            color=colors,
            line=dict(width=1, color='white')
        ),
        hovertemplate='<b>Lap %{x}</b><br>Time: %{y:.3f}s<extra></extra>'
    ))

    # Highlight best lap
    if highlight_best:
        best_lap = lap_times_df.loc[lap_times_df['lap_time'].idxmin()]
        fig.add_annotation(
            x=best_lap['lap'],
            y=best_lap['lap_time'],
            text=f"Best: {best_lap['lap_time']:.3f}s",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=2,
            arrowcolor=config.COLORS['best_lap'],
            ax=0,
            ay=-40
        )

    # Layout
    fig.update_layout(
        title="Lap Time Progression",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        hovermode='x unified',
        height=config.CHART_HEIGHT,
        template='plotly_white'
    )

    return fig


def create_sector_delta_chart(sector_times_df: pd.DataFrame,
                              lap_num: int) -> go.Figure:
    """
    Create a sector delta bar chart for a specific lap.

    Args:
        sector_times_df: DataFrame with sector time data
        lap_num: Lap number to display

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    # Filter for specific lap
    lap_sectors = sector_times_df[sector_times_df['lap'] == lap_num].copy()

    if len(lap_sectors) == 0:
        return fig

    # Sort sectors
    if 'sector' in lap_sectors.columns:
        lap_sectors = lap_sectors.sort_values('sector')

    # Color bars based on delta (green = faster, red = slower)
    colors = [
        config.COLORS['fast_lap'] if delta <= 0 else config.COLORS['slow_lap']
        for delta in lap_sectors['delta_to_best']
    ]

    # Create bar chart
    fig.add_trace(go.Bar(
        x=lap_sectors['sector'],
        y=lap_sectors['delta_to_best'],
        marker=dict(color=colors),
        hovertemplate='<b>%{x}</b><br>Delta: %{y:.3f}s<br>Time: %{customdata:.3f}s<extra></extra>',
        customdata=lap_sectors['sector_time']
    ))

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Layout
    fig.update_layout(
        title=f"Sector Deltas - Lap {lap_num}",
        xaxis_title="Sector",
        yaxis_title="Delta to Best (seconds)",
        height=config.CHART_HEIGHT,
        template='plotly_white',
        showlegend=False
    )

    return fig


def create_speed_trace_chart(telemetry_df: pd.DataFrame,
                             laps: List[int],
                             show_zones: bool = True) -> go.Figure:
    """
    Create a speed vs distance chart for selected laps.

    Args:
        telemetry_df: DataFrame with telemetry data
        laps: List of lap numbers to display
        show_zones: Whether to shade braking/throttle zones

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    if 'Speed' not in telemetry_df.columns or 'Laptrigger_lapdist_dls' not in telemetry_df.columns:
        return fig

    # Plot each lap
    for lap_num in laps:
        lap_data = telemetry_df[telemetry_df['lap'] == lap_num].copy()

        if len(lap_data) == 0:
            continue

        lap_data = lap_data.sort_values('Laptrigger_lapdist_dls')

        fig.add_trace(go.Scatter(
            x=lap_data['Laptrigger_lapdist_dls'],
            y=lap_data['Speed'],
            mode='lines',
            name=f'Lap {lap_num}',
            line=dict(width=2),
            hovertemplate='Distance: %{x:.0f}m<br>Speed: %{y:.1f} km/h<extra></extra>'
        ))

    # Add braking zones (if showing zones and data available)
    if show_zones and len(laps) > 0:
        first_lap_data = telemetry_df[telemetry_df['lap'] == laps[0]].copy()

        if 'brake_intensity' in first_lap_data.columns:
            # Identify heavy braking zones
            heavy_brake = first_lap_data['brake_intensity'] > config.HEAVY_BRAKE_THRESHOLD

            if heavy_brake.any():
                # Add shaded regions for braking zones
                brake_zones = []
                in_zone = False
                start_dist = None

                for idx, is_braking in enumerate(heavy_brake):
                    dist = first_lap_data.iloc[idx]['Laptrigger_lapdist_dls']

                    if is_braking and not in_zone:
                        start_dist = dist
                        in_zone = True
                    elif not is_braking and in_zone:
                        brake_zones.append((start_dist, dist))
                        in_zone = False

                # Add shapes for brake zones
                for start, end in brake_zones:
                    fig.add_vrect(
                        x0=start, x1=end,
                        fillcolor="red", opacity=0.1,
                        layer="below", line_width=0,
                    )

    # Layout
    fig.update_layout(
        title="Speed vs Distance",
        xaxis_title="Distance from Start/Finish (meters)",
        yaxis_title="Speed (km/h)",
        hovermode='x unified',
        height=config.CHART_HEIGHT,
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_telemetry_comparison_chart(telemetry_df: pd.DataFrame,
                                      lap1: int,
                                      lap2: int,
                                      metric: str = 'ath') -> go.Figure:
    """
    Create a comparison chart for a specific telemetry metric between two laps.

    Args:
        telemetry_df: DataFrame with telemetry data
        lap1: First lap number
        lap2: Second lap number
        metric: Telemetry metric to compare (e.g., 'ath', 'pbrake_f', 'Steering_Angle')

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    metric_labels = {
        'ath': 'Throttle Position (%)',
        'pbrake_f': 'Front Brake Pressure (bar)',
        'pbrake_r': 'Rear Brake Pressure (bar)',
        'brake_intensity': 'Brake Intensity (bar)',
        'Steering_Angle': 'Steering Angle (degrees)',
        'accx_can': 'Longitudinal G-Force',
        'accy_can': 'Lateral G-Force'
    }

    if metric not in telemetry_df.columns:
        return fig

    # Get data for both laps
    for lap_num, color_idx in [(lap1, 0), (lap2, 1)]:
        lap_data = telemetry_df[telemetry_df['lap'] == lap_num].copy()

        if len(lap_data) == 0:
            continue

        if 'Laptrigger_lapdist_dls' in lap_data.columns:
            x_data = lap_data['Laptrigger_lapdist_dls']
            x_label = "Distance (m)"
        else:
            x_data = range(len(lap_data))
            x_label = "Data Point"

        fig.add_trace(go.Scatter(
            x=x_data,
            y=lap_data[metric],
            mode='lines',
            name=f'Lap {lap_num}',
            line=dict(width=2),
            hovertemplate=f'{x_label}: %{{x:.0f}}<br>{metric_labels.get(metric, metric)}: %{{y:.2f}}<extra></extra>'
        ))

    # Layout
    fig.update_layout(
        title=f"{metric_labels.get(metric, metric)} Comparison",
        xaxis_title=x_label if 'x_label' in locals() else "Distance (m)",
        yaxis_title=metric_labels.get(metric, metric),
        hovermode='x unified',
        height=config.CHART_HEIGHT,
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def create_multi_telemetry_chart(telemetry_df: pd.DataFrame,
                                 lap_num: int,
                                 metrics: List[str] = None) -> go.Figure:
    """
    Create a multi-panel chart showing multiple telemetry metrics for a lap.

    Args:
        telemetry_df: DataFrame with telemetry data
        lap_num: Lap number to display
        metrics: List of metrics to display (default: throttle, brake, steering)

    Returns:
        Plotly figure object with subplots
    """
    from plotly.subplots import make_subplots

    if metrics is None:
        metrics = ['ath', 'brake_intensity', 'Steering_Angle']

    # Filter available metrics
    available_metrics = [m for m in metrics if m in telemetry_df.columns]

    if not available_metrics:
        return go.Figure()

    # Create subplots
    fig = make_subplots(
        rows=len(available_metrics),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=[m.replace('_', ' ').title() for m in available_metrics]
    )

    # Get lap data
    lap_data = telemetry_df[telemetry_df['lap'] == lap_num].copy()

    if len(lap_data) == 0:
        return fig

    if 'Laptrigger_lapdist_dls' in lap_data.columns:
        x_data = lap_data['Laptrigger_lapdist_dls']
    else:
        x_data = range(len(lap_data))

    # Add traces for each metric
    color_map = {
        'ath': config.COLORS['throttle'],
        'brake_intensity': config.COLORS['brake'],
        'Steering_Angle': config.COLORS['steering'],
        'Speed': config.COLORS['speed']
    }

    for idx, metric in enumerate(available_metrics, start=1):
        fig.add_trace(
            go.Scatter(
                x=x_data,
                y=lap_data[metric],
                mode='lines',
                name=metric,
                line=dict(color=color_map.get(metric, '#333'), width=2),
                showlegend=False
            ),
            row=idx,
            col=1
        )

    # Update layout
    fig.update_xaxes(title_text="Distance (m)", row=len(available_metrics), col=1)
    fig.update_layout(
        height=config.CHART_HEIGHT * len(available_metrics) // 2,
        template='plotly_white',
        title_text=f"Telemetry Overview - Lap {lap_num}",
        hovermode='x unified'
    )

    return fig


def format_lap_time(seconds: float) -> str:
    """
    Format lap time in MM:SS.mmm format.

    Args:
        seconds: Lap time in seconds

    Returns:
        Formatted time string
    """
    if pd.isna(seconds):
        return "N/A"

    minutes = int(seconds // 60)
    secs = seconds % 60

    return f"{minutes}:{secs:06.3f}"


def get_lap_pace_category(lap_time: float, best_time: float) -> str:
    """
    Categorize lap pace relative to best lap.

    Args:
        lap_time: Lap time in seconds
        best_time: Best lap time in seconds

    Returns:
        Pace category string
    """
    if lap_time == best_time:
        return "Best"
    elif lap_time <= best_time * 1.02:
        return "Fast"
    elif lap_time <= best_time * 1.05:
        return "Medium"
    else:
        return "Slow"
