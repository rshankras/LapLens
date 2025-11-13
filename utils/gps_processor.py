"""
GPS data processing utilities for LapLens.
Handles GPS track visualization and analysis.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import List, Dict, Optional
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from config import config


def create_gps_track_visualization(
    telemetry: pd.DataFrame,
    laps: Optional[List[int]] = None,
    color_by: str = 'Speed',
    show_start_finish: bool = True
) -> go.Figure:
    """
    Create GPS track visualization with color-coded speed/brake data.

    Args:
        telemetry: Telemetry DataFrame with GPS coordinates
        laps: List of lap numbers to plot (None = all laps)
        color_by: Column name to use for color coding ('Speed', 'brake_intensity', etc.)
        show_start_finish: Whether to mark start/finish line

    Returns:
        Plotly figure object
    """
    # Check if GPS data exists
    if 'VBOX_Lat_Min' not in telemetry.columns or 'VBOX_Long_Minutes' not in telemetry.columns:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="GPS data not available in this dataset",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        return fig

    # Filter by laps if specified
    if laps is not None:
        telemetry = telemetry[telemetry['lap'].isin(laps)].copy()

    # Remove any rows with missing GPS data
    telemetry = telemetry.dropna(subset=['VBOX_Lat_Min', 'VBOX_Long_Minutes'])

    if len(telemetry) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No GPS data available for selected laps",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="gray")
        )
        return fig

    # Create figure
    fig = go.Figure()

    # If showing multiple laps, plot each separately
    if laps is not None and len(laps) > 1:
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']

        for idx, lap_num in enumerate(sorted(laps)):
            lap_data = telemetry[telemetry['lap'] == lap_num].copy()

            if len(lap_data) == 0:
                continue

            # Prepare color data
            if color_by in lap_data.columns:
                color_values = lap_data[color_by]
                color_label = color_by
            else:
                color_values = lap_data['Speed'] if 'Speed' in lap_data.columns else None
                color_label = 'Speed'

            # Create hover text
            hover_text = []
            for _, row in lap_data.iterrows():
                text = f"Lap {lap_num}<br>"
                text += f"Speed: {row['Speed']:.1f} km/h<br>" if 'Speed' in lap_data.columns else ""
                text += f"Distance: {row['Laptrigger_lapdist_dls']:.0f}m<br>" if 'Laptrigger_lapdist_dls' in lap_data.columns else ""
                hover_text.append(text)

            fig.add_trace(go.Scattergl(
                x=lap_data['VBOX_Long_Minutes'],
                y=lap_data['VBOX_Lat_Min'],
                mode='lines',
                name=f'Lap {lap_num}',
                line=dict(
                    width=3,
                    color=colors[idx % len(colors)]
                ),
                hovertext=hover_text,
                hoverinfo='text'
            ))

    else:
        # Single lap or all laps - use color gradient
        if color_by in telemetry.columns:
            color_values = telemetry[color_by]
            color_label = color_by
        else:
            color_values = telemetry['Speed'] if 'Speed' in telemetry.columns else range(len(telemetry))
            color_label = 'Speed (km/h)'

        # Create hover text
        hover_text = []
        for _, row in telemetry.iterrows():
            text = f"Lap {row['lap']:.0f}<br>" if 'lap' in telemetry.columns else ""
            text += f"Speed: {row['Speed']:.1f} km/h<br>" if 'Speed' in telemetry.columns else ""
            text += f"Distance: {row['Laptrigger_lapdist_dls']:.0f}m<br>" if 'Laptrigger_lapdist_dls' in telemetry.columns else ""
            if 'brake_intensity' in telemetry.columns:
                text += f"Brake: {row['brake_intensity']:.0f} bar<br>"
            hover_text.append(text)

        fig.add_trace(go.Scattergl(
            x=telemetry['VBOX_Long_Minutes'],
            y=telemetry['VBOX_Lat_Min'],
            mode='markers',
            marker=dict(
                size=3,
                color=color_values,
                colorscale='RdYlGn' if color_label == 'Speed' or color_label == 'Speed (km/h)' else 'Reds',
                showscale=True,
                colorbar=dict(
                    title=color_label,
                    thickness=15,
                    len=0.7
                ),
                line=dict(width=0)
            ),
            hovertext=hover_text,
            hoverinfo='text',
            showlegend=False
        ))

    # Mark start/finish if requested
    if show_start_finish and len(telemetry) > 0:
        start_point = telemetry.iloc[0]
        fig.add_trace(go.Scatter(
            x=[start_point['VBOX_Long_Minutes']],
            y=[start_point['VBOX_Lat_Min']],
            mode='markers+text',
            marker=dict(size=15, color='green', symbol='star'),
            text=['START'],
            textposition='top center',
            name='Start/Finish',
            showlegend=True
        ))

    # Update layout
    fig.update_layout(
        title="GPS Track Map",
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        height=700,
        hovermode='closest',
        plot_bgcolor='white',
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgray',
            scaleanchor="y",
            scaleratio=1
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='lightgray'
        ),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )

    return fig


def calculate_track_statistics(telemetry: pd.DataFrame) -> Dict:
    """
    Calculate GPS-based track statistics.

    Args:
        telemetry: Telemetry DataFrame with GPS data

    Returns:
        Dictionary with track statistics
    """
    if 'VBOX_Lat_Min' not in telemetry.columns or 'VBOX_Long_Minutes' not in telemetry.columns:
        return {}

    stats = {}

    # Track bounds
    stats['lat_min'] = telemetry['VBOX_Lat_Min'].min()
    stats['lat_max'] = telemetry['VBOX_Lat_Min'].max()
    stats['lon_min'] = telemetry['VBOX_Long_Minutes'].min()
    stats['lon_max'] = telemetry['VBOX_Long_Minutes'].max()

    # Track dimensions (approximate in meters)
    lat_range = stats['lat_max'] - stats['lat_min']
    lon_range = stats['lon_max'] - stats['lon_min']

    # Convert to meters (approximate: 1 degree latitude ≈ 111km, longitude varies by latitude)
    avg_lat = (stats['lat_min'] + stats['lat_max']) / 2
    stats['track_width_m'] = lon_range * 111000 * np.cos(np.radians(avg_lat))
    stats['track_height_m'] = lat_range * 111000

    return stats
