"""
Telemetry processing and analysis utilities.
Calculates lap times, sector splits, and performance metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import sys

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))
from config import config


class TelemetryProcessor:
    """Processes telemetry data to extract lap and sector metrics."""

    def __init__(self, track_name: str = "default"):
        """
        Initialize the telemetry processor.

        Args:
            track_name: Name of the track for sector definitions
        """
        self.track_name = track_name
        self.sectors = config.SECTORS.get(track_name, config.SECTORS["default"])

    def detect_laps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect lap boundaries based on distance from start/finish line.

        Args:
            df: DataFrame with telemetry data

        Returns:
            DataFrame with lap numbers added/corrected
        """
        df = df.copy()

        if 'Laptrigger_lapdist_dls' not in df.columns:
            # If no distance column, use existing lap numbers if available
            if 'lap' not in df.columns:
                df['lap'] = 1
            return df

        # Detect lap crossings (distance resets)
        distance = df['Laptrigger_lapdist_dls']
        max_distance = distance.max()

        # Lap crossing occurs when distance drops significantly or wraps around
        lap_crossing = (
            (distance < config.LAP_DISTANCE_THRESHOLD) &
            (distance.shift(1) > max_distance - config.LAP_DISTANCE_THRESHOLD)
        )

        # Create lap number from cumulative crossings
        df['lap_detected'] = lap_crossing.cumsum() + 1

        # Use detected laps if original lap column doesn't exist or is unreliable
        if 'lap' not in df.columns or (df['lap'] == config.ERRONEOUS_LAP_NUMBER).any():
            df['lap'] = df['lap_detected']

        df = df.drop(columns=['lap_detected'])

        return df

    def calculate_lap_times(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate lap times for each lap.

        Args:
            df: DataFrame with telemetry data

        Returns:
            DataFrame with lap time statistics
        """
        if 'lap' not in df.columns:
            df = self.detect_laps(df)

        # Group by lap and calculate time range
        lap_stats = []

        for lap_num in sorted(df['lap'].unique()):
            lap_data = df[df['lap'] == lap_num].copy()

            if len(lap_data) == 0:
                continue

            # Calculate lap time from time_normalized
            if 'time_normalized' in lap_data.columns:
                start_time = lap_data['time_normalized'].iloc[0]
                end_time = lap_data['time_normalized'].iloc[-1]
                lap_time = (end_time - start_time).total_seconds()
            else:
                lap_time = None

            lap_stats.append({
                'lap': lap_num,
                'lap_time': lap_time,
                'records': len(lap_data),
                'avg_speed': lap_data['Speed'].mean() if 'Speed' in lap_data.columns else None,
                'max_speed': lap_data['Speed'].max() if 'Speed' in lap_data.columns else None,
            })

        return pd.DataFrame(lap_stats)

    def assign_sectors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Assign sector labels to each data point based on distance.

        Args:
            df: DataFrame with telemetry data

        Returns:
            DataFrame with sector column added
        """
        df = df.copy()

        if 'Laptrigger_lapdist_dls' not in df.columns or self.sectors is None:
            # If no distance or sector definitions, divide evenly
            df['sector'] = 'S1.a'  # Default sector
            return df

        # Assign sectors based on distance thresholds
        def get_sector(distance):
            for sector_name, (start, end) in self.sectors.items():
                if start <= distance < end:
                    return sector_name
            return list(self.sectors.keys())[-1]  # Last sector if beyond all

        df['sector'] = df['Laptrigger_lapdist_dls'].apply(get_sector)

        return df

    def calculate_sector_times(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate sector times for each lap.

        Args:
            df: DataFrame with telemetry data

        Returns:
            DataFrame with sector time statistics
        """
        if 'sector' not in df.columns:
            df = self.assign_sectors(df)

        if 'lap' not in df.columns:
            df = self.detect_laps(df)

        # Group by lap and sector
        sector_stats = []

        for lap_num in sorted(df['lap'].unique()):
            lap_data = df[df['lap'] == lap_num]

            for sector_name in self.sectors.keys() if self.sectors else ['S1.a']:
                sector_data = lap_data[lap_data['sector'] == sector_name]

                if len(sector_data) == 0:
                    continue

                # Calculate sector time
                if 'time_normalized' in sector_data.columns:
                    start_time = sector_data['time_normalized'].iloc[0]
                    end_time = sector_data['time_normalized'].iloc[-1]
                    sector_time = (end_time - start_time).total_seconds()
                else:
                    sector_time = None

                sector_stats.append({
                    'lap': lap_num,
                    'sector': sector_name,
                    'sector_time': sector_time,
                    'avg_speed': sector_data['Speed'].mean() if 'Speed' in sector_data.columns else None,
                })

        return pd.DataFrame(sector_stats)

    def calculate_braking_intensity(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate braking intensity metrics.

        Args:
            df: DataFrame with telemetry data

        Returns:
            DataFrame with braking metrics added
        """
        df = df.copy()

        # Average brake pressure (front + rear)
        if 'pbrake_f' in df.columns and 'pbrake_r' in df.columns:
            df['brake_intensity'] = (df['pbrake_f'] + df['pbrake_r']) / 2
        elif 'pbrake_f' in df.columns:
            df['brake_intensity'] = df['pbrake_f']
        elif 'pbrake_r' in df.columns:
            df['brake_intensity'] = df['pbrake_r']
        else:
            df['brake_intensity'] = 0

        # Classify braking zones
        df['braking_zone'] = pd.cut(
            df['brake_intensity'],
            bins=[0, config.BRAKE_THRESHOLD, config.HEAVY_BRAKE_THRESHOLD, float('inf')],
            labels=['None', 'Light', 'Heavy']
        )

        return df

    def calculate_throttle_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate throttle usage metrics.

        Args:
            df: DataFrame with telemetry data

        Returns:
            DataFrame with throttle metrics added
        """
        df = df.copy()

        if 'ath' not in df.columns:
            return df

        # Classify throttle zones
        df['throttle_zone'] = pd.cut(
            df['ath'],
            bins=[0, config.THROTTLE_PARTIAL_THRESHOLD, config.THROTTLE_FULL_THRESHOLD, 100],
            labels=['Off', 'Partial', 'Full']
        )

        return df

    def calculate_steering_smoothness(self, df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Calculate steering smoothness (rolling std dev of steering angle).

        Args:
            df: DataFrame with telemetry data
            window: Window size for rolling calculation

        Returns:
            DataFrame with steering smoothness metric added
        """
        df = df.copy()

        if 'Steering_Angle' not in df.columns:
            return df

        # Rolling standard deviation of steering angle
        df['steering_smoothness'] = df['Steering_Angle'].rolling(window=window).std()

        return df

    def calculate_g_force_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate G-force derived metrics.

        Args:
            df: DataFrame with telemetry data

        Returns:
            DataFrame with G-force metrics added
        """
        df = df.copy()

        # Combined G-force magnitude
        if 'accx_can' in df.columns and 'accy_can' in df.columns:
            df['g_force_combined'] = np.sqrt(df['accx_can']**2 + df['accy_can']**2)

        return df

    def calculate_lap_deltas(self, lap_times_df: pd.DataFrame,
                            reference_lap: Optional[int] = None) -> pd.DataFrame:
        """
        Calculate lap time deltas compared to a reference lap (default: best lap).

        Args:
            lap_times_df: DataFrame with lap time statistics
            reference_lap: Lap number to compare against (None = best lap)

        Returns:
            DataFrame with delta column added
        """
        df = lap_times_df.copy()

        if 'lap_time' not in df.columns:
            return df

        # Determine reference lap time
        if reference_lap is not None:
            ref_time = df[df['lap'] == reference_lap]['lap_time'].iloc[0]
        else:
            ref_time = df['lap_time'].min()  # Best lap

        # Calculate deltas
        df['delta_to_best'] = df['lap_time'] - ref_time

        return df

    def calculate_sector_deltas(self, sector_times_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate sector time deltas compared to best sector time.

        Args:
            sector_times_df: DataFrame with sector time statistics

        Returns:
            DataFrame with delta column added
        """
        df = sector_times_df.copy()

        if 'sector_time' not in df.columns:
            return df

        # Calculate best time per sector
        best_sectors = df.groupby('sector')['sector_time'].min().to_dict()

        # Calculate deltas
        df['delta_to_best'] = df.apply(
            lambda row: row['sector_time'] - best_sectors.get(row['sector'], 0),
            axis=1
        )

        return df

    def get_lap_summary(self, df: pd.DataFrame, lap_num: int) -> Dict:
        """
        Get comprehensive summary for a specific lap.

        Args:
            df: DataFrame with telemetry data
            lap_num: Lap number to summarize

        Returns:
            Dictionary with lap summary statistics
        """
        lap_data = df[df['lap'] == lap_num].copy()

        if len(lap_data) == 0:
            return {}

        summary = {
            'lap': lap_num,
            'records': len(lap_data),
        }

        # Time
        if 'time_normalized' in lap_data.columns:
            summary['start_time'] = lap_data['time_normalized'].iloc[0]
            summary['end_time'] = lap_data['time_normalized'].iloc[-1]
            summary['lap_time'] = (summary['end_time'] - summary['start_time']).total_seconds()

        # Speed metrics
        if 'Speed' in lap_data.columns:
            summary['avg_speed'] = lap_data['Speed'].mean()
            summary['max_speed'] = lap_data['Speed'].max()
            summary['min_speed'] = lap_data['Speed'].min()

        # Throttle metrics
        if 'ath' in lap_data.columns:
            summary['avg_throttle'] = lap_data['ath'].mean()
            summary['full_throttle_pct'] = (
                (lap_data['ath'] > config.THROTTLE_FULL_THRESHOLD).sum() / len(lap_data) * 100
            )

        # Braking metrics
        if 'brake_intensity' in lap_data.columns:
            summary['avg_brake'] = lap_data['brake_intensity'].mean()
            summary['max_brake'] = lap_data['brake_intensity'].max()

        # G-force metrics
        if 'accx_can' in lap_data.columns:
            summary['max_accel_g'] = lap_data['accx_can'].max()
            summary['max_decel_g'] = lap_data['accx_can'].min()

        if 'accy_can' in lap_data.columns:
            summary['max_lateral_g'] = lap_data['accy_can'].abs().max()

        return summary

    def process_full_session(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Process entire session and return all calculated metrics.

        Args:
            df: Raw telemetry DataFrame

        Returns:
            Dictionary containing processed DataFrames:
            - 'telemetry': Full telemetry with calculated fields
            - 'lap_times': Lap time statistics
            - 'sector_times': Sector time statistics
        """
        # Detect laps
        df = self.detect_laps(df)

        # Assign sectors
        df = self.assign_sectors(df)

        # Calculate metrics
        df = self.calculate_braking_intensity(df)
        df = self.calculate_throttle_metrics(df)
        df = self.calculate_steering_smoothness(df)
        df = self.calculate_g_force_metrics(df)

        # Calculate lap and sector times
        lap_times = self.calculate_lap_times(df)
        lap_times = self.calculate_lap_deltas(lap_times)

        sector_times = self.calculate_sector_times(df)
        sector_times = self.calculate_sector_deltas(sector_times)

        return {
            'telemetry': df,
            'lap_times': lap_times,
            'sector_times': sector_times
        }
