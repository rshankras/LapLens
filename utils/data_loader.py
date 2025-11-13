"""
Data loading and preprocessing utilities for LapLens.
Handles telemetry data from Toyota GR Cup datasets.
"""

import pandas as pd
import streamlit as st
import re
import zipfile
import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import sys

# Add parent directory to path for config import
sys.path.append(str(Path(__file__).parent.parent))
from config import config


class TelemetryDataLoader:
    """Loads and preprocesses telemetry data from CSV/ZIP files."""

    # Track name mapping
    TRACK_NAMES = {
        'barber': 'Barber Motorsports Park',
        'cota': 'Circuit of the Americas',
        'indianapolis': 'Indianapolis Motor Speedway',
        'road_america': 'Road America',
        'sebring': 'Sebring International Raceway',
        'sonoma': 'Sonoma Raceway',
        'vir': 'Virginia International Raceway'
    }

    def __init__(self, datasets_dir: str = "datasets"):
        """
        Initialize the data loader.

        Args:
            datasets_dir: Path to the directory containing telemetry datasets
        """
        self.datasets_dir = Path(datasets_dir)

    def list_available_datasets(self) -> List[Dict[str, str]]:
        """
        List all available datasets in the datasets directory.
        Searches both root directory and subdirectories for telemetry files.

        Returns:
            List of dictionaries with dataset metadata
        """
        datasets = []

        if not self.datasets_dir.exists():
            return datasets

        # Search for telemetry data files in subdirectories (recursive)
        for track_dir in self.datasets_dir.iterdir():
            if track_dir.is_dir():
                # Look for telemetry data files recursively (searches all nested folders)
                for file_path in track_dir.glob("**/*telemetry*.csv"):
                    datasets.append({
                        "name": f"{track_dir.name} - {file_path.stem}",
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "extension": file_path.suffix,
                        "track": track_dir.name
                    })

        # Also check root directory for direct CSV files
        for file_path in self.datasets_dir.glob("*.csv"):
            datasets.append({
                "name": file_path.stem,
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "extension": file_path.suffix,
                "track": "Unknown"
            })

        return sorted(datasets, key=lambda x: x["name"])

    @st.cache_data(ttl=config.CACHE_TTL)
    def load_dataset(_self, file_path: str) -> pd.DataFrame:
        """
        Load telemetry data from CSV or ZIP file.
        Handles both long format (telemetry_name/value) and wide format data.

        Args:
            file_path: Path to the dataset file

        Returns:
            DataFrame with raw telemetry data in wide format
        """
        file_path = Path(file_path)

        if file_path.suffix.lower() == ".csv":
            df = pd.read_csv(file_path)
        elif file_path.suffix.lower() == ".zip":
            # Extract first CSV from ZIP
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                csv_files = [f for f in zip_ref.namelist() if f.endswith('.csv')]
                if not csv_files:
                    raise ValueError(f"No CSV files found in {file_path}")
                with zip_ref.open(csv_files[0]) as csv_file:
                    df = pd.read_csv(csv_file)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")

        # Check if data is in long format (has telemetry_name and telemetry_value columns)
        if 'telemetry_name' in df.columns and 'telemetry_value' in df.columns:
            df = _self._pivot_long_to_wide(df)

        return df

    def _pivot_long_to_wide(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert long format telemetry data to wide format.

        Args:
            df: DataFrame in long format with telemetry_name and telemetry_value columns

        Returns:
            DataFrame in wide format with each telemetry metric as a column
        """
        # Key columns to preserve for grouping (timestamp-based grouping)
        key_cols = [
            'timestamp', 'meta_time', 'lap', 'vehicle_id', 'original_vehicle_id',
            'vehicle_number', 'outing', 'meta_session', 'meta_event', 'meta_source'
        ]

        # Find which key columns actually exist in the dataframe
        group_cols = [col for col in key_cols if col in df.columns]

        if not group_cols:
            # Fallback: use all columns except telemetry_name and telemetry_value
            group_cols = [col for col in df.columns
                         if col not in ['telemetry_name', 'telemetry_value', 'expire_at']]

        # Create a unique row identifier for grouping
        # Group by timestamp and vehicle to combine all telemetry readings at same time
        df['_row_id'] = df.groupby(group_cols).ngroup()

        # Pivot the data
        df_wide = df.pivot_table(
            index=['_row_id'] + group_cols,
            columns='telemetry_name',
            values='telemetry_value',
            aggfunc='first'  # Use first value if duplicates
        ).reset_index()

        # Remove the temporary row_id column
        df_wide = df_wide.drop(columns=['_row_id'])

        # Flatten column names
        df_wide.columns.name = None

        # Rename speed to Speed for consistency
        if 'speed' in df_wide.columns:
            df_wide = df_wide.rename(columns={'speed': 'Speed'})

        # If aps exists but not ath, use aps as throttle
        if 'aps' in df_wide.columns and 'ath' not in df_wide.columns:
            df_wide['ath'] = df_wide['aps']

        return df_wide

    def parse_vehicle_id(self, vehicle_id: str) -> Tuple[str, str]:
        """
        Parse vehicle ID into chassis number and car number.

        Args:
            vehicle_id: Vehicle ID in format GR86-chassis-carNumber

        Returns:
            Tuple of (chassis_number, car_number)
        """
        match = re.match(config.VEHICLE_ID_PATTERN, vehicle_id)
        if match:
            chassis, car_num = match.groups()
            return chassis, car_num
        return "Unknown", "000"

    def get_vehicle_display_name(self, vehicle_id: str) -> str:
        """
        Get human-readable vehicle display name.

        Args:
            vehicle_id: Vehicle ID string

        Returns:
            Formatted display name
        """
        chassis, car_num = self.parse_vehicle_id(vehicle_id)

        if car_num == config.UNASSIGNED_CAR_NUMBER:
            return f"Chassis {chassis} (Unassigned)"
        else:
            return f"Car #{car_num} (Chassis {chassis})"

    def clean_lap_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean erroneous lap numbers (e.g., lap #32768).
        Recalculate lap numbers based on distance from start/finish.

        Args:
            df: DataFrame with telemetry data

        Returns:
            DataFrame with cleaned lap numbers
        """
        df = df.copy()

        # Check if lap column exists
        if 'lap' not in df.columns:
            return df

        # Detect erroneous lap numbers
        erroneous_mask = df['lap'] == config.ERRONEOUS_LAP_NUMBER

        if erroneous_mask.any():
            # Recalculate laps based on Laptrigger_lapdist_dls
            if 'Laptrigger_lapdist_dls' in df.columns:
                # Detect lap crossings (distance resets or crosses threshold)
                df['lap_corrected'] = (
                    (df['Laptrigger_lapdist_dls'] < config.LAP_DISTANCE_THRESHOLD) &
                    (df['Laptrigger_lapdist_dls'].shift(1) >
                     df['Laptrigger_lapdist_dls'].max() - config.LAP_DISTANCE_THRESHOLD)
                ).cumsum() + 1

                # Replace erroneous laps with corrected ones
                df.loc[erroneous_mask, 'lap'] = df.loc[erroneous_mask, 'lap_corrected']
                df = df.drop(columns=['lap_corrected'])

        return df

    def normalize_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize timestamps, handling discrepancies between meta_time and ECU timestamp.

        Args:
            df: DataFrame with telemetry data

        Returns:
            DataFrame with normalized timestamp column
        """
        df = df.copy()

        # Prefer meta_time if available, fallback to timestamp
        if 'meta_time' in df.columns:
            df['time_normalized'] = pd.to_datetime(df['meta_time'], errors='coerce')
        elif 'timestamp' in df.columns:
            df['time_normalized'] = pd.to_datetime(df['timestamp'], errors='coerce')
        else:
            # No timestamp available, create sequential time
            df['time_normalized'] = pd.to_timedelta(df.index, unit='s')

        # Sort by normalized time
        df = df.sort_values('time_normalized').reset_index(drop=True)

        return df

    def filter_outliers(self, df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        """
        Filter outliers in specified columns using z-score method.

        Args:
            df: DataFrame with telemetry data
            columns: List of column names to check for outliers

        Returns:
            DataFrame with outliers removed
        """
        df = df.copy()

        for col in columns:
            if col in df.columns:
                mean = df[col].mean()
                std = df[col].std()

                # Mark outliers
                z_scores = ((df[col] - mean) / std).abs()
                outliers = z_scores > config.OUTLIER_STD_THRESHOLD

                # Replace outliers with NaN
                df.loc[outliers, col] = pd.NA

        return df

    def preprocess_dataset(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply all preprocessing steps to the dataset.

        Args:
            df: Raw telemetry DataFrame

        Returns:
            Preprocessed DataFrame
        """
        # Clean lap numbers
        df = self.clean_lap_numbers(df)

        # Normalize timestamps
        df = self.normalize_timestamps(df)

        # Filter outliers in GPS coordinates
        if 'VBOX_Long_Minutes' in df.columns and 'VBOX_Lat_Min' in df.columns:
            df = self.filter_outliers(df, ['VBOX_Long_Minutes', 'VBOX_Lat_Min'])

        return df

    def get_unique_tracks(self, df: pd.DataFrame) -> List[str]:
        """
        Extract unique track names from the dataset.

        Args:
            df: Telemetry DataFrame

        Returns:
            List of unique track names
        """
        if 'track' in df.columns:
            return sorted(df['track'].unique().tolist())
        return ["Unknown Track"]

    def get_unique_vehicles(self, df: pd.DataFrame) -> List[str]:
        """
        Extract unique vehicle IDs from the dataset.

        Args:
            df: Telemetry DataFrame

        Returns:
            List of unique vehicle IDs
        """
        # Common column names for vehicle ID
        vehicle_columns = ['vehicle_id', 'original_vehicle_id', 'car_id', 'VehicleID', 'Vehicle']

        for col in vehicle_columns:
            if col in df.columns:
                unique_vehicles = df[col].dropna().unique().tolist()
                return sorted([str(v) for v in unique_vehicles])

        return ["Unknown Vehicle"]

    def filter_by_vehicle(self, df: pd.DataFrame, vehicle_id: str) -> pd.DataFrame:
        """
        Filter dataset by specific vehicle.

        Args:
            df: Telemetry DataFrame
            vehicle_id: Vehicle ID to filter by

        Returns:
            Filtered DataFrame
        """
        vehicle_columns = ['vehicle_id', 'original_vehicle_id', 'car_id', 'VehicleID', 'Vehicle']

        for col in vehicle_columns:
            if col in df.columns:
                return df[df[col] == vehicle_id].copy()

        return df

    def get_session_summary(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Generate summary statistics for a session.

        Args:
            df: Telemetry DataFrame

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_records": len(df),
            "start_time": None,
            "end_time": None,
            "duration_seconds": None,
        }

        # Time-based stats
        if 'time_normalized' in df.columns:
            summary["start_time"] = df['time_normalized'].min()
            summary["end_time"] = df['time_normalized'].max()
            summary["duration_seconds"] = (
                (summary["end_time"] - summary["start_time"]).total_seconds()
            )

        # Lap-based stats
        if 'lap' in df.columns:
            summary["total_laps"] = df['lap'].max()
            summary["unique_laps"] = df['lap'].nunique()

        return summary

    def extract_track_name(self, file_path: str) -> str:
        """
        Extract track name from file path.

        Args:
            file_path: Path to the dataset file

        Returns:
            Human-readable track name
        """
        file_path_lower = file_path.lower()

        # Try to match known track names
        for key, name in self.TRACK_NAMES.items():
            if key in file_path_lower:
                return name

        # Fallback: extract from directory or filename
        path_obj = Path(file_path)

        # Check parent directory name
        parent_name = path_obj.parent.name.lower()
        for key, name in self.TRACK_NAMES.items():
            if key in parent_name:
                return name

        # Check filename
        file_name = path_obj.stem.lower()
        for key, name in self.TRACK_NAMES.items():
            if key in file_name:
                return name

        # Ultimate fallback
        return "Unknown Track"
