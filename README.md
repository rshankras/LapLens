# 🏁 LapLens - Stories Behind Every Lap

**Tagline:** Discover what truly happened between the start and finish line — Automatic storytelling from Toyota GR telemetry.

## Overview

LapLens is a Streamlit-based dashboard application that transforms Toyota GR Cup telemetry data into compelling visual insights and data-driven storytelling. Instead of just showing lap times, LapLens reveals the complete story of the race — key overtakes, strategy moments, braking consistency, and driver performance evolution.

## Features

### Phase 1 (MVP) - Completed ✅

- **📁 Dataset Management**
  - Load telemetry data from CSV files
  - Support for both long-format and wide-format data
  - Automatic detection and processing of Toyota GR Cup data
  - Vehicle selection and filtering

- **🏠 Home Page**
  - Dataset selection and loading
  - Vehicle/driver selection
  - Session summary with key metrics:
    - Total laps, best lap time, average lap time
    - Speed statistics (avg, max, top speed)
    - Consistency metrics
    - Lap times table with deltas

- **📊 Lap Analysis Page**
  - **Lap Time Progression**: Interactive chart showing lap times with pace categorization
  - **Sector Analysis**: Sector-by-sector breakdown with delta comparisons
  - **Speed Trace**: Speed vs distance visualization with braking zone overlays
  - **Telemetry Comparison**: Side-by-side comparison of throttle, brake, steering, and G-forces
  - **Detailed Lap View**: Multi-panel telemetry overview for individual laps

### Phase 2 (Future)

- 🗺️ **Track Map Page**: GPS-based track visualization with speed/G-force heatmaps
- ⚡ **Key Moments Page**: AI-powered event detection (heavy braking, pace changes, consistency issues)
- 📄 **PDF Export**: Download race story summaries
- 🤖 **AI Narratives**: Gemini-powered race storytelling

## Project Structure

```
LapLens/
├── streamlit_app.py          # Main app entry point (Home page)
├── pages/
│   └── 1_📊_Lap_Analysis.py  # Lap Analysis page
├── utils/
│   ├── data_loader.py         # Dataset loading & preprocessing
│   ├── telemetry_processor.py # Lap/sector calculations
│   └── visualizations.py      # Chart creation utilities
├── config/
│   └── config.py              # App settings & constants
├── datasets/                  # Telemetry data files
├── trackmaps/                 # Track map images
└── requirements.txt
```

## Installation

### Prerequisites

- Python 3.9 or higher
- pip

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

1. **Start the Streamlit app:**
   ```bash
   streamlit run streamlit_app.py
   ```

2. **Open your browser** to the URL shown (typically `http://localhost:8501`)

### Using LapLens

1. **Home Page:**
   - Select a dataset from the dropdown
   - Click "Load Dataset" to process the telemetry data
   - Select a vehicle/driver
   - View session summary and lap times

2. **Lap Analysis Page:**
   - Navigate using the sidebar
   - Explore lap time progression charts
   - Analyze sector performance
   - Compare speed traces across laps
   - View detailed telemetry for specific laps

## Data Format

LapLens supports Toyota GR Cup telemetry data with parameters including:
- Speed, throttle/brake positions
- G-forces (lateral & longitudinal)
- Steering angle, GPS coordinates
- Lap distance, gear, engine RPM

## Configuration

Edit `config/config.py` to customize track sector definitions, thresholds, and visualization settings.

## Credits

Built with Streamlit, Plotly, and Pandas.

## License

Apache 2.0