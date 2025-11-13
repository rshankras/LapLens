"""
Configuration settings for LapLens application.
Contains track definitions, thresholds, and visualization settings.
"""

# ============================================================================
# TRACK SECTOR DEFINITIONS
# ============================================================================
# Distance thresholds in meters for each sector
# Format: {track_name: {sector: (start_distance, end_distance)}}

SECTORS = {
    "Barber": {
        "S1.a": (0, 400),
        "S1.b": (400, 800),
        "S2.a": (800, 1200),
        "S2.b": (1200, 1600),
        "S3.a": (1600, 2000),
        "S3.b": (2000, 2400),
    },
    "COTA": {
        "S1.a": (0, 900),
        "S1.b": (900, 1800),
        "S2.a": (1800, 2700),
        "S2.b": (2700, 3600),
        "S3.a": (3600, 4500),
        "S3.b": (4500, 5513),  # COTA full lap ~5.513 km
    },
    # Generic fallback for unknown tracks (will be divided into equal sectors)
    "default": None
}

# ============================================================================
# TELEMETRY THRESHOLDS
# ============================================================================

# Braking thresholds (in bar)
BRAKE_THRESHOLD = 20  # Light braking
HEAVY_BRAKE_THRESHOLD = 50  # Heavy braking zone
MAX_BRAKE_PRESSURE = 100  # Maximum expected brake pressure

# Throttle thresholds (in %)
THROTTLE_FULL_THRESHOLD = 90  # Consider full throttle
THROTTLE_PARTIAL_THRESHOLD = 50  # Partial throttle
MIN_THROTTLE = 0
MAX_THROTTLE = 100

# Speed thresholds
MIN_SPEED = 0  # km/h
MAX_SPEED = 250  # km/h (reasonable max for GR Cup)

# G-force thresholds
ACCEL_G_THRESHOLD = 1.0  # Significant acceleration/braking
LATERAL_G_THRESHOLD = 1.5  # Significant lateral G-force (cornering)

# Lap detection
LAP_DISTANCE_THRESHOLD = 100  # meters - threshold to detect lap completion
ERRONEOUS_LAP_NUMBER = 32768  # Known erroneous lap number in telemetry

# ============================================================================
# VEHICLE IDENTIFICATION
# ============================================================================

# Vehicle ID format: GR86-{chassis}-{car_number}
UNASSIGNED_CAR_NUMBER = "000"  # Indicates car number not assigned yet
VEHICLE_ID_PATTERN = r"GR86-(\d+)-(\d+)"  # Regex to parse vehicle ID

# ============================================================================
# VISUALIZATION SETTINGS
# ============================================================================

# Color scheme
COLORS = {
    # Lap pace categories
    "fast_lap": "#00cc66",      # Green for fast laps
    "medium_lap": "#ffcc00",    # Yellow for medium laps
    "slow_lap": "#ff3333",      # Red for slow laps
    "best_lap": "#0066ff",      # Blue for best lap

    # Telemetry traces
    "speed": "#1f77b4",         # Blue
    "throttle": "#2ca02c",      # Green
    "brake": "#d62728",         # Red
    "steering": "#ff7f0e",      # Orange
    "gear": "#9467bd",          # Purple
    "rpm": "#8c564b",           # Brown

    # G-forces
    "accel_g": "#e377c2",       # Pink
    "lateral_g": "#7f7f7f",     # Gray

    # Zones
    "brake_zone": "rgba(255, 0, 0, 0.2)",      # Light red
    "throttle_zone": "rgba(0, 255, 0, 0.2)",   # Light green
}

# Chart dimensions
CHART_HEIGHT = 400
CHART_WIDTH = None  # Auto-width based on container

# Map visualization
MAP_RESOLUTION = (1200, 800)  # Default track map resolution
MAP_ALPHA = 0.7  # Transparency for overlays

# ============================================================================
# DATA PROCESSING
# ============================================================================

# Smoothing parameters
SMOOTHING_WINDOW = 5  # Rolling average window for smoothing telemetry

# Missing data handling
MAX_GAP_INTERPOLATION = 10  # Max data points to interpolate across

# Outlier detection
OUTLIER_STD_THRESHOLD = 3  # Standard deviations for outlier detection

# ============================================================================
# APP SETTINGS
# ============================================================================

# Page configuration
PAGE_TITLE = "LapLens"
PAGE_ICON = "🏁"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"

# Cache settings
CACHE_TTL = 3600  # Time to live for cached data (1 hour)

# Dataset file extensions
SUPPORTED_EXTENSIONS = [".csv", ".zip"]

# Timezone
DEFAULT_TIMEZONE = "America/New_York"  # For timestamp processing
